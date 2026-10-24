"""
Adversarial Verification Suite for Skinning Weight Stealing & Partition of Unity.

Empirically challenges MorphoMesh's Volumetric Geodesic Voxel Biharmonic Skinning Solver:
1. Synthetic T-pose meshes with narrow air gaps (1.5 - 2.5 cm) at axilla (arm-chest).
2. Synthetic meshes with narrow air gaps (1.5 - 2.5 cm) between left and right inner thighs.
3. Strict assertions:
   - Arm bone influence on chest/torso vertices is exactly 0.000 (0.00% weight stealing).
   - Left leg bone influence on right thigh vertices is exactly 0.000 (0.00% weight stealing).
   - Right leg bone influence on left thigh vertices is exactly 0.000 (0.00% weight stealing).
   - Partition-of-unity on ALL vertices: sum(w_j) == 1.0 +- 1e-5, non-negative, max 4 influences.
4. Stress-testing boundary conditions:
   - Air gaps at 1.5 cm, 2.0 cm, 2.5 cm, and extreme 1.0 cm.
   - Point clouds vs. closed triangulated surface meshes.
   - Varied grid resolutions (24, 32, 40, 48).
   - Dense vertex sampling near boundary interfaces.
"""

import math
from typing import Dict, List, Tuple
import numpy as np
import pytest

from morphomesh.anatomy.skinning import (
    SkinWeightMap,
    VoxelGrid,
    _build_voxel_grid,
    compute_geodesic_skin_weights,
)


# ==============================================================================
# SYNTHETIC MESH BUILDERS WITH CONTROLLED AIR GAPS
# ==============================================================================

def create_synthetic_axilla_mesh(
    air_gap_m: float = 0.020,
    torso_radius: float = 0.12,
    arm_radius: float = 0.04,
    height: float = 0.8,
    z_bottom: float = 0.4,
    radial_samples: int = 16,
    height_samples: int = 20,
) -> Tuple[np.ndarray, List[int], List[int]]:
    """
    Constructs an adversarial torso-arm synthetic mesh with a strictly controlled air gap.
    
    Torso center: (0, 0, z), radius = torso_radius. Torso spans x in [-torso_radius, torso_radius].
    Arm center: (torso_radius + air_gap_m + arm_radius, 0, z), radius = arm_radius.
    Minimum air gap between torso surface and arm surface is exactly air_gap_m.
    
    Returns:
        all_verts: (N, 3) float64
        torso_indices: list of vertex indices belonging to the torso
        arm_indices: list of vertex indices belonging to the arm
    """
    torso_pts = []
    arm_center_x = torso_radius + air_gap_m + arm_radius
    arm_pts = []

    z_levels = np.linspace(z_bottom, z_bottom + height, height_samples)
    angles = np.linspace(0, 2 * math.pi, radial_samples, endpoint=False)

    # Torso vertices
    for z in z_levels:
        for ang in angles:
            x = torso_radius * math.cos(ang)
            y = 0.08 * math.sin(ang)  # slight elliptical cross-section
            torso_pts.append([x, y, z])

    # Arm vertices
    for z in z_levels:
        for ang in angles:
            x = arm_center_x + arm_radius * math.cos(ang)
            y = arm_radius * math.sin(ang)
            arm_pts.append([x, y, z])

    all_verts = np.array(torso_pts + arm_pts, dtype=np.float64)
    torso_indices = list(range(len(torso_pts)))
    arm_indices = list(range(len(torso_pts), len(all_verts)))

    # Verify geometric air gap empirically
    torso_arr = all_verts[torso_indices]
    arm_arr = all_verts[arm_indices]
    # Smallest Euclidean distance between any arm vertex and any torso vertex
    min_dist = float("inf")
    for a_pt in arm_arr:
        d = np.min(np.linalg.norm(torso_arr - a_pt, axis=1))
        if d < min_dist:
            min_dist = d
    assert abs(min_dist - air_gap_m) < 0.005, f"Measured gap {min_dist:.4f} differs from requested {air_gap_m:.4f}"

    return all_verts, torso_indices, arm_indices


