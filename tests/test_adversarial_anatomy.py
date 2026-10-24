"""
Adversarial Empirical Stress Test Suite for MorphoMesh Anatomy Engine.

Author: Challenger M2-1 (Kinematic & Stance Empirical Stress Test)
Targets:
1. Stance classification boundary conditions, degeneracies, scale extremes, and noise.
2. Palpable bony landmark detection: malleoli vertical/anterior asymmetry across scale spectrum ($H=0.3$m to $6.0$m) and translations.
3. ICR joint pivot estimation stability under rigid transformations, scaling, and biocentric internal offsets.
4. Bone roll normalization: 360-degree pole sweep, singular orientations, collinear pre-bend injection, and candy-wrapper elimination.
5. Volumetric geodesic biharmonic skinning air-gap boundary barrier verification.
"""

import math
from typing import Dict, List, Tuple
import numpy as np
import pytest

from morphomesh.anatomy import (
    LocomotorStance,
    StanceClassificationResult,
    classify_locomotor_stance,
    BonyLandmark,
    BonyLandmarks,
    ICRJointPivot,
    compute_bony_landmarks,
    estimate_icr_joint_pivot,
    estimate_icr_joint_pivots,
    BoneRollResult,
    PreBendResult,
    apply_joint_prebend,
    compute_hinge_plane_normal,
    solve_biomechanical_bone_roll,
    solve_limb_chain_bone_roll_and_prebend,
    compute_geodesic_skin_weights,
)
from tests.test_anatomy import (
    generate_humanoid_mesh,
    generate_plantigrade_bear_mesh,
    generate_digitigrade_canine_mesh,
    generate_unguligrade_horse_mesh,
)


# ==============================================================================
# 1. ADVERSARIAL STANCE CLASSIFICATION
# ==============================================================================

