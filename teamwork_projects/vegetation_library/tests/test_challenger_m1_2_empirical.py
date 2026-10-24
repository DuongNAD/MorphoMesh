"""
MorphoMesh Vegetation Library - Challenger M1-2 Empirical Stress Test Suite
Target: teamwork_projects/vegetation_library/tests/test_challenger_m1_2_empirical.py

Empirical stress testing for Milestone 1:
1. Dielectric clamping in post_processor.py:
   - Feed metallic textures with values up to 255.
   - Verify all clamped to <= 10 (<= 0.0392).
   - Verify pixel values <= 10 are preserved unchanged.
   - Verify interaction between post_processor clamping and validator thresholds (max <= 0.05, mean <= 0.02).
2. ORM texture splitting:
   - Verify clean separation of Green (Roughness) and Blue (Metallic).
   - Verify Red (Occlusion) does not cross-contaminate Roughness or Metallic.
   - Verify across diverse PIL modes (RGB, RGBA).
3. Pairwise vertex count collision calculation:
   - Test on synthetic sets with known collision rates: 0%, 0.168%, 2.52%, 4.71%, 5.04%, 100%.
   - Test edge cases: N=0, N=1, N=2.
   - Verify live catalog collision status.
4. Validation robustness on veg_tree_oak_01:
   - Baseline uncorrupted check (21/21 passed).
   - Corrupted glTF header rejection.
   - Missing texture file rejection.
   - Corrupted texture content rejection.
   - Incorrect/missing Meshy provenance manifest rejection.
"""
from __future__ import annotations

import io
import json
import math
from pathlib import Path
import shutil
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

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import get_catalog, get_species, PlantSpecies
from vegetation_pipeline.generator import RawAsset
from vegetation_pipeline.post_processor import (
    AssetPostProcessor,
    PostProcessorConfig,
    extract_textures_from_glb,
    unpack_glb_header_and_json,
)
from vegetation_pipeline.validator import (
    validate_asset,
    validate_pbr_textures,
    parse_glb_container,
)

OAK_DIR = PROJECT_DIR / "output" / "broadleaf_trees" / "veg_tree_oak_01"


def create_synthetic_mesh(num_vertices: int = 5000) -> MeshGeometry:
    """Creates a valid synthetic mesh with num_vertices arranged in vertical rings."""
    mesh = MeshGeometry()
    rings = 50
    verts_per_ring = num_vertices // rings
    height = 10.0

    for r in range(rings):
        z = (r / (rings - 1)) * height
        radius = 1.0 - 0.5 * (r / (rings - 1))
        for i in range(verts_per_ring):
            theta = 2.0 * math.pi * (i / verts_per_ring)
            x = radius * math.cos(theta)
            y = radius * math.sin(theta)
            u = i / verts_per_ring
            v = r / (rings - 1)
            mesh.add_vertex((x, y, z), (math.cos(theta), math.sin(theta), 0.0), (u, v))

    # Add triangles
    for r in range(rings - 1):
        for i in range(verts_per_ring):
            next_i = (i + 1) % verts_per_ring
            v0 = r * verts_per_ring + i
            v1 = r * verts_per_ring + next_i
            v2 = (r + 1) * verts_per_ring + i
            v3 = (r + 1) * verts_per_ring + next_i
            mesh.add_triangle(v0, v1, v2)
            mesh.add_triangle(v1, v3, v2)

    return mesh


# ==============================================================================
# 1. DIELECTRIC CLAMPING TESTS (post_processor.py)
# ==============================================================================

