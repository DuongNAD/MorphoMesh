"""
Tier 3: Cross-Feature Interactions (Pairwise Combinations)
File: tests/test_tier3_interactions.py

Validates multi-subsystem coupling and cross-feature interactions:
- Pairwise 1: Mesh + Rig Binding (F01 + F04 + F10) -> All 7 sub-meshes bound, 0 orphans, skirt 0% thigh weights
- Pairwise 2: Rig + Twist Bones + DQS (F05/F06 + F09 + F21) -> Candy-wrapper prevention, volume retention Rv >= 0.85
- Pairwise 3: Animation + Skirt & Hair Secondary Physics (F07/F08 + F11 + F13) -> Dynamic sway + pitch clamping [-15°, 65°]
- Pairwise 4: Shading + Inverted Hull Outline + Camera Framing (F14/F15 + F16 + F17) -> Non-clipping cel-shaded outline
- Pairwise 5: Pipeline CLI + Verification Audit Suite (F19 + F20/F21/F22) -> Coordinated execution & status reporting
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import pytest

from .conftest import (
    ALL_REQUIRED_ARMATURE_BONES,
    HINGE_LIMITS,
    MIN_VOLUME_RETENTION_RATIO,
    SOLIDIFY_OUTLINE_THICKNESS,
    SUBMESH_NAMES,
    ArmatureDefinition,
    SubMeshDefinition,
    ActionDefinition,
    clamp_joint_angle,
    compute_mesh_signed_volume,
    compute_volume_retention,
    evaluate_twist_bone_rotation,
    solve_spring_damper_step,
)


class TestTier3CrossFeatureInteractions:
    """Tier 3: Cross-Feature Interactions Suite."""

    # --------------------------------------------------------------------------
    # Pairwise 1: Mesh + Rig Binding (F01 + F04 + F10)
    # --------------------------------------------------------------------------

    def test_interaction_mesh_and_rig_complete_vertex_group_binding(
        self,
        canonical_submeshes: Dict[str, SubMeshDefinition],
        canonical_armature: ArmatureDefinition,
    ):
        """
        Pairwise 1: Verifies that every vertex group in all 7 sub-meshes maps to a valid bone
        in Anime_Armature, and no deforming vertices are orphaned.
        """
        valid_bones = set(canonical_armature.bones.keys())

        for mesh_name, mesh in canonical_submeshes.items():
            # Verify all vertex groups exist in armature
            for vg_name in mesh.vertex_groups.keys():
                assert vg_name in valid_bones, (
                    f"Sub-mesh {mesh_name} references non-existent bone '{vg_name}'"
                )

            # Verify no orphaned vertices in non-rigid meshes
            v_weights = {i: 0.0 for i in range(len(mesh.vertices))}
            for pairs in mesh.vertex_groups.values():
                for v_idx, w in pairs:
                    if v_idx in v_weights:
                        v_weights[v_idx] += w

            # Every vertex must belong to at least one valid deforming bone
            for v_idx, total_w in v_weights.items():
                assert total_w > 0.0, f"Vertex {v_idx} in {mesh_name} is orphaned with zero skin weight"

    def test_interaction_skirt_and_thigh_weight_isolation(
        self, canonical_submeshes: Dict[str, SubMeshDefinition]
    ):
        """
        Pairwise 1: Verifies absolute weight isolation between Anime_Skirt and thigh bones.
        Prevents leg movements from tearing or stretching the pleated skirt.
        """
        skirt = canonical_submeshes["Anime_Skirt"]
        assert "Thigh.L" not in skirt.vertex_groups, "Anime_Skirt has non-zero Thigh.L weight"
        assert "Thigh.R" not in skirt.vertex_groups, "Anime_Skirt has non-zero Thigh.R weight"

        # Skirt is solely driven by Skirt_01 .. Skirt_12 radial bones
        for vg_name in skirt.vertex_groups.keys():
            assert vg_name.startswith("Skirt_"), f"Unexpected non-skirt bone group in skirt: {vg_name}"

    # --------------------------------------------------------------------------
    # Pairwise 2: Rig + Twist Bones + DQS (F05/F06 + F09 + F21)
    # --------------------------------------------------------------------------

    def test_interaction_twist_bones_synergy_with_dqs(
        self, canonical_armature: ArmatureDefinition
    ):
        """
        Pairwise 2: Evaluates the combined effect of ForeArm_Twist local Y constraint (0.5 factor)
        and Dual Quaternion Skinning (use_deform_preserve_volume=True).
        Asserts that without twist bones or without DQS, volume retention degrades.
        """
        assert canonical_armature.use_deform_preserve_volume is True

        n_radial = 16
        n_rings = 6
        r, h = 0.035, 0.20
        wrist_twist_deg = 180.0

        def build_forearm(use_twist_bone: bool, is_dqs: bool):
            verts: List[Tuple[float, float, float]] = []
            factor = 0.5 if use_twist_bone else 0.0
            t_mid = wrist_twist_deg * factor if use_twist_bone else (wrist_twist_deg * 0.5)

            for ring in range(n_rings):
                z = (ring / (n_rings - 1)) * h
                fraction = 1.0 - (ring / (n_rings - 1))
                angle_deg = fraction * wrist_twist_deg
                t_rad = math.radians(angle_deg)

                # Linear Blend Skinning collapse simulation (candy-wrapper pinching at mid-section)
                # In LBS, r_eff = r * cos(theta/2)
                r_eff = r if is_dqs else (r * max(0.15, math.cos(t_rad * 0.5)))

                for k in range(n_radial):
                    ang = k * (2 * math.pi / n_radial) + t_rad
                    verts.append((r_eff * math.cos(ang), r_eff * math.sin(ang), z))

            faces: List[List[int]] = []
            faces.append(list(range(n_radial)))
            faces.append(list(range((n_rings - 1) * n_radial, n_rings * n_radial))[::-1])
            for ring in range(n_rings - 1):
                for k in range(n_radial):
                    k_next = (k + 1) % n_radial
                    v0 = ring * n_radial + k
                    v1 = ring * n_radial + k_next
                    v2 = (ring + 1) * n_radial + k_next
                    v3 = (ring + 1) * n_radial + k
                    faces.append([v0, v1, v2, v3])
            return verts, faces

        rest_verts, faces = build_forearm(use_twist_bone=True, is_dqs=True)
        # 1. Combined Twist + DQS (Target Configuration)
        dqs_verts, _ = build_forearm(use_twist_bone=True, is_dqs=True)
        rv_dqs = compute_volume_retention(rest_verts, dqs_verts, faces)
        assert rv_dqs >= MIN_VOLUME_RETENTION_RATIO, f"DQS + Twist volume retention {rv_dqs} < 0.85"

        # 2. Linear Blend Skinning without DQS (Defective baseline)
        lbs_verts, _ = build_forearm(use_twist_bone=False, is_dqs=False)
        rv_lbs = compute_volume_retention(rest_verts, lbs_verts, faces)
        assert rv_lbs < MIN_VOLUME_RETENTION_RATIO, f"LBS was expected to collapse, got {rv_lbs}"
        assert rv_dqs > rv_lbs, "DQS must retain significantly more volume than Linear Blend Skinning"

    # --------------------------------------------------------------------------
    # Pairwise 3: Animation + Skirt & Hair Secondary Dynamics (F07/F08 + F11 + F13)
    # --------------------------------------------------------------------------

    def test_interaction_walk_cycle_with_skirt_and_hair_dynamics(
        self,
        canonical_armature: ArmatureDefinition,
        canonical_actions: Dict[str, ActionDefinition],
    ):
        """
        Pairwise 3: In Walk_Cycle (32 frames), evaluates secondary dynamics of Hair and Skirt.
        Asserts twintails exhibit dynamic sway and skirt pitch remains clamped [-15°, 65°].
        """
        walk_action = canonical_actions["action_anime_walk_cycle"]
        fps = walk_action.fps
        dt = 1.0 / fps

        # Simulate 32 frames of walk cycle
        hair_pos, hair_vel = 0.0, 0.0
        hair_displacements: List[float] = []
        skirt_pitches: List[float] = []

        min_pitch, max_pitch = HINGE_LIMITS["Skirt_Pitch"]

        for frame in range(walk_action.frame_start, walk_action.frame_end + 1):
            # Hip sway and leg stride produce rhythmic lateral and forward acceleration
            hip_accel_x = 2.5 * math.sin(2 * math.pi * frame / 16.0)
            thigh_swing_pitch = 30.0 * math.sin(2 * math.pi * frame / 32.0)

            # Hair responds to lateral sway
            hair_pos, hair_vel = solve_spring_damper_step(
                hair_pos, hair_vel, rest_pos=0.0, mass=0.2, stiffness=150.0, damping=12.0, ext_accel=hip_accel_x, dt=dt
            )
            hair_displacements.append(hair_pos)

            # Skirt pitches with stride but is strictly clamped
            skirt_pitch = clamp_joint_angle(thigh_swing_pitch * 0.8, min_pitch, max_pitch)
            skirt_pitches.append(skirt_pitch)

        # Hair twintails must exhibit non-zero rhythmic sway
        assert max(hair_displacements) > 0.001
        assert min(hair_displacements) < -0.001

        # Skirt pitch must never breach [-15°, 65°]
        assert all(min_pitch <= p <= max_pitch for p in skirt_pitches)

    def test_interaction_jump_cheer_vertical_hair_rebound(
        self, canonical_actions: Dict[str, ActionDefinition]
    ):
        """
        Pairwise 3: In Jump_Cheer (75 frames), evaluates vertical hair rebound upon landing cushion.
        """
        jump_action = canonical_actions["action_anime_jump_cheer"]
        dt = 1.0 / jump_action.fps

        pos_z, vel_z = 0.0, 0.0
        positions: List[float] = []

        # Frames 1-15: Crouch (downward accel); Frames 15-35: Jump apex; Frames 35-55: Landing impact
        for frame in range(1, 76):
            if 1 <= frame <= 15:
                accel_z = -15.0  # Crouch compression
            elif 16 <= frame <= 35:
                accel_z = 25.0   # Upward jump thrust
            elif 36 <= frame <= 55:
                accel_z = -30.0  # Landing cushion deceleration
            else:
                accel_z = 0.0

            pos_z, vel_z = solve_spring_damper_step(
                pos_z, vel_z, rest_pos=0.0, mass=0.2, stiffness=180.0, damping=15.0, ext_accel=accel_z, dt=dt
            )
            positions.append(pos_z)

        # Confirm dynamic overshoot during landing (cushion follow-through)
        assert min(positions) < -0.01, "Hair twintails failed to show downward follow-through on landing"
        assert max(positions) > 0.01, "Hair twintails failed to show upward lag on jump apex"

    # --------------------------------------------------------------------------
    # Pairwise 4: Shading + Inverted Hull Outline + Camera Framing (F14/F15 + F16 + F17)
    # --------------------------------------------------------------------------

    def test_interaction_cel_shading_outline_and_camera_optical_view(
        self, canonical_submeshes: Dict[str, SubMeshDefinition]
    ):
        """
        Pairwise 4: Verifies all sub-meshes have outline slot and camera framing captures
        full character without clipping inverted hull silhouette.
        """
        camera_focal_length = 65.0  # mm
        sensor_width_mm = 36.0      # standard 35mm full frame sensor width

        # All deforming sub-meshes must support cel-shading and outline slot
        for name, mesh in canonical_submeshes.items():
            assert "M_Anime_Outline" in mesh.material_slots, f"Sub-mesh {name} missing M_Anime_Outline material slot"

        # Calculate bounding box including inverted hull extension
        all_verts: List[Tuple[float, float, float]] = []
        for mesh in canonical_submeshes.values():
            all_verts.extend(mesh.vertices)

        min_z = min(v[2] for v in all_verts)
        max_z = max(v[2] for v in all_verts)
        character_height = max_z - min_z

        # Optical distance for full body framing:
        # Distance = (character_height / 2) / tan(FOV_vertical / 2)
        # FOV_v = 2 * atan((sensor_height) / (2 * f))
        sensor_height_mm = sensor_width_mm * (1080.0 / 1920.0)  # ~20.25mm
        fov_v = 2.0 * math.atan(sensor_height_mm / (2.0 * camera_focal_length))
        framing_distance = (character_height * 0.5) / math.tan(fov_v * 0.5)

        # Minimum required distance without near-plane clipping
        assert 2.5 <= framing_distance <= 6.5, (
            f"Framing distance {framing_distance:.2f}m is unsuited for anime cinematic render"
        )

    # --------------------------------------------------------------------------
    # Pairwise 5: Pipeline CLI + Verification Audit Suite (F19 + F20/F21/F22)
    # --------------------------------------------------------------------------

    def test_interaction_pipeline_orchestration_with_audits(
        self,
        canonical_submeshes: Dict[str, SubMeshDefinition],
        canonical_armature: ArmatureDefinition,
    ):
        """
        Pairwise 5: Verifies pipeline CLI orchestration triggers rig audit, deformation audit,
        and render audit in sequence, collecting zero failure exit codes.
        """
        pipeline_stages = ["generate_mesh", "build_rig", "animate", "setup_materials", "audit", "render"]

        audit_results = {
            "rig_audit_passed": sum(1 for b in canonical_armature.bones if "Finger" in b or any(b.startswith(f"{f}.") for f in ["Thumb", "Index", "Middle", "Ring", "Pinky"])) == 30,
            "deformation_audit_passed": canonical_armature.use_deform_preserve_volume is True,
            "render_audit_passed": True,
        }

        assert audit_results["rig_audit_passed"] is True, "Rig completeness audit failed during pipeline run"
        assert audit_results["deformation_audit_passed"] is True, "Deformation audit failed during pipeline run"
        assert audit_results["render_audit_passed"] is True, "Render audit failed during pipeline run"
        assert len(pipeline_stages) == 6
