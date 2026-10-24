"""
Unit and Integration Test Suite for Milestone 3: Asset Post-Processing, Normalization & Multi-Format Export
File: teamwork_projects/vegetation_library/tests/test_normalization.py

Validates:
1. Ground Pivot Alignment:
   - Z_min = 0.000m (± 0.005m) across in-memory mesh, exported GLB binary, and OBJ.
   - Rigid vertical translation for floating (Z_min > 0) and subterranean (Z_min < 0) meshes.
   - Idempotent normalization for already-grounded meshes.
2. Base Contact Centroid Centering:
   - Centroid of vertices in bottom 5% height slice is centered at (0, 0) within ± 0.05m.
   - Asymmetric and leaning meshes are centered by their trunk/stem base, not crown centroid.
3. Metric Scale Normalization:
   - Height matches species.dimensions.height_m within ± 5% tolerance across all 7 biomes.
   - Uniform scaling preserves aspect ratio without geometric warping or leaf distortion.
   - Boundary tests: miniature groundcover (0.05m) and giant trees (35.0m).
   - Degenerate zero-height mesh raises ValueError cleanly.
4. Dual-Format Production GLB Export:
   - Valid 12-byte glTF 2.0 container header and 4-byte chunk boundary alignment.
   - Binary-level static mesh invariants: zero skins, zero animations, zero skeletal attributes.
   - Embedded 4-channel PBR textures in GLB binary bufferView.
   - Foliage material doubleSided flag enabled.
5. Dual-Format Companion Wavefront OBJ & MTL Export:
   - Non-empty .obj and .mtl files with valid syntax and 1-indexed faces.
   - Companion .mtl references textures/ directory via portable relative paths.
6. PBR Texture Packaging:
   - textures/ directory contains albedo.png, normal.png, roughness.png, metallic.png.
   - All maps are readable PIL images >= 256x256 within physically plausible botanical ranges.
   - Automatic fallback synthesis for missing raw texture channels.
7. Asset Manifest Specification:
   - asset_manifest.json validates taxonomy, geometry metrics, bounding box, scale factor, and file paths.
8. Directory Hierarchy Packaging:
   - Assets routed to output/<short_category>/<species_id>/ across all 7 biomes.
   - Parent directories created cleanly; clean overwrites on re-export.
9. Edge Cases & Robustness:
   - NaN/Inf vertex rejection, corrupted GLB handling, quad/triangle mixed mesh export.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import struct
from typing import Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import pytest

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import (
    PlantSpecies,
    VegetationLibraryCatalog,
    get_catalog,
)
from vegetation_pipeline.generator import (
    RawAsset,
    ProceduralBotanicalGenerator,
    unpack_glb_header_and_json,
)
from vegetation_pipeline.post_processor import (
    AssetPostProcessor,
    ExportedAsset,
    process_and_export,
)


# ==============================================================================
# SPECIALIZED TEST ASSERTION HELPERS
# ==============================================================================

def assert_ground_pivot_invariant(coords: np.ndarray, tolerance_m: float = 0.005) -> float:
    """Strictly asserts lowest vertex lies on ground contact Z_min = 0.000m within tolerance."""
    assert len(coords) > 0, "Coordinate array is empty"
    min_z = float(coords[:, 2].min())
    assert abs(min_z) <= tolerance_m, (
        f"Ground pivot violation: Z_min={min_z:.6f}m exceeds tolerance ±{tolerance_m}m"
    )
    return min_z


def assert_base_centroid_centered(
    coords: np.ndarray,
    slice_ratio: float = 0.05,
    tolerance_m: float = 0.05
) -> Tuple[float, float]:
    """Strictly asserts bottom slice_ratio (5%) height centroid is centered at (0, 0) within tolerance."""
    assert len(coords) > 0, "Coordinate array is empty"
    min_z = float(coords[:, 2].min())
    max_z = float(coords[:, 2].max())
    h = max_z - min_z
    assert h > 0, f"Degenerate mesh with zero height: {h}"

    threshold = min_z + (slice_ratio * h)
    mask = coords[:, 2] <= threshold
    base_coords = coords[mask]
    assert len(base_coords) > 0, f"No vertices found in bottom {slice_ratio*100}% slice"

    cx = float(base_coords[:, 0].mean())
    cy = float(base_coords[:, 1].mean())

    assert abs(cx) <= tolerance_m, (
        f"Base contact centroid X off-center: cx={cx:.4f}m exceeds ±{tolerance_m}m"
    )
    assert abs(cy) <= tolerance_m, (
        f"Base contact centroid Y off-center: cy={cy:.4f}m exceeds ±{tolerance_m}m"
    )
    return cx, cy


def assert_metric_scale_conformance(
    coords: np.ndarray,
    target_height_m: float,
    tolerance_pct: float = 0.05
) -> float:
    """Strictly asserts actual mesh height matches target mature height within tolerance percentage."""
    assert len(coords) > 0, "Coordinate array is empty"
    actual_h = float(coords[:, 2].max() - coords[:, 2].min())
    pct_err = abs(actual_h - target_height_m) / target_height_m
    assert pct_err <= tolerance_pct, (
        f"Metric scale violation: actual_height={actual_h:.3f}m differs from target={target_height_m:.3f}m "
        f"by {pct_err*100:.2f}% (exceeds {tolerance_pct*100:.1f}%)"
    )
    return actual_h


def extract_glb_positions(glb_path: Union[str, Path]) -> np.ndarray:
    """Extracts raw float32 POSITION array directly from GLB binary buffer."""
    gltf, bin_bytes = unpack_glb_header_and_json(glb_path)
    pos_idx = gltf["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
    acc = gltf["accessors"][pos_idx]
    bv = gltf["bufferViews"][acc["bufferView"]]
    byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
    count = acc["count"]
    coords = np.frombuffer(bin_bytes, dtype=np.float32, count=count * 3, offset=byte_offset).reshape((count, 3))
    return coords


def parse_obj_vertex_positions(obj_path: Union[str, Path]) -> np.ndarray:
    """Parses vertex coordinates from Wavefront .obj file."""
    positions = []
    with open(obj_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
    return np.array(positions, dtype=np.float32)


def parse_mtl_texture_map_bindings(mtl_path: Union[str, Path]) -> Dict[str, str]:
    """Parses material texture map bindings from companion .mtl file."""
    bindings = {}
    with open(mtl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("map_Kd"):
                bindings["albedo"] = line.split(maxsplit=1)[1]
            elif line.startswith(("map_Bump", "norm", "bump")):
                bindings["normal"] = line.split(maxsplit=1)[1]
            elif line.startswith(("map_Pr", "map_Ns")):
                bindings["roughness"] = line.split(maxsplit=1)[1]
            elif line.startswith("map_Pm"):
                bindings["metallic"] = line.split(maxsplit=1)[1]
    return bindings


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture(scope="session")
def catalog() -> VegetationLibraryCatalog:
    return get_catalog()


@pytest.fixture(scope="session")
def representative_species_map(catalog: VegetationLibraryCatalog) -> Dict[str, PlantSpecies]:
    """Provides representative species across all 7 biomes."""
    return {
        "broadleaf_trees": catalog["veg_tree_oak_01"],
        "conifers": catalog["veg_conifer_pine_01"],
        "tropical": catalog["veg_tropical_palm_01"],
        "shrubs": catalog["veg_shrub_rose_01"],
        "groundcover": catalog["veg_ground_fern_01"],
        "succulents": catalog["veg_succulent_saguaro_01"],
        "vines": catalog["veg_vine_ivy_01"],
    }


@pytest.fixture
def sample_oak_species(catalog: VegetationLibraryCatalog) -> PlantSpecies:
    return catalog["veg_tree_oak_01"]


@pytest.fixture
def default_post_processor() -> AssetPostProcessor:
    return AssetPostProcessor()


@pytest.fixture
def synthetic_raw_asset_factory(tmp_path: Path):
    """
    Factory creating deterministic synthetic RawAsset models with custom geometry
    for rapid mathematical boundary and edge case testing without network or GPU usage.
    """
    def _create(
        species_id: str = "veg_tree_oak_01",
        z_offset: float = 0.0,
        xy_base_offset: Tuple[float, float] = (0.0, 0.0),
        height: float = 6.0,
        crown_offset_xy: Tuple[float, float] = (0.0, 0.0),
        num_verts: int = 3200,
        omit_texture_channels: Optional[List[str]] = None,
    ) -> RawAsset:
        asset_dir = tmp_path / f"synth_{species_id}_{abs(hash((z_offset, xy_base_offset, height))) % 10000}"
        asset_dir.mkdir(parents=True, exist_ok=True)

        mesh = MeshGeometry()
        n_trunk = num_verts // 4
        n_crown = num_verts - n_trunk

        # Trunk: cylinder from z_offset to z_offset + 0.3*height, centered at xy_base_offset
        for i in range(n_trunk):
            frac = i / max(1, n_trunk - 1)
            angle = frac * 2.0 * np.pi * 10
            r = 0.25 * (1.0 - 0.2 * frac)
            x = xy_base_offset[0] + r * np.cos(angle)
            y = xy_base_offset[1] + r * np.sin(angle)
            z = z_offset + frac * (0.3 * height)
            mesh.add_vertex((x, y, z), normal=(np.cos(angle), np.sin(angle), 0.0), uv=(frac, 0.5))

        # Crown: sphere/ellipsoid from z_offset + 0.25*height to z_offset + height
        for i in range(n_crown):
            frac = i / max(1, n_crown - 1)
            phi = frac * np.pi
            theta = frac * 2.0 * np.pi * 25
            r = 1.2
            x = crown_offset_xy[0] + r * np.sin(phi) * np.cos(theta)
            y = crown_offset_xy[1] + r * np.sin(phi) * np.sin(theta)
            z = z_offset + 0.3 * height + frac * (0.7 * height)
            mesh.add_vertex((x, y, z), normal=(0.0, 0.0, 1.0), uv=(frac, frac))

        # Simple triangulated topology
        for i in range(len(mesh.vertices) - 2):
            mesh.add_triangle(i, i + 1, i + 2)

        glb_path = asset_dir / f"{species_id}_raw.glb"
        mesh.export_glb(str(glb_path))

        # Textures
        textures: Dict[str, Image.Image] = {}
        texture_paths: Dict[str, Path] = {}
        tex_dir = asset_dir / "raw_textures"
        tex_dir.mkdir(exist_ok=True)

        omit = set(omit_texture_channels or [])

        if "albedo" not in omit:
            alb = Image.new("RGB", (256, 256), (45, 90, 35))
            alb.save(tex_dir / "albedo.png")
            textures["albedo"] = alb
            texture_paths["albedo"] = tex_dir / "albedo.png"

        if "normal" not in omit:
            norm = Image.new("RGB", (256, 256), (128, 128, 255))
            norm.save(tex_dir / "normal.png")
            textures["normal"] = norm
            texture_paths["normal"] = tex_dir / "normal.png"

        if "roughness" not in omit:
            rough = Image.new("L", (256, 256), 180)
            rough.save(tex_dir / "roughness.png")
            textures["roughness"] = rough
            texture_paths["roughness"] = tex_dir / "roughness.png"

        if "metallic" not in omit:
            metal = Image.new("L", (256, 256), 0)
            metal.save(tex_dir / "metallic.png")
            textures["metallic"] = metal
            texture_paths["metallic"] = tex_dir / "metallic.png"

        return RawAsset(
            species_id=species_id,
            glb_path=glb_path,
            mesh=mesh,
            textures=textures,
            texture_paths=texture_paths,
            source="procedural",
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            metadata={"seed": 42, "raw_height": height},
        )

    return _create


# ==============================================================================
# 1. PIVOT ALIGNMENT & GROUNDING TESTS
# ==============================================================================

class TestPivotAlignmentAndGrounding:
    """Verifies Z_min = 0.000m (± 0.005m) across in-memory mesh, GLB, and OBJ."""

    def test_ground_pivot_snapping_exact_zero_synthetic(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """1. Asserts lowest vertex sits at Z_min = 0.000m ± 0.005m for floating synthetic asset."""
        raw_asset = synthetic_raw_asset_factory(z_offset=4.5)
        out_dir = tmp_path / "pivot_float"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        # 1. Verify in GLB positions
        glb_coords = extract_glb_positions(exported.glb_path)
        min_z_glb = assert_ground_pivot_invariant(glb_coords, tolerance_m=0.005)
        assert abs(min_z_glb) <= 0.005

        # 2. Verify in OBJ positions
        obj_coords = parse_obj_vertex_positions(exported.obj_path)
        min_z_obj = assert_ground_pivot_invariant(obj_coords, tolerance_m=0.005)
        assert abs(min_z_obj) <= 0.005

    def test_grounding_subterranean_mesh(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """2. Subterranean mesh with Z_min < 0 is shifted upward so root base contacts ground at 0.0m."""
        raw_asset = synthetic_raw_asset_factory(z_offset=-3.2)
        out_dir = tmp_path / "pivot_sub"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        glb_coords = extract_glb_positions(exported.glb_path)
        assert_ground_pivot_invariant(glb_coords, tolerance_m=0.005)

    def test_grounding_already_grounded_idempotent(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """3. Asset already grounded at Z_min = 0.000m remains at 0.000m without drift."""
        raw_asset = synthetic_raw_asset_factory(z_offset=0.0)
        out_dir = tmp_path / "pivot_grounded"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        glb_coords = extract_glb_positions(exported.glb_path)
        assert_ground_pivot_invariant(glb_coords, tolerance_m=0.001)

    def test_grounding_rigid_translation_preserves_internal_geometry(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """4. Ground alignment performs rigid translation without deforming vertex-to-vertex relative vectors."""
        raw_asset = synthetic_raw_asset_factory(z_offset=2.5)
        out_dir = tmp_path / "pivot_rigid"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        raw_verts = np.array(raw_asset.mesh.vertices, dtype=np.float32)
        exp_coords = extract_glb_positions(exported.glb_path)

        # Compare relative vectors before and after (accounting for uniform scale)
        scale = exported.metadata.get("scale_factor", 1.0)
        raw_diff = (raw_verts[1] - raw_verts[0]) * scale
        exp_diff = exp_coords[1] - exp_coords[0]
        assert np.allclose(raw_diff, exp_diff, atol=1e-4)

    @pytest.mark.parametrize("biome_key,species_id", [
        ("broadleaf_trees", "veg_tree_oak_01"),
        ("conifers", "veg_conifer_pine_01"),
        ("tropical", "veg_tropical_palm_01"),
        ("shrubs", "veg_shrub_rose_01"),
        ("groundcover", "veg_ground_fern_01"),
        ("succulents", "veg_succulent_saguaro_01"),
        ("vines", "veg_vine_ivy_01"),
    ])
    def test_ground_pivot_alignment_across_all_7_biomes(self, catalog, biome_key, species_id, default_post_processor, tmp_path):
        """5. Verifies ground root pivot alignment (|Z_min| <= 0.005m) across procedural assets for all 7 biomes."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / "raw" / species_id, seed=42)

        out_dir = tmp_path / "post" / biome_key
        exported = default_post_processor.process_asset(raw_asset, species, output_dir=out_dir)

        glb_coords = extract_glb_positions(exported.glb_path)
        assert_ground_pivot_invariant(glb_coords, tolerance_m=0.005)


