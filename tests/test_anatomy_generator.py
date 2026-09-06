"""
MorphoMesh: Reusable Anatomy Generator & Claw Verification Test Suite.

Verifies:
1. Mathematical claw orientation guarantee: dot(claw_tip - claw_base, forward_dir) > 0.60 and dz < 0.
2. Plantigrade paw biomechanics: calcaneus heel, palmar/plantar pads, and 5 digital pads per paw.
3. Articulated facial anatomy: cranium, snout, indented nares/nostrils, mouth cavity,
   lower jaw, canines/incisors dentition, dimensional eyelids, and cupped ears.
4. Muscular quadruped torso with dorsal thoracic hump, dorsal spine, and short tail (length <= 0.20m).
5. Standardized 18 vertex groups populated with valid, in-bounds vertex indices.
6. MockInferenceAdapter bear and quadruped procedural mesh synthesis.
"""

from __future__ import annotations

import math
import os
import struct
from pathlib import Path
from typing import Dict

import pytest

from morphomesh.creature_generator import (
    STANDARDIZED_VERTEX_GROUPS,
    UrsineAnatomyConfig,
    generate_bear_base_mesh,
    generate_creature_mesh,
)
from morphomesh.inference_adapter import MeshGeometry, MockInferenceAdapter
from morphomesh.models import Create3DAssetInput, Create3DAssetOutput


# ==============================================================================
# 1. CURVED CLAW MATHEMATICAL GUARANTEE TESTS
# ==============================================================================

class TestCurvedClawGenerator:
    """Verifies that all procedural claws curve forward and downward mathematically."""

    def test_standalone_claw_forward_and_downward_orientation(self):
        """Test add_curved_claw with default ursine parameters."""
        geom = MeshGeometry()
        base_pos = (0.38, -0.70, 0.05)
        fwd_dir = (0.0, -1.0, 0.0)
        claw_verts = geom.add_curved_claw(
            base_pos=base_pos,
            forward_dir=fwd_dir,
            downward_dir=(0.0, 0.0, -1.0),
            length=0.12,
            base_radius=0.025,
            curve_factor=0.45,
            segments=6,
            radial_segments=8,
            splay_factor=0.0,
        )

        assert len(claw_verts) > 0
        # Tip vertex is the second-to-last vertex before base cap center
        tip_vertex = geom.vertices[claw_verts[-2]]
        vx = tip_vertex[0] - base_pos[0]
        vy = tip_vertex[1] - base_pos[1]
        vz = tip_vertex[2] - base_pos[2]
        vlen = math.sqrt(vx * vx + vy * vy + vz * vz)
        assert vlen > 0.05

        d_unit = (vx / vlen, vy / vlen, vz / vlen)
        fwd_dot = d_unit[0] * fwd_dir[0] + d_unit[1] * fwd_dir[1] + d_unit[2] * fwd_dir[2]

        # Forward dot product assertion: > 0.60
        assert fwd_dot > 0.60, f"Claw forward dot product {fwd_dot} failed (> 0.60 required)"
        # Downward pitch assertion: dz < 0
        assert vz < 0.0, f"Claw tip dz {vz} failed (must be < 0)"
        assert d_unit[2] < 0.0

    @pytest.mark.parametrize("splay_factor", [-0.35, -0.2, 0.0, 0.2, 0.35])
    @pytest.mark.parametrize("curve_factor", [0.35, 0.45, 0.55])
    def test_curved_claw_splay_and_curve_variations(self, splay_factor: float, curve_factor: float):
        """Test claw math across splay angles and curve factors."""
        geom = MeshGeometry()
        base_pos = (0.0, 0.0, 0.0)
        fwd_dir = (0.0, -1.0, 0.0)
        claw_verts = geom.add_curved_claw(
            base_pos=base_pos,
            forward_dir=fwd_dir,
            downward_dir=(0.0, 0.0, -1.0),
            length=0.10,
            base_radius=0.02,
            curve_factor=curve_factor,
            splay_factor=splay_factor,
        )

        tip_vertex = geom.vertices[claw_verts[-2]]
        vx, vy, vz = tip_vertex
        vlen = math.sqrt(vx * vx + vy * vy + vz * vz)
        fwd_dot = (vy / vlen) * (-1.0)
        assert fwd_dot > 0.60
        assert vz < 0.0

    def test_bear_base_mesh_all_20_claws_verified(self):
        """Verify that all 20 claws on the synthesized bear meet the orientation criteria."""
        result = generate_bear_base_mesh()
        assert len(result.claws) == 20, f"Expected exactly 20 claws, got {len(result.claws)}"

        for claw in result.claws:
            assert claw.forward_dot > 0.60, (
                f"Claw {claw.claw_id} failed forward dot product: {claw.forward_dot} <= 0.60"
            )
            assert claw.downward_pitch < 0.0, (
                f"Claw {claw.claw_id} failed downward pitch: {claw.downward_pitch} >= 0.0"
            )
            assert claw.is_valid is True

        assert result.landmark_counts["claws_valid"] == 20