def create_synthetic_thighs_mesh(
    air_gap_m: float = 0.020,
    thigh_radius: float = 0.06,
    height: float = 0.6,
    z_bottom: float = 0.1,
    radial_samples: int = 16,
    height_samples: int = 20,
) -> Tuple[np.ndarray, List[int], List[int]]:
    """
    Constructs an adversarial bilateral thigh synthetic mesh with a strictly controlled air gap.
    
    Inner thighs face each other across the X=0 symmetry plane:
    Left thigh center x: +(air_gap_m / 2 + thigh_radius)
    Right thigh center x: -(air_gap_m / 2 + thigh_radius)
    Air gap between surfaces at closest approach is exactly air_gap_m.
    
    Returns:
        all_verts: (N, 3) float64
        left_indices: list of vertex indices for left thigh
        right_indices: list of vertex indices for right thigh
    """
    left_center_x = (air_gap_m / 2.0) + thigh_radius
    right_center_x = -left_center_x

    left_pts = []
    right_pts = []

    z_levels = np.linspace(z_bottom, z_bottom + height, height_samples)
    angles = np.linspace(0, 2 * math.pi, radial_samples, endpoint=False)

    for z in z_levels:
        for ang in angles:
            dx = thigh_radius * math.cos(ang)
            dy = thigh_radius * math.sin(ang)
            left_pts.append([left_center_x + dx, dy, z])
            right_pts.append([right_center_x + dx, dy, z])

    all_verts = np.array(left_pts + right_pts, dtype=np.float64)
    left_indices = list(range(len(left_pts)))
    right_indices = list(range(len(left_pts), len(all_verts)))

    # Verify geometric air gap empirically
    left_arr = all_verts[left_indices]
    right_arr = all_verts[right_indices]
    min_dist = float("inf")
    for r_pt in right_arr:
        d = np.min(np.linalg.norm(left_arr - r_pt, axis=1))
        if d < min_dist:
            min_dist = d
    assert abs(min_dist - air_gap_m) < 0.005, f"Measured gap {min_dist:.4f} differs from requested {air_gap_m:.4f}"

    return all_verts, left_indices, right_indices


def create_full_tpose_mesh_with_air_gaps(
    axilla_gap_m: float = 0.020,
    thigh_gap_m: float = 0.020,
) -> Tuple[np.ndarray, Dict[str, List[int]], Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]]]:
    """
    Constructs a complete synthetic humanoid T-pose mesh with specified axilla and thigh air gaps.
    """
    groups: Dict[str, List[int]] = {
        "chest": [],
        "upper_arm_L": [],
        "upper_arm_R": [],
        "thigh_L": [],
        "thigh_R": [],
    }
    pts: List[List[float]] = []

    # 1. Torso/Chest: column from z=0.8 to z=1.4, radius 0.12
    torso_rad = 0.12
    for z in np.linspace(0.8, 1.4, 15):
        for ang in np.linspace(0, 2 * math.pi, 12, endpoint=False):
            groups["chest"].append(len(pts))
            pts.append([torso_rad * math.cos(ang), 0.08 * math.sin(ang), z])

    # 2. Upper arm Left: horizontal cylinder along +X
    # Starts at x = torso_rad + axilla_gap_m, radius 0.045
    arm_rad = 0.045
    arm_start_x = torso_rad + axilla_gap_m
    for x in np.linspace(arm_start_x, arm_start_x + 0.30, 15):
        for ang in np.linspace(0, 2 * math.pi, 10, endpoint=False):
            groups["upper_arm_L"].append(len(pts))
            pts.append([x, arm_rad * math.sin(ang), 1.25 + arm_rad * math.cos(ang)])

    # 3. Upper arm Right: horizontal cylinder along -X
    arm_start_x_R = -(torso_rad + axilla_gap_m)
    for x in np.linspace(arm_start_x_R, arm_start_x_R - 0.30, 15):
        for ang in np.linspace(0, 2 * math.pi, 10, endpoint=False):
            groups["upper_arm_R"].append(len(pts))
            pts.append([x, arm_rad * math.sin(ang), 1.25 + arm_rad * math.cos(ang)])

    # 4. Thigh Left: vertical cylinder along -Z, inner edge at +(thigh_gap_m / 2)
    thigh_rad = 0.055
    thigh_center_x_L = (thigh_gap_m / 2.0) + thigh_rad
    for z in np.linspace(0.2, 0.75, 15):
        for ang in np.linspace(0, 2 * math.pi, 10, endpoint=False):
            groups["thigh_L"].append(len(pts))
            pts.append([thigh_center_x_L + thigh_rad * math.cos(ang), thigh_rad * math.sin(ang), z])

    # 5. Thigh Right: vertical cylinder along -Z, inner edge at -(thigh_gap_m / 2)
    thigh_center_x_R = -thigh_center_x_L
    for z in np.linspace(0.2, 0.75, 15):
        for ang in np.linspace(0, 2 * math.pi, 10, endpoint=False):
            groups["thigh_R"].append(len(pts))
            pts.append([thigh_center_x_R + thigh_rad * math.cos(ang), thigh_rad * math.sin(ang), z])

    all_verts = np.array(pts, dtype=np.float64)

    bones: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]] = {
        "DEF-spine": ((0.0, 0.0, 0.8), (0.0, 0.0, 1.4)),
        "DEF-upper_arm.L": ((arm_start_x, 0.0, 1.25), (arm_start_x + 0.30, 0.0, 1.25)),
        "DEF-upper_arm.R": ((arm_start_x_R, 0.0, 1.25), (arm_start_x_R - 0.30, 0.0, 1.25)),
        "DEF-thigh.L": ((thigh_center_x_L, 0.0, 0.75), (thigh_center_x_L, 0.0, 0.2)),
        "DEF-thigh.R": ((thigh_center_x_R, 0.0, 0.75), (thigh_center_x_R, 0.0, 0.2)),
    }

    return all_verts, groups, bones


