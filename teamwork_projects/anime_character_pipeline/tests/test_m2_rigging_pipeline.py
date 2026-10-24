"""
tests/test_m2_rigging_pipeline.py
Comprehensive Verification Suite for Milestone 2:
Features F04, F05, F06, F07, F08, F09, F10:
- F04: Universal Humanoid Armature Hierarchy (Spine, Neck, Head, Limbs, Clavicles)
- F05: 30 Articulated Finger Phalanges (5 digits x 3 phalanges x 2 hands)
- F06: UpperArm and ForeArm Twist Bones (0.5 local Y copy-rotation)
- F07: 12-Radial Skirt Secondary Rig (pitch clamped [-15°, +65°]) & 0% Thigh Weight Transfer
- F08: Dual 5-Bone Twintail Secondary Chains (spring dynamics m=0.2, k=150, c=12)
- F09: Dual Quaternion Skinning (use_deform_preserve_volume = True)
- F10: Smooth Weight Paint Transfer, Harmonic Cosine Falloff, Modular Isolation
- Deliverables: output/anime_rigged.blend and output/anime_rigged.glb
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest

from anime_pipeline.rigging import (
    ALL_10_HAIR_BONES,
    ALL_30_FINGER_BONES,
    ALL_REQUIRED_ARMATURE_BONES,
    FINGER_NAMES,
    MMD_BONE_MAP,
    MODULAR_ISOLATION_RULES,
    PHALANGES,
    RIGIFY_DEF_BONE_MAP,
    SKIRT_BONES,
    SKIRT_BONE_COUNT,
    SKIRT_BONE_NAMES,
    SKIRT_PITCH_MAX_DEG,
    SKIRT_PITCH_MIN_DEG,
    SPRING_DAMPING,
    SPRING_MASS,
    SPRING_REST_POS,
    SPRING_STIFFNESS,
    TWINTAIL_SEGMENT_COUNT,
    TWIST_BONES,
    TWIST_BONE_CONFIGS,
    UNIVERSAL_LIMB_BONES,
    UNIVERSAL_SPINE_BONES,
    VRM_1_0_BONE_MAP,
    ArmatureBuilder,
    ArmatureSpec,
    BoneSpec,
    SecondaryBonesRig,
    SkinningDQS,
    VertexWeightTable,
    calculate_submesh_skin_weights,
    clamp_skirt_pitch,
    evaluate_cubic_bezier_3d,
    harmonic_cosine_falloff,
    point_to_segment_distance_and_proj,
    verify_skin_weights_normalization,
)


class TestM2RiggingPipeline:
    """Milestone 2 Rigging, Twist/Spring Bones, and DQS Test Suite."""

    # --------------------------------------------------------------------------
    # F04: Universal Humanoid Armature Hierarchy
    # --------------------------------------------------------------------------

    def test_armature_builder_78_bones_and_spine_hierarchy(self):
        """F04: Verifies exactly 78 bones and unbroken spine parent-child chain."""
        builder = ArmatureBuilder(height=1.650)
        spec = builder.generate_armature_spec()

        assert spec.name == "Anime_Armature"
        assert spec.total_bones == 78, f"Expected 78 bones, got {spec.total_bones}"
        assert set(spec.bones.keys()) == set(ALL_REQUIRED_ARMATURE_BONES)

        # Spine chain hierarchy
        bones = spec.bones
        assert bones["Hips"].parent is None
        assert bones["Spine"].parent == "Hips"
        assert bones["Spine1"].parent == "Spine"
        assert bones["Spine2"].parent == "Spine1"
        assert bones["Neck"].parent == "Spine2"
        assert bones["Head"].parent == "Neck"

        # Clavicle and limb parents
        for side in ["L", "R"]:
            assert bones[f"Clavicle.{side}"].parent == "Spine2"
            assert bones[f"UpperArm.{side}"].parent == f"Clavicle.{side}"
            assert bones[f"ForeArm.{side}"].parent == f"UpperArm.{side}"
            assert bones[f"Hand.{side}"].parent == f"ForeArm.{side}"
            assert bones[f"Thigh.{side}"].parent == "Hips"
            assert bones[f"Shin.{side}"].parent == f"Thigh.{side}"
            assert bones[f"Foot.{side}"].parent == f"Shin.{side}"
            assert bones[f"Toe.{side}"].parent == f"Foot.{side}"

    def test_cross_standard_bone_mappings(self):
        """F04: Verifies comprehensive 1:1 cross-standard mappings for VRM 1.0, Rigify, and MMD."""
        for b in UNIVERSAL_SPINE_BONES + UNIVERSAL_LIMB_BONES + ALL_30_FINGER_BONES:
            assert b in VRM_1_0_BONE_MAP, f"Bone {b} missing from VRM 1.0 map"
            assert b in RIGIFY_DEF_BONE_MAP, f"Bone {b} missing from Rigify map"

        for b in UNIVERSAL_SPINE_BONES + UNIVERSAL_LIMB_BONES:
            assert b in MMD_BONE_MAP, f"Bone {b} missing from MMD map"

    @pytest.mark.parametrize("height", [1.45, 1.58, 1.65, 1.70, 1.75])
    def test_dynamic_landmark_scaling(self, height: float):
        """F04: Verifies proportional joint landmark scaling from 1.45m to 1.75m."""
        builder = ArmatureBuilder(height=height)
        spec = builder.generate_armature_spec()
        head_top_z = spec.bones["Head"].tail[2]
        assert abs(head_top_z - height) < 0.05, (
            f"At height {height}, Head top Z {head_top_z} deviates unexpectedly"
        )
        assert spec.bones["Hips"].head[2] > 0.70
        assert spec.bones["Hips"].head[2] < 1.00

    # --------------------------------------------------------------------------
    # F05: 30 Articulated Finger Phalanges
    # --------------------------------------------------------------------------

    def test_thirty_articulated_finger_phalanges_structure(self):
        """F05: Verifies exactly 30 finger phalanges (5 digits x 3 phalanges x 2 hands)."""
        builder = ArmatureBuilder(height=1.650)
        spec = builder.generate_armature_spec()

        assert len(ALL_30_FINGER_BONES) == 30
        for side in ["L", "R"]:
            for finger in FINGER_NAMES:
                # Phalange 01 parent is Hand
                p01 = spec.bones[f"{finger}.01.{side}"]
                assert p01.parent == f"Hand.{side}"
                # Phalange 02 parent is Phalange 01
                p02 = spec.bones[f"{finger}.02.{side}"]
                assert p02.parent == f"{finger}.01.{side}"
                # Phalange 03 parent is Phalange 02
                p03 = spec.bones[f"{finger}.03.{side}"]
                assert p03.parent == f"{finger}.02.{side}"

    # --------------------------------------------------------------------------
    # F06: Twist Bones & COPY_ROTATION Constraints
    # --------------------------------------------------------------------------

    def test_twist_bones_constraints_specification(self):
        """F06: Verifies 4 twist bones have local Y copy-rotation constraints with factor 0.5."""
        builder = ArmatureBuilder(height=1.650)
        spec = builder.generate_armature_spec()

        for twist_bone in TWIST_BONES:
            assert twist_bone in spec.bones
            b = spec.bones[twist_bone]
            assert len(b.constraints) > 0
            c = b.constraints[0]
            assert c["type"] == "COPY_ROTATION"
            assert c["axis"] == "Y"
            assert abs(c["factor"] - 0.5) < 1e-4

        # Standalone constraints setup
        dqs = SkinningDQS()
        mock_res = dqs.setup_twist_bone_constraints(armature_obj=None)
        assert len(mock_res) == 4
        for name, cfg in mock_res.items():
            assert cfg["type"] == "COPY_ROTATION"
            assert cfg["axis"] == "Y"
            assert cfg["factor"] == 0.50
            assert cfg["target_space"] == "LOCAL"
            assert cfg["owner_space"] == "LOCAL"

    # --------------------------------------------------------------------------
    # F07: 12-Radial Skirt Rig & Strict 0% Thigh Weight Bleeding
    # --------------------------------------------------------------------------

    def test_skirt_twelve_radial_bones_and_pitch_clamping(self):
        """F07: Verifies 12 radial skirt bones parented to Hips with [-15°, +65°] pitch limits."""
        builder = ArmatureBuilder(height=1.650)
        spec = builder.generate_armature_spec()

        assert len(SKIRT_BONES) == 12
        for bname in SKIRT_BONES:
            assert bname in spec.bones
            b = spec.bones[bname]
            assert b.parent == "Hips"
            assert len(b.constraints) > 0
            c = b.constraints[0]
            assert c["type"] == "LIMIT_ROTATION"
            assert c["min_pitch"] == SKIRT_PITCH_MIN_DEG
            assert c["max_pitch"] == SKIRT_PITCH_MAX_DEG

        assert clamp_skirt_pitch(-25.0) == -15.0
        assert clamp_skirt_pitch(80.0) == 65.0
        assert clamp_skirt_pitch(30.0) == 30.0

    def test_skirt_strict_zero_thigh_weight_bleeding(self):
        """F07 CRITICAL INVARIANT: Anime_Skirt has strictly 0.000 weight on Thigh.L and Thigh.R."""
        # Synthesize sample skirt vertices (concentric cylinders)
        sample_verts: List[Tuple[float, float, float]] = []
        for ring in range(5):
            z = 0.54 + ring * 0.08
            r = 0.25 - ring * 0.02
            for step in range(12):
                ang = step * (2.0 * math.pi / 12.0)
                sample_verts.append((r * math.cos(ang), r * math.sin(ang) - 0.016, z))

        vgroups = calculate_submesh_skin_weights("Anime_Skirt", sample_verts)

        # 1. No Thigh groups exist on Anime_Skirt
        assert "Thigh.L" not in vgroups
        assert "Thigh.R" not in vgroups

        # 2. All groups start with Skirt_
        for gname in vgroups.keys():
            assert gname.startswith("Skirt_")

        # 3. All vertices have normalized weights summing to 1.0
        valid, msg = verify_skin_weights_normalization("Anime_Skirt", vgroups, len(sample_verts))
        assert valid, msg

    # --------------------------------------------------------------------------
    # F08: 5-Bone Twintail Secondary Chains & Spring Dynamics
    # --------------------------------------------------------------------------

    def test_twintail_five_bone_chains_and_spring_parameters(self):
        """F08: Verifies dual 5-bone twintail chains parented to Head with spring params."""
        builder = ArmatureBuilder(height=1.650)
        spec = builder.generate_armature_spec()

        assert len(ALL_10_HAIR_BONES) == 10
        for side in ["L", "R"]:
            # Chain root parented to Head
            assert spec.bones[f"Hair_{side}_01"].parent == "Head"
            # Subsequent links parented in sequence
            for i in range(1, 5):
                curr = f"Hair_{side}_{i:02d}"
                nxt = f"Hair_{side}_{i+1:02d}"
                assert spec.bones[nxt].parent == curr

        # Spring dynamics constants
        assert SPRING_MASS == 0.20
        assert SPRING_STIFFNESS == 150.0
        assert SPRING_DAMPING == 12.0

        # Bézier evaluation
        p0 = (0.088, -0.02, 1.53)
        p1 = (0.160, -0.04, 1.48)
        p2 = (0.175, -0.05, 1.32)
        p3 = (0.150, -0.03, 1.15)
        pt_mid = evaluate_cubic_bezier_3d(p0, p1, p2, p3, 0.5)
        assert pt_mid[0] > 0.10 and pt_mid[2] < 1.50

    # --------------------------------------------------------------------------
    # F09: Dual Quaternion Skinning (DQS)
    # --------------------------------------------------------------------------

    def test_dual_quaternion_skinning_preserve_volume_flag(self):
        """F09: Verifies ArmatureSpec and DQS configuration enable use_deform_preserve_volume."""
        builder = ArmatureBuilder()
        spec = builder.generate_armature_spec()
        assert spec.use_deform_preserve_volume is True

    # --------------------------------------------------------------------------
    # F10: Smooth Weight Paint Transfer & Modular Isolation
    # --------------------------------------------------------------------------

    def test_harmonic_cosine_falloff_c1_continuity(self):
        """F10: Verifies C1 harmonic cosine falloff f(u) = 0.5*(1+cos(pi*u))."""
        assert abs(harmonic_cosine_falloff(0.0) - 1.0) < 1e-6
        assert abs(harmonic_cosine_falloff(0.5) - 0.5) < 1e-6
        assert abs(harmonic_cosine_falloff(1.0) - 0.0) < 1e-6
        # Clamping
        assert harmonic_cosine_falloff(-0.2) == 1.0
        assert harmonic_cosine_falloff(1.5) == 0.0

    def test_modular_isolation_rules_compliance_across_all_submeshes(self):
        """F10: Verifies that skin weights on every submesh obey strict modular isolation."""
        submesh_sample_points: Dict[str, List[Tuple[float, float, float]]] = {
            "Anime_Head": [(0.0, 0.0, 1.55), (0.0, 0.0, 1.41), (0.0, 0.0, 1.39)],
            "Anime_Torso": [(0.0, 0.0, 1.38), (0.0, 0.0, 1.25), (0.0, 0.0, 1.10), (0.0, 0.0, 0.85)],
            "Anime_Arms": [(0.20, 0.0, 1.25), (0.35, -0.05, 1.12), (0.42, -0.22, 1.02), (-0.20, 0.0, 1.25)],
            "Anime_Legs": [(0.10, 0.0, 0.80), (0.12, -0.02, 0.60), (0.16, -0.03, 0.45), (0.21, 0.0, 0.20)],
            "Anime_Skirt": [(0.20, 0.0, 0.80), (0.0, 0.18, 0.70), (-0.22, 0.0, 0.60)],
            "Anime_Hair": [(0.0, 0.0, 1.58), (0.12, -0.02, 1.45), (-0.12, -0.02, 1.45)],
            "Anime_Shoes": [(0.21, 0.0, 0.05), (0.21, -0.15, 0.01), (-0.21, 0.0, 0.05)],
        }

        for mesh_name, pts in submesh_sample_points.items():
            vgroups = calculate_submesh_skin_weights(mesh_name, pts)
            valid, msg = verify_skin_weights_normalization(mesh_name, vgroups, len(pts))
            assert valid, f"{mesh_name} failed normalization: {msg}"

            allowed = MODULAR_ISOLATION_RULES[mesh_name]
            for bname in vgroups.keys():
                assert bname in allowed, f"Prohibited bone {bname} found in {mesh_name}"

    # --------------------------------------------------------------------------
    # Output Deliverables Validation
    # --------------------------------------------------------------------------

    def test_rigged_deliverables_exist_and_non_empty(self):
        """Verifies anime_rigged.blend and anime_rigged.glb are generated and valid."""
        proj_root = Path(__file__).resolve().parent.parent
        blend_file = proj_root / "output" / "anime_rigged.blend"
        glb_file = proj_root / "output" / "anime_rigged.glb"

        assert blend_file.exists(), "anime_rigged.blend does not exist"
        assert blend_file.stat().st_size > 1_000_000, "anime_rigged.blend is too small (< 1 MB)"

        assert glb_file.exists(), "anime_rigged.glb does not exist"
        assert glb_file.stat().st_size > 100_000, "anime_rigged.glb is too small (< 100 KB)"