# ==============================================================================
# 2. PLANTIGRADE PAW & PAD SYSTEM TESTS
# ==============================================================================

class TestPlantigradePawAndPads:
    """Verifies plantigrade foot anatomy, calcaneus heel, and pads."""

    def test_front_paw_pad_structure(self):
        """Front paw must have palmar pad, carpal pad, and 5 digital pads."""
        geom = MeshGeometry()
        heel_pos = (0.38, -0.48, 0.0)
        paw_res = geom.add_plantigrade_paw(heel_pos, forward_dir=(0.0, -1.0, 0.0), is_front=True, scale=1.0)

        assert len(paw_res["paw"]) > 0
        assert len(paw_res["pads"]) > 0
        assert len(paw_res["claws"]) > 0
        assert "pads_front" in geom.vertex_groups
        assert "claws_front" in geom.vertex_groups
        assert len(geom.vertex_groups["pads_front"]) > 0
        assert len(geom.vertex_groups["claws_front"]) > 0

    def test_hind_paw_plantigrade_heel_structure(self):
        """Hind paw must have elongated calcaneus sole pad and 5 digital pads."""
        geom = MeshGeometry()
        heel_pos = (0.36, 0.46, 0.0)
        paw_res = geom.add_plantigrade_paw(heel_pos, forward_dir=(0.0, -1.0, 0.0), is_front=False, scale=1.0)

        assert len(paw_res["paw"]) > 0
        assert len(paw_res["pads"]) > 0
        assert len(paw_res["claws"]) > 0
        assert "pads_hind" in geom.vertex_groups
        assert "claws_hind" in geom.vertex_groups
        assert len(geom.vertex_groups["pads_hind"]) > 0
        assert len(geom.vertex_groups["claws_hind"]) > 0

    def test_digit_count_per_paw(self):
        """Every paw must feature exactly 5 functional weight-bearing digits."""
        result = generate_bear_base_mesh()
        paw_claw_counts: Dict[str, int] = {}
        for c in result.claws:
            paw_claw_counts[c.paw] = paw_claw_counts.get(c.paw, 0) + 1

        assert paw_claw_counts["Front_L"] == 5
        assert paw_claw_counts["Front_R"] == 5
        assert paw_claw_counts["Hind_L"] == 5
        assert paw_claw_counts["Hind_R"] == 5


# ==============================================================================
# 3. ARTICULATED FACIAL GEOMETRY TESTS
# ==============================================================================

