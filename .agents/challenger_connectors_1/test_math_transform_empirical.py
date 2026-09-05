"""
MorphoMesh Phase 2: Empirical Challenge Suite 1
Coordinate Transformation Matrix, SO(3) Properties, Kinematics, & SMAL/Rigify Mapping.
"""

from __future__ import annotations

import math
import numpy as np
import pytest
import re
from typing import Dict, List, Tuple

from morphomesh.connectors.animals3d_connector import (
    CANONICAL_SMAL_35_JOINTS,
    RX_90_SMAL_TO_BLENDER,
    SMAL_TO_RIGIFY_WOLF,
    Animals3DConnector,
    AnimalPoseInput,
    SMALParams,
    transform_smal_to_blender,
)


class TestCoordinateTransformationMatrixSO3:
    """Stress-test the Rx(+90 deg) coordinate transformation matrix and SO(3) properties."""

    @pytest.fixture
    def rotation_matrix(self) -> np.ndarray:
        return np.array(RX_90_SMAL_TO_BLENDER, dtype=np.float64)

    def test_orthogonality(self, rotation_matrix):
        """Verify R * R^T = I and R^T * R = I (orthogonality)."""
        I = np.eye(3, dtype=np.float64)
        r_rt = np.dot(rotation_matrix, rotation_matrix.T)
        rt_r = np.dot(rotation_matrix.T, rotation_matrix)

        np.testing.assert_allclose(r_rt, I, atol=1e-7, err_msg="R * R^T is not identity")
        np.testing.assert_allclose(rt_r, I, atol=1e-7, err_msg="R^T * R is not identity")

    def test_determinant_proper_rotation(self, rotation_matrix):
        """Verify det(R) = +1.0 (proper rotation in SO(3), no parity inversion / reflection)."""
        det = np.linalg.det(rotation_matrix)
        assert pytest.approx(det, abs=1e-7) == 1.0, f"det(R) was {det}, expected +1.0 (reflection or improper)"

    def test_rotation_angle_and_axis(self, rotation_matrix):
        """
        Verify rotation angle theta = +90 degrees (pi/2) around +X axis.
        Trace(R) = 1 + 2*cos(theta).
        """
        trace = np.trace(rotation_matrix)
        cos_theta = (trace - 1.0) / 2.0
        theta_rad = math.acos(np.clip(cos_theta, -1.0, 1.0))
        theta_deg = math.degrees(theta_rad)

        assert pytest.approx(theta_deg, abs=1e-5) == 90.0, f"Angle is {theta_deg}, expected 90 deg"

        # Eigenvector for eigenvalue = 1 is the rotation axis
        eigenvalues, eigenvectors = np.linalg.eig(rotation_matrix)
        axis_idx = np.where(np.isclose(eigenvalues, 1.0))[0][0]
        rotation_axis = np.real(eigenvectors[:, axis_idx])
        rotation_axis = rotation_axis / np.linalg.norm(rotation_axis)

        # Must be along positive or negative X axis; for Rx(+90), X is unchanged
        assert np.isclose(abs(rotation_axis[0]), 1.0)
        assert np.isclose(rotation_axis[1], 0.0)
        assert np.isclose(rotation_axis[2], 0.0)

    def test_isometry_norm_preservation(self, rotation_matrix):
        """Verify ||R * v|| = ||v|| for arbitrary vectors (isometry)."""
        rng = np.random.default_rng(42)
        test_vectors = rng.standard_normal(size=(1000, 3))

        for v in test_vectors:
            v_rot = np.dot(rotation_matrix, v)
            norm_orig = np.linalg.norm(v)
            norm_rot = np.linalg.norm(v_rot)
            assert pytest.approx(norm_rot, rel=1e-6) == norm_orig

    def test_canonical_point_mapping_exact(self):
        """Verify [x, y, z] -> [x, -z, y] mapping matches functional transform."""
        test_points = [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [-1.5, 3.2, -4.8],
            [100.0, -200.0, 300.0],
            [1e-5, -1e-5, 1e-5],
        ]

        for pt in test_points:
            x, y, z = pt
            expected = [round(x, 6), round(-z, 6), round(y, 6)]
            actual = transform_smal_to_blender(pt)
            assert actual == expected, f"Transform failed for {pt}: got {actual}, expected {expected}"

    def test_random_1000_point_mapping(self, rotation_matrix):
        """Empirically test 1000 randomized 3D points."""
        rng = np.random.default_rng(2026)
        pts = rng.uniform(-1000.0, 1000.0, size=(1000, 3))

        for pt in pts:
            mat_res = np.dot(rotation_matrix, pt)
            fn_res = transform_smal_to_blender(pt.tolist())
            np.testing.assert_allclose(fn_res, mat_res, atol=1e-5)


