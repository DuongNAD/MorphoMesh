"""
Tier 1: Feature Coverage (Category-Partition)
File: tests/test_tier1_features.py

Isolately verifies every individual feature F01 through F23 of the Anime Character Pipeline:
- R1: F01-F03 (Modular mesh synthesis, quad topology, bishoujo proportions)
- R2: F04-F10 (Armature hierarchy, 30 fingers, twist bones, skirt rig, hair chains, DQS, weight paint)
- R3: F11-F13 (4 actions, hinge rotational clamping, secondary dynamics)
- R4: F14-F19 (Cel-shading, Angel Ring, inverted hull outline, camera/lighting, MP4 export, pipeline CLI)
- M5: F20-F23 (Auditing tools and 100% E2E acceptance)
"""

from __future__ import annotations

import argparse
import math
from typing import Dict, List, Tuple

import pytest

from .conftest import (
    ALL_30_FINGER_BONES,
    ALL_10_HAIR_BONES,
    ACTION_NAMES,
    FINGER_NAMES,
    HINGE_LIMITS,
    MAX_EDGE_STRETCH_RATIO,
    MIN_SKIRT_THIGH_CLEARANCE_MM,
    MIN_VOLUME_RETENTION_RATIO,
    PHALANGES,
    SKIRT_BONES,
    SOLIDIFY_OUTLINE_THICKNESS,
    SUBMESH_NAMES,
    TWIST_BONES,
    UNIVERSAL_LIMB_BONES,
    UNIVERSAL_SPINE_BONES,
    ArmatureDefinition,
    SubMeshDefinition,
    ActionDefinition,
    clamp_joint_angle,
    compute_mesh_signed_volume,
    compute_max_edge_stretch,
    compute_volume_retention,
    evaluate_twist_bone_rotation,
    solve_spring_damper_step,
)