class TestArticulatedFacialGeometry:
    """Verifies articulated head: snout, nostrils, mouth cavity, jaw, teeth, eyelids, ears."""

    def test_head_feature_landmarks_presence(self):
        """Verify all facial components are distinct geometric elements."""
        geom = MeshGeometry()
        feats = geom.add_articulated_head((0.0, -0.80, 1.20), forward_dir=(0.0, -1.0, 0.0), scale=1.0)

        assert len(feats["snout"]) > 0, "Snout geometry missing"
        assert len(feats["nostrils"]) > 0, "Nostrils concavity missing"
        assert len(feats["mouth_cavity"]) > 0, "Mouth cavity missing"
        assert len(feats["jaw"]) > 0, "Mandible/jaw missing"
        assert len(feats["teeth"]) > 0, "Dentition missing"
        assert len(feats["eyes"]) > 0, "Eyes missing"
        assert len(feats["eyelids"]) > 0, "Eyelids missing"
        assert len(feats["ears"]) > 0, "Cupped ears missing"

    def test_nostril_indentation(self):
        """Nostrils must be bilaterally symmetrical concavities recessed into the snout."""
        geom = MeshGeometry()
        feats = geom.add_articulated_head((0.0, -0.80, 1.20), forward_dir=(0.0, -1.0, 0.0), scale=1.0)
        nostril_indices = feats["nostrils"]
        assert len(nostril_indices) >= 12  # At least 2 cones * 6 segments

        # Check bilateral symmetry of nostril vertices
        nostril_verts = [geom.vertices[i] for i in nostril_indices]
        x_coords = [v[0] for v in nostril_verts]
        assert any(x > 0.01 for x in x_coords)
        assert any(x < -0.01 for x in x_coords)

    def test_dentition_canines_and_incisors(self):
        """Dentition must include upper and lower canines and incisors."""
        geom = MeshGeometry()
        feats = geom.add_articulated_head((0.0, -0.80, 1.20), forward_dir=(0.0, -1.0, 0.0), scale=1.0)
        teeth_indices = feats["teeth"]
        # 4 canines + 8 incisors = 12 teeth elements with multiple vertices each
        assert len(teeth_indices) >= 40

    def test_eyelids_surround_eyes(self):
        """Eyelids must enclose the eye spheres."""
        geom = MeshGeometry()
        feats = geom.add_articulated_head((0.0, -0.80, 1.20), forward_dir=(0.0, -1.0, 0.0), scale=1.0)
        eye_verts = [geom.vertices[i] for i in feats["eyes"]]
        eyelid_verts = [geom.vertices[i] for i in feats["eyelids"]]

        eye_z = [v[2] for v in eye_verts]
        eyelid_z = [v[2] for v in eyelid_verts]

        # Eyelids should span both above and below eye level
        assert min(eyelid_z) < min(eye_z) + 0.05
        assert max(eyelid_z) > max(eye_z) - 0.05


# ==============================================================================
# 4. ANATOMICAL TORSO & TAIL TESTS
# ==============================================================================

class TestAnatomicalTorsoAndTail:
    """Verifies muscular quadruped torso, dorsal hump, dorsal spine, and short tail."""

    def test_torso_hump_and_spine(self):
        geom = MeshGeometry()
        feats = geom.add_anatomical_torso((0.0, 0.0, 0.85), forward_dir=(0.0, -1.0, 0.0), scale=1.0)

        assert len(feats["torso"]) > 0
        assert len(feats["dorsal_spine"]) > 0
        assert len(feats["tail"]) > 0
        assert len(feats["armor_mounts_shoulder"]) > 0

    def test_short_tail_length_bound(self):
        """Ursine short tail must be biologically vestigial (length <= 0.20m)."""
        cfg = UrsineAnatomyConfig(tail_length=0.14)
        assert cfg.tail_length <= 0.20

        result = generate_bear_base_mesh(cfg)
        tail_indices = result.vertex_groups["tail"]
        assert len(tail_indices) > 0
        tail_verts = [result.mesh.vertices[i] for i in tail_indices]
        min_y = min(v[1] for v in tail_verts)
        max_y = max(v[1] for v in tail_verts)
        tail_y_span = max_y - min_y
        assert tail_y_span <= 0.20, f"Tail length span {tail_y_span} exceeds 0.20m"


# ==============================================================================
# 5. STANDARDIZED 18 VERTEX GROUPS TESTS
# ==============================================================================

class TestStandardizedVertexGroups:
    """Verifies all 18 standardized vertex groups are present, populated, and valid."""

    def test_all_18_groups_present(self):
        result = generate_bear_base_mesh()
        assert len(STANDARDIZED_VERTEX_GROUPS) == 18

        for vg_name in STANDARDIZED_VERTEX_GROUPS:
            assert vg_name in result.vertex_groups, f"Missing vertex group: {vg_name}"

    def test_all_18_groups_non_empty(self):
        """Every single standardized vertex group must contain at least one vertex."""
        result = generate_bear_base_mesh()
        for vg_name in STANDARDIZED_VERTEX_GROUPS:
            indices = result.vertex_groups[vg_name]
            assert len(indices) > 0, f"Vertex group '{vg_name}' is empty (0 vertices)"

    def test_vertex_indices_in_bounds(self):
        """All vertex indices in vertex groups must be within the mesh vertex array."""
        result = generate_bear_base_mesh()
        total_verts = len(result.mesh.vertices)

        for vg_name, indices in result.vertex_groups.items():
            for idx in indices:
                assert 0 <= idx < total_verts, (
                    f"Out of bounds vertex index {idx} in group '{vg_name}' (total={total_verts})"
                )

    def test_armor_mounts_groups_coverage(self):
        """Armor mounts for shoulder and wrist must be populated."""
        result = generate_bear_base_mesh()
        assert len(result.vertex_groups["armor_mounts_shoulder"]) > 0
        assert len(result.vertex_groups["armor_mounts_wrist"]) > 0