# ==============================================================================
# ADVERSARIAL TEST CASES
# ==============================================================================

class TestAdversarialAxillaWeightStealing:
    """Stress-tests axilla (arm-chest) narrow air gaps between 1.5 cm and 2.5 cm."""

    @pytest.mark.parametrize("air_gap_cm", [2.5, 2.0, 1.5])
    def test_axilla_zero_weight_stealing_narrow_gaps(self, air_gap_cm: float):
        """
        Verify that for air gaps between 1.5 cm and 2.5 cm,
        arm bone influence on chest/torso vertices is exactly 0.000.
        """
        air_gap_m = air_gap_cm / 100.0
        verts, torso_idx, arm_idx = create_synthetic_axilla_mesh(
            air_gap_m=air_gap_m,
            torso_radius=0.10,
            arm_radius=0.04,
            height=0.6,
        )

        arm_center_x = 0.10 + air_gap_m + 0.04
        bones = {
            "DEF-spine": ((0.0, 0.0, 0.4), (0.0, 0.0, 1.0)),
            "DEF-upper_arm.L": ((arm_center_x, 0.0, 0.4), (arm_center_x, 0.0, 1.0)),
        }

        # Run skinning solver
        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=36)

        # Assert zero weight stealing on torso
        stolen_count = 0
        max_stolen_weight = 0.0
        for v_idx in torso_idx:
            vw = skin_map.get_vertex_weights(v_idx)
            w = vw.get("DEF-upper_arm.L", 0.0)
            if w > 0.0:
                stolen_count += 1
                max_stolen_weight = max(max_stolen_weight, w)

        assert stolen_count == 0, (
            f"Weight stealing at axilla gap {air_gap_cm}cm! "
            f"{stolen_count}/{len(torso_idx)} torso vertices stolen. "
            f"Max stolen weight: {max_stolen_weight:.5f}"
        )

    @pytest.mark.parametrize("air_gap_cm", [2.5, 2.0, 1.5])
    def test_axilla_partition_of_unity(self, air_gap_cm: float):
        """Verify partition-of-unity (sum == 1.0 +- 1e-5) on all vertices."""
        air_gap_m = air_gap_cm / 100.0
        verts, _, _ = create_synthetic_axilla_mesh(air_gap_m=air_gap_m)
        arm_center_x = 0.12 + air_gap_m + 0.04
        bones = {
            "DEF-spine": ((0.0, 0.0, 0.4), (0.0, 0.0, 1.2)),
            "DEF-upper_arm.L": ((arm_center_x, 0.0, 0.4), (arm_center_x, 0.0, 1.2)),
        }

        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=32)
        assert skin_map.verify_partition_of_unity(tol=1e-5) is True

        # Check vertex-level sum and non-negativity
        for v_idx in range(skin_map.vertex_count):
            vw = skin_map.get_vertex_weights(v_idx)
            total = sum(vw.values())
            assert abs(total - 1.0) <= 1e-5, f"Vertex {v_idx} partition of unity violated: {total}"
            for bname, w in vw.items():
                assert w >= 0.0, f"Vertex {v_idx} negative weight for {bname}: {w}"