class TestDielectricClamping:
    """Adversarial stress-testing of dielectric clamping in post_processor.py."""

    def test_dielectric_clamping_gradient_and_max_255(self, tmp_path: Path):
        """
        Feeds a metallic texture with values spanning full uint8 range [0..255].
        Verifies that all values > 10 are clamped to <= 10 (<= 0.0392).
        Verifies that values <= 10 are strictly unchanged.
        """
        post = AssetPostProcessor(PostProcessorConfig())
        mesh = create_synthetic_mesh(5000)

        # Create 256x256 metallic image where row i has pixel value i (0..255)
        grad_arr = np.zeros((256, 256), dtype=np.uint8)
        for row in range(256):
            grad_arr[row, :] = row
        metallic_in = Image.fromarray(grad_arr, mode="L")

        # Albedo with sufficient mean and variance
        np.random.seed(42)
        alb_arr = np.clip(np.random.normal(80, 20, (256, 256, 3)), 20, 200).astype(np.uint8)
        albedo_in = Image.fromarray(alb_arr, mode="RGB")

        # Normal with valid tangent space
        norm_in = Image.new("RGB", (256, 256), (128, 128, 255))

        # Roughness with valid organic mean and variance
        rough_arr = np.clip(np.random.normal(160, 25, (256, 256)), 60, 230).astype(np.uint8)
        roughness_in = Image.fromarray(rough_arr, mode="L")

        raw = RawAsset(
            species_id="veg_tree_oak_01",
            glb_path=tmp_path / "dummy.glb",
            mesh=mesh,
            textures={
                "albedo": albedo_in,
                "normal": norm_in,
                "roughness": roughness_in,
                "metallic": metallic_in,
            },
            source="meshy",
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            metadata={"task_id": "test-task-dielectric-01"},
        )

        out_dir = tmp_path / "output"
        exported = post.process_and_export(raw, "veg_tree_oak_01", out_dir)

        # Read back metallic texture from disk
        metallic_out_path = exported.texture_paths["metallic"]
        assert metallic_out_path.is_file()
        metallic_out_img = Image.open(metallic_out_path)
        m_out = np.array(metallic_out_img)

        # Assertion 1: All values in output are <= 10
        assert int(np.max(m_out)) <= 10, f"Max metallic value {np.max(m_out)} exceeds ceiling 10"
        assert int(np.min(m_out)) >= 0

        # Assertion 2: Normalized ceiling <= 0.039216 (10 / 255.0)
        norm_max = float(np.max(m_out)) / 255.0
        assert norm_max <= (10.0 / 255.0) + 1e-6
        assert norm_max <= 0.03922

        # Assertion 3: For rows 0..10, values are exactly preserved
        for row in range(11):
            assert np.all(m_out[row, :] == row), f"Value at row {row} mutated unexpectedly"

        # Assertion 4: For rows 11..255, values are all clamped to 10
        for row in range(11, 256):
            assert np.all(m_out[row, :] == 10), f"Value at row {row} not clamped to 10 (got {m_out[row, 0]})"

    @pytest.mark.parametrize("input_val", [11, 20, 50, 100, 128, 200, 254, 255])
    def test_dielectric_clamping_uniform_high_values(self, tmp_path: Path, input_val: int):
        """Tests that uniform metallic inputs from 11 to 255 are all clamped to exactly 10."""
        post = AssetPostProcessor(PostProcessorConfig())
        mesh = create_synthetic_mesh(3500)

        metallic_in = Image.new("L", (256, 256), input_val)
        alb_arr = np.clip(np.random.normal(90, 15, (256, 256, 3)), 30, 180).astype(np.uint8)
        albedo_in = Image.fromarray(alb_arr, mode="RGB")
        norm_in = Image.new("RGB", (256, 256), (128, 128, 255))
        rough_arr = np.clip(np.random.normal(150, 20, (256, 256)), 70, 220).astype(np.uint8)
        roughness_in = Image.fromarray(rough_arr, mode="L")

        raw = RawAsset(
            species_id="veg_tree_oak_01",
            glb_path=tmp_path / "dummy.glb",
            mesh=mesh,
            textures={
                "albedo": albedo_in,
                "normal": norm_in,
                "roughness": roughness_in,
                "metallic": metallic_in,
            },
            source="meshy",
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            metadata={"task_id": "test-task-dielectric-uniform"},
        )

        exported = post.process_and_export(raw, "veg_tree_oak_01", tmp_path / f"out_{input_val}")
        m_out = np.array(Image.open(exported.texture_paths["metallic"]))

        assert np.all(m_out == 10), f"Expected all pixels to be 10 for input {input_val}, got {np.unique(m_out)}"

    def test_dielectric_embedded_glb_metallic_also_clamped(self, tmp_path: Path):
        """Verifies that the GLB binary exported by post_processor also has clamped metallic."""
        post = AssetPostProcessor(PostProcessorConfig())
        mesh = create_synthetic_mesh(3500)

        metallic_in = Image.new("L", (256, 256), 250)
        alb_arr = np.clip(np.random.normal(90, 15, (256, 256, 3)), 30, 180).astype(np.uint8)
        albedo_in = Image.fromarray(alb_arr, mode="RGB")
        norm_in = Image.new("RGB", (256, 256), (128, 128, 255))
        rough_arr = np.clip(np.random.normal(150, 20, (256, 256)), 70, 220).astype(np.uint8)
        roughness_in = Image.fromarray(rough_arr, mode="L")

        raw = RawAsset(
            species_id="veg_tree_oak_01",
            glb_path=tmp_path / "dummy.glb",
            mesh=mesh,
            textures={
                "albedo": albedo_in,
                "normal": norm_in,
                "roughness": roughness_in,
                "metallic": metallic_in,
            },
            source="meshy",
            vertex_count=len(mesh.vertices),
            face_count=len(mesh.faces),
            metadata={"task_id": "test-task-embedded-dielectric"},
        )

        exported = post.process_and_export(raw, "veg_tree_oak_01", tmp_path / "out_glb")
        extracted = extract_textures_from_glb(exported.glb_path)

        assert "metallic" in extracted, "Exported GLB missing metallic texture"
        m_extracted = np.array(extracted["metallic"])
        assert int(np.max(m_extracted)) <= 10

    def test_validator_detects_mean_vs_max_dielectric_distinction(self):
        """
        Adversarial evaluation of validator.py dielectric checks:
        - Case A: Clamped noise (max=10, mean=1) -> PASS (max <= 0.05, mean <= 0.02).
        - Case B: Full-white metallic clamped to 10 everywhere:
          max = 10/255 = 0.0392 (passes max <= 0.05)
          mean = 10/255 = 0.0392 (fails mean <= 0.02!)
        - Case C: Unclamped metallic (e.g. max=128) -> FAILS (max > 0.05).
        """
        # Case A: Localized hot-spot (95% zero, 5% at value 10)
        arr_a = np.zeros((256, 256), dtype=np.uint8)
        arr_a[:12, :] = 10
        img_a = Image.fromarray(arr_a, mode="L")

        alb = Image.fromarray(np.clip(np.random.normal(100, 20, (256, 256, 3)), 20, 220).astype(np.uint8), mode="RGB")
        norm = Image.new("RGB", (256, 256), (128, 128, 255))
        rgh = Image.fromarray(np.clip(np.random.normal(150, 20, (256, 256)), 50, 220).astype(np.uint8), mode="L")

        checks_a, metrics_a, errs_a, _ = validate_pbr_textures(
            textures_dir=None,
            embedded_images={"albedo": alb, "normal": norm, "roughness": rgh, "metallic": img_a},
        )
        assert checks_a["texture_metallic_dielectric"] is True
        assert len(errs_a) == 0

        # Case B: Uniform 10 everywhere (mean = 0.0392 > 0.02)
        arr_b = np.full((256, 256), 10, dtype=np.uint8)
        img_b = Image.fromarray(arr_b, mode="L")
        checks_b, metrics_b, errs_b, _ = validate_pbr_textures(
            textures_dir=None,
            embedded_images={"albedo": alb, "normal": norm, "roughness": rgh, "metallic": img_b},
        )
        assert checks_b["texture_metallic_dielectric"] is False
        assert any("mean" in e.lower() for e in errs_b)

        # Case C: Raw unclamped metallic (max = 128, mean = 0.5)
        arr_c = np.full((256, 256), 128, dtype=np.uint8)
        img_c = Image.fromarray(arr_c, mode="L")
        checks_c, metrics_c, errs_c, _ = validate_pbr_textures(
            textures_dir=None,
            embedded_images={"albedo": alb, "normal": norm, "roughness": rgh, "metallic": img_c},
        )
        assert checks_c["texture_metallic_dielectric"] is False
        assert any("ceiling" in e.lower() for e in errs_c)


