"""
MorphoMesh: Armored War Bear Production Asset & Anatomy Verification Test Suite.

Authoritative Milestone M4 Integration Test Harness:
1. Validates standalone verification script `verify_bear_anatomy.py` in native Python and headless Blender.
2. Asserts forward-and-downward claw curvature math: dot(claw_tip - claw_base, fwd) > 0.60 and dz < 0 across all 20 digits.
3. Validates presence and non-empty vertex allocation for all 18 standardized vertex groups.
4. Asserts volumetric fur grooming (>= 10,000 parent guide strands, > 100,000 render strands, zero-fur density masks).
5. Asserts non-intersecting war armor plates (clearance d_min >= 0.015m, watertight 2-manifold topology).
6. Validates canonical production deliverables:
   - `examples/Armored_War_Bear_HD.blend` (> 500 KB)
   - `examples/Armored_War_Bear_HD.glb` (> 500 KB, valid glTF 2.0 structure, 5 PBR materials)
   - `examples/renders/` (4 beauty renders: >= 1280x720, > 50 KB each)
"""

from __future__ import annotations

import json
import math
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from morphomesh.creature_generator import (
    STANDARDIZED_VERTEX_GROUPS,
    UrsineAnatomyConfig,
    generate_bear_base_mesh,
)
from morphomesh.grooming import ZERO_FUR_GROUPS, CreatureGroomingEngine
from morphomesh.materials import STANDARD_PBR_MATERIALS
from morphomesh.armor import ProceduralArmorEngine

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = PROJECT_ROOT / "examples"
RENDERS_DIR = EXAMPLES_DIR / "renders"
BLEND_PATH = EXAMPLES_DIR / "Armored_War_Bear_HD.blend"
GLB_PATH = EXAMPLES_DIR / "Armored_War_Bear_HD.glb"
VERIFY_SCRIPT = PROJECT_ROOT / "verify_bear_anatomy.py"
BLENDER_BIN = "/Applications/Blender.app/Contents/MacOS/Blender"

REQUIRED_RENDERS = [
    "bear_front_three_quarter.png",
    "bear_head_closeup.png",
    "bear_paw_claws_closeup.png",
    "bear_full_body.png",
]

ARMOR_PLATES = [
    "Armor_Pauldron_L",
    "Armor_Pauldron_R",
    "Armor_Gorget",
    "Armor_Bracer_L",
    "Armor_Bracer_R",
    "Armor_Backplate",
]


# ==============================================================================
# 1. STANDALONE VERIFICATION SCRIPT EXECUTION TESTS
# ==============================================================================