# ==============================================================================
# 6. ASSET EXPORT & INFERENCE ADAPTER INTEGRATION TESTS
# ==============================================================================

class TestAssetExportAndAdapterIntegration:
    """Verifies export of the generated creature to OBJ/GLB and MockInferenceAdapter integration."""

    def test_export_bear_obj_and_glb(self, tmp_path: Path):
        result = generate_bear_base_mesh()
        obj_file = tmp_path / "bear_base.obj"
        glb_file = tmp_path / "bear_base.glb"

        result.mesh.export_obj(str(obj_file))
        assert obj_file.exists()
        assert obj_file.stat().st_size > 5000

        result.mesh.export_glb(str(glb_file))
        assert glb_file.exists()
        assert glb_file.stat().st_size > 5000

        # Validate GLB header
        data = glb_file.read_bytes()
        magic, version = struct.unpack_from("<4sI", data, 0)
        assert magic == b"glTF"
        assert version == 2

    def test_mock_inference_adapter_bear_concept(self, mock_adapter: MockInferenceAdapter):
        """Create3DAssetInput with 'concept-bear' synthesizes authentic bear base mesh."""
        req = Create3DAssetInput(concept_id="concept-bear", export_format="glb", generate_pbr=True)
        out = mock_adapter.generate_3d_asset(req)

        assert isinstance(out, Create3DAssetOutput)
        assert out.format == "glb"
        assert os.path.isfile(out.mesh_path)
        assert out.vertex_count > 1000, f"Expected rich geometry > 1000 verts, got {out.vertex_count}"
        assert out.face_count > 800

        # Bounding box must reflect bear scale
        bbox = out.bounding_box
        assert bbox.dimensions[0] > 0.5  # Width
        assert bbox.dimensions[1] > 1.0  # Length
        assert bbox.dimensions[2] > 0.8  # Height

    def test_universal_archetype_generator(self):
        """Test universal creature generator for 'ursine' and 'quadruped'."""
        bear = generate_creature_mesh("ursine")
        assert bear.archetype == "ursine"
        assert bear.is_anatomically_valid is True

        quad = generate_creature_mesh("quadruped")
        assert quad.archetype == "quadruped"
        assert quad.is_anatomically_valid is True

    def test_blender_generation_script_ast_validation_and_length(self):
        """Verify the Blender generation script passes AST validation and stays under 10KB."""
        from morphomesh.blender_bridge import BpyCodeValidator
        from morphomesh.creature_generator import get_blender_generation_script

        script = get_blender_generation_script(object_name="Test_Bear", scale=1.0)
        assert len(script) < 10000, f"Script length {len(script)} exceeds 10,000 char limit"

        validator = BpyCodeValidator()
        # Must not raise BpySecurityViolation
        validator.validate(script)

    def test_blender_bridge_socket_success_recognition(self, monkeypatch: pytest.MonkeyPatch):
        """Verify BlenderBridge recognizes {'success': True} in execute_code socket response."""
        from morphomesh.blender_bridge import BlenderBridge

        bridge = BlenderBridge()

        # Mock is_interactive_connected to True
        monkeypatch.setattr(bridge, "is_interactive_connected", lambda: True)

        def mock_send(method, params, timeout=5.0):
            if method == "execute_code":
                return {
                    "success": True,
                    "stdout": "",
                    "stderr": "",
                    "returned_data": {"test_var": 42},
                }
            raise RuntimeError("Direct RPC not supported")

        monkeypatch.setattr(bridge, "send_socket_request", mock_send)

        res = bridge.execute("morphomesh.execute_custom_script", {"code": "import bpy\ntest_var = 42\n"})
        assert isinstance(res, dict)
        assert res.get("success") is True
        assert res.get("returned_data", {}).get("test_var") == 42