class TestAdversarialStanceClassification:
    """Stress-tests stance classification across boundary cases, perturbations, and degenerate inputs."""

    @pytest.mark.parametrize("r_hock, hint, expected_stance", [
        (0.12, "bear", LocomotorStance.PLANTIGRADE),
        (0.18, None, LocomotorStance.PLANTIGRADE),
        (0.22, "bear", LocomotorStance.PLANTIGRADE),
        (0.26, "wolf", LocomotorStance.DIGITIGRADE),
        (0.35, "canine", LocomotorStance.DIGITIGRADE),
        (0.42, "feline", LocomotorStance.DIGITIGRADE),
        (0.50, "horse", LocomotorStance.UNGULIGRADE),
        (0.65, None, LocomotorStance.UNGULIGRADE),
        (0.85, "deer", LocomotorStance.UNGULIGRADE),
    ])
    def test_hock_ratio_step_boundaries(self, r_hock: float, hint: str, expected_stance: LocomotorStance):
        """Verify stance classification across the spectrum of hock height ratios."""
        base_verts = generate_digitigrade_canine_mesh(height=1.0)
        z_hip = 0.8
        z_hock = z_hip * r_hock
        joints = {
            "hip": (0.0, -0.3, z_hip),
            "hock": (0.0, -0.3, z_hock),
            "toe": (0.0, -0.3, 0.0),
        }
        res = classify_locomotor_stance(base_verts, skeleton_joints=joints, species_hint=hint)
        assert isinstance(res.stance, LocomotorStance)
        assert res.stance == expected_stance, f"Expected {expected_stance} for r_hock={r_hock}, got {res.stance}"
        assert 0.0 <= res.confidence <= 1.0

    def test_pure_geometric_digitigrade_classification(self):
        """Verify that digitigrade stance can be classified purely geometrically without species hints."""
        # Quadruped mesh with 4 compact round pads (aspect ratio ~ 1.0, moderate contact area)
        pts = []
        for y in np.linspace(-0.5, 0.5, 100):
            pts.append([0.1 * math.cos(y * 10), y, 1.0])
        # 4 round paw pads: 2cm x 2cm -> contact_area_ratio = 0.0016
        for sx in [-0.2, 0.2]:
            for sy in [-0.35, 0.35]:
                for x in np.linspace(sx - 0.01, sx + 0.01, 5):
                    for y in np.linspace(sy - 0.01, sy + 0.01, 5):
                        pts.append([x, y, 0.0])
        pts = np.array(pts)
        # Moderate hock height: hip at 0.35m, hock at 0.11m -> eta_hock = 0.314, metapodial angle ~ 33.4 deg
        joints = {"hip": (0.0, -0.35, 0.35), "hock": (0.0, -0.35, 0.11), "toe": (0.0, -0.35, 0.0)}
        res = classify_locomotor_stance(pts, skeleton_joints=joints)
        assert res.stance == LocomotorStance.DIGITIGRADE
        assert res.confidence >= 0.85
        assert 0.22 < res.hock_height_ratio <= 0.48

    @pytest.mark.parametrize("scale", [0.005, 0.05, 0.5, 1.0, 5.0, 50.0, 500.0])
    def test_uniform_scale_invariance_across_all_stances(self, scale: float):
        """Stance classification must remain invariant from rodent scale (5mm) to kaiju scale (500m)."""
        # Humanoid (uniform scaling of base mesh)
        base_human = generate_humanoid_mesh(height=1.65)
        res_h = classify_locomotor_stance(base_human * scale)
        assert res_h.stance == LocomotorStance.HUMANOID
        assert res_h.is_biped is True
        assert res_h.ground_contact_count == 2

        # Bear (Plantigrade)
        base_bear = generate_plantigrade_bear_mesh(height=1.2, length=1.8)
        res_b = classify_locomotor_stance(base_bear * scale, species_hint="bear")
        assert res_b.stance == LocomotorStance.PLANTIGRADE
        assert res_b.is_biped is False

        # Wolf (Digitigrade)
        base_wolf = generate_digitigrade_canine_mesh(height=0.8, length=1.1)
        res_w = classify_locomotor_stance(base_wolf * scale, species_hint="wolf")
        assert res_w.stance == LocomotorStance.DIGITIGRADE

        # Horse (Unguligrade)
        base_horse = generate_unguligrade_horse_mesh(height=1.6, length=1.9)
        res_eq = classify_locomotor_stance(base_horse * scale, species_hint="horse")
        assert res_eq.stance == LocomotorStance.UNGULIGRADE

    def test_extreme_translation_invariance(self):
        """Mesh coordinates offset by massive world translation must classify identically."""
        base_verts = generate_humanoid_mesh(height=1.65)
        offset = np.array([12345.67, -98765.43, 54321.0])
        res_orig = classify_locomotor_stance(base_verts)
        res_trans = classify_locomotor_stance(base_verts + offset)
        assert res_trans.stance == res_orig.stance
        assert res_trans.is_biped == res_orig.is_biped
        assert res_trans.ground_contact_count == res_orig.ground_contact_count

    def test_insufficient_vertices_safe_fallback(self):
        """Point clouds with less than 4 vertices should fallback gracefully without crashing."""
        few_pts = np.array([[0.0, 0.0, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)
        res = classify_locomotor_stance(few_pts)
        assert isinstance(res, StanceClassificationResult)
        assert res.stance == LocomotorStance.HUMANOID
        assert res.diagnostics.get("reason") == "insufficient_vertices"

    def test_heavy_vertex_jitter_noise(self):
        """Classification must resist uniform Gaussian noise up to 3% body height."""
        verts = generate_plantigrade_bear_mesh(height=1.2)
        rng = np.random.RandomState(42)
        noise = rng.normal(0, 0.03 * 1.2, verts.shape)
        res = classify_locomotor_stance(verts + noise, species_hint="bear")
        assert res.stance == LocomotorStance.PLANTIGRADE

    def test_aspect_ratio_biped_transition_boundary(self):
        """Verify boundary behavior for vertical aspect ratio around humanoid transition threshold."""
        pts_tall = np.array([
            [-0.1, 0.0, 0.0], [0.1, 0.0, 0.0],  # 2 ground contacts
            [0.0, 0.0, 1.5],                    # Top vertex, vertical_aspect = 1.5 / 0.2 = 7.5
            [0.0, 0.0, 0.8],
        ], dtype=np.float64)
        res_tall = classify_locomotor_stance(pts_tall)
        assert res_tall.stance == LocomotorStance.HUMANOID
        assert res_tall.is_biped is True


# ==============================================================================
# 2. ADVERSARIAL PALPABLE BONY LANDMARKS & MALLEOLI ASYMMETRY
# ==============================================================================

class TestAdversarialBonyLandmarks:
    """Rigorous verification of anthropometric landmarks and malleoli asymmetry."""

    @pytest.mark.parametrize("height", [0.30, 0.75, 1.20, 1.65, 2.10, 3.50, 6.0])
    def test_malleoli_anthropometric_asymmetry_across_heights(self, height: float):
        """
        CRITICAL BIO-METRIC MANDATE:
        For authentic human skeletal anatomy:
        1. Vertical asymmetry: Medial malleolus is HIGHER (+Z) than lateral malleolus by >= 10mm (0.010m).
        2. Anterior-posterior asymmetry: Medial malleolus is ANTERIOR (-Y in Blender space) to lateral malleolus.
        Must hold for both Left and Right limbs across dwarf to giant heights.
        """
        verts = generate_humanoid_mesh(height=height)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=height)

        for side in ["L", "R"]:
            med_key = f"medial_malleolus_{side}"
            lat_key = f"lateral_malleolus_{side}"
            assert med_key in lms, f"Missing {med_key}"
            assert lat_key in lms, f"Missing {lat_key}"

            med = lms[med_key]
            lat = lms[lat_key]

            # 1. Vertical asymmetry (Delta Z >= 10mm)
            delta_z = med.position[2] - lat.position[2]
            assert delta_z >= 0.010, (
                f"Height {height}m ({side}): Medial malleolus Z ({med.position[2]:.4f}) must be >= 10mm "
                f"higher than lateral malleolus Z ({lat.position[2]:.4f}), got delta_z={delta_z*1000:.1f}mm"
            )

            # 2. Anterior-posterior asymmetry (Y_medial < Y_lateral)
            delta_y = lat.position[1] - med.position[1]
            assert delta_y > 0.0, (
                f"Height {height}m ({side}): Medial malleolus Y ({med.position[1]:.4f}) must be anterior "
                f"(smaller Y) to lateral malleolus Y ({lat.position[1]:.4f}), got delta_y={delta_y:.4f}"
            )

    def test_bilateral_sagittal_symmetry(self):
        """Left and Right bilateral landmarks must exhibit exact mirror symmetry across X=0."""
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)

        bilateral_pairs = [
            ("acromion_L", "acromion_R"),
            ("olecranon_L", "olecranon_R"),
            ("patella_L", "patella_R"),
            ("medial_femoral_epicondyle_L", "medial_femoral_epicondyle_R"),
            ("lateral_femoral_epicondyle_L", "lateral_femoral_epicondyle_R"),
            ("medial_malleolus_L", "medial_malleolus_R"),
            ("lateral_malleolus_L", "lateral_malleolus_R"),
            ("greater_trochanter_L", "greater_trochanter_R"),
        ]

        for left_name, right_name in bilateral_pairs:
            assert left_name in lms and right_name in lms
            p_L = lms[left_name].np_position
            p_R = lms[right_name].np_position

            # X coordinates must be opposite signs (p_L.x == -p_R.x)
            assert np.isclose(p_L[0], -p_R[0], atol=1e-5), f"{left_name}/{right_name} X asymmetry: {p_L[0]} vs {p_R[0]}"
            # Y and Z coordinates must match
            assert np.isclose(p_L[1], p_R[1], atol=1e-5), f"{left_name}/{right_name} Y mismatch: {p_L[1]} vs {p_R[1]}"
            assert np.isclose(p_L[2], p_R[2], atol=1e-5), f"{left_name}/{right_name} Z mismatch: {p_L[2]} vs {p_R[2]}"

    def test_landmarks_translation_equivariance(self):
        """Translating vertices by vector T must shift all landmarks by exactly T."""
        verts = generate_humanoid_mesh(height=1.65)
        T = np.array([3.45, -7.89, 12.34])
        lms_orig = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        lms_trans = compute_bony_landmarks(verts + T, stance=LocomotorStance.HUMANOID, height=1.65)

        for name in lms_orig.keys():
            p_orig = lms_orig[name].np_position
            p_trans = lms_trans[name].np_position
            expected = p_orig + T
            assert np.allclose(p_trans, expected, atol=1e-4), f"Landmark {name} failed translation equivariance"

    def test_quadruped_landmarks_across_stances(self):
        """Verify presence and relative hock height across quadruped stances."""
        hocks = {}
        for st in [LocomotorStance.PLANTIGRADE, LocomotorStance.DIGITIGRADE, LocomotorStance.UNGULIGRADE]:
            verts = generate_plantigrade_bear_mesh(height=1.2)
            lms = compute_bony_landmarks(verts, stance=st, height=1.2)
            assert "withers" in lms
            assert "stifle_L" in lms
            assert "hock_L" in lms
            hocks[st] = lms["hock_L"].position[2]

        # Hock height must strictly increase: plantigrade < digitigrade < unguligrade
        assert hocks[LocomotorStance.PLANTIGRADE] < hocks[LocomotorStance.DIGITIGRADE] < hocks[LocomotorStance.UNGULIGRADE]


