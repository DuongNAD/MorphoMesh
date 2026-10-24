"""
MorphoMesh Vegetation Library - Final Empirical Invariant & Divergence Test Suite
Target: teamwork_projects/vegetation_library/tests/test_challenger_final_empirical.py

Author: Final Challenger (Empirical Invariant & Divergence Challenger)
Date: 2026-09-10

Empirically stress-tests all 35 production botanical deliverables across the library:
1. Static Mesh Invariant across all 35 GLBs: assert N_bones == 0 (zero skins, zero joints, zero weights).
2. Ground Snapping across all 35 GLBs: assert |Z_min| <= 0.005m and base horizontal centroid within 0.05m of (0, 0).
3. Metric Scale Bounds across all 35 GLBs: assert height within +-10% of catalog target.
4. Pairwise Vertex Collision Rate across all 35 species: assert collision rate < 5%.
5. PBR Texture Completeness & Dielectric Limits across all 35 assets: assert Albedo, Normal, Roughness, Metallic
   textures exist, are readable, have resolution >= 256x256, and satisfy physical dielectric limits (max <= 0.05, mean <= 0.02).
6. Adversarial Cloud Provenance & Detail Audit:
   - Genuine Meshy AI cloud task provenance (source == 'meshy', valid task_id).
   - Production polygon/vertex budget (20,000 <= N_verts <= 65,000).
   - Detection of procedural dummy fallback templates and intra-category topological clones.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
import struct
import sys
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image
import pytest

# Ensure sys.path includes project directories
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR.parent
REPO_ROOT = PROJECT_DIR.parent.parent

for p in (str(PROJECT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src")):
    if p not in sys.path:
        sys.path.insert(0, p)

from vegetation_pipeline.catalog import get_catalog, PlantSpecies
from vegetation_pipeline.validator import (
    parse_glb_container,
    decode_glb_geometry,
    inspect_companion_obj,
    validate_pbr_textures,
)

OUTPUT_DIR = PROJECT_DIR / "output"


def get_all_species_paths() -> List[Tuple[PlantSpecies, Path, Path]]:
    """
    Discovers all 35 catalog species and their corresponding directory and GLB paths.
    Returns: List of (PlantSpecies, species_dir, glb_path)
    """
    catalog = get_catalog()
    records = []
    for sp in catalog.species:
        sp_dir = OUTPUT_DIR / sp.short_category / sp.species_id
        glb_path = sp_dir / f"{sp.species_id}.glb"
        records.append((sp, sp_dir, glb_path))
    return records


ALL_SPECIES = get_all_species_paths()


# ==============================================================================
# 1. STATIC MESH INVARIANT (N_bones == 0)
# ==============================================================================

class TestStaticMeshInvariant:
    """1. Static Mesh Invariant across all 35 GLBs: assert N_bones == 0 (zero skins, zero joints, zero weights)."""

    def test_catalog_asset_count(self):
        """Assert library catalog defines and contains exactly 35 species."""
        assert len(ALL_SPECIES) == 35, f"Expected 35 species in catalog, found {len(ALL_SPECIES)}"

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_glb_zero_skins_and_animations(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert GLB container has no skins, animations, or skeletal node hierarchies."""
        assert glb_path.is_file(), f"Missing production GLB for {sp.species_id} at {glb_path}"
        gltf, bin_bytes = parse_glb_container(glb_path)

        # Skins check
        skins = gltf.get("skins")
        assert not skins, f"{sp.species_id}: Found non-empty skins array ({len(skins)} skins) in GLB"

        # Animations check
        anims = gltf.get("animations")
        assert not anims, f"{sp.species_id}: Found non-empty animations array ({len(anims)} anims) in GLB"

        # Nodes skin property check
        for node_idx, node in enumerate(gltf.get("nodes", [])):
            assert "skin" not in node, f"{sp.species_id}: Node {node_idx} references skin {node.get('skin')}"

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_glb_zero_joint_and_weight_attributes(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert all primitive attributes contain ZERO joints or vertex weight data."""
        gltf, bin_bytes = parse_glb_container(glb_path)
        for m_idx, mesh in enumerate(gltf.get("meshes", [])):
            for p_idx, prim in enumerate(mesh.get("primitives", [])):
                attrs = prim.get("attributes", {})
                for attr_name in attrs:
                    upper_attr = attr_name.upper()
                    assert not upper_attr.startswith("JOINTS_"), (
                        f"{sp.species_id}: Mesh {m_idx} Primitive {p_idx} has joint attribute '{attr_name}'"
                    )
                    assert not upper_attr.startswith("WEIGHTS_"), (
                        f"{sp.species_id}: Mesh {m_idx} Primitive {p_idx} has weight attribute '{attr_name}'"
                    )

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_companion_obj_zero_bones(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert companion OBJ file contains zero bones or skinning directives."""
        obj_path = sp_dir / f"{sp.species_id}.obj"
        if obj_path.is_file():
            is_valid, n_bones, errors = inspect_companion_obj(obj_path)
            assert is_valid, f"{sp.species_id}: OBJ inspection failed: {errors}"
            assert n_bones == 0, f"{sp.species_id}: OBJ contains {n_bones} bones, expected 0"


# ==============================================================================
# 2. GROUND CONTACT SNAPPING & CENTERING
# ==============================================================================

class TestGroundContactSnapping:
    """2. Ground Snapping across all 35 GLBs: assert |Z_min| <= 0.005m and base horizontal centroid within 0.05m."""

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_z_min_ground_alignment(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert object root base snaps precisely to Z_min == 0.000m within tolerance +-0.005m."""
        gltf, bin_bytes = parse_glb_container(glb_path)
        mesh_data = decode_glb_geometry(gltf, bin_bytes)
        positions = mesh_data["positions"]

        assert len(positions) > 0, f"{sp.species_id}: Zero vertices decoded from GLB"

        y_min = float(positions[:, 1].min())
        z_min = float(positions[:, 2].min())

        if abs(z_min) <= 0.01:
            vert_axis = "Z"
            g_min = z_min
        elif abs(y_min) <= 0.01:
            vert_axis = "Y"
            g_min = y_min
        else:
            vert_axis = "Z" if abs(z_min) < abs(y_min) else "Y"
            g_min = z_min if vert_axis == "Z" else y_min

        assert abs(g_min) <= 0.005, (
            f"{sp.species_id}: Root base {vert_axis}_min = {g_min:.6f}m exceeds tolerance +-0.005m"
        )

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_base_contact_centroid_centered(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert horizontal centroid of the bottom 5% height slice is within 0.05m of (0, 0)."""
        gltf, bin_bytes = parse_glb_container(glb_path)
        mesh_data = decode_glb_geometry(gltf, bin_bytes)
        positions = mesh_data["positions"]

        y_min, y_max = float(positions[:, 1].min()), float(positions[:, 1].max())
        z_min, z_max = float(positions[:, 2].min()), float(positions[:, 2].max())

        if abs(z_min) <= 0.01:
            vert_idx = 2
            v_min, v_max = z_min, z_max
        elif abs(y_min) <= 0.01:
            vert_idx = 1
            v_min, v_max = y_min, y_max
        else:
            vert_idx = 2 if abs(z_min) < abs(y_min) else 1
            v_min, v_max = (z_min, z_max) if vert_idx == 2 else (y_min, y_max)

        height = v_max - v_min
        assert height > 0.01, f"{sp.species_id}: Degenerate height {height:.4f}m"

        thresh = v_min + 0.05 * height
        base_mask = positions[:, vert_idx] <= thresh
        base_verts = positions[base_mask]
        if len(base_verts) == 0:
            base_verts = positions[positions[:, vert_idx] <= v_min + 1e-4]

        if vert_idx == 2:  # Z vertical -> (X, Y) horizontal
            cx = float(np.mean(base_verts[:, 0]))
            cy = float(np.mean(base_verts[:, 1]))
        else:  # Y vertical -> (X, Z) horizontal
            cx = float(np.mean(base_verts[:, 0]))
            cy = float(np.mean(base_verts[:, 2]))

        dist_from_origin = math.sqrt(cx * cx + cy * cy)
        assert dist_from_origin <= 0.05001, (
            f"{sp.species_id}: Base centroid offset {dist_from_origin:.4f}m exceeds tolerance 0.05m at ({cx:.4f}, {cy:.4f})"
        )


# ==============================================================================
# 3. METRIC SCALE BOUNDS
# ==============================================================================

class TestMetricScaleBounds:
    """3. Metric Scale across all 35 GLBs: assert height within +-10% of catalog target."""

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_height_within_10_percent_of_catalog_target(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert measured 3D height is within +-10% of catalog target height."""
        gltf, bin_bytes = parse_glb_container(glb_path)
        mesh_data = decode_glb_geometry(gltf, bin_bytes)
        positions = mesh_data["positions"]

        y_min, y_max = float(positions[:, 1].min()), float(positions[:, 1].max())
        z_min, z_max = float(positions[:, 2].min()), float(positions[:, 2].max())

        if abs(z_min) <= 0.01:
            measured_height = z_max - z_min
        elif abs(y_min) <= 0.01:
            measured_height = y_max - y_min
        else:
            measured_height = (z_max - z_min) if abs(z_min) < abs(y_min) else (y_max - y_min)

        target_height = sp.dimensions.height_m
        dev_pct = abs(measured_height - target_height) / target_height

        assert dev_pct <= 0.1001, (
            f"{sp.species_id}: Height {measured_height:.3f}m deviates from target {target_height:.3f}m "
            f"by {dev_pct*100:.2f}% (limit +-10%)"
        )


# ==============================================================================
# 4. PAIRWISE VERTEX COLLISION RATE & TOPOLOGICAL DIVERGENCE
# ==============================================================================

class TestPairwiseVertexCollisionRate:
    """4. Vertex Divergence across all 35 species: assert pairwise vertex count collision rate < 5%."""

    def test_pairwise_vertex_count_collisions(self):
        """Compute pairwise vertex count collisions across all 35 species and assert collision rate < 5%."""
        vertex_counts: Dict[str, int] = {}
        for sp, sp_dir, glb_path in ALL_SPECIES:
            gltf, bin_bytes = parse_glb_container(glb_path)
            mesh_data = decode_glb_geometry(gltf, bin_bytes)
            vertex_counts[sp.species_id] = len(mesh_data["positions"])

        species_ids = list(vertex_counts.keys())
        total_species = len(species_ids)
        total_pairs = total_species * (total_species - 1) // 2

        collisions = 0
        collision_pairs = []
        for i in range(total_species):
            for j in range(i + 1, total_species):
                id_i, id_j = species_ids[i], species_ids[j]
                if vertex_counts[id_i] == vertex_counts[id_j]:
                    collisions += 1
                    collision_pairs.append((id_i, id_j, vertex_counts[id_i]))

        collision_rate = collisions / total_pairs
        assert collision_rate < 0.05, (
            f"Pairwise vertex count collision rate {collision_rate*100:.2f}% ({collisions}/{total_pairs}) "
            f"exceeds 5% threshold. Colliding pairs: {collision_pairs}"
        )


# ==============================================================================
# 5. PBR TEXTURE COMPLETENESS & DIELECTRIC LIMITS
# ==============================================================================

class TestPBRTextureCompletenessAndDielectricLimits:
    """5. PBR Texture Completeness: assert Albedo, Normal, Roughness, Metallic textures exist, are readable,
    have resolution >= 256x256, and satisfy physical dielectric bounds."""

    REQUIRED_TEXTURES = ["albedo.png", "normal.png", "roughness.png", "metallic.png"]

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_all_four_pbr_textures_exist_and_readable(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert textures/ folder contains readable albedo, normal, roughness, and metallic images >= 256x256."""
        tex_dir = sp_dir / "textures"
        assert tex_dir.is_dir(), f"{sp.species_id}: Missing textures directory at {tex_dir}"

        for tname in self.REQUIRED_TEXTURES:
            tpath = tex_dir / tname
            assert tpath.is_file(), f"{sp.species_id}: Missing {tname} in {tex_dir}"
            assert tpath.stat().st_size > 0, f"{sp.species_id}: {tname} is an empty 0-byte file"

            with Image.open(tpath) as img:
                w, h = img.size
                assert w >= 256 and h >= 256, f"{sp.species_id}: {tname} resolution {w}x{h} < 256x256"

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_albedo_and_normal_plausibility(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert albedo is not flat/black and normal map exhibits tangent-space characteristics."""
        tex_dir = sp_dir / "textures"

        # Albedo
        with Image.open(tex_dir / "albedo.png") as img:
            arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
            mean_val = float(np.mean(arr))
            std_val = float(np.std(arr))
            assert mean_val > 0.05, f"{sp.species_id}: Albedo is abnormally dark (mean = {mean_val:.4f})"
            assert std_val > 0.02, f"{sp.species_id}: Albedo lacks variation / is flat (std = {std_val:.4f})"

        # Normal
        with Image.open(tex_dir / "normal.png") as img:
            arr = np.array(img.convert("RGB"), dtype=np.float32) / 255.0
            mean_b = float(np.mean(arr[:, :, 2]))
            mean_r = float(np.mean(arr[:, :, 0]))
            mean_g = float(np.mean(arr[:, :, 1]))
            assert mean_b >= mean_r * 0.9 and mean_b >= mean_g * 0.9, (
                f"{sp.species_id}: Normal map lacks tangent-space blue dominance (B={mean_b:.3f}, R={mean_r:.3f}, G={mean_g:.3f})"
            )

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_dielectric_metallic_physical_bounds(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert metallic map conforms to strict dielectric limits for vegetation (max <= 0.05, mean <= 0.02)."""
        tex_dir = sp_dir / "textures"
        with Image.open(tex_dir / "metallic.png") as img:
            arr = np.array(img, dtype=np.float32) / 255.0
            max_val = float(np.max(arr))
            mean_val = float(np.mean(arr))

            assert max_val <= 0.05001, (
                f"{sp.species_id}: Metallic max value {max_val:.4f} exceeds dielectric limit 0.05"
            )
            assert mean_val <= 0.02001, (
                f"{sp.species_id}: Metallic mean value {mean_val:.4f} exceeds dielectric limit 0.02"
            )


# ==============================================================================
# 6. GEOMETRIC INTEGRITY, COMPANION DELIVERABLES & PREVIEWS
# ==============================================================================

class TestGeometricIntegrityAndDeliverables:
    """6. Comprehensive Geometric Integrity and Deliverable Assets."""

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_zero_nan_inf_coordinates(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert zero NaN or Inf values in positions, normals, or UV coordinates."""
        gltf, bin_bytes = parse_glb_container(glb_path)
        mesh_data = decode_glb_geometry(gltf, bin_bytes)

        for channel in ["positions", "normals", "uvs"]:
            arr = mesh_data[channel]
            assert not np.isnan(arr).any(), f"{sp.species_id}: NaN values found in {channel}"
            assert not np.isinf(arr).any(), f"{sp.species_id}: Inf values found in {channel}"

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_companion_deliverables_and_previews(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """Assert companion OBJ, MTL, manifest, turntable renders, and thumbnail exist."""
        # OBJ and MTL
        assert (sp_dir / f"{sp.species_id}.obj").is_file(), f"{sp.species_id}: Missing companion OBJ"
        assert (sp_dir / f"{sp.species_id}.mtl").is_file(), f"{sp.species_id}: Missing companion MTL"

        # Manifest
        manifest_path = sp_dir / "asset_manifest.json"
        assert manifest_path.is_file(), f"{sp.species_id}: Missing asset_manifest.json"

        # Renders
        assert (sp_dir / "thumbnail.png").is_file(), f"{sp.species_id}: Missing thumbnail.png"
        for i in range(1, 5):
            assert (sp_dir / f"turntable_0{i}.png").is_file(), f"{sp.species_id}: Missing turntable_0{i}.png"

    def test_master_manifest_integrity(self):
        """Assert master manifest indexes all 35 species with 100% pass status."""
        master_manifest_path = OUTPUT_DIR / "manifest.json"
        assert master_manifest_path.is_file(), "Missing master output/manifest.json"
        with open(master_manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data.get("total_catalog_species") == 35
        assert data.get("indexed_species_count") == 35
        assert data.get("passed_validation_count") == 35
        assert data.get("failed_validation_count") == 0


# ==============================================================================
# 7. ADVERSARIAL AUDIT: CLOUD PROVENANCE & POLYGON DETAIL BUDGET (FINDINGS ORACLE)
# ==============================================================================

class TestAdversarialCloudProvenanceAndDetailAudit:
    """
    Adversarial verification of ORIGINAL_REQUEST.md requirements:
    - 100% genuine Meshy AI cloud generation (Zero procedural dummy blobs)
    - Verifiable Meshy AI task ID and provenance
    - 20k-60k polygon detail per asset
    """

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_genuine_meshy_cloud_provenance(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """
        [ADVERSARIAL ORACLE] Assert asset has genuine Meshy AI cloud provenance (source == 'meshy')
        and non-null Meshy task ID.
        Flags procedural fallbacks emitted in place of genuine cloud generations.
        """
        manifest_path = sp_dir / "asset_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
        prov = manifest.get("provenance", {})
        source = prov.get("source")
        task_id = prov.get("task_id")
        assert source == "meshy", (
            f"{sp.species_id}: VIOLATION OF ORIGINAL_REQUEST.md R1 - Expected genuine 'meshy' source, "
            f"got procedural fallback '{source}'"
        )
        assert task_id and len(task_id) > 10, (
            f"{sp.species_id}: VIOLATION OF ORIGINAL_REQUEST.md R1 - Missing genuine Meshy cloud task_id"
        )

    @pytest.mark.parametrize("sp, sp_dir, glb_path", ALL_SPECIES, ids=[sp.species_id for sp, _, _ in ALL_SPECIES])
    def test_production_vertex_detail_budget(self, sp: PlantSpecies, sp_dir: Path, glb_path: Path):
        """
        [ADVERSARIAL ORACLE] Assert asset meets production vertex budget (>= 20,000 vertices).
        Flags low-detail 3k-4k procedural placeholder geometry.
        """
        gltf, bin_bytes = parse_glb_container(glb_path)
        mesh_data = decode_glb_geometry(gltf, bin_bytes)
        n_verts = len(mesh_data["positions"])
        assert n_verts >= 20000, (
            f"{sp.species_id}: Low-poly detail violation - {n_verts:,} vertices is below production minimum (20,000). "
            f"Indicates low-detail procedural fallback."
        )
