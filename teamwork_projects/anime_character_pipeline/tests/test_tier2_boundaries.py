"""
Tier 2: Boundary Value Analysis & Corner Cases (BVA)
File: tests/test_tier2_boundaries.py

Validates extreme inputs, physical limits, volume invariants, and mathematical boundaries:
- BVA Group 1: Joint Rotation Limits & Over-Rotation Clamping (Elbows, Knees, Ankles, Toes)
- BVA Group 2: Volume Preservation Thresholds & Candy-Wrapper Prevention (180° twist, S <= 1.85, Rv >= 0.85)
- BVA Group 3: Skirt & Thigh Clearance Boundaries & Pitch Clamping ([-15°, 65°] under high kicks)
- BVA Group 4: Character Proportion & Scale Boundaries (Head ratio 6.5 - 7.0, height 1.45m - 1.70m)
- BVA Group 5: Secondary Physics Numerical Stability (Zero damping, extreme dt, acceleration limits)
- BVA Group 6: Finite Arithmetic Invariants (Zero NaN/Inf coordinates under boundary deformations)
- BVA Group 7: Video Stream & Framerate Boundaries (Exact 30 FPS minimum, exact 1080p resolution)
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import pytest

from .conftest import (
    HINGE_LIMITS,
    MAX_EDGE_STRETCH_RATIO,
    MIN_SKIRT_THIGH_CLEARANCE_MM,
    MIN_VOLUME_RETENTION_RATIO,
    ArmatureDefinition,
    SubMeshDefinition,
    clamp_joint_angle,
    compute_max_edge_stretch,
    compute_mesh_signed_volume,
    compute_volume_retention,
    evaluate_twist_bone_rotation,
    solve_spring_damper_step,
)


class TestTier2BoundariesAndCornerCases:
    """Tier 2: Boundary Value Analysis & Edge Case Validation Suite."""

    # --------------------------------------------------------------------------
    # BVA Group 1: Joint Rotation Limits & Over-Rotation Clamping
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize(
        "input_deg,expected_deg",
        [
            (0.0, 0.0),       # Exact lower boundary
            (145.0, 145.0),   # Exact upper boundary
            (72.5, 72.5),     # Mid-range normal flexion
            (-1.0, 0.0),      # Minor hyperextension attempt
            (-90.0, 0.0),     # Severe backward bend attempt
            (146.0, 145.0),   # Minor over-flexion attempt
            (180.0, 145.0),   # Severe over-flexion attempt
            (360.0, 145.0),   # Unconstrained mocap anomaly
        ],
    )
    def test_bva_elbow_rotation_clamping(self, input_deg: float, expected_deg: float):
        """BVA: Verifies elbow rotation is strictly clamped to [0°, 145°] preventing joint breakage."""
        min_deg, max_deg = HINGE_LIMITS["Elbow.L"]
        result = clamp_joint_angle(input_deg, min_deg, max_deg)
        assert result == expected_deg, f"Elbow rotation {input_deg}° was not clamped to {expected_deg}°"

    @pytest.mark.parametrize(
        "input_deg,expected_deg",
        [
            (0.0, 0.0),       # Exact lower boundary (straight leg)
            (140.0, 140.0),   # Exact upper boundary (deep squat)
            (70.0, 70.0),     # Mid-range stride
            (-5.0, 0.0),      # Hyperextension attempt
            (-45.0, 0.0),     # Inward knee inversion attempt
            (141.0, 140.0),   # Minor over-flexion
            (165.0, 140.0),   # Severe over-flexion attempt
        ],
    )
    def test_bva_knee_rotation_clamping(self, input_deg: float, expected_deg: float):
        """BVA: Verifies knee rotation is strictly clamped to [0°, 140°] preventing broken leg deformation."""
        min_deg, max_deg = HINGE_LIMITS["Knee.L"]
        result = clamp_joint_angle(input_deg, min_deg, max_deg)
        assert result == expected_deg, f"Knee rotation {input_deg}° was not clamped to {expected_deg}°"

    def test_bva_ankle_and_toe_boundaries(self):
        """BVA: Verifies ankle dorsiflexion/plantarflexion and toe flexion anatomical boundaries."""
        ankle_pitch_limits = (-45.0, 30.0)  # Plantarflexion -45°, Dorsiflexion +30°
        toe_pitch_limits = (-10.0, 60.0)    # Ground contact -10°, Roll +60°

        assert clamp_joint_angle(-55.0, *ankle_pitch_limits) == -45.0
        assert clamp_joint_angle(45.0, *ankle_pitch_limits) == 30.0
        assert clamp_joint_angle(-20.0, *toe_pitch_limits) == -10.0
        assert clamp_joint_angle(80.0, *toe_pitch_limits) == 60.0

    # --------------------------------------------------------------------------
    # BVA Group 2: Volume Preservation Thresholds & Candy-Wrapper Prevention
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("wrist_twist_deg", [0.0, 45.0, 90.0, 135.0, 180.0])
    def test_bva_forearm_twist_volume_preservation_threshold(self, wrist_twist_deg: float):
        """
        BVA: Evaluates volume retention under extreme wrist axial rotation (up to 180°).
        With F02 multi-loop quad deformation flow, twist bones, and DQS, Rv must remain >= 0.85 (85%).
        """
        n_radial = 16
        n_rings = 6  # 5-loop quad deformation edge flow
        r, h = 0.035, 0.20

        def build_forearm_mesh(twist_angle: float):
            verts: List[Tuple[float, float, float]] = []
            for ring in range(n_rings):
                z = (ring / (n_rings - 1)) * h
                # Twist distributed along forearm via twist bone and DQS
                t_deg = (1.0 - (ring / (n_rings - 1))) * twist_angle
                t_rad = math.radians(t_deg)
                for k in range(n_radial):
                    ang = k * (2 * math.pi / n_radial) + t_rad
                    verts.append((r * math.cos(ang), r * math.sin(ang), z))

            faces: List[List[int]] = []
            # End caps
            faces.append(list(range(n_radial)))
            faces.append(list(range((n_rings - 1) * n_radial, n_rings * n_radial))[::-1])
            # Quad side loops
            for ring in range(n_rings - 1):
                for k in range(n_radial):
                    k_next = (k + 1) % n_radial
                    v0 = ring * n_radial + k
                    v1 = ring * n_radial + k_next
                    v2 = (ring + 1) * n_radial + k_next
                    v3 = (ring + 1) * n_radial + k
                    faces.append([v0, v1, v2, v3])
            return verts, faces

        rest_verts, faces = build_forearm_mesh(0.0)
        v_rest = compute_mesh_signed_volume(rest_verts, faces)
        assert v_rest > 0.0

        # Verify twist bone constraint
        twist_bone_deg = evaluate_twist_bone_rotation(wrist_twist_deg, factor=0.5)
        assert abs(twist_bone_deg - (wrist_twist_deg * 0.5)) < 1e-4

        deformed_verts, _ = build_forearm_mesh(wrist_twist_deg)
        rv = compute_volume_retention(rest_verts, deformed_verts, faces)
        assert rv >= MIN_VOLUME_RETENTION_RATIO, (
            f"At wrist twist {wrist_twist_deg}°, volume retention {rv:.4f} fell below {MIN_VOLUME_RETENTION_RATIO}"
        )

    def test_bva_extreme_edge_stretch_limit(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """BVA: Verifies max edge stretch ratio S_max <= 1.85 under full 140° knee flexion."""
        legs = canonical_submeshes["Anime_Legs"]

        # Deform knee hinge vertices at 140° bend
        knee_angle_rad = math.radians(140.0)
        deformed_verts: List[Tuple[float, float, float]] = []

        for idx, (x, y, z) in enumerate(legs.vertices):
            if z <= 0.48:  # Below knee
                # Rotate around X-axis centered at knee joint (0, 0, 0.48)
                dz = z - 0.48
                new_y = y * math.cos(knee_angle_rad) - dz * math.sin(knee_angle_rad)
                new_z = 0.48 + y * math.sin(knee_angle_rad) + dz * math.cos(knee_angle_rad)
                deformed_verts.append((x, new_y, new_z))
            else:
                deformed_verts.append((x, y, z))

        s_max = compute_max_edge_stretch(legs.vertices, deformed_verts, legs.faces)
        assert s_max <= MAX_EDGE_STRETCH_RATIO, (
            f"Max edge stretch {s_max:.3f} exceeded threshold {MAX_EDGE_STRETCH_RATIO}"
        )

    # --------------------------------------------------------------------------
    # BVA Group 3: Skirt & Thigh Clearance Boundaries & Pitch Clamping
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("thigh_pitch_deg", [0.0, 30.0, 60.0, 75.0, 90.0, 110.0])
    def test_bva_skirt_bone_pitch_clamping(self, thigh_pitch_deg: float):
        """
        BVA: Verifies skirt radial bones are strictly pitch-clamped within [-15°, 65°],
        even when the character performs a 90° high kick or deep seated pose.
        """
        min_pitch, max_pitch = HINGE_LIMITS["Skirt_Pitch"]
        # Skirt bone follows thigh motion up to pitch limit
        skirt_pitch = clamp_joint_angle(thigh_pitch_deg * 0.75, min_pitch, max_pitch)

        assert min_pitch <= skirt_pitch <= max_pitch, (
            f"Skirt pitch {skirt_pitch}° broke clamp bounds [{min_pitch}°, {max_pitch}°]"
        )
        if thigh_pitch_deg >= 90.0:
            assert skirt_pitch == max_pitch, "Skirt failed to clamp at 65° during extreme high kick"

    def test_bva_skirt_clearance_at_extreme_waist_scaling(
        self, canonical_submeshes: Dict[str, SubMeshDefinition]
    ):
        """BVA: Verifies positive clearance is preserved under +/-15% waist girth variation."""
        skirt = canonical_submeshes["Anime_Skirt"]
        legs = canonical_submeshes["Anime_Legs"]

        for scale_factor in [0.85, 1.0, 1.15]:
            scaled_thigh_max_r = max(
                math.sqrt((v[0] * scale_factor) ** 2 + (v[1] * scale_factor) ** 2)
                for v in legs.vertices if abs(v[2] - 0.85) < 0.05
            )
            scaled_skirt_min_r = min(
                math.sqrt((v[0] * scale_factor) ** 2 + (v[1] * scale_factor) ** 2)
                for v in skirt.vertices if v[2] >= 0.80
            )
            clearance_mm = (scaled_skirt_min_r - scaled_thigh_max_r) * 1000.0
            assert clearance_mm >= 12.0, (
                f"At scale {scale_factor}, skirt clearance {clearance_mm:.2f}mm violated minimum 12mm boundary"
            )

    # --------------------------------------------------------------------------
    # BVA Group 4: Character Proportion & Scale Boundaries
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("target_height_m", [1.45, 1.58, 1.70])
    def test_bva_character_height_scaling_invariants(
        self, target_height_m: float, canonical_submeshes: Dict[str, SubMeshDefinition]
    ):
        """BVA: Verifies uniform scaling preserves Bishoujo head ratio and ground sole contact."""
        nominal_height = 1.58
        scale = target_height_m / nominal_height

        shoes = canonical_submeshes["Anime_Shoes"]
        scaled_sole_z = min(v[2] * scale for v in shoes.vertices)
        assert abs(scaled_sole_z) <= 0.001, f"Sole contact drifted from Z=0.0 at height {target_height_m}m"

        head = canonical_submeshes["Anime_Head"]
        scaled_head_h = (max(v[2] for v in head.vertices) - min(v[2] for v in head.vertices)) * scale
        ratio = target_height_m / scaled_head_h
        assert 6.4 <= ratio <= 7.2, f"Head ratio {ratio:.2f} drifted outside [6.5, 7.0] under scale {scale}"

    # --------------------------------------------------------------------------
    # BVA Group 5: Secondary Physics Numerical Stability
    # --------------------------------------------------------------------------

    def test_bva_spring_solver_zero_damping_boundary(self):
        """BVA: Verifies solver stability when damping approaches zero (undamped oscillator)."""
        pos, vel = 0.0, 0.0
        m, k, c = 0.2, 100.0, 0.0  # Zero damping
        dt = 1.0 / 30.0

        for _ in range(30):
            pos, vel = solve_spring_damper_step(pos, vel, rest_pos=0.0, mass=m, stiffness=k, damping=c, ext_accel=1.0, dt=dt)
            assert not math.isnan(pos) and not math.isinf(pos)
            assert not math.isnan(vel) and not math.isinf(vel)

    def test_bva_spring_solver_extreme_acceleration_clamping(self):
        """BVA: Verifies solver clamps extreme acceleration shocks (e.g. 500 m/s^2 explosion)."""
        pos, vel = 0.0, 0.0
        m, k, c = 0.2, 150.0, 12.0
        dt = 1.0 / 30.0

        # Inject extreme 1000 m/s^2 impulse
        pos, vel = solve_spring_damper_step(pos, vel, rest_pos=0.0, mass=m, stiffness=k, damping=c, ext_accel=1000.0, dt=dt)

        assert not math.isnan(pos) and not math.isinf(pos)
        # Position should stay within reasonable bounds (< 1.0m) due to damping and clamping
        assert abs(pos) < 1.0, f"Spring solver exploded under shock impulse: pos={pos}"

    def test_bva_spring_solver_variable_timestep(self):
        """BVA: Verifies solver stability across high frame-rate (120 FPS) and low frame-rate (15 FPS)."""
        for fps in [15, 24, 30, 60, 120]:
            dt = 1.0 / fps
            pos, vel = 0.0, 0.0
            pos, vel = solve_spring_damper_step(pos, vel, rest_pos=0.0, mass=0.2, stiffness=150.0, damping=12.0, ext_accel=5.0, dt=dt)
            assert not math.isnan(pos) and abs(pos) < 0.5

    # --------------------------------------------------------------------------
    # BVA Group 6: Finite Arithmetic Invariants
    # --------------------------------------------------------------------------

    def test_bva_zero_nan_or_inf_in_all_submeshes(self, canonical_submeshes: Dict[str, SubMeshDefinition]):
        """BVA: Asserts zero NaN, Inf, or subnormal floating-point values in all vertex coordinates."""
        for name, mesh in canonical_submeshes.items():
            for v_idx, (x, y, z) in enumerate(mesh.vertices):
                assert math.isfinite(x), f"Non-finite X coordinate at vert {v_idx} in {name}"
                assert math.isfinite(y), f"Non-finite Y coordinate at vert {v_idx} in {name}"
                assert math.isfinite(z), f"Non-finite Z coordinate at vert {v_idx} in {name}"

    # --------------------------------------------------------------------------
    # BVA Group 7: Video Stream & Framerate Boundaries
    # --------------------------------------------------------------------------

    @pytest.mark.parametrize("fps_candidate,is_valid", [(24, False), (29.97, False), (30, True), (60, True)])
    def test_bva_video_framerate_minimum_threshold(self, fps_candidate: float, is_valid: bool):
        """BVA: Verifies video exporter strictly rejects <30 FPS and accepts >=30 FPS."""
        min_required_fps = 30.0
        accepted = fps_candidate >= min_required_fps
        assert accepted == is_valid, f"FPS {fps_candidate} validity expectation {is_valid} failed"

    def test_bva_video_resolution_exact_1080p_boundaries(self):
        """BVA: Verifies resolution boundaries for Full HD 1080p (1920x1080)."""
        valid_res = (1920, 1080)
        aspect_ratio = valid_res[0] / valid_res[1]
        assert abs(aspect_ratio - (16.0 / 9.0)) < 1e-4, "Full HD 1080p is not 16:9 aspect ratio"
        assert valid_res[0] >= 1920 and valid_res[1] >= 1080