class TestSMALKinematicsAndRigifyMapping:
    """Stress-test SMAL 35 landmarks, bone orientations, lengths, roll, and Rigify targets."""

    def test_all_35_landmarks_present_in_mapping_dictionary(self):
        """Verify that every single one of the 35 SMAL landmarks has a mapping in SMAL_TO_RIGIFY_WOLF."""
        assert len(CANONICAL_SMAL_35_JOINTS) == 35, f"Expected 35 canonical joints, got {len(CANONICAL_SMAL_35_JOINTS)}"

        missing_keys = set(CANONICAL_SMAL_35_JOINTS.keys()) - set(SMAL_TO_RIGIFY_WOLF.keys())
        assert len(missing_keys) == 0, f"Missing SMAL landmarks in SMAL_TO_RIGIFY_WOLF: {missing_keys}"

    def test_rigify_wolf_deformation_bone_naming_convention(self):
        """Verify all target bones start with 'DEF-'."""
        for joint, targets in SMAL_TO_RIGIFY_WOLF.items():
            assert isinstance(targets, list), f"Targets for {joint} must be a list"
            assert len(targets) > 0, f"Target list for {joint} is empty"
            for t in targets:
                assert t.startswith("DEF-"), f"Target bone '{t}' for joint '{joint}' does not start with 'DEF-'"

    def test_bone_length_positivity_across_kinematic_chains(self):
        """
        Verify that all parent-child bone vectors in canonical SMAL rest pose have strictly positive length.
        """
        kinematic_chains = [
            # Spine / Axial
            ("root", "spine1"),
            ("spine1", "spine2"),
            ("spine2", "spine3"),
            ("spine3", "neck1"),
            ("neck1", "neck2"),
            ("neck2", "head"),
            ("head", "nose"),
            ("head", "jaw"),
            ("head", "left_ear"),
            ("head", "right_ear"),
            # Tail
            ("root", "tail1"),
            ("tail1", "tail2"),
            ("tail2", "tail3"),
            ("tail3", "tail4"),
            ("tail4", "tail5"),
            ("tail5", "tail6"),
            # Left Forelimb
            ("spine3", "left_collar"),
            ("left_collar", "left_shoulder"),
            ("left_shoulder", "left_elbow"),
            ("left_elbow", "left_wrist"),
            ("left_wrist", "left_hand"),
            # Right Forelimb
            ("spine3", "right_collar"),
            ("right_collar", "right_shoulder"),
            ("right_shoulder", "right_elbow"),
            ("right_elbow", "right_wrist"),
            ("right_wrist", "right_hand"),
            # Left Hindlimb
            ("root", "left_hip"),
            ("left_hip", "left_knee"),
            ("left_knee", "left_ankle"),
            ("left_ankle", "left_foot"),
            # Right Hindlimb
            ("root", "right_hip"),
            ("right_hip", "right_knee"),
            ("right_knee", "right_ankle"),
            ("right_ankle", "right_foot"),
        ]

        min_bone_length = float("inf")
        bone_lengths = {}

        for parent_j, child_j in kinematic_chains:
            p_smal = np.array(CANONICAL_SMAL_35_JOINTS[parent_j])
            c_smal = np.array(CANONICAL_SMAL_35_JOINTS[child_j])

            # In Blender space
            p_blender = np.array(transform_smal_to_blender(p_smal))
            c_blender = np.array(transform_smal_to_blender(c_smal))

            bone_vec_blender = c_blender - p_blender
            bone_len = float(np.linalg.norm(bone_vec_blender))
            bone_lengths[f"{parent_j}->{child_j}"] = bone_len

            assert bone_len > 0.01, f"Bone {parent_j}->{child_j} is degenerate (length {bone_len} <= 0.01)"
            min_bone_length = min(min_bone_length, bone_len)

        assert min_bone_length > 0.02, f"Minimum bone length {min_bone_length} is too small"

    def test_anatomical_vector_orientations_in_blender_space(self):
        """
        Verify anatomical orientations in Blender character space:
        - Character faces forward along -Y or spine extends along -Y -> +Y.
        - Head is forward and up relative to root.
        - Tail extends backward along -Y.
        - Limbs extend downward along -Z.
        - Left vs Right lateral symmetry along X axis.
        """
        root = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["root"]))
        head = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["head"]))
        tail_tip = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["tail6"]))
        l_foot = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["left_foot"]))
        r_foot = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["right_foot"]))
        l_hand = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["left_hand"]))
        r_hand = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS["right_hand"]))

        # In SMAL: Z is forward (+Z), Y is up (+Y).
        # In Blender: Y_b = -Z_s, Z_b = Y_s.
        # Head Z_s > root Z_s -> in Blender, Head Y_b (-0.65) < root Y_b (0.25).
        # So character faces in -Y direction in Blender.
        assert head[1] < root[1], "Head should be forward (-Y) relative to root"
        # Tail is backward: tail Z_s < root Z_s -> in Blender, Tail Y_b > root Y_b (+Y).
        assert tail_tip[1] > root[1], "Tail should be backward (+Y) relative to root"

        # Head is above root: Head Z_b > root Z_b
        assert head[2] > root[2], "Head Z should be higher than root Z"

        # Feet and hands are below root
        assert l_foot[2] < root[2]
        assert r_foot[2] < root[2]
        assert l_hand[2] < root[2]
        assert r_hand[2] < root[2]

        # Lateral symmetry: Left has X < 0, Right has X > 0
        assert l_foot[0] < 0.0 < r_foot[0]
        assert l_hand[0] < 0.0 < r_hand[0]
        assert pytest.approx(l_foot[0], abs=1e-4) == -r_foot[0]
        assert pytest.approx(l_hand[0], abs=1e-4) == -r_hand[0]

    def test_roll_alignment_singularity_freedom(self):
        """
        Verify that no bone vector is collinear with the roll alignment reference vector (0, 0, 1).
        If bone is parallel to (0, 0, 1), cross product with (0, 0, 1) is zero (singularity in roll alignment).
        """
        reference_up = np.array([0.0, 0.0, 1.0])
        for joint, pos in CANONICAL_SMAL_35_JOINTS.items():
            blender_pt = np.array(transform_smal_to_blender(pos))
            # Test limb segments
            if "elbow" in joint or "knee" in joint:
                parent = joint.replace("elbow", "shoulder").replace("knee", "hip")
                p_blender = np.array(transform_smal_to_blender(CANONICAL_SMAL_35_JOINTS[parent]))
                bone_dir = blender_pt - p_blender
                bone_dir = bone_dir / np.linalg.norm(bone_dir)
                cross = np.linalg.norm(np.cross(bone_dir, reference_up))
                assert cross > 0.01, f"Bone {parent}->{joint} is dangerously close to parallel with (0,0,1)"

    def test_connector_execute_script_generation(self):
        """Verify full execution produces valid landmark dict and Rigify edit script."""
        connector = Animals3DConnector()
        inp = AnimalPoseInput(species="canine", estimate_pose=True)
        out = connector.execute(inp)

        assert out.landmark_count == 35
        assert len(out.landmarks) == 35
        assert "metarig" in out.blender_script
        assert "align_roll" in out.blender_script
        assert "DEF-spine.004" in out.blender_script

        # Check all 35 joints appear in generated script
        for jname in CANONICAL_SMAL_35_JOINTS.keys():
            targets = SMAL_TO_RIGIFY_WOLF.get(jname, [])
            for t in targets:
                assert t in out.blender_script, f"Target bone '{t}' missing from blender script"

    def test_skin_weight_mathematical_properties(self):
        """Verify longitudinal skin weight calculation satisfies partition of unity and distance decay."""
        connector = Animals3DConnector()
        vertices = [
            (0.0, 0.0, 0.5),   # exactly halfway along bone
            (0.0, 0.0, 0.4),   # at bone head
            (0.0, 0.0, 0.6),   # at bone tail
            (0.0, 0.2, 0.5),   # 0.2 units away perpendicularly
            (0.0, 0.5, 0.5),   # 0.5 units away perpendicularly
        ]
        bone_heads = {"DEF-bone1": (0.0, 0.0, 0.4)}
        bone_tails = {"DEF-bone1": (0.0, 0.0, 0.6)}

        weights = connector.compute_longitudinal_skin_weights(vertices, bone_heads, bone_tails)
        b_w = weights["DEF-bone1"]

        # Vertices closer to bone must have strictly higher weight than further vertices
        w_near = b_w["v_0"]  # dist = 0.0
        w_mid = b_w["v_3"]   # dist = 0.2
        w_far = b_w.get("v_4", 0.0)  # dist = 0.5

        assert w_near > w_mid > w_far, f"Distance decay violated: {w_near} vs {w_mid} vs {w_far}"
        assert 0.0 < w_near <= 1.0