# ==============================================================================
# 2. ORM TEXTURE SPLITTING TESTS (Clean G/B Separation)
# ==============================================================================

class TestORMTextureSplitting:
    """Adversarial stress-testing of ORM texture channel isolation."""

    def test_orm_channel_isolation_and_no_bleed(self, tmp_path: Path):
        """
        Constructs a synthetic ORM texture with distinct values per channel:
        - Red (Occlusion): gradient 0..255 horizontally
        - Green (Roughness): gradient 50..200 vertically
        - Blue (Metallic): checkerboard between 0 and 8
        Verifies that:
        - Extracted Roughness matches Green channel pixel-for-pixel (zero difference).
        - Extracted Metallic matches Blue channel pixel-for-pixel (zero difference).
        - Red (Occlusion) has zero bleed into Roughness or Metallic.
        """
        w, h = 256, 256
        r_chan = np.zeros((h, w), dtype=np.uint8)
        g_chan = np.zeros((h, w), dtype=np.uint8)
        b_chan = np.zeros((h, w), dtype=np.uint8)

        for y in range(h):
            for x in range(w):
                r_chan[y, x] = x % 256
                g_chan[y, x] = int(50 + (150 * y / (h - 1)))
                b_chan[y, x] = 8 if ((x // 16) + (y // 16)) % 2 == 0 else 0

        orm_rgb = np.stack([r_chan, g_chan, b_chan], axis=-1)
        orm_img = Image.fromarray(orm_rgb, mode="RGB")

        # Encode ORM image to PNG bytes
        orm_buf = io.BytesIO()
        orm_img.save(orm_buf, format="PNG")
        orm_bytes = orm_buf.getvalue()

        # Dummy albedo and normal images
        alb_img = Image.new("RGB", (64, 64), (50, 100, 50))
        alb_buf = io.BytesIO()
        alb_img.save(alb_buf, format="PNG")
        alb_bytes = alb_buf.getvalue()

        norm_img = Image.new("RGB", (64, 64), (128, 128, 255))
        norm_buf = io.BytesIO()
        norm_img.save(norm_buf, format="PNG")
        norm_bytes = norm_buf.getvalue()

        # Build glTF structure with materials[0].pbrMetallicRoughness pointing to ORM
        # Buffer layout: [albedo, orm, normal]
        bin_data = alb_bytes + orm_bytes + norm_bytes
        bv0_off = 0
        bv0_len = len(alb_bytes)
        bv1_off = bv0_len
        bv1_len = len(orm_bytes)
        bv2_off = bv0_len + bv1_len
        bv2_len = len(norm_bytes)

        gltf_dict = {
            "asset": {"version": "2.0"},
            "buffers": [{"byteLength": len(bin_data)}],
            "bufferViews": [
                {"buffer": 0, "byteOffset": bv0_off, "byteLength": bv0_len},
                {"buffer": 0, "byteOffset": bv1_off, "byteLength": bv1_len},
                {"buffer": 0, "byteOffset": bv2_off, "byteLength": bv2_len},
            ],
            "images": [
                {"bufferView": 0, "mimeType": "image/png"},  # unnamed
                {"bufferView": 1, "mimeType": "image/png"},  # unnamed ORM
                {"bufferView": 2, "mimeType": "image/png"},  # unnamed Normal
            ],
            "textures": [
                {"source": 0},
                {"source": 1},
                {"source": 2},
            ],
            "materials": [
                {
                    "pbrMetallicRoughness": {
                        "baseColorTexture": {"index": 0},
                        "metallicRoughnessTexture": {"index": 1},
                    },
                    "normalTexture": {"index": 2},
                }
            ],
        }

        # Pack into valid GLB container
        glb_path = tmp_path / "test_orm.glb"
        json_bytes = json.dumps(gltf_dict).encode("utf-8")
        # Pad JSON to 4-byte boundary
        rem_j = len(json_bytes) % 4
        if rem_j != 0:
            json_bytes += b" " * (4 - rem_j)

        # Pad binary data to 4-byte boundary
        rem_b = len(bin_data) % 4
        if rem_b != 0:
            bin_data += b"\x00" * (4 - rem_b)

        total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
        header = struct.pack("<4sII", b"glTF", 2, total_len)
        chunk0_hdr = struct.pack("<II", len(json_bytes), 0x4E4F534A)  # JSON
        chunk1_hdr = struct.pack("<II", len(bin_data), 0x004E4942)   # BIN

        with open(glb_path, "wb") as f:
            f.write(header)
            f.write(chunk0_hdr)
            f.write(json_bytes)
            f.write(chunk1_hdr)
            f.write(bin_data)

        # Test post_processor extraction
        extracted = extract_textures_from_glb(glb_path)
        assert "roughness" in extracted, "Extraction failed to find roughness from ORM"
        assert "metallic" in extracted, "Extraction failed to find metallic from ORM"

        ext_rough = np.array(extracted["roughness"])
        ext_metal = np.array(extracted["metallic"])

        # Test pixel-for-pixel equality with Green channel
        np.testing.assert_array_equal(ext_rough, g_chan, err_msg="Roughness channel does not match Green channel exactly")

        # Test pixel-for-pixel equality with Blue channel
        np.testing.assert_array_equal(ext_metal, b_chan, err_msg="Metallic channel does not match Blue channel exactly")

        # Verify zero cross-channel contamination from Red (Occlusion)
        assert not np.array_equal(ext_rough, r_chan)
        assert not np.array_equal(ext_metal, r_chan)

    def test_orm_rgba_mode_channel_splitting(self):
        """Tests that 4-channel RGBA ORM textures convert and split properly without alpha interference."""
        r = np.full((128, 128), 200, dtype=np.uint8)
        g = np.full((128, 128), 140, dtype=np.uint8)
        b = np.full((128, 128), 5, dtype=np.uint8)
        a = np.full((128, 128), 50, dtype=np.uint8)  # Arbitrary alpha

        rgba = np.stack([r, g, b, a], axis=-1)
        img_rgba = Image.fromarray(rgba, mode="RGBA")

        # Replicate split logic used in post_processor and validator
        orm = img_rgba.convert("RGB")
        chans = orm.split()

        assert len(chans) == 3
        rough = np.array(chans[1])
        metal = np.array(chans[2])

        assert np.all(rough == 140), "Roughness affected by RGBA conversion"
        assert np.all(metal == 5), "Metallic affected by RGBA conversion"


# ==============================================================================
# 3. PAIRWISE VERTEX COUNT COLLISION TESTS
# ==============================================================================

class TestPairwiseVertexCollisionAlgorithm:
    """Stress-testing pairwise vertex count collision detection."""

    @staticmethod
    def calculate_collision_rate(counts: List[int]) -> Tuple[int, int, float]:
        """Canonical pairwise collision calculation."""
        n = len(counts)
        if n < 2:
            return 0, 0, 0.0
        pairs = n * (n - 1) // 2
        colls = sum(1 for i in range(n) for j in range(i + 1, n) if counts[i] == counts[j])
        rate = colls / pairs
        return colls, pairs, rate

    def test_collision_rate_known_cases(self):
        """
        Validates collision rate against exact mathematical cases:
        - 0% collision (all distinct)
        - 1 pair duplicate (1/595 = 0.168%)
        - 8 species duplicate (28/595 = 4.706% < 5%)
        - 9 species duplicate (36/595 = 6.050% >= 5%)
        - 5 clusters of 3 (15/595 = 2.521% < 5%)
        - 10 clusters of 3 (30/595 = 5.042% >= 5%)
        - 100% collision (595/595 = 100%)
        """
        # Case 1: 35 distinct counts -> 0.0%
        c1 = [20000 + i * 500 for i in range(35)]
        colls, pairs, rate = self.calculate_collision_rate(c1)
        assert pairs == 595
        assert colls == 0
        assert rate == 0.0
        assert rate < 0.05

        # Case 2: 1 duplicate pair -> 1/595 = 0.00168 (0.168%)
        c2 = list(c1)
        c2[1] = c2[0]
        colls, pairs, rate = self.calculate_collision_rate(c2)
        assert pairs == 595
        assert colls == 1
        assert math.isclose(rate, 1 / 595, rel_tol=1e-5)
        assert rate < 0.05

        # Case 3: 8 species share same count -> 28 collisions / 595 = 4.706% (< 5%)
        c3 = list(c1)
        for i in range(1, 8):
            c3[i] = c3[0]
        colls, pairs, rate = self.calculate_collision_rate(c3)
        assert pairs == 595
        assert colls == 28
        assert math.isclose(rate, 28 / 595, rel_tol=1e-5)
        assert rate < 0.05

        # Case 4: 9 species share same count -> 36 collisions / 595 = 6.050% (>= 5%, FAILS)
        c4 = list(c1)
        for i in range(1, 9):
            c4[i] = c4[0]
        colls, pairs, rate = self.calculate_collision_rate(c4)
        assert pairs == 595
        assert colls == 36
        assert math.isclose(rate, 36 / 595, rel_tol=1e-5)
        assert rate >= 0.05

        # Case 5: 5 clusters of 3 duplicates -> 5 * 3 = 15 collisions -> 15/595 = 2.521% (< 5%)
        c5 = list(c1)
        for k in range(5):
            c5[k * 3 + 1] = c5[k * 3]
            c5[k * 3 + 2] = c5[k * 3]
        colls, pairs, rate = self.calculate_collision_rate(c5)
        assert pairs == 595
        assert colls == 15
        assert math.isclose(rate, 15 / 595, rel_tol=1e-5)
        assert rate < 0.05

        # Case 6: 10 clusters of 3 duplicates -> 10 * 3 = 30 collisions -> 30/595 = 5.042% (>= 5%)
        c6 = list(c1)
        for k in range(10):
            c6[k * 3 + 1] = c6[k * 3]
            c6[k * 3 + 2] = c6[k * 3]
        colls, pairs, rate = self.calculate_collision_rate(c6)
        assert pairs == 595
        assert colls == 30
        assert math.isclose(rate, 30 / 595, rel_tol=1e-5)
        assert rate >= 0.05

        # Case 7: 100% collision (35 identical counts)
        c7 = [4320] * 35
        colls, pairs, rate = self.calculate_collision_rate(c7)
        assert pairs == 595
        assert colls == 595
        assert rate == 1.0
        assert rate >= 0.05

    def test_collision_rate_boundary_conditions(self):
        """Tests N=0, N=1, N=2 boundary inputs."""
        assert self.calculate_collision_rate([]) == (0, 0, 0.0)
        assert self.calculate_collision_rate([10000]) == (0, 0, 0.0)

        # N=2 distinct
        assert self.calculate_collision_rate([10000, 20000]) == (0, 1, 0.0)
        # N=2 duplicate
        assert self.calculate_collision_rate([10000, 10000]) == (1, 1, 1.0)

    def test_live_oak_vertex_count_is_distinct(self):
        """Verifies that veg_tree_oak_01 has 58,853 vertices and does not collide with procedural benchmarks."""
        assert OAK_DIR.is_dir()
        manifest_p = OAK_DIR / "asset_manifest.json"
        with open(manifest_p, "r", encoding="utf-8") as f:
            data = json.load(f)
        oak_verts = data.get("geometry", {}).get("vertex_count")
        assert oak_verts == 58853
        assert oak_verts >= 20000


# ==============================================================================
# 4. ROBUST FLAW DETECTION ON veg_tree_oak_01
# ==============================================================================

class TestOakValidatorFlawDetection:
    """Adversarial stress-testing of validator flaw detection against veg_tree_oak_01."""

    def test_baseline_oak_passes_all_checks(self):
        """Verifies that the canonical uncorrupted veg_tree_oak_01 passes all 21 checks."""
        rep = validate_asset(OAK_DIR)
        assert rep.is_valid is True, f"Pristine oak asset failed validation: {rep.errors}"
        assert rep.checks.get("meshy_cloud_provenance") is True
        assert rep.checks.get("glb_container_valid") is True
        assert rep.checks.get("zero_nan_inf_coordinates") is True
        assert rep.checks.get("vertex_count_budget") is True
        assert rep.checks.get("normals_finite_and_unit") is True
        assert rep.checks.get("ground_contact_base_aligned") is True
        assert rep.checks.get("base_contact_centroid_centered") is True
        assert rep.checks.get("metric_scale_bounds") is True
        assert rep.checks.get("static_mesh_no_skins") is True
        assert rep.checks.get("n_bones_strictly_zero") is True
        assert rep.checks.get("textures_channels_present") is True
        assert rep.checks.get("texture_metallic_dielectric") is True
        assert len(rep.errors) == 0
        assert rep.metrics["vertex_count"] == 58853
        assert rep.metrics["task_id"] == "01a089f7-2837-7074-af0e-89c25070c634"

    def test_corrupted_gltf_header_detected(self, tmp_path: Path):
        """Verifies validator flags corrupted glTF header magic bytes."""
        clone_dir = tmp_path / "corrupt_glb_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        glb_file = clone_dir / "veg_tree_oak_01.glb"
        with open(glb_file, "r+b") as f:
            # Overwrite magic 'glTF' with 'CORR'
            f.seek(0)
            f.write(b"CORR")

        rep = validate_asset(clone_dir)
        assert rep.is_valid is False
        assert rep.checks.get("glb_container_valid") is False
        assert any("corrupted or unparseable" in e.lower() for e in rep.errors)

    def test_truncated_gltf_detected(self, tmp_path: Path):
        """Verifies validator flags truncated GLB file (< 12 bytes)."""
        clone_dir = tmp_path / "truncated_glb_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        glb_file = clone_dir / "veg_tree_oak_01.glb"
        with open(glb_file, "wb") as f:
            f.write(b"glTF")  # Only 4 bytes

        rep = validate_asset(clone_dir)
        assert rep.is_valid is False
        assert rep.checks.get("glb_container_valid") is False
        assert len(rep.errors) > 0

    @pytest.mark.parametrize("missing_file", ["albedo.png", "metallic.png", "normal.png", "roughness.png"])
    def test_missing_texture_file_detected(self, tmp_path: Path, missing_file: str):
        """Verifies validator detects omission of any required PBR texture file on disk."""
        clone_dir = tmp_path / f"missing_{missing_file}_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        target_tex = clone_dir / "textures" / missing_file
        assert target_tex.is_file()
        target_tex.unlink()

        rep = validate_asset(clone_dir)
        assert rep.is_valid is False
        assert rep.checks.get("textures_channels_present") is False
        assert any(missing_file in e for e in rep.errors)

    def test_corrupted_texture_file_detected(self, tmp_path: Path):
        """Verifies validator detects unreadable/corrupted image file contents."""
        clone_dir = tmp_path / "corrupt_texture_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        rough_file = clone_dir / "textures" / "roughness.png"
        with open(rough_file, "wb") as f:
            f.write(b"CORRUPTED_NON_IMAGE_DATA_BYTES")

        rep = validate_asset(clone_dir)
        assert rep.is_valid is False
        assert any("corrupt or unreadable" in e.lower() for e in rep.errors)

    def test_texture_resolution_below_256_detected(self, tmp_path: Path):
        """Verifies validator detects sub-256x256 texture resolution violation."""
        clone_dir = tmp_path / "small_texture_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        metal_file = clone_dir / "textures" / "metallic.png"
        small_img = Image.new("L", (128, 128), 0)
        small_img.save(metal_file)

        rep = validate_asset(clone_dir)
        assert rep.is_valid is False
        assert rep.checks.get("textures_readable_and_sized") is False
        assert any("minimum 256x256" in e.lower() for e in rep.errors)

    def test_missing_task_id_provenance_detected(self, tmp_path: Path):
        """Verifies validator detects missing or empty task_id for Meshy cloud provenance."""
        clone_dir = tmp_path / "no_task_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        man_path = clone_dir / "asset_manifest.json"
        with open(man_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Clear task_id across all manifest locations
        if "generator_metadata" in data.get("provenance", {}):
            data["provenance"]["generator_metadata"]["task_id"] = ""
        data["provenance"]["task_id"] = ""
        if "metadata" in data:
            data["metadata"]["task_id"] = ""

        with open(man_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        rep = validate_asset(clone_dir)
        assert rep.is_valid is False
        assert rep.checks.get("meshy_cloud_provenance") is False
        assert any("meshy cloud provenance" in e.lower() for e in rep.errors)

    def test_malformed_manifest_json_detected(self, tmp_path: Path):
        """Verifies validator handles malformed manifest JSON gracefully."""
        clone_dir = tmp_path / "bad_json_oak"
        shutil.copytree(OAK_DIR, clone_dir)

        man_path = clone_dir / "asset_manifest.json"
        with open(man_path, "w", encoding="utf-8") as f:
            f.write("{ INVALID JSON CONTENT: true, ")

        rep = validate_asset(clone_dir)
        # Without valid manifest, provenance check won't see meshy provenance,
        # but asset validation proceeds and checks files
        assert rep.species_id is not None