# ==============================================================================
# 3. ADVERSARIAL ICR JOINT PIVOTS STABILITY
# ==============================================================================

class TestAdversarialICRJointPivots:
    """Stress-tests Instantaneous Center of Rotation pivot estimation stability."""

    def test_icr_translation_equivariance(self):
        """Translating landmarks by T must translate ICR pivot center by exactly T and preserve rotation axis."""
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        pivots_orig = estimate_icr_joint_pivots(lms, vertices=verts)

        T = np.array([4.2, -6.8, 9.1])
        verts_trans = verts + T
        lms_trans = compute_bony_landmarks(verts_trans, stance=LocomotorStance.HUMANOID, height=1.65)
        pivots_trans = estimate_icr_joint_pivots(lms_trans, vertices=verts_trans)

        for jname in pivots_orig.keys():
            p_orig = pivots_orig[jname]
            p_trans = pivots_trans[jname]

            # Pivot center translation
            expected_center = p_orig.np_center + T
            assert np.allclose(p_trans.np_center, expected_center, atol=1e-4), (
                f"ICR pivot {jname} failed translation equivariance: {p_trans.np_center} vs {expected_center}"
            )
            # Rotation axis invariance
            assert np.allclose(p_trans.np_axis, p_orig.np_axis, atol=1e-4), (
                f"ICR rotation axis {jname} changed under translation"
            )
            # Unit norm
            assert np.isclose(np.linalg.norm(p_trans.np_axis), 1.0, atol=1e-6)

    def test_icr_hinge_scaling_equivariance(self):
        """Hinge joint ICR pivot centers (knee, elbow, ankle) must scale with exact mathematical equivariance."""
        s = 2.5
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        pivots_orig = estimate_icr_joint_pivots(lms, vertices=verts)

        verts_scaled = verts * s
        lms_scaled = compute_bony_landmarks(verts_scaled, stance=LocomotorStance.HUMANOID, height=1.65 * s)
        pivots_scaled = estimate_icr_joint_pivots(lms_scaled, vertices=verts_scaled)

        # Hinge joints derive their centers directly from epicondylar/malleoli vectors
        for jname in ["knee_L", "knee_R", "elbow_L", "elbow_R", "ankle_L", "ankle_R"]:
            p_orig = pivots_orig[jname]
            p_scaled = pivots_scaled[jname]

            expected_center = p_orig.np_center * s
            assert np.allclose(p_scaled.np_center, expected_center, atol=1e-4), (
                f"Hinge ICR pivot {jname} failed exact scaling: {p_scaled.np_center} vs {expected_center}"
            )

        # Knee and elbow radius estimates scale with bicondylar distance
        for jname in ["knee_L", "knee_R", "elbow_L", "elbow_R"]:
            assert np.isclose(pivots_scaled[jname].radius_estimate, pivots_orig[jname].radius_estimate * s, rtol=1e-3)

    def test_icr_bilateral_mirroring(self):
        """Left and right ICR pivots must exhibit sagittal mirror symmetry."""
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        pivots = estimate_icr_joint_pivots(lms, vertices=verts)

        for joint_base in ["knee", "elbow", "hip", "shoulder", "ankle"]:
            p_L = pivots[f"{joint_base}_L"]
            p_R = pivots[f"{joint_base}_R"]

            # Centers: X mirrored, Y and Z equal
            assert np.isclose(p_L.np_center[0], -p_R.np_center[0], atol=1e-4)
            assert np.isclose(p_L.np_center[1], p_R.np_center[1], atol=1e-4)
            assert np.isclose(p_L.np_center[2], p_R.np_center[2], atol=1e-4)

    def test_icr_internal_offset_directions(self):
        """Verify biocentric offsets: knee posterior (+Y), elbow anterior (-Y), hip medial/superior."""
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        pivots = estimate_icr_joint_pivots(lms, vertices=verts)

        # Knee: posterior offset (+Y) relative to epicondylar midpoint
        p_med_k = lms["medial_femoral_epicondyle_L"].np_position
        p_lat_k = lms["lateral_femoral_epicondyle_L"].np_position
        mid_k = 0.5 * (p_med_k + p_lat_k)
        assert pivots["knee_L"].np_center[1] > mid_k[1]

        # Elbow: anterior offset (-Y) relative to epicondylar midpoint
        p_med_e = lms["medial_epicondyle_L"].np_position
        p_lat_e = lms["lateral_epicondyle_L"].np_position
        mid_e = 0.5 * (p_med_e + p_lat_e)
        assert pivots["elbow_L"].np_center[1] < mid_e[1]

        # Hip: medial offset (-X for Left side) relative to greater trochanter
        p_gt = lms["greater_trochanter_L"].np_position
        assert pivots["hip_L"].np_center[0] < p_gt[0]