class TestAdversarialInnerThighWeightStealing:
    """Stress-tests inner thigh bilateral narrow air gaps between 1.5 cm and 2.5 cm."""

    @pytest.mark.parametrize("air_gap_cm", [2.5, 2.0, 1.5])
    def test_inner_thighs_zero_weight_stealing(self, air_gap_cm: float):
        """
        Verify that for air gaps between 1.5 cm and 2.5 cm,
        left leg bone influence on right thigh is exactly 0.000,
        and right leg bone influence on left thigh is exactly 0.000.
        """
        air_gap_m = air_gap_cm / 100.0
        thigh_rad = 0.05
        verts, left_idx, right_idx = create_synthetic_thighs_mesh(
            air_gap_m=air_gap_m,
            thigh_radius=thigh_rad,
            height=0.6,
        )

        left_center_x = (air_gap_m / 2.0) + thigh_rad
        right_center_x = -left_center_x
        bones = {
            "DEF-thigh.L": ((left_center_x, 0.0, 0.7), (left_center_x, 0.0, 0.1)),
            "DEF-thigh.R": ((right_center_x, 0.0, 0.7), (right_center_x, 0.0, 0.1)),
        }

        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=36)

        # 1. Left thigh vertices: DEF-thigh.R influence must be 0.000
        for v_idx in left_idx:
            vw = skin_map.get_vertex_weights(v_idx)
            r_weight = vw.get("DEF-thigh.R", 0.0)
            assert r_weight == 0.0, (
                f"Inner thigh weight stealing on Left Thigh vertex {v_idx} (gap {air_gap_cm}cm): "
                f"DEF-thigh.R={r_weight:.5f}"
            )

        # 2. Right thigh vertices: DEF-thigh.L influence must be 0.000
        for v_idx in right_idx:
            vw = skin_map.get_vertex_weights(v_idx)
            l_weight = vw.get("DEF-thigh.L", 0.0)
            assert l_weight == 0.0, (
                f"Inner thigh weight stealing on Right Thigh vertex {v_idx} (gap {air_gap_cm}cm): "
                f"DEF-thigh.L={l_weight:.5f}"
            )

    @pytest.mark.parametrize("air_gap_cm", [2.5, 2.0, 1.5])
    def test_inner_thighs_partition_of_unity(self, air_gap_cm: float):
        air_gap_m = air_gap_cm / 100.0
        thigh_rad = 0.05
        verts, _, _ = create_synthetic_thighs_mesh(air_gap_m=air_gap_m, thigh_radius=thigh_rad)
        left_center_x = (air_gap_m / 2.0) + thigh_rad
        right_center_x = -left_center_x
        bones = {
            "DEF-thigh.L": ((left_center_x, 0.0, 0.7), (left_center_x, 0.0, 0.1)),
            "DEF-thigh.R": ((right_center_x, 0.0, 0.7), (right_center_x, 0.0, 0.1)),
        }
        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=32)
        assert skin_map.verify_partition_of_unity(tol=1e-5) is True


class TestAdversarialFullTPoseSkinning:
    """Stress-tests full humanoid T-pose with simultaneous axilla and inner thigh gaps."""

    @pytest.mark.parametrize("air_gap_cm", [2.5, 2.0, 1.5])
    def test_full_tpose_zero_cross_influence(self, air_gap_cm: float):
        """Simultaneous verification of chest isolation, arm isolation, and bilateral thigh isolation."""
        air_gap_m = air_gap_cm / 100.0
        verts, groups, bones = create_full_tpose_mesh_with_air_gaps(
            axilla_gap_m=air_gap_m,
            thigh_gap_m=air_gap_m,
        )

        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=38, max_influences=4)

        # 1. Partition of unity across entire mesh
        assert skin_map.verify_partition_of_unity(tol=1e-5) is True

        # 2. Chest vertices must have ZERO influence from both upper arms
        for v_idx in groups["chest"]:
            vw = skin_map.get_vertex_weights(v_idx)
            assert vw.get("DEF-upper_arm.L", 0.0) == 0.0, f"Chest vertex {v_idx} contaminated by DEF-upper_arm.L"
            assert vw.get("DEF-upper_arm.R", 0.0) == 0.0, f"Chest vertex {v_idx} contaminated by DEF-upper_arm.R"

        # 3. Left thigh vertices must have ZERO influence from right thigh bone
        for v_idx in groups["thigh_L"]:
            vw = skin_map.get_vertex_weights(v_idx)
            assert vw.get("DEF-thigh.R", 0.0) == 0.0, f"Left thigh vertex {v_idx} contaminated by DEF-thigh.R"

        # 4. Right thigh vertices must have ZERO influence from left thigh bone
        for v_idx in groups["thigh_R"]:
            vw = skin_map.get_vertex_weights(v_idx)
            assert vw.get("DEF-thigh.L", 0.0) == 0.0, f"Right thigh vertex {v_idx} contaminated by DEF-thigh.L"

        # 5. Maximum 4 influences enforced
        assert skin_map.max_influences_per_vertex() <= 4


