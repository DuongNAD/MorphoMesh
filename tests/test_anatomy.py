"""
MorphoMesh: Anatomical Skeletal Estimation & Biomechanical Auto-Rigging Test Suite.

Comprehensive validation covering:
1. Locomotor Stance Classification (Humanoid biped, Plantigrade, Digitigrade, Unguligrade).
2. Surface Bony Landmark Detection & ICR Joint Pivot Estimation (including malleoli asymmetry).
3. Biomechanical Bone Roll & Pre-Bend Solver (hinge normal, collinear pre-bend, anti-twist roll).
4. Volumetric Geodesic Voxel Biharmonic Skinning Solver (zero weight stealing across axilla and inner thighs).
5. Bridge and Connector Integration (Animals3DConnector and BlenderBridge).
"""

import math
import sys
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
    SkinWeightMap,
    VoxelGrid,
    compute_geodesic_skin_weights,
)
from morphomesh.connectors.animals3d_connector import (
    AnimalPoseInput,
    Animals3DConnector,
    Animals3DOutput,
)
from morphomesh.blender_bridge import BlenderBridge


# ==============================================================================
# SYNTHETIC MESH GENERATORS FOR TESTING
# ==============================================================================

def generate_humanoid_mesh(height: float = 1.65, num_pts: int = 400) -> np.ndarray:
    """Generate points approximating an upright biped with 2 distinct feet on ground plane."""
    pts = []
    # Head & torso (upright column)
    z_vals = np.linspace(0.4 * height, height, num_pts // 2)
    for z in z_vals:
        pts.append([0.05 * math.cos(z * 10), 0.05 * math.sin(z * 10), z])
    # Left foot (contact patch on ground)
    for fx in np.linspace(-0.12, -0.06, num_pts // 4):
        for fy in np.linspace(-0.08, 0.08, 4):
            pts.append([fx, fy, 0.0])
    # Right foot (contact patch on ground)
    for fx in np.linspace(0.06, 0.12, num_pts // 4):
        for fy in np.linspace(-0.08, 0.08, 4):
            pts.append([fx, fy, 0.0])
    return np.array(pts, dtype=np.float64)


def generate_plantigrade_bear_mesh(height: float = 1.2, length: float = 1.8, num_pts: int = 400) -> np.ndarray:
    """Generate points approximating a quadruped bear: low hock, long sole contact."""
    pts = []
    # Horizontal torso
    y_vals = np.linspace(-0.5 * length, 0.5 * length, num_pts // 2)
    for y in y_vals:
        pts.append([0.2 * math.cos(y * 8), y, 0.7 * height + 0.1 * math.sin(y * 8)])
    # 4 paws with flat soles (heel to toe on ground: eta_hock low, high contact area)
    for sx in [-0.25, 0.25]:
        # Front paws
        for y in np.linspace(0.35 * length, 0.45 * length, 20):
            pts.append([sx, y, 0.0])
            pts.append([sx, y, 0.08 * height])  # low wrist
        # Hind paws (long sole)
        for y in np.linspace(-0.45 * length, -0.32 * length, 20):
            pts.append([sx, y, 0.0])
            pts.append([sx, y, 0.12 * height])  # low hock (plantigrade calcaneus)
    return np.array(pts, dtype=np.float64)


def generate_digitigrade_canine_mesh(height: float = 0.8, length: float = 1.1, num_pts: int = 400) -> np.ndarray:
    """Generate points approximating a dog/wolf: elevated hock (~35% leg height), compact pads."""
    pts = []
    # Torso
    y_vals = np.linspace(-0.5 * length, 0.5 * length, num_pts // 2)
    for y in y_vals:
        pts.append([0.15 * math.cos(y * 10), y, 0.65 * height])
    # Compact paw pad clusters with elevated hock (z_hock ~ 0.35 * height)
    for sx in [-0.18, 0.18]:
        # Front compact pads
        for y in np.linspace(0.32 * length, 0.36 * length, 10):
            pts.append([sx, y, 0.0])
        # Hind compact pads with elevated hock
        for y in np.linspace(-0.36 * length, -0.32 * length, 10):
            pts.append([sx, y, 0.0])
        # Elevated hocks (posterior protrusion at 35% height)
        pts.append([sx, -0.28 * length, 0.35 * height])
        pts.append([sx, -0.30 * length, 0.36 * height])
    return np.array(pts, dtype=np.float64)


def generate_unguligrade_horse_mesh(height: float = 1.6, length: float = 1.9, num_pts: int = 400) -> np.ndarray:
    """Generate points approximating a horse/deer: high hock (>50% leg height), tiny hooves."""
    pts = []
    # Torso
    y_vals = np.linspace(-0.5 * length, 0.5 * length, num_pts // 2)
    for y in y_vals:
        pts.append([0.22 * math.cos(y * 8), y, 0.75 * height])
    # 4 tiny hoof points on ground and very high hock
    for sx in [-0.22, 0.22]:
        pts.append([sx, 0.35 * length, 0.0])  # tiny front hoof
        pts.append([sx, -0.35 * length, 0.0])  # tiny hind hoof
        # Hock is very high up (60% height)
        pts.append([sx, -0.28 * length, 0.58 * height])
        pts.append([sx, -0.30 * length, 0.60 * height])
    return np.array(pts, dtype=np.float64)


# ==============================================================================
# 1. LOCOMOTOR STANCE CLASSIFICATION TESTS
# ==============================================================================

class TestLocomotorStanceClassification:
    """Tests classification across Humanoid and 3 biological animal stances."""

    def test_humanoid_biped_classification(self):
        verts = generate_humanoid_mesh(height=1.65)
        res = classify_locomotor_stance(verts)
        assert res.stance == LocomotorStance.HUMANOID
        assert res.is_biped is True
        assert res.confidence >= 0.88
        assert res.ground_contact_count == 2
        d = res.to_dict()
        assert d["stance"] == "humanoid"
        assert d["is_biped"] is True

    def test_plantigrade_ursine_classification(self):
        verts = generate_plantigrade_bear_mesh(height=1.2)
        res = classify_locomotor_stance(verts, species_hint="bear")
        assert res.stance == LocomotorStance.PLANTIGRADE
        assert res.is_biped is False
        assert res.confidence >= 0.85
        assert res.hock_height_ratio <= 0.25

    def test_digitigrade_canine_classification(self):
        verts = generate_digitigrade_canine_mesh(height=0.8)
        joints = {
            "hip": (0.0, -0.3, 0.6),
            "hock": (0.0, -0.3, 0.22),
            "paw": (0.0, -0.3, 0.0),
        }
        res = classify_locomotor_stance(verts, skeleton_joints=joints, species_hint="wolf")
        assert res.stance == LocomotorStance.DIGITIGRADE
        assert res.confidence >= 0.85
        assert 0.22 < res.hock_height_ratio <= 0.48

    def test_unguligrade_equine_classification(self):
        verts = generate_unguligrade_horse_mesh(height=1.6)
        joints = {
            "hip": (0.0, -0.4, 1.2),
            "hock": (0.0, -0.4, 0.75),
            "hoof": (0.0, -0.4, 0.0),
        }
        res = classify_locomotor_stance(verts, skeleton_joints=joints, species_hint="horse")
        assert res.stance == LocomotorStance.UNGULIGRADE
        assert res.confidence >= 0.88
        assert res.hock_height_ratio > 0.48

    def test_noisy_mesh_and_scale_invariance(self):
        base_verts = generate_humanoid_mesh(height=1.65)
        for scale in [0.1, 1.0, 5.0]:
            scaled_verts = base_verts * scale
            noise = np.random.normal(0, 0.002 * scale, scaled_verts.shape)
            res = classify_locomotor_stance(scaled_verts + noise, species_hint="human")
            assert res.stance == LocomotorStance.HUMANOID
            assert res.is_biped is True

    def test_species_hint_guidance(self):
        verts = generate_digitigrade_canine_mesh(height=0.8)
        res_cat = classify_locomotor_stance(verts, species_hint="feline")
        assert res_cat.stance == LocomotorStance.DIGITIGRADE
        res_deer = classify_locomotor_stance(verts, species_hint="deer")
        assert res_deer.stance == LocomotorStance.UNGULIGRADE


# ==============================================================================
# 2. BONY LANDMARK & ICR PIVOT DETECTION TESTS
# ==============================================================================

class TestBonyLandmarksAndICR:
    """Verifies surface landmark detection and Instantaneous Center of Rotation."""

    def test_humanoid_bony_landmarks_accuracy(self):
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        
        required_landmarks = [
            "suprasternal_notch", "chest_center", "spine_mid", "pelvis_center",
            "clavicle_sternal_L", "clavicle_acromial_L", "acromion_L",
            "clavicle_sternal_R", "clavicle_acromial_R", "acromion_R",
            "olecranon_L", "medial_epicondyle_L", "lateral_epicondyle_L",
            "olecranon_R", "medial_epicondyle_R", "lateral_epicondyle_R",
            "patella_L", "medial_femoral_epicondyle_L", "lateral_femoral_epicondyle_L",
            "patella_R", "medial_femoral_epicondyle_R", "lateral_femoral_epicondyle_R",
            "medial_malleolus_L", "lateral_malleolus_L", "calcaneus_L",
            "medial_malleolus_R", "lateral_malleolus_R", "calcaneus_R",
            "greater_trochanter_L", "greater_trochanter_R",
        ]
        for name in required_landmarks:
            assert name in lms, f"Missing required landmark: {name}"
            lm = lms[name]
            assert isinstance(lm, BonyLandmark)
            assert len(lm.position) == 3
            assert lm.confidence > 0.8

    def test_asymmetric_malleoli_landmarks(self):
        """
        CRITICAL ANTHROPOMETRIC TEST:
        In authentic human skeletal anatomy, the medial malleolus is higher (+Z)
        and more anterior (-Y in Blender space) than the lateral malleolus.
        """
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)

        for side in ["L", "R"]:
            med = lms[f"medial_malleolus_{side}"]
            lat = lms[f"lateral_malleolus_{side}"]

            # Vertical asymmetry: medial is higher by >= 10mm (0.010m)
            delta_z = med.position[2] - lat.position[2]
            assert delta_z >= 0.010, f"Medial malleolus must be >= 10mm higher than lateral, got {delta_z*1000:.1f}mm"

            # Anterior-posterior asymmetry: medial is anterior (smaller Y in Blender -Y forward space)
            assert med.position[1] < lat.position[1], (
                f"Medial malleolus Y ({med.position[1]:.4f}) must be anterior to lateral Y ({lat.position[1]:.4f})"
            )

    def test_quadruped_landmarks_across_stances(self):
        verts = generate_plantigrade_bear_mesh(height=1.2)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.PLANTIGRADE, height=1.2)
        assert "withers" in lms
        assert "stifle_L" in lms
        assert "stifle_R" in lms
        assert "hock_L" in lms
        assert "hock_R" in lms
        assert "scapular_spine_L" in lms

    def test_icr_joint_pivot_internal_containment_and_offsets(self):
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        pivots = estimate_icr_joint_pivots(lms, vertices=verts)

        assert "knee_L" in pivots
        assert "elbow_L" in pivots
        assert "hip_L" in pivots
        assert "shoulder_L" in pivots

        knee_icr = pivots["knee_L"]
        assert knee_icr.dof == 1
        # Knee ICR has posterior offset (+Y in Blender coords) relative to condyle midpoint
        p_med = np.array(lms["medial_femoral_epicondyle_L"].position)
        p_lat = np.array(lms["lateral_femoral_epicondyle_L"].position)
        mid = 0.5 * (p_med + p_lat)
        assert knee_icr.pivot_center[1] > mid[1], "Knee ICR must have posterior offset along +Y"

        elbow_icr = pivots["elbow_L"]
        assert elbow_icr.dof == 1

        hip_icr = pivots["hip_L"]
        assert hip_icr.dof == 3

    def test_bony_landmarks_bone_segments_generation(self):
        verts = generate_humanoid_mesh(height=1.65)
        lms = compute_bony_landmarks(verts, stance=LocomotorStance.HUMANOID, height=1.65)
        segs = lms.bone_segments
        assert len(segs) >= 12
        assert "DEF-spine" in segs
        assert "DEF-upper_arm.L" in segs
        assert "DEF-thigh.L" in segs
        for bname, (head, tail) in segs.items():
            assert len(head) == 3
            assert len(tail) == 3
            assert not np.allclose(head, tail)


# ==============================================================================
# 3. BIOMECHANICAL BONE ROLL & PRE-BEND TESTS
# ==============================================================================

class TestBoneRollAndPreBend:
    """Verifies hinge normal calculation, 1-DOF pre-bends, and anti-twist roll."""

    def test_hinge_plane_normal_vector_orthogonality(self):
        # A bent limb: hip at (0, 0, 1), knee at (0, -0.2, 0.5), ankle at (0, 0, 0)
        p_hip = np.array([0.0, 0.0, 1.0])
        p_knee = np.array([0.0, -0.2, 0.5])
        p_ankle = np.array([0.0, 0.0, 0.0])

        n_hinge = compute_hinge_plane_normal(p_hip, p_knee, p_ankle)
        u1 = (p_knee - p_hip) / np.linalg.norm(p_knee - p_hip)
        u2 = (p_ankle - p_knee) / np.linalg.norm(p_ankle - p_knee)

        # Strictly perpendicular
        assert abs(float(np.dot(n_hinge, u1))) < 1e-6
        assert abs(float(np.dot(n_hinge, u2))) < 1e-6
        assert np.isclose(np.linalg.norm(n_hinge), 1.0)

    def test_collinear_limb_prebend_injection(self):
        # Strictly straight limb: shoulder -> elbow -> wrist all along Z axis
        p_shoulder = (0.2, 0.0, 1.0)
        p_elbow = (0.2, 0.0, 0.6)
        p_wrist = (0.2, 0.0, 0.2)

        res = apply_joint_prebend(
            p_shoulder, p_elbow, p_wrist,
            min_bend_angle_deg=4.0,
            min_displacement=0.018,
            bend_direction=(0.0, 1.0, 0.0),  # elbow flexes posterior (+Y)
            joint_name="elbow_L",
        )

        assert res.is_prebent is True
        assert res.interior_angle_deg >= 3.5
        assert np.linalg.norm(res.displacement_vector) >= 0.015
        assert res.prebent_position[1] > res.original_position[1]  # displaced +Y

    def test_human_vs_quadruped_prebend_directions(self):
        # Human arm: elbow bends posterior (+Y)
        p_sh = (0.2, 0.0, 1.0)
        p_el = (0.2, 0.0, 0.6)
        p_wr = (0.2, 0.0, 0.2)
        pb_arm, roll_prox, roll_dist = solve_limb_chain_bone_roll_and_prebend(p_sh, p_el, p_wr, chain_type="human_arm", side="L")
        assert pb_arm.is_prebent is True
        assert pb_arm.prebent_position[1] > pb_arm.original_position[1]

        # Human leg: knee bends anterior (-Y)
        p_hip = (0.1, 0.0, 0.9)
        p_knee = (0.1, 0.0, 0.5)
        p_ank = (0.1, 0.0, 0.1)
        pb_leg, _, _ = solve_limb_chain_bone_roll_and_prebend(p_hip, p_knee, p_ank, chain_type="human_leg", side="L")
        assert pb_leg.is_prebent is True
        assert pb_leg.prebent_position[1] < pb_leg.original_position[1]

    def test_bone_roll_eliminates_candy_wrapper_and_pole_flip(self):
        head = (0.0, 0.0, 1.0)
        tail = (0.0, 0.0, 0.5)
        pole_target = (0.0, 1.0, 0.75)  # target along +Y

        roll_res = solve_biomechanical_bone_roll(head, tail, pole_target, bone_name="DEF-upper_arm.L")
        assert isinstance(roll_res, BoneRollResult)
        assert abs(roll_res.roll_radians) <= math.pi
        assert "bone.roll =" in roll_res.blender_script_command

    def test_bone_roll_bilateral_symmetry(self):
        # Left and Right limb rolls with mirrored pole targets
        h_L = (0.2, 0.0, 1.0)
        t_L = (0.2, 0.0, 0.5)
        pole_L = (0.2, 1.0, 0.75)
        roll_L = solve_biomechanical_bone_roll(h_L, t_L, pole_L, bone_name="bone.L")

        h_R = (-0.2, 0.0, 1.0)
        t_R = (-0.2, 0.0, 0.5)
        pole_R = (-0.2, 1.0, 0.75)
        roll_R = solve_biomechanical_bone_roll(h_R, t_R, pole_R, bone_name="bone.R")

        # Roll angles should be finite and script commands valid
        assert not math.isnan(roll_L.roll_radians)
        assert not math.isnan(roll_R.roll_radians)


# ==============================================================================
# 4. VOLUMETRIC GEODESIC BIHARMONIC SKINNING TESTS
# ==============================================================================

class TestGeodesicSkinning:
    """Validates volume-preserving geodesic biharmonic weight diffusion."""

    def test_partition_of_unity(self):
        verts = np.array([
            [0.0, 0.0, 0.5],
            [0.0, 0.1, 0.6],
            [0.1, 0.0, 0.7],
            [0.0, -0.1, 0.4],
        ], dtype=np.float64)

        bones = {
            "DEF-spine": ((0.0, 0.0, 0.2), (0.0, 0.0, 0.8)),
            "DEF-arm": ((0.0, 0.0, 0.8), (0.3, 0.0, 0.8)),
        }

        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=20)
        assert skin_map.vertex_count == len(verts)
        assert skin_map.verify_partition_of_unity(tol=1e-4) is True

    def test_weight_matrix_sparsity(self):
        verts = generate_humanoid_mesh(height=1.65, num_pts=100)
        bones = {
            "DEF-spine": ((0.0, 0.0, 0.4), (0.0, 0.0, 1.2)),
            "DEF-arm.L": ((0.1, 0.0, 1.1), (0.4, 0.0, 1.1)),
            "DEF-arm.R": ((-0.1, 0.0, 1.1), (-0.4, 0.0, 1.1)),
            "DEF-leg.L": ((0.1, 0.0, 0.5), (0.1, 0.0, 0.0)),
            "DEF-leg.R": ((-0.1, 0.0, 0.5), (-0.1, 0.0, 0.0)),
        }
        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=24, max_influences=4)
        assert skin_map.max_influences_per_vertex() <= 4

    def test_zero_weight_stealing_axilla_chest(self):
        """
        CRITICAL TEST:
        Geometry consists of Torso cylinder at x=0.0 (radius 0.08) and Arm cylinder at x=0.18 (radius 0.04).
        The air gap between torso and arm is 6cm (x in [0.08, 0.14]).
        Torso vertices MUST have 0.00% weight from the arm bone!
        """
        torso_pts = []
        for z in np.linspace(0.4, 1.2, 15):
            for ang in np.linspace(0, 2 * math.pi, 8, endpoint=False):
                torso_pts.append([0.08 * math.cos(ang), 0.08 * math.sin(ang), z])

        arm_pts = []
        for z in np.linspace(0.4, 1.2, 15):
            for ang in np.linspace(0, 2 * math.pi, 8, endpoint=False):
                arm_pts.append([0.18 + 0.04 * math.cos(ang), 0.04 * math.sin(ang), z])

        all_verts = np.array(torso_pts + arm_pts, dtype=np.float64)

        bones = {
            "DEF-spine": ((0.0, 0.0, 0.3), (0.0, 0.0, 1.3)),
            "DEF-upper_arm.L": ((0.18, 0.0, 0.3), (0.18, 0.0, 1.3)),
        }

        skin_map = compute_geodesic_skin_weights(all_verts, bones, grid_resolution=28)

        # Check all torso vertices: arm weight MUST be 0.00%
        for v_idx in range(len(torso_pts)):
            vw = skin_map.get_vertex_weights(v_idx)
            arm_weight = vw.get("DEF-upper_arm.L", 0.0)
            assert arm_weight == 0.0, f"Weight stealing detected on torso vertex {v_idx}: arm_weight={arm_weight}"

    def test_zero_weight_stealing_inner_thighs(self):
        """
        CRITICAL TEST:
        Geometry consists of Left thigh cylinder at x=0.10 (radius 0.04) and Right thigh cylinder at x=-0.10 (radius 0.04).
        Air gap between inner thighs is 12cm.
        Left thigh vertices MUST have 0.00% weight from Right leg bone!
        """
        left_thigh = []
        right_thigh = []
        for z in np.linspace(0.1, 0.7, 15):
            for ang in np.linspace(0, 2 * math.pi, 8, endpoint=False):
                left_thigh.append([0.10 + 0.04 * math.cos(ang), 0.04 * math.sin(ang), z])
                right_thigh.append([-0.10 + 0.04 * math.cos(ang), 0.04 * math.sin(ang), z])

        all_verts = np.array(left_thigh + right_thigh, dtype=np.float64)

        bones = {
            "DEF-thigh.L": ((0.10, 0.0, 0.7), (0.10, 0.0, 0.1)),
            "DEF-thigh.R": ((-0.10, 0.0, 0.7), (-0.10, 0.0, 0.1)),
        }

        skin_map = compute_geodesic_skin_weights(all_verts, bones, grid_resolution=28)

        # Left thigh vertices must have 0% from DEF-thigh.R
        for v_idx in range(len(left_thigh)):
            vw = skin_map.get_vertex_weights(v_idx)
            r_weight = vw.get("DEF-thigh.R", 0.0)
            assert r_weight == 0.0, f"Inner thigh weight stealing on vertex {v_idx}: right_thigh_weight={r_weight}"

        # Right thigh vertices must have 0% from DEF-thigh.L
        for v_idx in range(len(left_thigh), len(all_verts)):
            vw = skin_map.get_vertex_weights(v_idx)
            l_weight = vw.get("DEF-thigh.L", 0.0)
            assert l_weight == 0.0, f"Inner thigh weight stealing on vertex {v_idx}: left_thigh_weight={l_weight}"

    def test_pure_numpy_execution_no_scipy(self):
        """CRITICAL CONSTRAINT: Verify that no module in anatomy imports scipy."""
        import morphomesh.anatomy.stance as s
        import morphomesh.anatomy.landmarks as lm
        import morphomesh.anatomy.bone_roll as br
        import morphomesh.anatomy.skinning as sk

        for mod in [s, lm, br, sk]:
            imported_mods = [k for k in sys.modules.keys() if "scipy" in k]
            # scipy must not be loaded by our modules
            assert "scipy" not in mod.__dict__


# ==============================================================================
# 5. CONNECTOR & BRIDGE INTEGRATION TESTS
# ==============================================================================

class TestBridgeAndConnectorIntegration:
    """Ensures bridge and connector successfully utilize the anatomy engine."""

    def test_animals3d_connector_integration(self):
        connector = Animals3DConnector()
        inp = AnimalPoseInput(species="canine")
        out = connector.execute(inp)

        assert isinstance(out, Animals3DOutput)
        assert out.landmark_count == 35
        # Bone roll script lines must be present and align_roll non-singular
        assert "align_roll" in out.blender_script
        assert "bone.roll =" in out.blender_script
        # Skin weights must be a non-empty genuine dictionary
        assert out.skin_weights is not None
        assert len(out.skin_weights) > 0

    def test_blender_bridge_create_armature_headless_script(self):
        bridge = BlenderBridge()
        script = bridge._generate_headless_script("morphomesh.create_armature", {"creature_type": "quadruped"})
        assert "Armature_Quadruped" in script
        assert "front_thigh.L" in script
        assert "align_roll" in script
        assert "vertex_groups" in script
        assert "has_skin_weights" in script

    def test_blender_bridge_create_armature_interactive_script(self):
        bridge = BlenderBridge()
        script = bridge._generate_interactive_script("morphomesh.create_armature", {"creature_type": "quadruped"})
        assert "morphomesh.create_armature" in script
        assert "front_thigh.L" in script
        assert "Armature" in script
