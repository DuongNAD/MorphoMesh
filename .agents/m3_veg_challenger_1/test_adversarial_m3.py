"""
Adversarial Test Harness for Milestone 3 (M3: Asset Post-Processing, Normalization & Multi-Format Export).
Challenger: m3_veg_challenger_1
Location: E:\\tool\\mcp\\MorphoMesh\\.agents\\m3_veg_challenger_1\\test_adversarial_m3.py

Challenges:
1. Floating and subterranean meshes (Z_min = +100m, Z_min = -50m, Z_min = -1000m, Z_min = +1000m).
2. Asymmetric and leaning crowns (Trunk base off-center, crown leaning far away; verify bottom 5% centroid centered at (0, 0) +- 0.01m).
3. Extreme dimension boundaries (miniature 0.01m, giant 150m, microscopic initial 0.0001m, giant initial 5000m).
4. Zero-height and degenerate meshes (flat planar H=0, H=1e-7, NaN/Inf vertices, empty meshes; verify ValueError).
5. Missing texture channels and fallback dielectric synthesis (missing roughness/metallic/albedo/normal, 1x1 low-res textures).
6. Manifest schema and file integrity validation (GLB, OBJ, MTL, textures, and asset_manifest.json field-by-field verification).
7. glTF 2.0 binary container standard compliance (chunk alignments, doubleSided foliage, N_bones=0).
8. Scaling strategies (uniform_height, aspect_constrained, exact_bounds, none).
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union

# Bootstrap sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
VEG_LIB_DIR = REPO_ROOT / "teamwork_projects" / "vegetation_library"
if str(VEG_LIB_DIR) not in sys.path:
    sys.path.insert(0, str(VEG_LIB_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
from PIL import Image
import pytest

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import PlantSpecies, DimensionsSpec, MorphologySpec, MeshyPromptSpec, get_species
from vegetation_pipeline.generator import RawAsset, unpack_glb_header_and_json
from vegetation_pipeline.post_processor import (
    AssetDimensions,
    AssetPostProcessor,
    PostProcessorConfig,
    ExportedAsset,
    compute_mesh_extents,
    export_companion_obj_mtl,
    export_production_glb,
    load_mesh_from_glb,
    normalize_metric_scale,
    pack_metallic_roughness,
    process_and_export,
    snap_ground_pivot_and_center,
)


# Helper geometry generators
def create_cylinder_mesh(
    radius: float = 0.5,
    height: float = 5.0,
    offset: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    segments: int = 16,
) -> MeshGeometry:
    """Generates a closed cylinder for trunk testing."""
    mesh = MeshGeometry()
    ox, oy, oz = offset

    # Bottom ring vertices
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = ox + radius * math.cos(angle)
        y = oy + radius * math.sin(angle)
        mesh.add_vertex((x, y, oz), (math.cos(angle), math.sin(angle), 0.0), (i / segments, 0.0))

    # Top ring vertices
    for i in range(segments):
        angle = 2.0 * math.pi * i / segments
        x = ox + radius * math.cos(angle)
        y = oy + radius * math.sin(angle)
        mesh.add_vertex((x, y, oz + height), (math.cos(angle), math.sin(angle), 0.0), (i / segments, 1.0))

    # Side faces
    for i in range(segments):
        nxt = (i + 1) % segments
        b1, b2 = i, nxt
        t1, t2 = segments + i, segments + nxt
        mesh.add_triangle(b1, b2, t2)
        mesh.add_triangle(b1, t2, t1)

    # Bottom cap center
    bc_idx = len(mesh.vertices)
    mesh.add_vertex((ox, oy, oz), (0.0, 0.0, -1.0), (0.5, 0.5))
    for i in range(segments):
        mesh.add_triangle(bc_idx, (i + 1) % segments, i)

    # Top cap center
    tc_idx = len(mesh.vertices)
    mesh.add_vertex((ox, oy, oz + height), (0.0, 0.0, 1.0), (0.5, 0.5))
    for i in range(segments):
        mesh.add_triangle(tc_idx, segments + i, segments + ((i + 1) % segments))

    return mesh


def create_leaning_tree_mesh(
    trunk_pos: Tuple[float, float] = (10.0, -15.0),
    trunk_radius: float = 0.4,
    trunk_height: float = 6.0,
    crown_offset: Tuple[float, float, float] = (30.0, 40.0, 8.0),
    crown_radius: float = 5.0,
    crown_segments: int = 16,
) -> MeshGeometry:
    """
    Creates an extremely asymmetric leaning tree:
    Trunk base is located at trunk_pos (e.g. 10.0, -15.0) at Z=0 to Z=6.
    A massive foliage crown is offset far away at crown_offset.
    """
    mesh = create_cylinder_mesh(
        radius=trunk_radius,
        height=trunk_height,
        offset=(trunk_pos[0], trunk_pos[1], 0.0),
        segments=16,
    )

    # Add crown sphere-like clusters offset far away
    cx, cy, cz = trunk_pos[0] + crown_offset[0], trunk_pos[1] + crown_offset[1], crown_offset[2]
    crown_base_idx = len(mesh.vertices)

    for i in range(crown_segments):
        lat = math.pi * (i + 1) / (crown_segments + 1)
        for j in range(crown_segments):
            lon = 2.0 * math.pi * j / crown_segments
            x = cx + crown_radius * math.sin(lat) * math.cos(lon)
            y = cy + crown_radius * math.sin(lat) * math.sin(lon)
            z = cz + crown_radius * math.cos(lat)
            mesh.add_vertex((x, y, z), (math.sin(lat) * math.cos(lon), math.sin(lat) * math.sin(lon), math.cos(lat)), (0.5, 0.5))

    for i in range(crown_segments - 1):
        for j in range(crown_segments):
            nxt_j = (j + 1) % crown_segments
            v0 = crown_base_idx + i * crown_segments + j
            v1 = crown_base_idx + i * crown_segments + nxt_j
            v2 = crown_base_idx + (i + 1) * crown_segments + nxt_j
            v3 = crown_base_idx + (i + 1) * crown_segments + j
            mesh.add_triangle(v0, v1, v2)
            mesh.add_triangle(v0, v2, v3)

    return mesh


def create_dummy_species(
    height_m: float = 10.0,
    canopy_spread_m: float = 6.0,
    species_id: str = "test_species_01",
) -> PlantSpecies:
    """Builds a valid PlantSpecies instance with requested dimensions by copying a canonical species."""
    base = get_species("veg_tree_oak_01")
    return base.model_copy(
        update={
            "species_id": species_id,
            "dimensions": DimensionsSpec(
                height_m=height_m,
                height_range_m=(max(0.001, height_m * 0.8), max(0.002, height_m * 1.2)),
                canopy_spread_m=canopy_spread_m,
                trunk_stem_diameter_m=max(0.01, canopy_spread_m * 0.1),
            ),
        }
    )


def make_raw_asset(
    mesh: Optional[MeshGeometry] = None,
    species_id: str = "test_species_01",
    glb_path: Optional[Path] = None,
    textures: Optional[dict] = None,
    texture_paths: Optional[dict] = None,
    source: str = "procedural",
    metadata: Optional[dict] = None,
) -> RawAsset:
    """Helper to construct valid RawAsset for testing."""
    if glb_path is None:
        glb_path = Path("dummy.glb")
    return RawAsset(
        species_id=species_id,
        glb_path=glb_path,
        mesh=mesh,
        textures=textures or {},
        texture_paths=texture_paths or {},
        source=source,
        metadata=metadata or {},
    )


# ==============================================================================
# 1. FLOATING AND SUBTERRANEAN MESHES
# ==============================================================================

class TestFloatingAndSubterraneanGrounded:
    """Stress tests extreme Z offsets (+100m, -50m, +-1000m) for strict Z_min = 0.000m."""

    @pytest.mark.parametrize("z_offset", [100.0, -50.0, -1000.0, 1000.0, 0.00001, -0.00001])
    def test_snap_ground_pivot_extreme_offsets(self, z_offset):
        """Verify snap_ground_pivot_and_center strictly places lowest vertex at Z = 0.000."""
        mesh = create_cylinder_mesh(radius=1.0, height=10.0, offset=(0.0, 0.0, z_offset))
        grounded_mesh, centroid, min_z = snap_ground_pivot_and_center(mesh)

        all_zs = [v[2] for v in grounded_mesh.vertices]
        computed_min = min(all_zs)

        assert abs(computed_min) <= 1e-6, f"Z_min is not zero: {computed_min}"
        assert abs(min_z) <= 1e-6, f"Returned min_z is not zero: {min_z}"
        assert max(all_zs) == pytest.approx(10.0, rel=1e-5)

    @pytest.mark.parametrize("z_offset", [100.0, -50.0])
    def test_full_pipeline_floating_and_subterranean(self, z_offset, tmp_path):
        """Verify full process_and_export pipeline strictly grounds floating and subterranean raw assets."""
        mesh = create_cylinder_mesh(radius=0.8, height=8.0, offset=(5.0, -3.0, z_offset))
        raw = make_raw_asset(
            mesh=mesh,
            textures={},
            source="procedural",
            metadata={"test": "floating_subterranean"},
        )
        species = create_dummy_species(height_m=12.0, species_id=f"test_ground_{int(z_offset)}")
        exported = process_and_export(raw, species, output_dir=tmp_path)

        assert exported.is_valid()
        assert abs(exported.ground_pivot_z) <= 1e-6
        assert exported.dimensions.bounding_box_min[2] == pytest.approx(0.0, abs=1e-4)

        # Inspect exported OBJ directly
        with open(exported.obj_path, "r", encoding="utf-8") as f:
            obj_lines = [line.strip().split() for line in f if line.startswith("v ")]
        obj_zs = [float(parts[3]) for parts in obj_lines]
        assert min(obj_zs) == pytest.approx(0.0, abs=1e-4)


# ==============================================================================
# 2. ASYMMETRIC AND LEANING CROWNS
# ==============================================================================

class TestAsymmetricAndLeaningCrowns:
    """Stress tests trunk base contact centering when crown is heavily leaning or asymmetric."""

    def test_leaning_crown_base_centering_within_tolerance(self):
        """
        Trunk base located at (15.0, -25.0), height 6.0m.
        Foliage crown offset at (30.0, 40.0, 8.0) with radius 5.0m.
        Centering the whole bounding box would place the base far away from (0, 0).
        Base contact centroid centering (bottom 5% slice) MUST center the trunk base at (0, 0) +- 0.01m.
        """
        mesh = create_leaning_tree_mesh(
            trunk_pos=(15.0, -25.0),
            trunk_radius=0.5,
            trunk_height=6.0,
            crown_offset=(30.0, 40.0, 8.0),
            crown_radius=5.0,
        )

        grounded_mesh, (cx, cy), min_z = snap_ground_pivot_and_center(mesh, base_slice_ratio=0.05)

        # Height extent
        zs = [v[2] for v in grounded_mesh.vertices]
        h = max(zs) - min(zs)
        slice_thresh = min(zs) + 0.05 * h
        base_verts = [v for v in grounded_mesh.vertices if v[2] <= slice_thresh]

        base_cx = float(np.mean([v[0] for v in base_verts]))
        base_cy = float(np.mean([v[1] for v in base_verts]))

        assert abs(base_cx) <= 0.01, f"Base contact X centroid {base_cx} exceeds tolerance 0.01m"
        assert abs(base_cy) <= 0.01, f"Base contact Y centroid {base_cy} exceeds tolerance 0.01m"

    def test_full_pipeline_leaning_crown_centering(self, tmp_path):
        """Verify full process_and_export correctly centers the base contact centroid within 0.01m."""
        mesh = create_leaning_tree_mesh(
            trunk_pos=(-20.0, 35.0),
            trunk_radius=0.6,
            trunk_height=8.0,
            crown_offset=(-40.0, -50.0, 10.0),
            crown_radius=6.0,
        )
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")
        species = create_dummy_species(height_m=15.0, species_id="test_leaning_tree")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        assert exported.is_valid()
        assert abs(exported.base_centroid[0]) <= 0.01
        assert abs(exported.base_centroid[1]) <= 0.01

        # Check manifest recorded base_centroid_xy
        with open(exported.manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        manifest_base = manifest["geometry"]["base_centroid_xy"]
        assert abs(manifest_base[0]) <= 0.01
        assert abs(manifest_base[1]) <= 0.01


# ==============================================================================
# 3. EXTREME DIMENSION BOUNDARIES
# ==============================================================================

class TestExtremeDimensionBoundaries:
    """Stress tests boundary scales: miniature plants (0.01m), giant trees (150m), and extreme raw meshes."""

    @pytest.mark.parametrize("target_h, target_spread", [
        (0.01, 0.02),      # Miniature lichen/moss
        (0.05, 0.05),      # Small groundcover
        (50.0, 20.0),      # Tall sequoia
        (150.0, 45.0),     # Giant redwood boundary
    ])
    def test_extreme_target_dimensions(self, target_h, target_spread, tmp_path):
        """Test scaling raw mesh to extreme botanical target sizes without NaN or numerical instability."""
        mesh = create_cylinder_mesh(radius=0.5, height=5.0)
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")
        species = create_dummy_species(height_m=target_h, canopy_spread_m=target_spread, species_id=f"extreme_{int(target_h*100)}")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        assert exported.is_valid()
        assert exported.dimensions.height_m == pytest.approx(target_h, rel=1e-3)
        assert math.isfinite(exported.dimensions.height_m)
        assert math.isfinite(exported.dimensions.canopy_spread_m)

        # Assert no vertex is NaN or Inf in exported GLB
        reloaded_mesh = load_mesh_from_glb(exported.glb_path)
        for v in reloaded_mesh.vertices:
            assert math.isfinite(v[0]) and math.isfinite(v[1]) and math.isfinite(v[2])
        for vn in reloaded_mesh.normals:
            assert math.isfinite(vn[0]) and math.isfinite(vn[1]) and math.isfinite(vn[2])
            n_len = math.sqrt(vn[0]**2 + vn[1]**2 + vn[2]**2)
            assert n_len == pytest.approx(1.0, abs=1e-2)

    def test_microscopic_and_gargantuan_raw_input_meshes(self, tmp_path):
        """Test raw input mesh of height 0.0001m and height 5000.0m scaled to normal botanical target."""
        species = create_dummy_species(height_m=10.0, canopy_spread_m=5.0, species_id="extreme_inputs")

        # 1. Microscopic input: height = 0.0005m
        micro_mesh = create_cylinder_mesh(radius=0.0001, height=0.0005)
        raw_micro = make_raw_asset(mesh=micro_mesh, textures={}, source="procedural")
        exp_micro = process_and_export(raw_micro, species, output_dir=tmp_path / "micro")
        assert exp_micro.dimensions.height_m == pytest.approx(10.0, rel=1e-3)

        # 2. Gargantuan input: height = 5000.0m
        giant_mesh = create_cylinder_mesh(radius=500.0, height=5000.0)
        raw_giant = make_raw_asset(mesh=giant_mesh, textures={}, source="procedural")
        exp_giant = process_and_export(raw_giant, species, output_dir=tmp_path / "giant")
        assert exp_giant.dimensions.height_m == pytest.approx(10.0, rel=1e-3)


# ==============================================================================
# 4. ZERO-HEIGHT AND DEGENERATE MESHES
# ==============================================================================

class TestZeroHeightAndDegenerateMeshes:
    """Stress tests degenerate geometry: flat planar meshes, zero height, NaN/Inf coords, empty meshes."""

    def test_flat_planar_mesh_rejected_with_value_error(self):
        """A flat planar mesh with all Z = 0 has height H = 0. Must raise ValueError."""
        mesh = MeshGeometry()
        mesh.add_vertex((-1.0, -1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0))
        mesh.add_vertex((1.0, -1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0))
        mesh.add_vertex((1.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0))
        mesh.add_triangle(0, 1, 2)

        species = create_dummy_species()
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")

        with pytest.raises(ValueError, match="zero height"):
            snap_ground_pivot_and_center(mesh)

        with pytest.raises(ValueError, match="zero height"):
            normalize_metric_scale(mesh, species)

        with pytest.raises(ValueError, match="zero height"):
            process_and_export(raw, species)

    def test_near_zero_height_epsilon_rejected(self):
        """A mesh with height 1e-7m is practically degenerate. Must raise ValueError."""
        mesh = MeshGeometry()
        mesh.add_vertex((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, 0.0))
        mesh.add_vertex((1.0, 0.0, 1e-7), (0.0, 0.0, 1.0), (1.0, 0.0))
        mesh.add_vertex((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0))
        mesh.add_triangle(0, 1, 2)

        with pytest.raises(ValueError, match="zero height"):
            snap_ground_pivot_and_center(mesh)

    def test_nan_or_inf_coordinates_rejected(self):
        """Meshes containing NaN or Infinity coordinates must be rejected with ValueError."""
        species = create_dummy_species()

        # NaN vertex
        mesh_nan = MeshGeometry()
        mesh_nan.add_vertex((float("nan"), 0.0, 1.0), (0.0, 0.0, 1.0), (0.0, 0.0))
        mesh_nan.add_vertex((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0))
        mesh_nan.add_vertex((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0))
        mesh_nan.add_triangle(0, 1, 2)

        with pytest.raises(ValueError, match="non-finite coordinates"):
            snap_ground_pivot_and_center(mesh_nan)

        with pytest.raises(ValueError, match="non-finite coordinates"):
            process_and_export(make_raw_asset(mesh=mesh_nan, textures={}, source="procedural"), species)

        # Inf vertex
        mesh_inf = MeshGeometry()
        mesh_inf.add_vertex((0.0, float("inf"), 1.0), (0.0, 0.0, 1.0), (0.0, 0.0))
        mesh_inf.add_vertex((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (1.0, 0.0))
        mesh_inf.add_vertex((0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (0.0, 1.0))
        mesh_inf.add_triangle(0, 1, 2)

        with pytest.raises(ValueError, match="non-finite coordinates"):
            snap_ground_pivot_and_center(mesh_inf)


# ==============================================================================
# 5. MISSING TEXTURE CHANNELS & DIELECTRIC FALLBACK SYNTHESIS
# ==============================================================================

class TestMissingTextureChannelsFallback:
    """Stress tests fallback synthesis for missing PBR texture channels (metallic, roughness, etc.)."""

    def test_completely_empty_textures_synthesizes_valid_dielectric(self, tmp_path):
        """When RawAsset provides zero textures, fallback must synthesize valid botanical dielectric maps."""
        mesh = create_cylinder_mesh(radius=0.5, height=5.0)
        raw = make_raw_asset(mesh=mesh, textures={}, texture_paths={}, source="procedural")
        species = create_dummy_species(species_id="test_missing_tex")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        assert exported.is_valid()

        # Check each discrete texture file on disk
        albedo_img = Image.open(exported.albedo_path)
        normal_img = Image.open(exported.normal_path)
        roughness_img = Image.open(exported.roughness_path)
        metallic_img = Image.open(exported.metallic_path)

        assert albedo_img.size >= (256, 256)
        assert normal_img.size >= (256, 256)
        assert roughness_img.size >= (256, 256)
        assert metallic_img.size >= (256, 256)

        # Verify fallback color values:
        # Dielectric metallic should be 0 (black / non-metallic)
        m_arr = np.array(metallic_img)
        assert np.all(m_arr == 0), f"Metallic fallback should be 0, got {np.unique(m_arr)}"

        # Dielectric roughness should be default ~180
        r_arr = np.array(roughness_img)
        assert np.all(r_arr == 180), f"Roughness fallback should be 180, got {np.unique(r_arr)}"

        # Flat normal should be RGB (128, 128, 255)
        n_arr = np.array(normal_img)
        assert np.all(n_arr[..., 0] == 128)
        assert np.all(n_arr[..., 1] == 128)
        assert np.all(n_arr[..., 2] == 255)

        # Botanical green albedo: (45, 95, 35)
        a_arr = np.array(albedo_img)
        assert np.all(a_arr[..., 0] == 45)
        assert np.all(a_arr[..., 1] == 95)
        assert np.all(a_arr[..., 2] == 35)

    def test_missing_roughness_and_metallic_only(self, tmp_path):
        """When RawAsset provides only albedo and normal, verify roughness and metallic are synthesized."""
        custom_albedo = Image.new("RGB", (512, 512), (100, 150, 50))
        custom_normal = Image.new("RGB", (512, 512), (128, 128, 255))
        mesh = create_cylinder_mesh(radius=0.5, height=5.0)

        raw = make_raw_asset(
            mesh=mesh,
            textures={"albedo": custom_albedo, "normal": custom_normal},
            source="procedural",
        )
        species = create_dummy_species(species_id="test_partial_tex")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        assert exported.is_valid()

        # Custom albedo preserved
        alb = Image.open(exported.albedo_path)
        assert np.array(alb)[0, 0, 0] == 100

        # Synthesized roughness and metallic
        r_arr = np.array(Image.open(exported.roughness_path))
        m_arr = np.array(Image.open(exported.metallic_path))
        assert np.all(r_arr == 180)
        assert np.all(m_arr == 0)

    def test_sub_256_resolution_texture_upscaled(self, tmp_path):
        """Textures below 256x256 (e.g. 16x16 or 1x1) must be upscaled to at least 256x256."""
        tiny_albedo = Image.new("RGB", (16, 16), (200, 100, 50))
        mesh = create_cylinder_mesh(radius=0.5, height=5.0)

        raw = make_raw_asset(
            mesh=mesh,
            textures={"albedo": tiny_albedo},
            source="procedural",
        )
        species = create_dummy_species(species_id="test_tiny_tex")
        exported = process_and_export(raw, species, output_dir=tmp_path)

        alb = Image.open(exported.albedo_path)
        assert alb.width >= 256 and alb.height >= 256


# ==============================================================================
# 6. MANIFEST SCHEMA AND ASSET INTEGRITY VALIDATION
# ==============================================================================

class TestManifestSchemaAndIntegrity:
    """Stress tests asset_manifest.json fields, cross-validating with exported geometry and catalog."""

    def test_manifest_schema_and_geometry_cross_validation(self, tmp_path):
        """Cross-check manifest values against catalog species and actual binary geometry."""
        species = get_species("veg_tree_oak_01")
        mesh = create_cylinder_mesh(radius=0.8, height=6.0)
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        manifest_path = exported.manifest_path
        assert manifest_path.is_file()

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Required top-level keys
        required_keys = {"schema_version", "species_id", "taxonomy", "geometry", "normalization", "materials", "files", "provenance", "metadata"}
        assert required_keys.issubset(data.keys())

        # 2. Taxonomy fidelity
        assert data["species_id"] == species.species_id
        assert data["taxonomy"]["common_name"] == species.common_name
        assert data["taxonomy"]["scientific_name"] == species.scientific_name
        assert data["taxonomy"]["category"] == species.category
        assert data["taxonomy"]["category_id"] == species.category_id

        # 3. Geometry verification
        geom = data["geometry"]
        assert geom["vertex_count"] == len(mesh.vertices)
        assert geom["face_count"] == len(mesh.faces)
        assert geom["has_armature"] is False
        assert geom["has_skins"] is False
        assert geom["pivot_grounded"] is True
        assert geom["ground_contact_z"] == pytest.approx(0.0, abs=1e-5)

        # Compare manifest dimensions with actual exported OBJ file vertices
        with open(exported.obj_path, "r", encoding="utf-8") as f:
            obj_verts = [
                [float(p) for p in line.strip().split()[1:4]]
                for line in f if line.startswith("v ")
            ]
        xs = [v[0] for v in obj_verts]
        ys = [v[1] for v in obj_verts]
        zs = [v[2] for v in obj_verts]

        assert geom["bounding_box"]["min_point"][0] == pytest.approx(min(xs), abs=1e-4)
        assert geom["bounding_box"]["min_point"][1] == pytest.approx(min(ys), abs=1e-4)
        assert geom["bounding_box"]["min_point"][2] == pytest.approx(min(zs), abs=1e-4)
        assert geom["bounding_box"]["max_point"][0] == pytest.approx(max(xs), abs=1e-4)
        assert geom["bounding_box"]["max_point"][1] == pytest.approx(max(ys), abs=1e-4)
        assert geom["bounding_box"]["max_point"][2] == pytest.approx(max(zs), abs=1e-4)

        # Height must match catalog target
        assert geom["dimensions_m"]["height_m"] == pytest.approx(species.dimensions.height_m, rel=1e-3)

        # 4. Files verification
        files = data["files"]
        assert files["glb"] == f"{species.species_id}.glb"
        assert files["obj"] == f"{species.species_id}.obj"
        assert files["mtl"] == f"{species.species_id}.mtl"
        for ch, rel_p in files["textures"].items():
            full_p = manifest_path.parent / rel_p
            assert full_p.is_file(), f"Texture path {rel_p} in manifest does not exist on disk"


# ==============================================================================
# 7. GLTF 2.0 BINARY CONTAINER COMPLIANCE
# ==============================================================================

class TestGLTFBinaryCompliance:
    """Stress tests glTF 2.0 binary chunks, 4-byte alignments, embedded textures, and doubleSided."""

    def test_gltf_binary_header_and_chunk_alignments(self, tmp_path):
        """Assert GLB starts with 'glTF', version 2, and all chunks are padded to 4-byte boundaries."""
        species = create_dummy_species()
        mesh = create_cylinder_mesh(radius=0.5, height=4.0)
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        glb_bytes = exported.glb_path.read_bytes()

        # 12-byte header
        magic, version, total_len = struct.unpack("<4sII", glb_bytes[:12])
        assert magic == b"glTF"
        assert version == 2
        assert total_len == len(glb_bytes)

        # Chunk 0: JSON
        c0_len, c0_type = struct.unpack("<I4s", glb_bytes[12:20])
        assert c0_type == b"JSON"
        assert c0_len % 4 == 0, f"JSON chunk length {c0_len} is not 4-byte aligned"

        # Chunk 1: BIN
        c1_start = 20 + c0_len
        c1_len, c1_type = struct.unpack("<I4s", glb_bytes[c1_start:c1_start + 8])
        assert c1_type == b"BIN\x00"
        assert c1_len % 4 == 0, f"BIN chunk length {c1_len} is not 4-byte aligned"
        assert 12 + 8 + c0_len + 8 + c1_len == total_len

        # Verify unpack_glb_header_and_json succeeds
        gltf_dict, bin_data = unpack_glb_header_and_json(exported.glb_path)
        assert "asset" in gltf_dict
        assert gltf_dict["asset"]["version"] == "2.0"

        # Material doubleSided check
        assert gltf_dict["materials"][0]["doubleSided"] is True

        # Strict N_bones = 0 check
        assert "skins" not in gltf_dict or len(gltf_dict["skins"]) == 0
        assert "animations" not in gltf_dict or len(gltf_dict["animations"]) == 0
        prim = gltf_dict["meshes"][0]["primitives"][0]
        assert "JOINTS_0" not in prim["attributes"]
        assert "WEIGHTS_0" not in prim["attributes"]


# ==============================================================================
# 8. SCALING STRATEGIES STRESS-TEST
# ==============================================================================

class TestScalingStrategies:
    """Stress tests aspect_constrained, exact_bounds, and none scaling strategies."""

    def test_aspect_constrained_scaling(self, tmp_path):
        """Aspect constrained scaling clamps spread scale within +-aspect_clamp of height scale."""
        species = create_dummy_species(height_m=10.0, canopy_spread_m=20.0) # aspect ratio 2:1
        mesh = create_cylinder_mesh(radius=1.0, height=5.0) # curr height 5, spread 2.0
        # raw scale_z = 10 / 5 = 2.0
        # raw spread_scale = 20 / 2.0 = 10.0 -> ratio = 5.0 -> clamped to 1.15!
        config = PostProcessorConfig(scaling_strategy="aspect_constrained", aspect_constraint_clamp=0.15)
        processor = AssetPostProcessor(config=config)
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")

        exported = processor.process_asset(raw, species, output_dir=tmp_path)
        assert exported.dimensions.height_m == pytest.approx(10.0, rel=1e-3)
        # scale_x/y should be 2.0 * 1.15 = 2.30 -> spread should be 2.0 * 2.30 = 4.60m (clamped from 20.0m)
        assert exported.dimensions.canopy_spread_m == pytest.approx(4.60, rel=1e-2)

    def test_exact_bounds_scaling(self, tmp_path):
        """Exact bounds scaling scales spread independently to match target canopy spread."""
        species = create_dummy_species(height_m=10.0, canopy_spread_m=8.0)
        mesh = create_cylinder_mesh(radius=1.0, height=5.0) # curr spread 2.0, curr height 5.0
        config = PostProcessorConfig(scaling_strategy="exact_bounds")
        processor = AssetPostProcessor(config=config)
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")

        exported = processor.process_asset(raw, species, output_dir=tmp_path)
        assert exported.dimensions.height_m == pytest.approx(10.0, rel=1e-3)
        assert exported.dimensions.canopy_spread_m == pytest.approx(8.0, rel=1e-2)


# ==============================================================================
# 9. COMPANION OBJ & MTL SYNTAX VALIDATION
# ==============================================================================

class TestWavefrontObjMtlSyntax:
    """Stress tests OBJ 1-indexing, mtllib linkage, and relative texture paths."""

    def test_obj_indexing_and_mtl_references(self, tmp_path):
        species = create_dummy_species()
        mesh = create_cylinder_mesh(radius=0.5, height=4.0)
        raw = make_raw_asset(mesh=mesh, textures={}, source="procedural")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        obj_content = exported.obj_path.read_text(encoding="utf-8")
        mtl_content = exported.mtl_path.read_text(encoding="utf-8")

        # 1. mtllib and usemtl
        assert f"mtllib {species.species_id}.mtl" in obj_content
        assert f"usemtl M_{species.species_id}" in obj_content

        # 2. 1-indexed faces (no vertex index 0, max index equals vertex count)
        v_lines = [l for l in obj_content.splitlines() if l.startswith("v ")]
        f_lines = [l for l in obj_content.splitlines() if l.startswith("f ")]
        total_v = len(v_lines)

        for f_line in f_lines:
            tokens = f_line.split()[1:]
            for tok in tokens:
                v_idx = int(tok.split("/")[0])
                assert 1 <= v_idx <= total_v, f"Face index {v_idx} out of range [1, {total_v}]"

        # 3. MTL contains relative texture paths
        assert "map_Kd textures/albedo.png" in mtl_content
        assert "map_Bump -bm 1.0 textures/normal.png" in mtl_content
        assert "map_Pr textures/roughness.png" in mtl_content
        assert "map_Pm textures/metallic.png" in mtl_content


# ==============================================================================
# 10. HIGH-POLY MESH (>65,535 VERTICES) & UINT32 INDEXING
# ==============================================================================

class TestHighPolyMeshUint32Indexing:
    """Stress tests meshes exceeding 65,535 vertices requiring uint32 GLB accessor componentType 5125."""

    def test_70k_vertices_uint32_glb_and_obj_roundtrip(self, tmp_path):
        """Builds a dense mesh with ~70,000 vertices and verifies uint32 GLB and OBJ export."""
        mesh = MeshGeometry()
        # Create a dense grid: 270 x 260 = 70,200 vertices
        rows, cols = 270, 260
        for r in range(rows):
            for c in range(cols):
                x = (c / cols) * 2.0 - 1.0
                y = (r / rows) * 2.0 - 1.0
                z = (r / rows) * 5.0
                mesh.add_vertex((x, y, z), (0.0, 0.0, 1.0), (c / cols, r / rows))

        for r in range(rows - 1):
            for c in range(cols - 1):
                v0 = r * cols + c
                v1 = r * cols + (c + 1)
                v2 = (r + 1) * cols + (c + 1)
                v3 = (r + 1) * cols + c
                mesh.add_triangle(v0, v1, v2)
                mesh.add_triangle(v0, v2, v3)

        num_verts = len(mesh.vertices)
        assert num_verts > 65535, f"Mesh should have > 65535 vertices, got {num_verts}"

        species = create_dummy_species(height_m=8.0, species_id="dense_highpoly")
        raw = make_raw_asset(mesh=mesh, source="procedural")

        exported = process_and_export(raw, species, output_dir=tmp_path)
        assert exported.is_valid()
        assert exported.vertex_count == num_verts

        # Inspect GLB indices accessor componentType
        gltf, _ = unpack_glb_header_and_json(exported.glb_path)
        idx_accessor = gltf["accessors"][3]
        assert idx_accessor["componentType"] == 5125, f"Expected uint32 (5125), got {idx_accessor['componentType']}"
        assert idx_accessor["count"] == len(mesh.faces) * 3

        # Verify load_mesh_from_glb reads it back with exact vertex count
        reloaded = load_mesh_from_glb(exported.glb_path)
        assert len(reloaded.vertices) == num_verts
        assert len(reloaded.faces) == len(mesh.faces)


# ==============================================================================
# 11. INPUT MESH IMMUTABILITY (PURITY & SIDE-EFFECT SAFETY)
# ==============================================================================

class TestInputMeshImmutability:
    """Verifies that process_asset does NOT mutate the input raw_asset.mesh in-place."""

    def test_raw_asset_mesh_unaltered_after_processing(self, tmp_path):
        initial_verts = [
            (-2.0, -2.0, 50.0),
            (2.0, -2.0, 50.0),
            (0.0, 2.0, 60.0),
        ]
        mesh = MeshGeometry()
        for v in initial_verts:
            mesh.add_vertex(v, (0.0, 0.0, 1.0), (0.0, 0.0))
        mesh.add_triangle(0, 1, 2)

        raw = make_raw_asset(mesh=mesh, source="procedural")
        species = create_dummy_species(height_m=10.0, species_id="immutability_test")

        # Record vertex copy
        verts_before = list(raw.mesh.vertices)

        exported = process_and_export(raw, species, output_dir=tmp_path)
        assert exported.is_valid()

        # Check raw_asset.mesh vertices are identical
        verts_after = list(raw.mesh.vertices)
        assert verts_before == verts_after, "Input mesh was mutated in-place by post_processor!"
        assert raw.mesh.vertices[0][2] == 50.0, "Raw asset mesh Z was modified!"


# ==============================================================================
# 12. IDEMPOTENCY AND ROUND-TRIP STABILITY
# ==============================================================================

class TestIdempotencyAndRoundTrip:
    """Verifies that re-processing an already normalized exported asset preserves metrics identically."""

    def test_reprocessing_exported_asset_is_idempotent(self, tmp_path):
        species = create_dummy_species(height_m=8.0, canopy_spread_m=4.0, species_id="idempotency_test")
        mesh = create_cylinder_mesh(radius=0.5, height=4.0, offset=(10.0, -10.0, -20.0))
        raw = make_raw_asset(mesh=mesh, source="procedural")

        # Pass 1
        exp1 = process_and_export(raw, species, output_dir=tmp_path / "pass1")
        assert exp1.is_valid()

        # Load exported GLB and pass into process_and_export again
        mesh_pass1 = load_mesh_from_glb(exp1.glb_path)
        raw_pass2 = make_raw_asset(mesh=mesh_pass1, source="procedural")
        exp2 = process_and_export(raw_pass2, species, output_dir=tmp_path / "pass2")
        assert exp2.is_valid()

        # Height and spread must be identical
        assert exp2.dimensions.height_m == pytest.approx(exp1.dimensions.height_m, abs=1e-3)
        assert exp2.dimensions.canopy_spread_m == pytest.approx(exp1.dimensions.canopy_spread_m, abs=1e-3)
        assert exp2.ground_pivot_z == pytest.approx(exp1.ground_pivot_z, abs=1e-5)
        assert exp2.base_centroid[0] == pytest.approx(exp1.base_centroid[0], abs=1e-4)
        assert exp2.base_centroid[1] == pytest.approx(exp1.base_centroid[1], abs=1e-4)


# ==============================================================================
# 13. ANISOTROPIC NORMAL TRANSFORMATION MATHEMATICAL CORRECTNESS
# ==============================================================================

class TestAnisotropicNormalTransformation:
    """Verifies normal vectors are mathematically orthogonal to surface tangents under anisotropic scaling."""

    def test_anisotropic_normal_orthogonality(self):
        mesh = MeshGeometry()
        # Create a sloped triangle in plane: Z = X + Y
        # Tangents: t1 = (1, 0, 1), t2 = (0, 1, 1)
        # Normal n = (-1, -1, 1) / sqrt(3)
        inv_sqrt3 = 1.0 / math.sqrt(3.0)
        n0 = (-inv_sqrt3, -inv_sqrt3, inv_sqrt3)
        mesh.add_vertex((0.0, 0.0, 0.0), n0, (0.0, 0.0))
        mesh.add_vertex((1.0, 0.0, 1.0), n0, (1.0, 0.0))
        mesh.add_vertex((0.0, 1.0, 1.0), n0, (0.0, 1.0))
        mesh.add_triangle(0, 1, 2)

        species = create_dummy_species(height_m=5.0, canopy_spread_m=10.0)
        # Force anisotropic scaling via aspect_constrained with aspect_clamp=0.5
        scaled_mesh, _, _, _ = normalize_metric_scale(
            mesh, species, strategy="aspect_constrained", aspect_clamp=0.5
        )

        # Scaled vertices
        v0 = np.array(scaled_mesh.vertices[0])
        v1 = np.array(scaled_mesh.vertices[1])
        v2 = np.array(scaled_mesh.vertices[2])

        edge1 = v1 - v0
        edge2 = v2 - v0
        scaled_normal = np.array(scaled_mesh.normals[0])

        # Dot product with surface edges must be zero (orthogonal)
        dot1 = float(np.dot(scaled_normal, edge1))
        dot2 = float(np.dot(scaled_normal, edge2))

        assert abs(dot1) <= 1e-4, f"Normal not orthogonal to edge 1: dot={dot1}"
        assert abs(dot2) <= 1e-4, f"Normal not orthogonal to edge 2: dot={dot2}"
        # Unit length
        norm_len = float(np.linalg.norm(scaled_normal))
        assert norm_len == pytest.approx(1.0, abs=1e-5)


# ==============================================================================
# 14. ORM CHANNEL PACKING FIDELITY
# ==============================================================================

class TestORMChannelPackingFidelity:
    """Verifies that pack_metallic_roughness maps R=Occlusion(255), G=Roughness, B=Metallic correctly."""

    def test_orm_channel_order_and_values(self):
        # Create gradient test textures
        w, h = 64, 64
        r_val = 142
        m_val = 210

        r_img = Image.new("L", (w, h), r_val)
        m_img = Image.new("L", (w, h), m_val)

        orm = pack_metallic_roughness(r_img, m_img)
        assert orm.mode == "RGB"
        assert orm.size == (w, h)

        orm_arr = np.array(orm)
        assert np.all(orm_arr[:, :, 0] == 255), "Red channel must be Occlusion (255)"
        assert np.all(orm_arr[:, :, 1] == r_val), f"Green channel must be Roughness ({r_val})"
        assert np.all(orm_arr[:, :, 2] == m_val), f"Blue channel must be Metallic ({m_val})"


# ==============================================================================
# 15. PATHS WITH SPACES AND CUSTOM DIRECTORIES
# ==============================================================================

class TestSpecialPathHandling:
    """Verifies that output paths containing spaces or custom directories are handled robustly."""

    def test_output_path_with_spaces(self, tmp_path):
        custom_dir = tmp_path / "My Custom Vegetation Library Output"
        species = get_species("veg_conifer_pine_01")
        mesh = create_cylinder_mesh(radius=0.5, height=5.0)
        raw = make_raw_asset(mesh=mesh, source="procedural")

        exported = process_and_export(raw, species, output_dir=custom_dir)
        assert exported.is_valid()
        assert "My Custom Vegetation Library Output" in str(exported.glb_path)
        assert exported.glb_path.is_file()
        assert exported.obj_path.is_file()
        assert exported.mtl_path.is_file()
        assert exported.manifest_path.is_file()