class TestAdversarialSkinningBoundaryStress:
    """Edge cases: extreme narrow gap (1.0cm), resolution scaling, dense sampling."""

    def test_extreme_narrow_air_gap_1cm(self):
        """Extreme challenge: 1.0cm air gap with higher grid resolution (48)."""
        air_gap_m = 0.010  # 1.0 cm
        verts, torso_idx, arm_idx = create_synthetic_axilla_mesh(
            air_gap_m=air_gap_m,
            torso_radius=0.08,
            arm_radius=0.035,
            height=0.4,
            radial_samples=20,
            height_samples=25,
        )
        arm_center_x = 0.08 + air_gap_m + 0.035
        bones = {
            "DEF-spine": ((0.0, 0.0, 0.4), (0.0, 0.0, 0.8)),
            "DEF-upper_arm.L": ((arm_center_x, 0.0, 0.4), (arm_center_x, 0.0, 0.8)),
        }

        skin_map = compute_geodesic_skin_weights(verts, bones, grid_resolution=48)
        assert skin_map.verify_partition_of_unity(tol=1e-5) is True

        for v_idx in torso_idx:
            vw = skin_map.get_vertex_weights(v_idx)
            assert vw.get("DEF-upper_arm.L", 0.0) == 0.0, f"1cm gap failed on torso vertex {v_idx}"

    def test_triangulated_surface_faces_air_barrier(self):
        """Verify that when triangular faces are provided, the manifold flood-fill maintains air barrier."""
        # Simple two disjoint cubes
        verts = []
        faces = []
        # Cube 1: [-0.10, -0.01] x [-0.05, 0.05] x [0, 0.1]
        c1 = [
            [-0.10, -0.05, 0.0], [-0.01, -0.05, 0.0], [-0.01, 0.05, 0.0], [-0.10, 0.05, 0.0],
            [-0.10, -0.05, 0.1], [-0.01, -0.05, 0.1], [-0.01, 0.05, 0.1], [-0.10, 0.05, 0.1],
        ]
        # Cube 2: [0.01, 0.10] x [-0.05, 0.05] x [0, 0.1] -> air gap = 0.02m (2.0 cm)
        c2 = [
            [0.01, -0.05, 0.0], [0.10, -0.05, 0.0], [0.10, 0.05, 0.0], [0.01, 0.05, 0.0],
            [0.01, -0.05, 0.1], [0.10, -0.05, 0.1], [0.10, 0.05, 0.1], [0.01, 0.05, 0.1],
        ]
        verts = np.array(c1 + c2, dtype=np.float64)

        # 12 triangles per cube
        def cube_faces(offset: int):
            return [
                [offset+0, offset+1, offset+2], [offset+0, offset+2, offset+3],  # bottom
                [offset+4, offset+5, offset+6], [offset+4, offset+6, offset+7],  # top
                [offset+0, offset+1, offset+5], [offset+0, offset+5, offset+4],  # front
                [offset+2, offset+3, offset+7], [offset+2, offset+7, offset+6],  # back
                [offset+0, offset+3, offset+7], [offset+0, offset+7, offset+4],  # left
                [offset+1, offset+2, offset+6], [offset+1, offset+6, offset+5],  # right
            ]
        faces = np.array(cube_faces(0) + cube_faces(8), dtype=int)

        bones = {
            "bone_left": ((-0.05, 0.0, 0.0), (-0.05, 0.0, 0.1)),
            "bone_right": ((0.05, 0.0, 0.0), (0.05, 0.0, 0.1)),
        }

        skin_map = compute_geodesic_skin_weights(verts, bones, faces=faces, grid_resolution=32)
        assert skin_map.verify_partition_of_unity(tol=1e-5) is True

        # Left cube vertices (0..7) must have 0 influence from bone_right
        for v in range(8):
            vw = skin_map.get_vertex_weights(v)
            assert vw.get("bone_right", 0.0) == 0.0
        # Right cube vertices (8..15) must have 0 influence from bone_left
        for v in range(8, 16):
            vw = skin_map.get_vertex_weights(v)
            assert vw.get("bone_left", 0.0) == 0.0