# ==============================================================================
# 4. ADVERSARIAL BONE ROLL NORMALIZATION & ANTI-TWIST VERIFICATION
# ==============================================================================

class TestAdversarialBoneRollAndAntiTwist:
    """Stress-tests bone roll math: 360-degree pole sweep, singular orientations, collinear limbs."""

    def test_360_degree_continuous_pole_sweep_zero_candy_wrapper(self):
        """
        SWEEP HARNESS:
        Rotate pole target full 360 degrees around a vertical bone in 1-degree increments.
        Assert:
        1. No NaN or Infinite roll values.
        2. Reconstructed bone local +Z axis aligns with projected pole target (dot product >= 0.9999).
        """
        head = np.array([0.0, 0.0, 1.0])
        tail = np.array([0.0, 0.0, 0.0])
        bone_axis = (tail - head) / np.linalg.norm(tail - head)

        angles_deg = np.linspace(0, 360, 361)

        for ang in angles_deg:
            rad = math.radians(ang)
            # Pole target at radius 0.5 in XY plane at mid-height Z=0.5
            pole = np.array([0.5 * math.cos(rad), 0.5 * math.sin(rad), 0.5])

            res = solve_biomechanical_bone_roll(head, tail, pole, bone_name="test_vertical")

            assert not math.isnan(res.roll_radians)
            assert not math.isinf(res.roll_radians)
            assert -math.pi - 1e-6 <= res.roll_radians <= math.pi + 1e-6

            # Compute bone local frame in Blender
            theta = res.roll_radians
            x0 = np.array([0.0, -1.0, 0.0])
            z0 = np.cross(x0, bone_axis)
            z0 = z0 / np.linalg.norm(z0)

            local_z = math.cos(theta) * z0 + math.sin(theta) * x0

            # Desired pole direction orthogonal to bone axis
            v_target = pole - head
            v_proj = v_target - np.dot(v_target, bone_axis) * bone_axis
            v_proj_hat = v_proj / np.linalg.norm(v_proj)

            alignment = float(np.dot(local_z, v_proj_hat))
            assert alignment >= 0.9999, f"Pole angle {ang} deg: local Z misaligned with pole target, dot={alignment}"

    @pytest.mark.parametrize("bone_vec, bone_name", [
        (np.array([0.0, 0.0, 1.0]), "vertical_up"),
        (np.array([0.0, 0.0, -1.0]), "vertical_down"),
        (np.array([1.0, 0.0, 0.0]), "horizontal_x_pos"),
        (np.array([-1.0, 0.0, 0.0]), "horizontal_x_neg"),
        (np.array([0.0, 1.0, 0.0]), "horizontal_y_pos"),
        (np.array([0.0, -1.0, 0.0]), "horizontal_y_neg"),
        (np.array([1.0, 1.0, 1.0]), "diagonal_pos"),
        (np.array([-1.0, -1.0, -1.0]), "diagonal_neg"),
        (np.array([0.00001, 0.00001, 1.0]), "near_vertical_singularity"),
    ])
    def test_singular_and_cardinal_bone_orientations(self, bone_vec: np.ndarray, bone_name: str):
        """Evaluate bone roll on cardinal and singular bone orientations with arbitrary pole targets."""
        head = np.array([0.0, 0.0, 0.0])
        tail = head + bone_vec
        pole = np.array([0.3, -0.4, 0.5])

        res = solve_biomechanical_bone_roll(head, tail, pole, bone_name=bone_name)

        assert not math.isnan(res.roll_radians)
        assert not math.isinf(res.roll_radians)
        assert len(res.hinge_normal) == 3
        assert np.isclose(np.linalg.norm(res.hinge_normal), 1.0, atol=1e-4)

    @pytest.mark.parametrize("direction_vec, chain_name", [
        ((0.0, 0.0, -1.0), "vertical_down_limb"),
        ((0.0, 0.0, 1.0), "vertical_up_limb"),
        ((1.0, 0.0, 0.0), "horizontal_x_limb"),
        ((0.0, -1.0, 0.0), "horizontal_y_limb"),
        ((1.0, 1.0, 1.0), "diagonal_limb"),
    ])
    def test_collinear_prebend_in_arbitrary_spatial_orientations(self, direction_vec: tuple, chain_name: str):
        """
        STRESS TEST FOR COLLINEAR LIMBS:
        A completely straight limb (3 collinear joints) in arbitrary 3D orientations
        must have pre-bend injected, achieving interior angle >= 3.5 deg and displacement >= 15mm.
        """
        dir_hat = np.array(direction_vec, dtype=np.float64)
        dir_hat = dir_hat / np.linalg.norm(dir_hat)

        p1 = np.array([0.0, 0.0, 0.0])
        p2 = p1 + 0.45 * dir_hat  # strictly collinear midpoint
        p3 = p1 + 0.90 * dir_hat  # strictly collinear endpoint

        # Anatomical bend direction orthogonal to limb
        ref = np.array([0.0, 1.0, 0.0]) if abs(dir_hat[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        bend_dir = np.cross(dir_hat, ref)
        bend_dir = bend_dir / np.linalg.norm(bend_dir)

        res = apply_joint_prebend(
            p1, p2, p3,
            min_bend_angle_deg=4.0,
            min_displacement=0.018,
            bend_direction=bend_dir,
            joint_name="test_joint",
            chain_name=chain_name,
        )

        assert res.is_prebent is True
        assert res.interior_angle_deg >= 3.5, f"Chain {chain_name} angle too small: {res.interior_angle_deg}"
        assert np.linalg.norm(res.displacement_vector) >= 0.015, (
            f"Chain {chain_name} displacement too small: {np.linalg.norm(res.displacement_vector)}"
        )
        # Prebent position must no longer be collinear
        p2_bent = np.array(res.prebent_position)
        w = p3 - p1
        w_hat = w / np.linalg.norm(w)
        d_perp = np.linalg.norm((p2_bent - p1) - np.dot(p2_bent - p1, w_hat) * w_hat)
        assert d_perp >= 0.015

    def test_solve_limb_chain_bilateral_symmetry(self):
        """Limb chain solver must produce mirrored roll commands and symmetric pre-bends for Left and Right."""
        # Straight human arms along Z
        p_sh_L = (0.22, 0.0, 1.10)
        p_el_L = (0.22, 0.0, 0.70)
        p_wr_L = (0.22, 0.0, 0.30)

        p_sh_R = (-0.22, 0.0, 1.10)
        p_el_R = (-0.22, 0.0, 0.70)
        p_wr_R = (-0.22, 0.0, 0.30)

        pb_L, roll_prox_L, roll_dist_L = solve_limb_chain_bone_roll_and_prebend(p_sh_L, p_el_L, p_wr_L, chain_type="human_arm", side="L")
        pb_R, roll_prox_R, roll_dist_R = solve_limb_chain_bone_roll_and_prebend(p_sh_R, p_el_R, p_wr_R, chain_type="human_arm", side="R")

        # Both must be pre-bent posterior (+Y)
        assert pb_L.is_prebent is True
        assert pb_R.is_prebent is True
        assert pb_L.prebent_position[1] > pb_L.original_position[1]
        assert pb_R.prebent_position[1] > pb_R.original_position[1]
        assert np.isclose(pb_L.interior_angle_deg, pb_R.interior_angle_deg, atol=1e-2)

        # Roll angles must be finite and non-NaN
        assert not math.isnan(roll_prox_L.roll_radians)
        assert not math.isnan(roll_prox_R.roll_radians)
        assert not math.isnan(roll_dist_L.roll_radians)
        assert not math.isnan(roll_dist_R.roll_radians)


# ==============================================================================
# 5. GEODESIC SKINNING WEIGHT STEALING EMPIRICAL STRESS
# ==============================================================================

class TestAdversarialSkinning:
    """Stress-tests the pure-NumPy geodesic biharmonic skinning solver against weight stealing."""

    def test_tight_air_gap_zero_leakage(self):
        """
        Extreme air-gap test: Two thin parallel plates separated by only 1.5cm air gap.
        Bone 1 is inside Plate 1, Bone 2 is inside Plate 2.
        Assert ZERO weight leakage across the air gap!
        """
        plate1_pts = []
        for z in np.linspace(0.2, 0.8, 10):
            for y in np.linspace(-0.1, 0.1, 5):
                plate1_pts.append([-0.02, y, z])
                plate1_pts.append([-0.01, y, z])

        plate2_pts = []
        for z in np.linspace(0.2, 0.8, 10):
            for y in np.linspace(-0.1, 0.1, 5):
                plate2_pts.append([0.01, y, z])
                plate2_pts.append([0.02, y, z])

        all_verts = np.array(plate1_pts + plate2_pts, dtype=np.float64)

        bones = {
            "DEF-plate1": ((-0.015, 0.0, 0.1), (-0.015, 0.0, 0.9)),
            "DEF-plate2": ((0.015, 0.0, 0.1), (0.015, 0.0, 0.9)),
        }

        skin_map = compute_geodesic_skin_weights(all_verts, bones, grid_resolution=30)
        assert skin_map.verify_partition_of_unity() is True

        # Check plate 1: plate 2 bone weight must be strictly 0.0
        for i in range(len(plate1_pts)):
            w = skin_map.get_vertex_weights(i)
            assert w.get("DEF-plate2", 0.0) == 0.0, f"Plate 1 vertex {i} leaked weight from DEF-plate2: {w}"

        # Check plate 2: plate 1 bone weight must be strictly 0.0
        for i in range(len(plate1_pts), len(all_verts)):
            w = skin_map.get_vertex_weights(i)
            assert w.get("DEF-plate1", 0.0) == 0.0, f"Plate 2 vertex {i} leaked weight from DEF-plate1: {w}"