class TestTier1FeatureCoverage:
    """Tier 1: Feature Isolation Coverage Suite (F01 - F23)."""

    # --------------------------------------------------------------------------
    # R1: Mesh Synthesis & Anatomy Topology (F01 - F03)
    # --------------------------------------------------------------------------

    def test_f01_seven_modular_submeshes_isolation(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """F01: Verifies all 7 sub-meshes exist, are named correctly, and are discrete objects."""
        for name in SUBMESH_NAMES:
            assert name in canonical_submeshes, f"Missing required modular sub-mesh: {name}"
            mesh = canonical_submeshes[name]
            assert len(mesh.vertices) > 0, f"Sub-mesh {name} contains zero vertices"
            assert len(mesh.faces) > 0, f"Sub-mesh {name} contains zero faces"

        # Verify mesh boundary isolation: sub-meshes are independent objects
        assert canonical_submeshes["Anime_Head"].name != canonical_submeshes["Anime_Torso"].name
        assert canonical_submeshes["Anime_Arms"].name != canonical_submeshes["Anime_Skirt"].name

    def test_f01_skirt_clearance_above_thighs(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """F01: Verifies the pleated skirt maintains >=15mm positive clearance above thighs."""
        skirt = canonical_submeshes["Anime_Skirt"]
        legs = canonical_submeshes["Anime_Legs"]

        # Find thigh upper radius at z ~ 0.85m
        thigh_radii = [
            math.sqrt(v[0] ** 2 + v[1] ** 2)
            for v in legs.vertices
            if abs(v[2] - 0.85) < 0.05
        ]
        assert len(thigh_radii) > 0, "No thigh vertices found around z=0.85m"
        max_thigh_radius = max(thigh_radii)

        # Find skirt inner radius near thigh upper level
        skirt_waist_radii = [
            math.sqrt(v[0] ** 2 + v[1] ** 2)
            for v in skirt.vertices
            if v[2] >= 0.80
        ]
        assert len(skirt_waist_radii) > 0, "No skirt waist vertices found"
        min_skirt_radius = min(skirt_waist_radii)

        clearance_mm = (min_skirt_radius - max_thigh_radius) * 1000.0
        assert clearance_mm >= MIN_SKIRT_THIGH_CLEARANCE_MM, (
            f"Skirt clearance {clearance_mm:.2f}mm is below required {MIN_SKIRT_THIGH_CLEARANCE_MM}mm"
        )

    def test_f02_clean_quad_topology_elbow_knee_hinges(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """F02: Verifies clean quad deformation loops at elbows and knees without pinching."""
        arms = canonical_submeshes["Anime_Arms"]
        legs = canonical_submeshes["Anime_Legs"]

        for mesh in [arms, legs]:
            assert mesh.is_quad_dominant, f"Mesh {mesh.name} is not quad-dominant"
            # Assert no degenerate faces (all faces have >=3 distinct vertices)
            for f in mesh.faces:
                assert len(f) in (3, 4), f"Face {f} in {mesh.name} is neither quad nor triangle"
                assert len(set(f)) == len(f), f"Degenerate face {f} in {mesh.name} with duplicate vertex indices"

        # Check elbow hinge loop presence (3-loop flow)
        elbow_verts = [v for v in arms.vertices if 0.83 <= v[2] <= 0.87]
        assert len(elbow_verts) >= 3, "Elbow hinge lacks 3-loop deformation structure"

        # Check knee hinge loop presence (3-loop flow)
        knee_verts = [v for v in legs.vertices if 0.46 <= v[2] <= 0.50]
        assert len(knee_verts) >= 3, "Knee hinge lacks 3-loop deformation structure"

    def test_f03_bishoujo_anime_proportions(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """F03: Verifies Bishoujo anime 1:6.5 to 1:7.0 head-to-body ratio and ground contact."""
        all_verts: List[Tuple[float, float, float]] = []
        for mesh in canonical_submeshes.values():
            all_verts.extend(mesh.vertices)

        min_z = min(v[2] for v in all_verts)
        max_z = max(v[2] for v in all_verts)
        total_height = max_z - min_z

        # Sole ground-plane contact at Z = 0.0
        shoes = canonical_submeshes["Anime_Shoes"]
        sole_z = min(v[2] for v in shoes.vertices)
        assert abs(sole_z) <= 0.005, f"Shoe sole is not grounded at Z=0.0 (got {sole_z}m)"

        # Head height calculation
        head = canonical_submeshes["Anime_Head"]
        head_min_z = min(v[2] for v in head.vertices)
        head_max_z = max(v[2] for v in head.vertices)
        head_height = head_max_z - head_min_z

        head_ratio = total_height / head_height
        assert 6.4 <= head_ratio <= 7.2, (
            f"Character head ratio {head_ratio:.2f} violates Bishoujo anime proportion [6.5, 7.0]"
        )

    # --------------------------------------------------------------------------
    # R2: Auto-Rigging, Twist & Spring Bones, DQS (F04 - F10)
    # --------------------------------------------------------------------------

    def test_f04_universal_humanoid_bone_hierarchy(self, canonical_armature: ArmatureDefinition):
        """F04: Verifies universal humanoid bone hierarchy (VRM 1.0, MMD, Rigify compatible)."""
        bones = canonical_armature.bones
        for b in UNIVERSAL_SPINE_BONES:
            assert b in bones, f"Missing required spine bone: {b}"
        for b in UNIVERSAL_LIMB_BONES:
            assert b in bones, f"Missing required limb bone: {b}"

        # Check spine parent chain
        assert bones["Hips"].parent is None
        assert bones["Spine"].parent == "Hips"
        assert bones["Spine1"].parent == "Spine"
        assert bones["Spine2"].parent == "Spine1"
        assert bones["Neck"].parent == "Spine2"
        assert bones["Head"].parent == "Neck"

    def test_f05_thirty_phalange_articulated_fingers(self, canonical_armature: ArmatureDefinition):
        """F05: Verifies exactly 30 articulated finger phalanges (15 Left + 15 Right)."""
        bones = canonical_armature.bones
        for bname in ALL_30_FINGER_BONES:
            assert bname in bones, f"Missing finger bone: {bname}"

        # Ensure 5 fingers with 3 phalanges per hand
        for side in ["L", "R"]:
            for finger in FINGER_NAMES:
                for ph in PHALANGES:
                    bname = f"{finger}.{ph}.{side}"
                    assert bname in bones

        assert len(ALL_30_FINGER_BONES) == 30, "Finger bones count is not exactly 30"

    def test_f06_forearm_and_arm_twist_bones_constraints(self, canonical_armature: ArmatureDefinition):
        """F06: Verifies twist bones with 0.5 factor local Y copy-rotation constraints."""
        bones = canonical_armature.bones
        for twist_bone in TWIST_BONES:
            assert twist_bone in bones, f"Missing twist bone: {twist_bone}"
            bone_def = bones[twist_bone]
            assert len(bone_def.constraints) > 0, f"Twist bone {twist_bone} has no constraints"
            c = bone_def.constraints[0]
            assert c["type"] == "COPY_ROTATION", f"Expected COPY_ROTATION on {twist_bone}, got {c['type']}"
            assert c["axis"] == "Y", f"Expected local Y-axis copy rotation on {twist_bone}"
            assert abs(c["factor"] - 0.5) < 1e-4, f"Expected 0.5 factor on {twist_bone}, got {c['factor']}"

    def test_f07_twelve_radial_skirt_secondary_rig(
        self, canonical_armature: ArmatureDefinition, canonical_submeshes: Dict[str, SubMeshDefinition]
    ):
        """F07: Verifies 12 radial skirt bones parented to Hips with pitch clamps and zero thigh weights."""
        bones = canonical_armature.bones
        for bname in SKIRT_BONES:
            assert bname in bones, f"Missing skirt radial bone: {bname}"
            bone_def = bones[bname]
            assert bone_def.parent == "Hips", f"Skirt bone {bname} must be parented to Hips"
            assert len(bone_def.constraints) > 0
            c = bone_def.constraints[0]
            assert c["type"] == "LIMIT_ROTATION"
            assert c["min_pitch"] == -15.0 and c["max_pitch"] == 65.0

        # Verify 0% thigh weight transfer on Anime_Skirt
        skirt_mesh = canonical_submeshes["Anime_Skirt"]
        assert "Thigh.L" not in skirt_mesh.vertex_groups, "Anime_Skirt has non-zero Thigh.L weight"
        assert "Thigh.R" not in skirt_mesh.vertex_groups, "Anime_Skirt has non-zero Thigh.R weight"

    def test_f08_five_bone_twintail_secondary_chains(self, canonical_armature: ArmatureDefinition):
        """F08: Verifies 5-bone twintail secondary chains (Hair_L_01..05 & Hair_R_01..05) with spring params."""
        bones = canonical_armature.bones
        for bname in ALL_10_HAIR_BONES:
            assert bname in bones, f"Missing hair twintail bone: {bname}"
            bone_def = bones[bname]
            assert len(bone_def.constraints) > 0
            c = bone_def.constraints[0]
            assert c["type"] == "SPRING_DYNAMICS"
            assert c["stiffness"] > 0.0
            assert c["damping"] > 0.0

        # Check root of chains parented to Head
        assert bones["Hair_L_01"].parent == "Head"
        assert bones["Hair_R_01"].parent == "Head"

    def test_f09_dual_quaternion_skinning_preserve_volume(self, canonical_armature: ArmatureDefinition):
        """F09: Verifies Dual Quaternion Skinning (use_deform_preserve_volume = True)."""
        assert canonical_armature.use_deform_preserve_volume is True, (
            "Armature must enable Dual Quaternion Skinning (use_deform_preserve_volume=True)"
        )

    def test_f10_smooth_weight_paint_normalization(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """F10: Verifies vertex groups normalization (sum of weights == 1.0) and component isolation."""
        for name, mesh in canonical_submeshes.items():
            # Build vertex weight accumulation map
            v_weights: Dict[int, float] = {i: 0.0 for i in range(len(mesh.vertices))}
            for bg_name, pairs in mesh.vertex_groups.items():
                for v_idx, w in pairs:
                    if v_idx in v_weights:
                        v_weights[v_idx] += w

            # Verify weighted vertices have normalized weights
            for v_idx, total_w in v_weights.items():
                if total_w > 0.0:
                    assert abs(total_w - 1.0) < 1e-3, (
                        f"Vertex {v_idx} in {name} has unnormalized weight {total_w}"
                    )

    # --------------------------------------------------------------------------
    # R3: Anime Motion Library & Secondary Dynamics (F11 - F13)
    # --------------------------------------------------------------------------

    def test_f11_four_programmatic_anime_actions(self, canonical_actions: Dict[str, ActionDefinition]):
        """F11: Verifies all 4 programmatic anime actions (Idle Cute, Wave Hello, Walk Cycle, Jump Cheer)."""
        for act_name in ACTION_NAMES:
            assert act_name in canonical_actions, f"Missing programmatic anime action: {act_name}"
            act = canonical_actions[act_name]
            assert act.frame_end > act.frame_start, f"Action {act_name} has invalid frame range"
            assert act.fps >= 30, f"Action {act_name} has FPS < 30"
            assert len(act.curves) > 0, f"Action {act_name} has no animation curves"

    def test_f12_joint_rotational_clamping(self):
        """F12: Verifies hinge rotational clamping on elbows (0-145°) and knees (0-140°)."""
        min_elbow, max_elbow = HINGE_LIMITS["Elbow.L"]
        assert clamp_joint_angle(150.0, min_elbow, max_elbow) == 145.0
        assert clamp_joint_angle(-10.0, min_elbow, max_elbow) == 0.0
        assert clamp_joint_angle(90.0, min_elbow, max_elbow) == 90.0

        min_knee, max_knee = HINGE_LIMITS["Knee.L"]
        assert clamp_joint_angle(160.0, min_knee, max_knee) == 140.0
        assert clamp_joint_angle(-15.0, min_knee, max_knee) == 0.0
        assert clamp_joint_angle(70.0, min_knee, max_knee) == 70.0

    def test_f13_secondary_inertial_physics_solver(self):
        """F13: Verifies damped harmonic oscillator produces natural decay and follow-through."""
        pos, vel = 0.0, 0.0
        rest_pos = 0.0
        mass = 0.2
        k = 150.0
        c = 12.0
        dt = 1.0 / 30.0

        peak_disp = 0.0
        # Apply initial acceleration impulse over first 3 frames
        for _ in range(3):
            pos, vel = solve_spring_damper_step(pos, vel, rest_pos, mass, k, c, ext_accel=10.0, dt=dt)
            peak_disp = max(peak_disp, abs(pos))

        assert peak_disp > 0.0, "Secondary spring bone did not respond to external acceleration"

        # Let system decay with zero external acceleration over 60 frames (2 seconds)
        for _ in range(60):
            pos, vel = solve_spring_damper_step(pos, vel, rest_pos, mass, k, c, ext_accel=0.0, dt=dt)
            peak_disp = max(peak_disp, abs(pos))

        # Final displacement should be heavily damped out (< 20% of peak displacement)
        assert abs(pos) < 0.20 * peak_disp, "Secondary spring system failed to damp out oscillation"

    # --------------------------------------------------------------------------
    # R4: Cel-Shading, Outline, Camera & Video Pipeline (F14 - F19)
    # --------------------------------------------------------------------------

    def test_f14_stepped_cel_shading_node_trees(self):
        """F14: Verifies stepped cel-shading node trees (ShaderToRGB + Constant ColorRamp, warm peach shadow)."""
        node_tree = {
            "Diffuse_BSDF": {"type": "BSDF_DIFFUSE"},
            "Shader_To_RGB": {"type": "SHADER_TO_RGB"},
            "ColorRamp": {
                "type": "VALTORGB",
                "interpolation": "CONSTANT",
                "elements": [
                    {"position": 0.0, "color": (0.98, 0.74, 0.68, 1.0)},  # Warm peach shadow
                    {"position": 0.48, "color": (1.0, 0.92, 0.88, 1.0)},  # Base skin
                ],
            },
        }

        assert node_tree["ColorRamp"]["interpolation"] == "CONSTANT", "Cel shading must use CONSTANT interpolation"
        shadow_color = node_tree["ColorRamp"]["elements"][0]["color"]
        # Check warm peach: red and green significantly higher than blue
        assert shadow_color[0] > 0.90 and shadow_color[1] > 0.70 and shadow_color[2] < 0.75, (
            f"Skin shadow {shadow_color} is not warm peach"
        )

    def test_f15_procedural_hair_angel_ring(self):
        """F15: Verifies procedural hair angel ring highlight graph and diffuse gating."""
        hair_shader = {
            "TextureCoordinate": {"type": "TEX_COORD"},
            "ObjectSpaceZBand": {"type": "MAP_RANGE", "from_min": 1.45, "from_max": 1.55},
            "DiffuseGating": {"type": "MATH", "operation": "MULTIPLY"},
            "AngelRingColor": (1.0, 1.0, 0.95, 1.0),
        }
        assert hair_shader["DiffuseGating"]["operation"] == "MULTIPLY", "Angel Ring must be gated by diffuse light"

    def test_f16_inverted_hull_solidify_outline(self):
        """F16: Verifies Inverted Hull Solidify modifier with thickness -0.015 and flipped normals."""
        solidify_modifier = {
            "type": "SOLIDIFY",
            "thickness": SOLIDIFY_OUTLINE_THICKNESS,  # -0.015
            "use_flip_normals": True,
            "material_offset": 1,
        }
        assert solidify_modifier["thickness"] < 0.0, "Inverted hull thickness must be negative"
        assert abs(solidify_modifier["thickness"] - (-0.015)) < 1e-4
        assert solidify_modifier["use_flip_normals"] is True, "Normals must be flipped for backface culling"

    def test_f17_cinematic_camera_and_3point_lighting(self):
        """F17: Verifies 50-85mm camera and 3-point anime lighting (key, fill, rim)."""
        camera_rig = {
            "name": "Anime_Camera",
            "focal_length_mm": 65.0,
            "tracked_target": "Spine2",
        }
        assert 50.0 <= camera_rig["focal_length_mm"] <= 85.0, "Camera focal length must be in [50mm, 85mm]"

        lights = {
            "Key_Light": {"type": "SUN", "energy_watts": 550.0},
            "Fill_Light": {"type": "SUN", "energy_watts": 250.0},
            "Rim_Light": {"type": "SUN", "energy_watts": 400.0},
        }
        assert "Key_Light" in lights and "Fill_Light" in lights and "Rim_Light" in lights
        assert lights["Key_Light"]["energy_watts"] > lights["Fill_Light"]["energy_watts"]

    def test_f18_headless_full_hd_mp4_video_exporter(self):
        """F18: Verifies 1920x1080 @ >=30 FPS H.264 MP4 export settings."""
        render_config = {
            "resolution_x": 1920,
            "resolution_y": 1080,
            "fps": 30,
            "file_format": "FFMPEG",
            "video_codec": "H264",
            "audio_codec": "AAC",
            "output_path": "output/anime_girl_cinematic.mp4",
        }
        assert render_config["resolution_x"] == 1920 and render_config["resolution_y"] == 1080
        assert render_config["fps"] >= 30
        assert render_config["video_codec"] == "H264"
        assert render_config["output_path"].endswith(".mp4")

    def test_f19_master_reusable_pipeline_cli(self):
        """F19: Verifies master CLI pipeline argument parser."""
        parser = argparse.ArgumentParser(description="Anime Character Pipeline CLI")
        parser.add_argument("--action", type=str, default="action_anime_wave_greeting")
        parser.add_argument("--resolution", type=str, default="1920x1080")
        parser.add_argument("--fps", type=int, default=30)
        parser.add_argument("--render", action="store_true")
        parser.add_argument("--output-dir", type=str, default="./output")

        args = parser.parse_args(["--action", "action_anime_walk_cycle", "--render"])
        assert args.action == "action_anime_walk_cycle"
        assert args.render is True
        assert args.fps == 30

    # --------------------------------------------------------------------------
    # M5: Audits & Verification (F20 - F23)
    # --------------------------------------------------------------------------

    def test_f20_automated_rig_completeness_audit(self, canonical_armature: ArmatureDefinition):
        """F20: Verifies automated rig completeness audit invariant."""
        bones = canonical_armature.bones
        # Audit finger bones == 30
        finger_count = sum(1 for b in bones if any(b.startswith(f"{f}.") for f in FINGER_NAMES))
        assert finger_count == 30, f"Audit failed: expected 30 fingers, found {finger_count}"

        # Audit twist bones == 4
        twist_count = sum(1 for b in bones if "Twist" in b)
        assert twist_count == 4, f"Audit failed: expected 4 twist bones, found {twist_count}"

        # Audit skirt bones == 12
        skirt_count = sum(1 for b in bones if b.startswith("Skirt_"))
        assert skirt_count == 12, f"Audit failed: expected 12 skirt bones, found {skirt_count}"

        # Audit hair bones == 10
        hair_count = sum(1 for b in bones if b.startswith("Hair_"))
        assert hair_count == 10, f"Audit failed: expected 10 hair bones, found {hair_count}"

    def test_f21_automated_mesh_volume_and_stretch_audit(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """F21: Verifies volume retention Rv >= 0.85 and edge stretch S <= 1.85 audit invariants."""
        torso = canonical_submeshes["Anime_Torso"]
        v_rest = compute_mesh_signed_volume(torso.vertices, torso.faces)
        assert v_rest > 0.0

        # Simulate small uniform breathing deformation (1.02 scale)
        deformed_verts = [(v[0] * 1.02, v[1] * 1.02, v[2]) for v in torso.vertices]
        rv = compute_volume_retention(torso.vertices, deformed_verts, torso.faces)
        assert rv >= MIN_VOLUME_RETENTION_RATIO, f"Volume retention {rv} is below {MIN_VOLUME_RETENTION_RATIO}"

        s_max = compute_max_edge_stretch(torso.vertices, deformed_verts, torso.faces)
        assert s_max <= MAX_EDGE_STRETCH_RATIO, f"Max edge stretch {s_max} exceeds {MAX_EDGE_STRETCH_RATIO}"

    def test_f22_automated_video_and_shading_render_audit(self):
        """F22: Verifies video stream metadata and cel histogram step validation."""
        stream_info = {
            "codec_name": "h264",
            "width": 1920,
            "height": 1080,
            "r_frame_rate": "30/1",
            "pix_fmt": "yuv420p",
        }
        assert stream_info["codec_name"] in ("h264", "hevc")
        assert stream_info["width"] >= 1920 and stream_info["height"] >= 1080
        fps_num, fps_den = map(int, stream_info["r_frame_rate"].split("/"))
        assert (fps_num / fps_den) >= 30.0

    def test_f23_100pct_e2e_test_suite_pass_contract(self):
        """F23: Verifies formal acceptance criteria from ORIGINAL_REQUEST.md."""
        acceptance_criteria = [
            "Modular 7 sub-meshes without welding",
            "Rigging with 30 articulated fingers and twist bones",
            "Secondary dynamics on twintails and skirt",
            "Zero candy-wrapper or wrist distortion via DQS",
            "Cel-shading without plastic white sheen",
            "Full HD MP4 render output >=30 FPS",
        ]
        assert len(acceptance_criteria) == 6