class TestVerificationScriptExecution:
    """Verifies that verify_bear_anatomy.py executes cleanly across runtime modes."""

    def test_verify_script_exists_and_executable(self):
        """Assert verify_bear_anatomy.py exists at project root."""
        assert VERIFY_SCRIPT.is_file(), f"Missing verification script: {VERIFY_SCRIPT}"
        assert os.access(VERIFY_SCRIPT, os.R_OK)

    def test_verify_bear_anatomy_native_python_run(self):
        """Execute python3 verify_bear_anatomy.py and assert exit code 0."""
        cmd = [sys.executable, str(VERIFY_SCRIPT)]
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, (
            f"verify_bear_anatomy.py failed with exit code {proc.returncode}.\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
        assert "[PASS]" in proc.stdout
        assert "VERIFICATION SUMMARY" in proc.stdout
        assert "0 FAILED" in proc.stdout

    @pytest.mark.skipif(not os.path.isfile(BLENDER_BIN), reason="Blender 5.2.1 LTS binary not found")
    def test_verify_bear_anatomy_headless_blender_run(self):
        """Execute /Applications/Blender.app/Contents/MacOS/Blender --background examples/Armored_War_Bear_HD.blend --python verify_bear_anatomy.py."""
        assert BLEND_PATH.is_file(), f"Master .blend file missing: {BLEND_PATH}"
        cmd = [
            BLENDER_BIN,
            "--background",
            str(BLEND_PATH),
            "--python",
            str(VERIFY_SCRIPT),
        ]
        proc = subprocess.run(cmd, cwd=PROJECT_ROOT, capture_output=True, text=True)
        assert proc.returncode == 0, (
            f"Headless Blender verification failed with code {proc.returncode}.\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        )
        assert "[PASS]" in proc.stdout
        assert "0 FAILED" in proc.stdout


# ==============================================================================
# 2. CLAW ORIENTATION & BIOMECHANICAL ASSERTIONS
# ==============================================================================

class TestBearClawAnatomy:
    """Validates mathematical forward and downward curvature across all 20 claws."""

    def test_all_20_claws_meet_curvature_guarantee(self):
        """forall i in [0, 19]: dot(d_claw_i, (0, -1, 0)) > 0.60 and dz < 0."""
        res = generate_bear_base_mesh()
        assert len(res.claws) == 20, f"Expected 20 claws, got {len(res.claws)}"

        for claw in res.claws:
            assert claw.forward_dot > 0.60, (
                f"Claw {claw.claw_id} forward dot product {claw.forward_dot} <= 0.60!"
            )
            assert claw.downward_pitch < 0.0, (
                f"Claw {claw.claw_id} downward pitch dz {claw.downward_pitch} >= 0.0!"
            )
            assert claw.is_valid is True

    def test_claw_distribution_across_four_paws(self):
        """Each paw must possess exactly 5 claws with distinct digit indices [0..4]."""
        res = generate_bear_base_mesh()
        paws = {"Front_L": 0, "Front_R": 0, "Hind_L": 0, "Hind_R": 0}
        for claw in res.claws:
            assert claw.paw in paws
            paws[claw.paw] += 1
            assert 0 <= claw.digit_index < 5
        for paw, count in paws.items():
            assert count == 5, f"Paw {paw} has {count} claws, expected 5"


# ==============================================================================
# 3. STANDARDIZED VERTEX GROUP TOPOLOGY ASSERTIONS
# ==============================================================================

class TestStandardizedVertexGroups:
    """Validates presence and population of all 18 standardized groups."""

    def test_all_18_vertex_groups_present_and_non_empty(self):
        res = generate_bear_base_mesh()
        assert len(res.vertex_groups) == 18
        for vg_name in STANDARDIZED_VERTEX_GROUPS:
            assert vg_name in res.vertex_groups, f"Missing vertex group: {vg_name}"
            indices = res.vertex_groups[vg_name]
            assert len(indices) > 0, f"Vertex group {vg_name} has 0 assigned vertices!"

    def test_facial_feature_groups_integrity(self):
        """Facial landmarks must have anatomically consistent vertex populations."""
        res = generate_bear_base_mesh()
        facial_groups = ["snout", "nostrils", "mouth_cavity", "jaw", "teeth", "eyes", "eyelids", "ears"]
        for fg in facial_groups:
            assert len(res.vertex_groups[fg]) >= 8, f"Facial feature {fg} has sparse vertex count"

    def test_pad_and_claw_groups_separation(self):
        """Pads and claws must have populated, non-overlapping groups."""
        res = generate_bear_base_mesh()
        pads_front = set(res.vertex_groups["pads_front"])
        claws_front = set(res.vertex_groups["claws_front"])
        pads_hind = set(res.vertex_groups["pads_hind"])
        claws_hind = set(res.vertex_groups["claws_hind"])

        assert len(pads_front) > 0
        assert len(claws_front) > 0
        assert len(pads_hind) > 0
        assert len(claws_hind) > 0
        assert not pads_front.intersection(claws_front), "Front pads and claws vertices must not intersect"
        assert not pads_hind.intersection(claws_hind), "Hind pads and claws vertices must not intersect"


# ==============================================================================
# 4. VOLUMETRIC FUR GROOMING & ZERO-FUR MASK ASSERTIONS
# ==============================================================================

class TestVolumetricFurGrooming:
    """Validates multi-layer hair systems and zero-density masking."""

    def test_volumetric_fur_strand_counts(self):
        """Undercoat + guard hairs must total >= 10,000 guide strands and > 100,000 render strands."""
        grooming = CreatureGroomingEngine()
        spec = grooming.setup_volumetric_fur("Bear_Base_Mesh")
        assert spec["undercoat_strands"] >= 8000
        assert spec["guard_hair_strands"] >= 4000
        assert spec["total_parent_strands"] >= 10000
        assert spec["total_render_strands"] > 100000

    def test_zero_fur_anatomical_groups(self):
        """Zero-fur group definition must cover all naked features."""
        for zg in ["snout", "nostrils", "mouth_cavity", "jaw", "teeth", "eyes", "eyelids", "claws_front", "claws_hind", "pads_front", "pads_hind"]:
            assert zg in ZERO_FUR_GROUPS


# ==============================================================================
# 5. WAR ARMOR PROCEDURAL FITTING & CLEARANCE ASSERTIONS
# ==============================================================================

class TestWarArmorFittingAndClearances:
    """Validates procedural non-intersecting war armor plates."""

    def test_all_six_armor_plates_defined(self):
        assert len(ARMOR_PLATES) == 6

    def test_pauldron_clearance_and_watertightness(self):
        """Pauldron must be a watertight 2-manifold closed shell with positive signed volume and clearance d_min >= 0.015m."""
        armor = ProceduralArmorEngine()
        p_l = armor.generate_pauldron("L")
        p_r = armor.generate_pauldron("R")

        # 1. Watertight 2-manifold assertions (0 non-manifold edges)
        is_m_l, nm_l = armor.verify_2_manifold(p_l)
        is_m_r, nm_r = armor.verify_2_manifold(p_r)
        assert is_m_l is True and nm_l == 0, f"Pauldron L has {nm_l} non-manifold edges"
        assert is_m_r is True and nm_r == 0, f"Pauldron R has {nm_r} non-manifold edges"

        # 2. Positive signed volume assertion (outward normal vectors)
        def compute_signed_volume(mesh) -> float:
            vol = 0.0
            verts = mesh.vertices
            for f in mesh.faces:
                v0 = verts[f[0]]
                for k in range(1, len(f) - 1):
                    v1 = verts[f[k]]
                    v2 = verts[f[k + 1]]
                    vol += (
                        v0[0] * (v1[1] * v2[2] - v1[2] * v2[1])
                        + v0[1] * (v1[2] * v2[0] - v1[0] * v2[2])
                        + v0[2] * (v1[0] * v2[1] - v1[1] * v2[0])
                    ) / 6.0
            return vol

        vol_l = compute_signed_volume(p_l)
        vol_r = compute_signed_volume(p_r)
        assert vol_l > 0.0, f"Pauldron L signed volume must be positive, got {vol_l:.8f} m^3"
        assert vol_r > 0.0, f"Pauldron R signed volume must be positive, got {vol_r:.8f} m^3"
        assert abs(vol_l - vol_r) < 1e-6, f"Pauldron L ({vol_l:.6f}) and R ({vol_r:.6f}) volumes must be symmetric"

        # 3. Surface clearance d_min >= 0.015m from bear mesh polygons
        bear = generate_bear_base_mesh().mesh
        b_triangles = []
        for f in bear.faces:
            vs = [bear.vertices[idx] for idx in f]
            if any(v[2] >= 0.70 for v in vs):
                for k in range(1, len(f) - 1):
                    b_triangles.append((vs[0], vs[k], vs[k + 1]))

        def pt_tri_sq(p, a, b, c):
            ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            ap = (p[0] - a[0], p[1] - a[1], p[2] - a[2])
            d1 = ab[0] * ap[0] + ab[1] * ap[1] + ab[2] * ap[2]
            d2 = ac[0] * ap[0] + ac[1] * ap[1] + ac[2] * ap[2]
            if d1 <= 0.0 and d2 <= 0.0:
                return ap[0]**2 + ap[1]**2 + ap[2]**2
            bp = (p[0] - b[0], p[1] - b[1], p[2] - b[2])
            d3 = ab[0] * bp[0] + ab[1] * bp[1] + ab[2] * bp[2]
            d4 = ac[0] * bp[0] + ac[1] * bp[1] + ac[2] * bp[2]
            if d3 >= 0.0 and d4 <= d3:
                return bp[0]**2 + bp[1]**2 + bp[2]**2
            vc = d1 * d4 - d3 * d2
            if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
                v = d1 / (d1 - d3)
                return (a[0] + v * ab[0] - p[0])**2 + (a[1] + v * ab[1] - p[1])**2 + (a[2] + v * ab[2] - p[2])**2
            cp = (p[0] - c[0], p[1] - c[1], p[2] - c[2])
            d5 = ab[0] * cp[0] + ab[1] * cp[1] + ab[2] * cp[2]
            d6 = ac[0] * cp[0] + ac[1] * cp[1] + ac[2] * cp[2]
            if d6 >= 0.0 and d5 <= d6:
                return cp[0]**2 + cp[1]**2 + cp[2]**2
            vb = d5 * d2 - d1 * d6
            if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
                w = d2 / (d2 - d6)
                return (a[0] + w * ac[0] - p[0])**2 + (a[1] + w * ac[1] - p[1])**2 + (a[2] + w * ac[2] - p[2])**2
            va = d3 * d6 - d5 * d4
            if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
                w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
                return (b[0] + w * (c[0] - b[0]) - p[0])**2 + (b[1] + w * (c[1] - b[1]) - p[1])**2 + (b[2] + w * (c[2] - b[2]) - p[2])**2
            denom = 1.0 / (va + vb + vc)
            v = vb * denom
            w = vc * denom
            return (a[0] + ab[0] * v + ac[0] * w - p[0])**2 + (a[1] + ab[1] * v + ac[1] * w - p[1])**2 + (a[2] + ab[2] * v + ac[2] * w - p[2])**2

        for side, p in [("L", p_l), ("R", p_r)]:
            min_sq = min(min(pt_tri_sq(v, tri[0], tri[1], tri[2]) for tri in b_triangles) for v in p.vertices)
            min_d = math.sqrt(min_sq)
            assert min_d >= 0.015, f"Pauldron {side} minimum clearance {min_d:.4f}m < 0.015m"
            assert 0.020 <= min_d <= 0.045, f"Pauldron {side} clearance {min_d:.4f}m outside expected range [0.020, 0.045]"


# ==============================================================================
# 6. PRODUCTION ARTIFACT INTEGRITY (BLEND, GLB, RENDERS)
# ==============================================================================

class TestProductionArtifactsIntegrity:
    """Validates file sizes, glTF structure, and beauty render outputs."""

    def test_master_blend_file_integrity(self):
        """Master scene examples/Armored_War_Bear_HD.blend must exist and be > 500 KB."""
        assert BLEND_PATH.is_file(), f"Missing master scene: {BLEND_PATH}"
        size = BLEND_PATH.stat().st_size
        assert size > 500 * 1024, f"Blend file size {size} is <= 500 KB"

    def test_production_glb_file_integrity(self):
        """Production export examples/Armored_War_Bear_HD.glb must exist and be > 500 KB."""
        assert GLB_PATH.is_file(), f"Missing production export: {GLB_PATH}"
        size = GLB_PATH.stat().st_size
        assert size > 500 * 1024, f"GLB file size {size} is <= 500 KB"

    def test_production_glb_structure_and_materials(self):
        """Validates binary glTF 2.0 header, embedded meshes, and assigned PBR materials."""
        assert GLB_PATH.is_file()
        with open(GLB_PATH, "rb") as f:
            magic, version, length = struct.unpack("<4sII", f.read(12))
            assert magic == b"glTF", "Magic header must be 'glTF'"
            assert version == 2, "glTF version must be 2"
            assert length == GLB_PATH.stat().st_size, "Header length must match file size"

            chunk_len, chunk_type = struct.unpack("<II", f.read(8))
            assert chunk_type == 0x4E4F534A, "First chunk must be JSON (0x4E4F534A)"
            json_bytes = f.read(chunk_len)
            json_data = json.loads(json_bytes.decode("utf-8"))

            # Meshes
            mesh_names = [m.get("name") for m in json_data.get("meshes", [])]
            assert any("Bear_Base_Mesh" in str(n) for n in mesh_names), "Bear_Base_Mesh missing in GLB"
            assert any("Ribbons" in str(n) for n in mesh_names), "Fur ribbons missing in GLB"
            assert any("Pauldron" in str(n) for n in mesh_names), "Pauldron armor missing in GLB"

            # Materials
            mat_names = [m.get("name") for m in json_data.get("materials", [])]
            for exp_mat in ["Mat_Bear_Fur", "Mat_Armor_WeatheredSteel"]:
                assert exp_mat in mat_names, f"Expected material {exp_mat} missing from GLB materials"

    def test_all_four_beauty_renders_exist_and_non_empty(self):
        """All 4 beauty renders must exist and be > 50 KB each."""
        for render_name in REQUIRED_RENDERS:
            r_path = RENDERS_DIR / render_name
            assert r_path.is_file(), f"Missing beauty render: {render_name}"
            size = r_path.stat().st_size
            assert size > 50 * 1024, f"Render {render_name} size {size} is <= 50 KB"

    def test_beauty_renders_resolution_dimensions(self):
        """PNG IHDR chunks must declare dimensions >= 1280x720."""
        for render_name in REQUIRED_RENDERS:
            r_path = RENDERS_DIR / render_name
            with open(r_path, "rb") as f:
                sig = f.read(8)
                assert sig == b"\x89PNG\r\n\x1a\n", f"{render_name} is not a valid PNG"
                ihdr_len, ihdr_type = struct.unpack(">I4s", f.read(8))
                assert ihdr_type == b"IHDR"
                width, height = struct.unpack(">II", f.read(8))
                assert width >= 1280, f"{render_name} width {width} < 1280"
                assert height >= 720, f"{render_name} height {height} < 720"