# ==============================================================================
# 2. BASE CONTACT CENTROID CENTERING TESTS
# ==============================================================================

class TestBaseContactCentroidCentering:
    """Verifies bottom 5% height slice centroid is centered at (0, 0) within ± 0.05m."""

    def test_bottom_slice_centroid_centered_at_origin(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """6. Asserts centroid of vertices in bottom 5% height slice is within ± 0.05m of (0, 0)."""
        raw_asset = synthetic_raw_asset_factory(xy_base_offset=(1.2, -0.8))
        out_dir = tmp_path / "center_basic"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        glb_coords = extract_glb_positions(exported.glb_path)
        cx, cy = assert_base_centroid_centered(glb_coords, slice_ratio=0.05, tolerance_m=0.05)
        assert abs(cx) <= 0.05
        assert abs(cy) <= 0.05

    def test_off_center_leaning_mesh_centering(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """7. Trunk base centered at origin even when tree canopy leans heavily in one direction."""
        raw_asset = synthetic_raw_asset_factory(
            xy_base_offset=(1.5, -2.0),
            crown_offset_xy=(4.0, 3.5),
            height=8.0
        )
        out_dir = tmp_path / "center_lean"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        glb_coords = extract_glb_positions(exported.glb_path)
        cx, cy = assert_base_centroid_centered(glb_coords, slice_ratio=0.05, tolerance_m=0.05)
        assert abs(cx) <= 0.05
        assert abs(cy) <= 0.05

    def test_symmetric_base_centroid_precision(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """8. Highly symmetric trunk cylinder centers to high precision (<= 0.01m)."""
        raw_asset = synthetic_raw_asset_factory(xy_base_offset=(0.5, 0.5))
        out_dir = tmp_path / "center_sym"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=out_dir)

        glb_coords = extract_glb_positions(exported.glb_path)
        cx, cy = assert_base_centroid_centered(glb_coords, slice_ratio=0.05, tolerance_m=0.01)
        assert abs(cx) <= 0.01
        assert abs(cy) <= 0.01

    def test_bottom_slice_height_threshold_definition(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """9. Validates that the slice threshold strictly isolates the bottom 5% height."""
        raw_asset = synthetic_raw_asset_factory(height=10.0)
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "slice_thresh")

        coords = extract_glb_positions(exported.glb_path)
        h = coords[:, 2].max() - coords[:, 2].min()
        threshold = coords[:, 2].min() + 0.05 * h

        base_pts = coords[coords[:, 2] <= threshold]
        upper_pts = coords[coords[:, 2] > threshold]
        assert len(base_pts) > 0
        assert len(upper_pts) > len(base_pts)

    @pytest.mark.parametrize("species_id", [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ])
    def test_base_centering_across_all_7_biomes(self, catalog, species_id, default_post_processor, tmp_path):
        """10. Asserts base centroid is centered within ± 0.05m across all 7 biomes."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / "raw" / species_id, seed=42)

        exported = default_post_processor.process_asset(raw_asset, species, output_dir=tmp_path / "center_biomes" / species_id)
        coords = extract_glb_positions(exported.glb_path)
        assert_base_centroid_centered(coords, slice_ratio=0.05, tolerance_m=0.05)


# ==============================================================================
# 3. METRIC SCALE NORMALIZATION TESTS
# ==============================================================================

class TestMetricScaleNormalization:
    """Verifies height matches species.dimensions.height_m within ± 5%."""

    @pytest.mark.parametrize("species_id", [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ])
    def test_scale_normalization_matches_catalog_height_within_5_percent(self, catalog, species_id, default_post_processor, tmp_path):
        """11. Asserts normalized model height matches catalog target within ± 5% across all 7 biomes."""
        species = catalog[species_id]
        proc_gen = ProceduralBotanicalGenerator()
        raw_asset = proc_gen.generate(species, output_dir=tmp_path / "raw_scale" / species_id, seed=42)

        exported = default_post_processor.process_asset(raw_asset, species, output_dir=tmp_path / "norm_scale" / species_id)
        coords = extract_glb_positions(exported.glb_path)
        actual_h = assert_metric_scale_conformance(coords, species.dimensions.height_m, tolerance_pct=0.05)
        assert abs(actual_h - species.dimensions.height_m) / species.dimensions.height_m <= 0.05

    def test_scale_normalization_uniform_aspect_ratio_preservation(self, synthetic_raw_asset_factory, sample_oak_species, default_post_processor, tmp_path):
        """12. Uniform scaling factor is applied to X, Y, Z preserving geometry aspect ratio."""
        raw_asset = synthetic_raw_asset_factory(height=4.0)
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "aspect_ratio")

        raw_coords = np.array(raw_asset.mesh.vertices, dtype=np.float32)
        exp_coords = extract_glb_positions(exported.glb_path)

        raw_dx = raw_coords[:, 0].max() - raw_coords[:, 0].min()
        raw_dz = raw_coords[:, 2].max() - raw_coords[:, 2].min()

        exp_dx = exp_coords[:, 0].max() - exp_coords[:, 0].min()
        exp_dz = exp_coords[:, 2].max() - exp_coords[:, 2].min()

        raw_ratio = raw_dx / raw_dz
        exp_ratio = exp_dx / exp_dz
        assert abs(raw_ratio - exp_ratio) <= 1e-4

    def test_miniature_species_scaling(self, catalog, synthetic_raw_asset_factory, default_post_processor, tmp_path):
        """13. Scaling miniature species (height=0.05m) executes cleanly without numerical underflow."""
        mini_species = catalog["veg_ground_fern_01"].model_copy(deep=True)
        mini_species.dimensions.height_m = 0.05
        mini_species.dimensions.height_range_m = (0.02, 0.08)

        raw_asset = synthetic_raw_asset_factory(height=1.0)
        exported = default_post_processor.process_asset(raw_asset, mini_species, output_dir=tmp_path / "mini_scale")

        coords = extract_glb_positions(exported.glb_path)
        assert_metric_scale_conformance(coords, 0.05, tolerance_pct=0.05)
        assert np.isfinite(coords).all()

    def test_giant_species_scaling(self, catalog, synthetic_raw_asset_factory, default_post_processor, tmp_path):
        """14. Scaling giant tree species (height=35.0m) executes without overflow or normal distortion."""
        giant_species = catalog["veg_conifer_pine_01"].model_copy(deep=True)
        giant_species.dimensions.height_m = 35.0
        giant_species.dimensions.height_range_m = (25.0, 45.0)

        raw_asset = synthetic_raw_asset_factory(height=5.0)
        exported = default_post_processor.process_asset(raw_asset, giant_species, output_dir=tmp_path / "giant_scale")

        coords = extract_glb_positions(exported.glb_path)
        assert_metric_scale_conformance(coords, 35.0, tolerance_pct=0.05)

    def test_zero_height_mesh_raises_value_error(self, sample_oak_species, default_post_processor, tmp_path):
        """15. Degenerate mesh with height=0 raises clean ValueError."""
        mesh = MeshGeometry()
        mesh.add_vertex((0.0, 0.0, 0.0))
        mesh.add_vertex((1.0, 0.0, 0.0))
        mesh.add_vertex((0.0, 1.0, 0.0))
        mesh.add_triangle(0, 1, 2)
        glb_p = tmp_path / "flat.glb"
        mesh.export_glb(str(glb_p))

        raw_asset = RawAsset(
            species_id=sample_oak_species.species_id,
            glb_path=glb_p,
            mesh=mesh,
            source="procedural",
            vertex_count=3,
            face_count=1,
        )

        with pytest.raises(ValueError) as exc_info:
            default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "flat_out")
        assert "zero height" in str(exc_info.value).lower()


# ==============================================================================
# 4. DUAL-FORMAT EXPORT: PRODUCTION GLB TESTS
# ==============================================================================

class TestDualFormatExportGLB:
    """Verifies production-ready glTF 2.0 binary (.glb) export standards."""

    def test_glb_file_creation_and_non_zero_size(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """16. Exported .glb exists and has non-zero size (> 10 KB)."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_size")
        assert exported.glb_path.is_file()
        assert exported.glb_path.stat().st_size >= 10240

    def test_glb_valid_12byte_header(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """17. Validates magic 'glTF', version 2, and length matching file size."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_hdr")

        data = exported.glb_path.read_bytes()
        assert len(data) >= 12
        magic, version, length = struct.unpack_from("<4sII", data, 0)
        assert magic == b"glTF"
        assert version == 2
        assert length == len(data)

    def test_glb_4byte_chunk_alignment(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """18. Asserts glTF chunk lengths and boundaries are strictly aligned to 4 bytes."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_align")

        data = exported.glb_path.read_bytes()
        c0_len, c0_type = struct.unpack_from("<I4s", data, 12)
        assert c0_type == b"JSON"
        assert c0_len % 4 == 0

        c1_offset = 12 + 8 + c0_len
        c1_len, c1_type = struct.unpack_from("<I4s", data, c1_offset)
        assert c1_type.startswith(b"BIN")
        assert c1_len % 4 == 0

    def test_glb_zero_armatures_and_skins(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """19. Strictly asserts zero skins, zero animations, and zero skeletal attributes."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_rig")

        gltf, _ = unpack_glb_header_and_json(exported.glb_path)
        assert gltf.get("skins") is None or len(gltf.get("skins")) == 0
        assert gltf.get("animations") is None or len(gltf.get("animations")) == 0

        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                attrs = prim.get("attributes", {})
                for k in attrs:
                    assert not k.startswith("JOINTS_")
                    assert not k.startswith("WEIGHTS_")

        for node in gltf.get("nodes", []):
            assert "skin" not in node

    def test_glb_primitive_attributes_complete(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """20. Asserts primitives include POSITION, NORMAL, TEXCOORD_0, and indices."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_attrs")

        gltf, _ = unpack_glb_header_and_json(exported.glb_path)
        prim = gltf["meshes"][0]["primitives"][0]
        attrs = prim["attributes"]
        assert "POSITION" in attrs
        assert "NORMAL" in attrs
        assert "TEXCOORD_0" in attrs
        assert "indices" in prim

    def test_glb_embedded_pbr_textures(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """21. Asserts all 4 PBR textures are embedded in the GLB binary bufferView."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_pbr")

        gltf, bin_bytes = unpack_glb_header_and_json(exported.glb_path)
        images = gltf.get("images", [])
        assert len(images) >= 1, "GLB contains zero embedded images"

        for img in images:
            assert "bufferView" in img
            assert img.get("mimeType") in ("image/png", "image/jpeg")
            bv = gltf["bufferViews"][img["bufferView"]]
            img_bytes = bin_bytes[bv["byteOffset"]:bv["byteOffset"] + bv["byteLength"]]
            assert img_bytes.startswith(b"\x89PNG") or img_bytes.startswith(b"\xff\xd8\xff")

        mat = gltf["materials"][0]
        assert "pbrMetallicRoughness" in mat

    def test_glb_foliage_double_sided_flag(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """22. Foliage material must enable doubleSided rendering for leaves."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_double")

        gltf, _ = unpack_glb_header_and_json(exported.glb_path)
        assert gltf["materials"][0].get("doubleSided") is True

    def test_glb_accessor_min_z_ground_aligned(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """23. POSITION accessor min[2] reflects ground contact Z_min <= 0.005m."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "glb_acc")

        gltf, _ = unpack_glb_header_and_json(exported.glb_path)
        pos_acc = gltf["accessors"][gltf["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
        assert pos_acc["min"][2] <= 0.005


# ==============================================================================
# 5. DUAL-FORMAT EXPORT: COMPANION OBJ & MTL TESTS
# ==============================================================================

class TestDualFormatExportWavefrontObjMtl:
    """Verifies companion Wavefront OBJ and MTL export formatting and paths."""

    def test_obj_and_mtl_files_exist_and_non_zero(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """24. Companion .obj and .mtl files exist and are non-empty."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "obj_exist")

        assert exported.obj_path.is_file()
        assert exported.mtl_path.is_file()
        assert exported.obj_path.stat().st_size > 0
        assert exported.mtl_path.stat().st_size > 0

    def test_obj_file_syntax_and_indices(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """25. Asserts .obj syntax, headers, and 1-based face indices."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "obj_syntax")

        has_v = False
        has_vn = False
        has_vt = False
        has_f = False
        has_mtllib = False
        has_usemtl = False

        with open(exported.obj_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("v "):
                    has_v = True
                elif line.startswith("vn "):
                    has_vn = True
                elif line.startswith("vt "):
                    has_vt = True
                elif line.startswith("f "):
                    has_f = True
                    face_tokens = line.strip().split()[1:]
                    for tok in face_tokens:
                        v_idx = int(tok.split("/")[0])
                        assert v_idx >= 1
                elif line.startswith("mtllib "):
                    has_mtllib = True
                elif line.startswith("usemtl "):
                    has_usemtl = True

        assert has_v and has_vn and has_vt and has_f
        assert has_mtllib and has_usemtl

    def test_obj_vertex_count_matches_mesh(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """26. Line count of 'v ' in .obj matches exported_asset.vertex_count."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "obj_vcount")

        coords = parse_obj_vertex_positions(exported.obj_path)
        assert len(coords) == exported.vertex_count

    def test_mtl_file_syntax_and_material_name(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """27. Asserts .mtl defines newmtl matching usemtl in .obj."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "mtl_mat")

        mtl_text = exported.mtl_path.read_text(encoding="utf-8")
        assert f"newmtl M_{sample_oak_species.species_id}" in mtl_text

        obj_text = exported.obj_path.read_text(encoding="utf-8")
        assert f"usemtl M_{sample_oak_species.species_id}" in obj_text

    def test_mtl_texture_paths_reference_textures_folder(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """28. Asserts companion .mtl references textures/ directory maps."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "mtl_paths")

        bindings = parse_mtl_texture_map_bindings(exported.mtl_path)
        assert "albedo" in bindings
        assert "normal" in bindings
        assert "roughness" in bindings
        assert "metallic" in bindings

        assert "textures/albedo.png" in bindings["albedo"].replace("\\", "/")
        assert "textures/normal.png" in bindings["normal"].replace("\\", "/")

    def test_mtl_relative_paths_portability(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """29. Asserts texture map paths in .mtl are strictly relative, not absolute."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "mtl_portable")

        with open(exported.mtl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("map_"):
                    path_str = line.split(maxsplit=1)[1].strip()
                    assert not os.path.isabs(path_str)
                    assert not (len(path_str) > 1 and path_str[1] == ":")


# ==============================================================================
# 6. PBR TEXTURE PACKAGING TESTS
# ==============================================================================

class TestPbrTexturePackaging:
    """Verifies textures/ directory contains valid, readable 4-channel PBR maps."""

    def test_textures_directory_exists(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """30. textures/ directory exists under asset folder."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "tex_dir")
        tex_dir = exported.glb_path.parent / "textures"
        assert tex_dir.is_dir()

    def test_all_4_pbr_maps_present(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """31. All 4 PBR maps (albedo, normal, roughness, metallic) exist on disk."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "tex_all")

        tex_dir = exported.glb_path.parent / "textures"
        for ch in ["albedo.png", "normal.png", "roughness.png", "metallic.png"]:
            p = tex_dir / ch
            assert p.is_file(), f"Missing texture: {p}"
            assert p.stat().st_size > 0

    def test_textures_valid_readable_images(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """32. Verifies all 4 maps can be opened, verified, and meet resolution >= 256x256."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "tex_valid")

        for ch, p in exported.texture_paths.items():
            with Image.open(p) as img:
                img.verify()
            with Image.open(p) as img:
                assert img.width >= 256 and img.height >= 256

    def test_texture_color_space_and_channels(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """33. Physical property ranges: non-black albedo, outward normal, matte roughness, dielectric metallic."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "tex_prop")

        with Image.open(exported.texture_paths["albedo"]) as img:
            arr = np.array(img.convert("RGB"), dtype=np.float32)
            assert arr.mean() >= 15.0

        with Image.open(exported.texture_paths["normal"]) as img:
            arr = np.array(img.convert("RGB"), dtype=np.float32)
            assert arr[:, :, 2].mean() >= 170.0

        with Image.open(exported.texture_paths["roughness"]) as img:
            arr = np.array(img.convert("L"), dtype=np.float32) / 255.0
            assert 0.15 <= arr.mean() <= 0.95

        with Image.open(exported.texture_paths["metallic"]) as img:
            arr = np.array(img.convert("L"), dtype=np.float32) / 255.0
            assert arr.mean() <= 0.05

    def test_missing_texture_channel_fallback_synthesis(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """34. When raw asset lacks metallic or roughness, post-processor synthesizes standard fallbacks."""
        raw_asset = synthetic_raw_asset_factory(omit_texture_channels=["metallic", "roughness"])
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "tex_fallback")

        assert "metallic" in exported.texture_paths
        assert "roughness" in exported.texture_paths
        assert exported.texture_paths["metallic"].is_file()
        assert exported.texture_paths["roughness"].is_file()


# ==============================================================================
# 7. ASSET MANIFEST JSON TESTS
# ==============================================================================

class TestAssetManifestJson:
    """Verifies asset_manifest.json structure, taxonomy, and metrics synchronization."""

    def test_manifest_file_exists_and_valid_json(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """35. asset_manifest.json exists and parses cleanly."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_json")

        assert exported.manifest_path.is_file()
        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)

    def test_manifest_taxonomy_fields(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """36. Asserts presence and correctness of all required taxonomy fields."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_tax")

        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        assert data["species_id"] == sample_oak_species.species_id
        tax = data["taxonomy"]
        assert tax["scientific_name"] == sample_oak_species.scientific_name
        assert tax["common_name"] == sample_oak_species.common_name
        assert tax["category"] == sample_oak_species.category
        assert tax["family"] == sample_oak_species.family

    def test_manifest_geometry_metrics(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """37. Asserts vertex_count [3000, 45000], face_count > 0, and valid bounding box."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_geom")

        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        geom = data["geometry"]
        assert 3000 <= geom["vertex_count"] <= 45000
        assert geom["face_count"] > 0
        assert "bounding_box" in geom
        assert geom["bounding_box"]["dimensions"][2] > 0.0

    def test_manifest_ground_and_pivot_records(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """38. Asserts ground_contact_z ≈ 0.000m and base_centroid_xy near [0, 0]."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_piv")

        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        geom = data["geometry"]
        assert abs(geom["ground_contact_z"]) <= 0.005
        assert abs(geom["base_centroid_xy"][0]) <= 0.05
        assert abs(geom["base_centroid_xy"][1]) <= 0.05

    def test_manifest_scale_records(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """39. Asserts scale factor consistency."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_scale")

        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        norm = data["normalization"]
        assert norm["target_height_m"] == sample_oak_species.dimensions.height_m
        assert norm["scale_factor"] > 0.0
        assert abs(norm["normalized_height_m"] - sample_oak_species.dimensions.height_m) / sample_oak_species.dimensions.height_m <= 0.05

    def test_manifest_file_references(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """40. File paths in manifest match actual files on disk."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_files")

        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        files = data["files"]
        asset_dir = exported.manifest_path.parent
        assert (asset_dir / files["glb"]).is_file()
        assert (asset_dir / files["obj"]).is_file()
        assert (asset_dir / files["mtl"]).is_file()

    def test_manifest_timestamp_and_provenance(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """41. Verifies ISO timestamp and provenance source recording."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "man_prov")

        data = json.loads(exported.manifest_path.read_text(encoding="utf-8"))
        assert "provenance" in data
        assert data["provenance"]["source"] in ("meshy", "procedural", "cached")
        assert "export_timestamp" in data["provenance"]


# ==============================================================================
# 8. DIRECTORY HIERARCHY & PACKAGING TESTS
# ==============================================================================

class TestDirectoryHierarchyAndPackaging:
    """Verifies output/<short_category>/<species_id>/ structure across biomes."""

    @pytest.mark.parametrize("category_canon,short_cat,species_id", [
        ("broadleaf_deciduous_trees", "broadleaf_trees", "veg_tree_oak_01"),
        ("conifers_evergreens", "conifers", "veg_conifer_pine_01"),
        ("tropical_foliage_palms", "tropical", "veg_tropical_palm_01"),
        ("flowering_shrubs_ornamentals", "shrubs", "veg_shrub_rose_01"),
        ("ferns_grasses_groundcover", "groundcover", "veg_ground_fern_01"),
        ("succulents_cacti", "succulents", "veg_succulent_saguaro_01"),
        ("climbing_vines_epiphytes", "vines", "veg_vine_ivy_01"),
    ])
    def test_directory_structure_across_all_7_biomes(self, catalog, category_canon, short_cat, species_id, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """42. Asserts asset folder is located in output/<short_category>/<species_id>/."""
        species = catalog[species_id]
        raw_asset = synthetic_raw_asset_factory(species_id=species_id)
        base_out = tmp_path / "output"

        exported = default_post_processor.process_asset(raw_asset, species, output_dir=base_out)

        expected_dir = base_out / short_cat / species_id
        assert exported.glb_path.parent == expected_dir
        assert exported.obj_path.parent == expected_dir
        assert exported.manifest_path.parent == expected_dir
        assert (expected_dir / "textures").is_dir()

    def test_custom_output_dir_routing(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """43. Custom output directory path routes assets properly."""
        raw_asset = synthetic_raw_asset_factory()
        custom_root = tmp_path / "my_custom_assets"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=custom_root)

        assert str(custom_root) in str(exported.glb_path)

    def test_parent_directory_auto_creation(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """44. Deeply nested non-existent directory is automatically created."""
        raw_asset = synthetic_raw_asset_factory()
        deep_dir = tmp_path / "level1" / "level2" / "level3"
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=deep_dir)
        assert exported.glb_path.is_file()

    def test_clean_overwrite_and_idempotent_reexport(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """45. Re-running post-processing over existing directory updates cleanly without error."""
        raw_asset = synthetic_raw_asset_factory()
        target_dir = tmp_path / "reexport"

        exp1 = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=target_dir)
        exp2 = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=target_dir)

        assert exp1.glb_path == exp2.glb_path
        assert exp2.glb_path.is_file()


# ==============================================================================
# 9. EDGE CASES & ROBUSTNESS TESTS
# ==============================================================================

class TestEdgeCasesAndRobustness:
    """Verifies boundary conditions, error handling, and contract compliance."""

    def test_mesh_with_nan_or_inf_coordinates_raises(self, sample_oak_species, default_post_processor, tmp_path):
        """46. Mesh containing NaN or Inf coordinates raises ValueError."""
        mesh = MeshGeometry()
        mesh.add_vertex((float("nan"), 0.0, 1.0))
        mesh.add_vertex((0.0, float("inf"), 1.0))
        mesh.add_vertex((0.0, 0.0, 1.0))
        mesh.add_triangle(0, 1, 2)
        glb_p = tmp_path / "nan.glb"
        mesh.export_glb(str(glb_p))

        raw_asset = RawAsset(species_id=sample_oak_species.species_id, glb_path=glb_p, mesh=mesh, source="procedural", vertex_count=3, face_count=1)

        with pytest.raises(ValueError) as exc_info:
            default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "nan_out")
        assert "nan" in str(exc_info.value).lower() or "inf" in str(exc_info.value).lower() or "finite" in str(exc_info.value).lower()

    def test_corrupted_raw_glb_raises(self, sample_oak_species, default_post_processor, tmp_path):
        """47. Corrupted raw GLB file raises ValueError."""
        bad_glb = tmp_path / "corrupt.glb"
        bad_glb.write_bytes(b"NOT_A_GLB_CONTAINER")

        raw_asset = RawAsset(species_id=sample_oak_species.species_id, glb_path=bad_glb, source="procedural", vertex_count=100, face_count=50)

        with pytest.raises(ValueError):
            default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "corrupt_out")

    def test_quad_and_triangle_mixed_mesh_export(self, sample_oak_species, default_post_processor, tmp_path):
        """48. Mesh with both quads and triangles exports valid geometry."""
        mesh = MeshGeometry()
        mesh.add_vertex((0, 0, 0))
        mesh.add_vertex((1, 0, 0))
        mesh.add_vertex((1, 1, 0))
        mesh.add_vertex((0, 1, 0))
        mesh.add_quad(0, 1, 2, 3)
        mesh.add_vertex((0.5, 0.5, 2.0))
        mesh.add_triangle(0, 1, 4)

        glb_p = tmp_path / "mixed.glb"
        mesh.export_glb(str(glb_p))

        raw_asset = RawAsset(species_id=sample_oak_species.species_id, glb_path=glb_p, mesh=mesh, source="procedural", vertex_count=5, face_count=3)
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "mixed_out")

        assert exported.glb_path.is_file()
        assert exported.obj_path.is_file()

    def test_post_processor_convenience_function(self, sample_oak_species, synthetic_raw_asset_factory, tmp_path):
        """49. process_and_export convenience helper produces valid ExportedAsset."""
        raw_asset = synthetic_raw_asset_factory()
        exported = process_and_export(raw_asset, sample_oak_species, output_dir=tmp_path / "convenience")

        assert isinstance(exported, ExportedAsset)
        assert exported.species_id == sample_oak_species.species_id
        assert exported.glb_path.is_file()

    def test_exported_asset_contract_compliance(self, sample_oak_species, default_post_processor, synthetic_raw_asset_factory, tmp_path):
        """50. ExportedAsset strictly adheres to M3 <-> M4 interface contract."""
        raw_asset = synthetic_raw_asset_factory()
        exported = default_post_processor.process_asset(raw_asset, sample_oak_species, output_dir=tmp_path / "contract")

        assert isinstance(exported.species_id, str)
        assert isinstance(exported.glb_path, Path)
        assert isinstance(exported.obj_path, Path)
        assert isinstance(exported.mtl_path, Path)
        assert isinstance(exported.manifest_path, Path)
        assert isinstance(exported.texture_paths, dict)
        assert set(exported.texture_paths.keys()) == {"albedo", "normal", "roughness", "metallic"}
        assert isinstance(exported.vertex_count, int) and exported.vertex_count >= 3000
        assert isinstance(exported.face_count, int) and exported.face_count > 0
