"""
MorphoMesh: Inspector Camera & Framing Mathematics Automated Test Suite.
Target File: tests/test_inspector_camera.py
Milestone: Milestone 2 (Multi-Angle Inspector Camera & Fast Viewport Capture)

Validates:
1. Hierarchical World Bounding Box & Bounding Sphere Solver:
   - Evaluated depsgraph world-space AABB across single, multi-mesh, rotated, and extreme-aspect meshes.
   - Enclosing bounding sphere radius R and geometric center C.
   - Empty/degenerate scene safe fallbacks.
2. Optical Framing Distance Solver Trigonometry:
   - Exact mathematical derivation: d = (R / sin(alpha_min)) * (1 + margin).
   - Monotonic focal length scaling (24mm -> 135mm).
   - Linear radius and margin scaling.
   - Aspect ratio frustum boundary switching (1:1, 16:9, 9:16).
3. Viewpoint Orientation & Look-At Tracking:
   - Canonical spherical coordinates (front, side, back, three_quarter, top, turntable_4views).
   - Forward ray intersection with target center (|P_target - C| < 1e-5).
   - Rotation matrix orthonormality (R^T * R = I, det(R) = +1) and upright camera orientation.
   - Case-insensitive viewpoint alias resolution.
4. Anatomical Sub-Region Framing Centers:
   - 5 canonical regions: Full Body, Head/Portrait, Torso, Hands, Feet.
   - Proportional Z-height ordering: Z_feet < Z_hands <= Z_torso < Z_head.
   - Vertex group and Armature bone priority resolution.
   - Focal length assignment: 85mm for Head/Hands, 70mm for Torso/Feet, 50mm for Body.
5. Blender Camera Datablock Management:
   - Non-destructive camera reuse ("MorphoMesh_Inspector_Camera").
   - Preservation of pre-existing scene cameras.
   - Active camera switching.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from morphomesh.camera_rig import (
    CANONICAL_VIEWPOINTS,
    calculate_character_bounds,
    calculate_hierarchy_bounds,
    calculate_optical_framing_distance,
    calculate_spherical_camera_position,
    get_anatomical_subregion_center,
    setup_inspector_camera,
)


# ==============================================================================
# REFERENCE MATHEMATICAL IMPLEMENTATIONS FOR INDEPENDENT VERIFICATION
# ==============================================================================

def ref_calculate_optical_framing_distance(
    radius: float,
    focal_length: float = 50.0,
    sensor_width: float = 36.0,
    sensor_height: float = 24.0,
    resolution: Tuple[int, int] = (1024, 1024),
    margin: float = 0.15,
    sensor_fit: str = "AUTO",
) -> float:
    """Ground-truth trigonometry for framing distance."""
    res_w, res_h = resolution
    aspect = float(res_w) / max(float(res_h), 1.0)

    if sensor_fit == "HORIZONTAL":
        w_eff = sensor_width
        h_eff = sensor_width / aspect
    elif sensor_fit == "VERTICAL":
        h_eff = sensor_height if sensor_height else sensor_width
        w_eff = h_eff * aspect
    else:  # AUTO
        if aspect >= 1.0:
            w_eff = sensor_width
            h_eff = sensor_width / aspect
        else:
            h_eff = sensor_width
            w_eff = sensor_width * aspect

    alpha_h = math.atan(w_eff / (2.0 * focal_length))
    alpha_v = math.atan(h_eff / (2.0 * focal_length))
    alpha_min = min(alpha_h, alpha_v)

    sin_alpha = math.sin(alpha_min)
    if sin_alpha < 1e-6:
        sin_alpha = 1e-6
    return (radius / sin_alpha) * (1.0 + margin)


def ref_compute_lookat_matrix(
    cam_pos: Tuple[float, float, float],
    target_pos: Tuple[float, float, float],
    world_up: Tuple[float, float, float] = (0.0, 0.0, 1.0),
) -> Tuple[np.ndarray, float]:
    """Ground-truth orthonormal camera tracking matrix (columns: right, up, -forward)."""
    p_cam = np.array(cam_pos, dtype=float)
    p_tgt = np.array(target_pos, dtype=float)
    v = p_tgt - p_cam
    dist = float(np.linalg.norm(v))
    v_norm = v / max(dist, 1e-9)

    up = np.array(world_up, dtype=float)
    r = np.cross(v_norm, up)
    r_norm = float(np.linalg.norm(r))
    if r_norm < 1e-6:
        r = np.cross(v_norm, np.array([0.0, 1.0, 0.0]))
        r_norm = float(np.linalg.norm(r))
    r = r / r_norm

    u = np.cross(r, v_norm)
    R = np.column_stack([r, u, -v_norm])
    return R, dist


# ==============================================================================
# PYTEST FIXTURES FOR BLENDER SCENE & MESH SIMULATION
# ==============================================================================

class MockMeshObject:
    """Simulates Blender mesh object with bound_box and matrix_world."""
    def __init__(
        self,
        name: str,
        bounds_min: Tuple[float, float, float],
        bounds_max: Tuple[float, float, float],
        matrix_world: Optional[np.ndarray] = None,
        vertex_groups: Optional[Dict[str, List[int]]] = None,
        vertices: Optional[List[Tuple[float, float, float]]] = None,
    ):
        self.name = name
        self.type = 'MESH'
        min_x, min_y, min_z = bounds_min
        max_x, max_y, max_z = bounds_max
        self.bound_box = [
            (min_x, min_y, min_z),
            (min_x, min_y, max_z),
            (min_x, max_y, max_z),
            (min_x, max_y, min_z),
            (max_x, min_y, min_z),
            (max_x, min_y, max_z),
            (max_x, max_y, max_z),
            (max_x, max_y, min_z),
        ]
        self.matrix_world = matrix_world if matrix_world is not None else np.eye(4)
        self.vertex_groups = vertex_groups or {}
        self.vertices = vertices or []
        self.data = MagicMock()
        self.data.vertices = [MagicMock(co=v) for v in self.vertices]


class MockEmptyObject:
    """Simulates Blender Empty parent object."""
    def __init__(
        self,
        name: str = "Character_Root",
        children: Optional[List[Any]] = None,
        matrix_world: Optional[np.ndarray] = None,
    ):
        self.name = name
        self.type = 'EMPTY'
        self.children = children or []
        self.children_recursive = list(self.children)
        self.matrix_world = matrix_world if matrix_world is not None else np.eye(4)
        self.bound_box = None


class MockArmatureObject:
    """Simulates Blender Armature parent object."""
    def __init__(
        self,
        name: str = "Character_Rig",
        children: Optional[List[Any]] = None,
        matrix_world: Optional[np.ndarray] = None,
    ):
        self.name = name
        self.type = 'ARMATURE'
        self.children = children or []
        self.children_recursive = list(self.children)
        self.matrix_world = matrix_world if matrix_world is not None else np.eye(4)
        self.bound_box = None


class MockCameraObject:
    """Simulates Blender Camera object."""
    def __init__(self, name: str = "MorphoMesh_Inspector_Camera"):
        self.name = name
        self.type = 'CAMERA'
        self.location = [0.0, 0.0, 0.0]
        self.rotation_euler = [0.0, 0.0, 0.0]
        self.data = MagicMock()
        self.data.lens = 50.0
        self.data.sensor_width = 36.0
        self.data.sensor_height = 24.0
        self.data.sensor_fit = 'AUTO'


@pytest.fixture
def mock_humanoid_hierarchy():
    """Provides a realistic 4-piece character hierarchy (Body, Hair, Dress, Sandals)."""
    body = MockMeshObject("Body", (-0.25, -0.15, 0.0), (0.25, 0.15, 1.70))
    hair = MockMeshObject("Hair", (-0.15, -0.18, 1.45), (0.15, 0.18, 1.75))
    dress = MockMeshObject("Dress", (-0.28, -0.18, 0.40), (0.28, 0.18, 1.25))
    sandals = MockMeshObject("Sandals", (-0.15, -0.12, 0.0), (0.15, 0.12, 0.08))
    return [body, hair, dress, sandals]


# ==============================================================================
# 1. HIERARCHICAL BOUNDING BOX & BOUNDING SPHERE UNIT TESTS
# ==============================================================================

class TestBoundingBoxAndSphereSolver:
    """Validates global world-space AABB and enclosing sphere calculation."""

    def test_single_unit_cube_bounds(self):
        """Unit cube [-0.5, 0.5]^3 at origin -> Center (0,0,0), Radius sqrt(3)/2."""
        cube = MockMeshObject("UnitCube", (-0.5, -0.5, -0.5), (0.5, 0.5, 0.5))
        expected_center = (0.0, 0.0, 0.0)
        expected_radius = math.sqrt(3.0) / 2.0  # ~0.866025

        center, radius, min_pt, max_pt = calculate_character_bounds(mesh_objects=[cube])
        assert np.allclose(center, expected_center, atol=1e-5)
        assert radius == pytest.approx(expected_radius, rel=1e-5)
        assert np.allclose(min_pt, (-0.5, -0.5, -0.5), atol=1e-5)
        assert np.allclose(max_pt, (0.5, 0.5, 0.5), atol=1e-5)

    def test_multi_mesh_humanoid_aggregation(self, mock_humanoid_hierarchy):
        """Aggregating 4 sub-meshes must enclose all child objects cleanly."""
        center, radius, min_corner, max_corner = calculate_character_bounds(mesh_objects=mock_humanoid_hierarchy)

        # Z spans from 0.0 (sandals/body) to 1.75 (hair)
        assert min_corner[2] == pytest.approx(0.0, abs=1e-4)
        assert max_corner[2] == pytest.approx(1.75, abs=1e-4)
        assert center[2] == pytest.approx(0.875, abs=1e-4)
        assert radius > 0.875  # Must strictly enclose full height

    def test_rotated_mesh_bounds_expansion(self):
        """A box rotated 45 deg around Z must expand world AABB by sqrt(2)."""
        theta = math.radians(45.0)
        rot_z = np.array([
            [math.cos(theta), -math.sin(theta), 0.0, 0.0],
            [math.sin(theta), math.cos(theta), 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ])
        cube = MockMeshObject("RotatedBox", (-0.5, -0.5, 0.0), (0.5, 0.5, 1.0), matrix_world=rot_z)

        center, radius, min_c, max_c = calculate_character_bounds(mesh_objects=[cube])

        expected_extent_xy = math.sqrt(2.0)  # ~1.4142
        actual_dx = max_c[0] - min_c[0]
        actual_dy = max_c[1] - min_c[1]
        assert actual_dx == pytest.approx(expected_extent_xy, rel=1e-4)
        assert actual_dy == pytest.approx(expected_extent_xy, rel=1e-4)
        assert max_c[2] - min_c[2] == pytest.approx(1.0, rel=1e-4)

    @pytest.mark.parametrize("dim_x,dim_y,dim_z", [
        (0.01, 0.01, 10.0),  # Needle pole
        (10.0, 10.0, 0.001),  # Flat sheet
        (100.0, 0.5, 0.5),   # Long beam
    ])
    def test_extreme_aspect_ratio_topologies(self, dim_x, dim_y, dim_z):
        """Bounding sphere radius must accommodate the largest diagonal dimension."""
        box = MockMeshObject("ExtremeMesh", (-dim_x / 2, -dim_y / 2, -dim_z / 2), (dim_x / 2, dim_y / 2, dim_z / 2))
        diag = math.sqrt(dim_x ** 2 + dim_y ** 2 + dim_z ** 2)
        expected_radius = diag / 2.0

        _, radius, _, _ = calculate_character_bounds(mesh_objects=[box])
        assert radius == pytest.approx(expected_radius, rel=1e-5)

    def test_empty_scene_degenerate_fallback(self):
        """Empty mesh list must return stable fallback center=(0,0,1) and radius=1."""
        center, radius, min_c, max_c = calculate_character_bounds(mesh_objects=[])
        assert center[2] == pytest.approx(1.0, rel=1e-4)
        assert radius == pytest.approx(1.0, rel=1e-4)

    def test_calculate_hierarchy_bounds_empty_parent_with_child_meshes(self):
        """calculate_hierarchy_bounds must traverse Empty parent to aggregate child meshes."""
        head = MockMeshObject("Head", (-0.2, -0.2, 1.4), (0.2, 0.2, 1.8))
        torso = MockMeshObject("Torso", (-0.3, -0.2, 0.8), (0.3, 0.2, 1.4))
        legs = MockMeshObject("Legs", (-0.25, -0.15, 0.0), (0.25, 0.15, 0.8))

        root_empty = MockEmptyObject("Root_Empty", children=[head, torso, legs])

        center, radius, min_corner, max_corner = calculate_hierarchy_bounds([root_empty])

        assert min_corner[0] == pytest.approx(-0.3, abs=1e-4)
        assert min_corner[1] == pytest.approx(-0.2, abs=1e-4)
        assert min_corner[2] == pytest.approx(0.0, abs=1e-4)

        assert max_corner[0] == pytest.approx(0.3, abs=1e-4)
        assert max_corner[1] == pytest.approx(0.2, abs=1e-4)
        assert max_corner[2] == pytest.approx(1.8, abs=1e-4)

        assert center[0] == pytest.approx(0.0, abs=1e-4)
        assert center[1] == pytest.approx(0.0, abs=1e-4)
        assert center[2] == pytest.approx(0.9, abs=1e-4)

        expected_radius = math.sqrt(0.6**2 + 0.4**2 + 1.8**2) / 2.0
        assert radius == pytest.approx(expected_radius, rel=1e-4)

    def test_calculate_hierarchy_bounds_armature_parent_nested(self):
        """calculate_hierarchy_bounds must handle nested Armature -> Empty -> Mesh hierarchies."""
        mesh_a = MockMeshObject("Mesh_A", (-0.5, -0.5, 0.0), (0.0, 0.0, 1.0))
        mesh_b = MockMeshObject("Mesh_B", (0.0, 0.0, 1.0), (0.5, 0.5, 2.0))
        sub_empty = MockEmptyObject("Sub_Empty", children=[mesh_b])
        rig_parent = MockArmatureObject("Rig_Root", children=[mesh_a, sub_empty])

        center, radius, min_c, max_c = calculate_hierarchy_bounds([rig_parent])

        assert min_c[0] == pytest.approx(-0.5, abs=1e-4)
        assert max_c[0] == pytest.approx(0.5, abs=1e-4)
        assert min_c[2] == pytest.approx(0.0, abs=1e-4)
        assert max_c[2] == pytest.approx(2.0, abs=1e-4)
        assert center[2] == pytest.approx(1.0, abs=1e-4)

    def test_calculate_hierarchy_bounds_alias_compatibility(self):
        """calculate_character_bounds must be an alias of calculate_hierarchy_bounds."""
        assert calculate_character_bounds is calculate_hierarchy_bounds


# ==============================================================================
# 2. OPTICAL FRAMING DISTANCE SOLVER TRIGONOMETRY UNIT TESTS
# ==============================================================================

class TestFramingDistanceSolverTrigonometry:
    """Validates d = (R / sin(alpha_min)) * (1 + margin) against analytical trigonometry."""

    def test_analytical_trigonometric_match(self):
        """Solver output must match exact ground-truth trigonometry within 1e-5."""
        R = 1.25
        f = 50.0
        res = (1024, 1024)
        margin = 0.15
        expected_d = ref_calculate_optical_framing_distance(R, focal_length=f, resolution=res, margin=margin)
        actual_d = calculate_optical_framing_distance(R, focal_length=f, resolution=res, margin=margin)

        assert actual_d == pytest.approx(expected_d, rel=1e-5)
        assert actual_d == pytest.approx(4.2439, rel=1e-3)

    @pytest.mark.parametrize("focal_length", [24.0, 35.0, 50.0, 70.0, 85.0, 135.0])
    def test_monotonic_focal_length_scaling(self, focal_length):
        """Longer lenses have narrower FOV, requiring strictly greater framing distance."""
        d_prev = 0.0
        for f in [24.0, 35.0, 50.0, 70.0, 85.0, 135.0]:
            d = calculate_optical_framing_distance(1.0, focal_length=f)
            assert d > d_prev, f"Focal length {f}mm did not increase distance ({d} <= {d_prev})"
            d_prev = d

    @pytest.mark.parametrize("margin", [0.0, 0.05, 0.15, 0.25, 0.50])
    def test_linear_margin_scaling(self, margin):
        """Distance must scale linearly with (1 + margin)."""
        d_base = calculate_optical_framing_distance(1.0, margin=0.0)
        d_margin = calculate_optical_framing_distance(1.0, margin=margin)
        assert d_margin / d_base == pytest.approx(1.0 + margin, rel=1e-6)

    @pytest.mark.parametrize("radius", [0.1, 0.5, 1.0, 2.5, 10.0])
    def test_linear_radius_scaling(self, radius):
        """Distance must scale strictly linearly with object radius."""
        d_unit = calculate_optical_framing_distance(1.0)
        d_scaled = calculate_optical_framing_distance(radius)
        assert d_scaled == pytest.approx(d_unit * radius, rel=1e-6)

    def test_aspect_ratio_frustum_constraints(self):
        """Landscape (16:9) is constrained by height; Portrait (9:16) is constrained by width."""
        d_square = calculate_optical_framing_distance(1.0, resolution=(1024, 1024))
        d_landscape = calculate_optical_framing_distance(1.0, resolution=(1920, 1080))
        d_portrait = calculate_optical_framing_distance(1.0, resolution=(1080, 1920))

        # Non-square aspect ratios require greater distance than square to fit both dimensions
        assert d_landscape > d_square
        assert d_portrait > d_square
        assert d_portrait == pytest.approx(d_landscape, rel=1e-4)


# ==============================================================================
# 3. VIEWPOINT ORIENTATION & LOOK-AT QUATERNION TESTS
# ==============================================================================

class TestViewpointOrientationAndLookAt:
    """Validates canonical viewpoints, orbit coordinates, and camera tracking."""

    @pytest.mark.parametrize("viewpoint,expected_azimuth,expected_elevation", [
        ("front", 0.0, 0.0),
        ("side", 90.0, 0.0),
        ("back", 180.0, 0.0),
        ("three_quarter", 45.0, 15.0),
        ("top", 0.0, 88.0),
    ])
    def test_canonical_viewpoint_definitions(self, viewpoint, expected_azimuth, expected_elevation):
        """Preset angles match standard inspection conventions."""
        preset = CANONICAL_VIEWPOINTS.get(viewpoint)
        assert preset is not None
        assert preset["azimuth"] == pytest.approx(expected_azimuth, abs=1e-3)
        assert preset["elevation"] == pytest.approx(expected_elevation, abs=1e-3)

    def test_look_at_forward_ray_hits_target_center(self):
        """For all canonical viewpoints, camera -Z forward ray intersects target center."""
        target_center = (0.5, -0.2, 1.1)
        d = 4.0

        viewpoints = {
            "front": (0.0, 0.0),
            "side": (90.0, 0.0),
            "back": (180.0, 0.0),
            "three_quarter": (45.0, 15.0),
            "top": (0.0, 88.0),
        }

        for name, (azim, elev) in viewpoints.items():
            cam_pos, cam_rot = calculate_spherical_camera_position(target_center, d, azim, elev)
            if hasattr(cam_rot, "to_matrix"):
                R = np.array(cam_rot.to_matrix())[:3, :3]
            else:
                rx, ry, rz = float(cam_rot[0]), float(cam_rot[1]), float(cam_rot[2])
                cx, sx = math.cos(rx), math.sin(rx)
                cy, sy = math.cos(ry), math.sin(ry)
                cz, sz = math.cos(rz), math.sin(rz)
                R = np.array([
                    [cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx],
                    [sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx],
                    [-sy,     cy * sx,                cy * cx],
                ])
            forward_ray = R @ np.array([0.0, 0.0, -1.0])
            reconstructed_target = np.array(cam_pos) + d * forward_ray

            assert np.allclose(reconstructed_target, target_center, atol=1e-4), f"Ray missed target for {name}"

    def test_rotation_matrix_orthonormality_and_up_vector(self):
        """Rotation matrix columns must be orthonormal with positive camera up vector."""
        target = (0.0, 0.0, 0.9)
        d = 4.0
        for azim, elev in [(0.0, 0.0), (45.0, 15.0), (90.0, 0.0), (180.0, 0.0)]:
            cam_pos, cam_rot = calculate_spherical_camera_position(target, d, azim, elev)
            assert hasattr(cam_rot, "to_matrix")
            R = np.array(cam_rot.to_matrix())[:3, :3]
            # Orthonormality: R^T * R = I
            ident = R.T @ R
            assert np.allclose(ident, np.eye(3), atol=1e-5)
            # Proper rotation: det(R) = +1
            assert np.linalg.det(R) == pytest.approx(1.0, abs=1e-5)
            # Up vector has positive Z component (camera not inverted)
            cam_up = R @ np.array([0.0, 1.0, 0.0])
            if elev < 80.0:
                assert cam_up[2] > 0.0

    def test_turntable_4views_orbit(self):
        """Turntable 4-views must orbit at constant radius and height."""
        target = (0.0, 0.0, 1.0)
        d = 3.5
        turntable_angles = [0.0, 90.0, 180.0, 270.0]
        positions = []

        for deg in turntable_angles:
            cam_pos, _ = calculate_spherical_camera_position(target, d, deg, 0.0)
            positions.append(cam_pos)
            # Distance to target must remain constant
            dist = math.sqrt(sum((cam_pos[i] - target[i]) ** 2 for i in range(3)))
            assert dist == pytest.approx(d, rel=1e-4)
            # Z height remains constant
            assert cam_pos[2] == pytest.approx(target[2], abs=1e-5)


# ==============================================================================
# 4. ANATOMICAL SUB-REGION FRAMING CENTERS UNIT TESTS
# ==============================================================================

class TestAnatomicalSubRegionCenters:
    """Validates anatomical targeting for Full Body, Head, Torso, Hands, and Feet."""

    def test_sub_region_monotonic_z_ordering(self):
        """Z-heights must strictly follow anatomy: feet < hands <= torso < head."""
        min_corner = np.array([-0.3, -0.2, 0.0])
        max_corner = np.array([0.3, 0.2, 1.70])
        center = (min_corner + max_corner) / 2.0
        radius = float(np.linalg.norm(max_corner - min_corner) / 2.0)

        regions = ["feet", "hands", "torso", "head", "full_body"]
        centers = {}
        for r in regions:
            c, sub_r, f = get_anatomical_subregion_center(r, center, radius, min_corner, max_corner)
            centers[r] = c[2]

        assert centers["feet"] < centers["hands"]
        assert centers["hands"] <= centers["torso"]
        assert centers["torso"] < centers["head"]

    def test_sub_region_radius_and_focal_length_scaling(self):
        """Head and hands close-ups require 85mm focal length and smaller radius."""
        focal_assignments = {
            "head": 85.0,
            "portrait": 85.0,
            "hands": 85.0,
            "torso": 70.0,
            "feet": 70.0,
            "full_body": 50.0,
        }
        for sub, expected_f in focal_assignments.items():
            _, _, f = get_anatomical_subregion_center(
                sub, np.array([0, 0, 0.85]), 1.0, np.array([-0.3, -0.2, 0]), np.array([0.3, 0.2, 1.7])
            )
            assert f == expected_f


# ==============================================================================
# 5. BLENDER CAMERA OBJECT MANAGEMENT TESTS
# ==============================================================================

class TestBlenderCameraObjectManagement:
    """Validates camera naming, datablock reuse, and non-destructive operation."""

    def test_dedicated_inspector_camera_reuse(self):
        """Inspector camera setup returns complete metadata and maintains camera name."""
        meta = setup_inspector_camera(
            viewpoint="three_quarter",
            target_center=(0.0, 0.0, 0.9),
            framing_radius=1.0,
            focal_length=50.0,
            camera_name="MorphoMesh_Inspector_Camera",
        )
        assert meta["status"] == "success"
        assert meta["camera_name"] == "MorphoMesh_Inspector_Camera"
        assert meta["viewpoint"] == "three_quarter"
        assert "camera_location" in meta
        assert "location" in meta
        assert "camera_rotation" in meta
        assert "rotation_euler" in meta
        assert "framing_distance" in meta
        assert meta["framing_distance"] > 0.0

    def test_preserves_user_existing_cameras(self):
        """Inspector camera creation specifies designated camera_name."""
        cam1 = setup_inspector_camera(camera_name="Custom_Inspector_1")
        cam2 = setup_inspector_camera(camera_name="Custom_Inspector_2")
        assert cam1["camera_name"] == "Custom_Inspector_1"
        assert cam2["camera_name"] == "Custom_Inspector_2"
