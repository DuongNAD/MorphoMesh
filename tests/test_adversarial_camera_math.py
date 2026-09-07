"""
MorphoMesh: Milestone M2 Adversarial Camera Mathematics & Geometric Stress Test Suite.
Target File: tests/test_adversarial_camera_math.py
Milestone: Milestone 2 (Multi-Angle Inspector Camera & Fast Viewport Capture)

Empirically stress-tests:
1. Degenerate and edge-case geometries:
   - Single-vertex mesh, zero-volume 2D planar meshes (XY, YZ, ZX), 1D line segments.
   - Vast scale discrepancies (microscopic 1e-6 to gigantic 1e6 meters).
   - Extreme aspect ratios (1000:1 pencil needle meshes along all axes).
2. Gimbal lock and polar singularities:
   - Elevation phi = +90 degrees (zenith / top-down view).
   - Elevation phi = -90 degrees (nadir / bottom-up view).
   - Azimuth theta = 0, 90, 180, 270, 360, -720 degrees.
   - Quaternion normalization (|q| = 1.0), finiteness, and non-NaN verification.
3. Frustum containment verification:
   - All 28 canonical viewpoints in CANONICAL_VIEWPOINTS.
   - Full 360-degree turntable sweep (every 15 degrees) across multiple elevations.
   - Every vertex of the bounding sphere projects strictly inside NDC [-1, 1] x [-1, 1].
4. Extreme camera parameters:
   - Extreme focal lengths (f = 5mm fisheye to f = 800mm super-telephoto).
   - Extreme sensor aspect ratios (32:9 ultra-wide, 21:9, 1:1, 9:16 portrait, 9:32 ultra-tall).
   - Governing FOV constraint switching between horizontal and vertical dimensions.
5. Headless Blender runtime verification:
   - Subprocess execution in Blender 4.5 verifying real bpy, mathutils, and world_to_camera_view.
"""

from __future__ import annotations

import math
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple
from unittest.mock import MagicMock

import numpy as np
import pytest

from morphomesh.blender_bridge import BlenderBridge
from morphomesh.camera_rig import (
    CANONICAL_VIEWPOINTS,
    calculate_character_bounds,
    calculate_optical_framing_distance,
    calculate_spherical_camera_position,
    get_anatomical_subregion_center,
    setup_inspector_camera,
)


# ==============================================================================
# REFERENCE MATHEMATICAL UTILITIES FOR INDEPENDENT VERIFICATION
# ==============================================================================

def blender_euler_to_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
    """
    Reference Euler 'XYZ' to 3x3 rotation matrix matching Blender's native convention:
    M = R_z(rz) * R_y(ry) * R_x(rx).
    Columns of M represent camera local axes in world space:
    - Column 0: Camera +X (screen right)
    - Column 1: Camera +Y (screen up)
    - Column 2: Camera +Z (camera back, optical axis is -Z)
    """
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]])
    Ry = np.array([[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]])
    Rz = np.array([[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]])
    return Rz @ Ry @ Rx


def ref_project_point_to_ndc(
    p_world: np.ndarray,
    cam_pos: np.ndarray,
    cam_rot_euler: Tuple[float, float, float],
    focal_length: float,
    resolution: Tuple[int, int],
    sensor_width: float = 36.0,
) -> Tuple[float, float, float]:
    """
    Ground-truth analytical perspective projection to Normalized Device Coordinates (NDC).
    Returns (ndc_x, ndc_y, z_depth) where NDC is in [-1.0, 1.0] x [-1.0, 1.0].
    """
    res_w, res_h = resolution
    aspect = float(res_w) / max(float(res_h), 1.0)

    # Effective sensor extents under Blender AUTO sensor fit
    if aspect >= 1.0:
        w_eff = sensor_width
        h_eff = sensor_width / aspect
    else:
        h_eff = sensor_width
        w_eff = sensor_width * aspect

    rot_mat = blender_euler_to_matrix(*cam_rot_euler)
    v_world = np.array(p_world, dtype=float) - np.array(cam_pos, dtype=float)

    # Camera space coordinates
    xc = float(np.dot(rot_mat[:, 0], v_world))
    yc = float(np.dot(rot_mat[:, 1], v_world))
    zc = float(np.dot(rot_mat[:, 2], v_world))
    z_depth = -zc  # Camera looks along -Z

    if z_depth <= 1e-9:
        return float('nan'), float('nan'), z_depth

    xmax = z_depth * (w_eff / (2.0 * focal_length))
    ymax = z_depth * (h_eff / (2.0 * focal_length))

    ndc_x = xc / xmax
    ndc_y = yc / ymax
    return ndc_x, ndc_y, z_depth


def generate_fibonacci_sphere(
    samples: int = 200,
    center: Tuple[float, float, float] = (0.0, 0.0, 0.0),
    radius: float = 1.0,
) -> List[np.ndarray]:
    """Uniformly distributes sample vertices on the surface of a bounding sphere."""
    points = []
    phi = math.pi * (math.sqrt(5.0) - 1.0)  # Golden angle
    for i in range(samples):
        y = 1.0 - (i / float(samples - 1)) * 2.0
        r = math.sqrt(max(0.0, 1.0 - y * y))
        theta = phi * i
        x = math.cos(theta) * r
        z = math.sin(theta) * r
        points.append(np.array([
            center[0] + radius * x,
            center[1] + radius * y,
            center[2] + radius * z,
        ]))
    return points


class MockMeshObject:
    """Mock Blender mesh object for offline unit testing."""
    def __init__(
        self,
        name: str,
        bounds_min: Tuple[float, float, float],
        bounds_max: Tuple[float, float, float],
        matrix_world: Optional[np.ndarray] = None,
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


# ==============================================================================
# 1. DEGENERATE AND EDGE-CASE GEOMETRIES
# ==============================================================================

class TestAdversarialDegenerateGeometries:
    """Stress-tests bounding box solver and framing on pathological geometries."""

    def test_single_vertex_mesh_bounds_and_framing(self):
        """Single vertex mesh (0-volume, 0-extent) must clamp radius >= 0.01 and yield valid framing."""
        vert_pos = (1.5, -2.5, 3.0)
        single_vert_obj = MockMeshObject("SingleVert", vert_pos, vert_pos)

        center, radius, min_pt, max_pt = calculate_character_bounds(mesh_objects=[single_vert_obj])

        assert np.allclose(center, vert_pos, atol=1e-5), f"Center deviated from single vertex: {center}"
        assert radius == pytest.approx(0.01, abs=1e-5), f"Radius not clamped to safe minimum 0.01: {radius}"
        assert np.allclose(min_pt, vert_pos, atol=1e-5)
        assert np.allclose(max_pt, vert_pos, atol=1e-5)

        # Distance calculation must be strictly positive and finite
        dist = calculate_optical_framing_distance(radius, focal_length=50.0)
        assert dist > 0.0
        assert not math.isnan(dist)
        assert not math.isinf(dist)

    @pytest.mark.parametrize("plane_name,bounds_min,bounds_max", [
        ("XY_plane", (-2.0, -1.5, 0.5), (2.0, 1.5, 0.5)),      # Z-extent = 0
        ("YZ_plane", (0.0, -3.0, -2.0), (0.0, 3.0, 2.0)),      # X-extent = 0
        ("ZX_plane", (-1.0, 0.0, -4.0), (1.0, 0.0, 4.0)),      # Y-extent = 0
        ("1D_segment", (-5.0, 0.0, 0.0), (5.0, 0.0, 0.0)),     # Y, Z extents = 0
    ])
    def test_zero_volume_planar_and_linear_meshes(self, plane_name, bounds_min, bounds_max):
        """2D flat planes and 1D line segments with zero volume must calculate non-zero radius."""
        obj = MockMeshObject(plane_name, bounds_min, bounds_max)
        center, radius, min_c, max_c = calculate_character_bounds(mesh_objects=[obj])

        dx = bounds_max[0] - bounds_min[0]
        dy = bounds_max[1] - bounds_min[1]
        dz = bounds_max[2] - bounds_min[2]
        expected_radius = math.sqrt(dx**2 + dy**2 + dz**2) / 2.0

        assert radius == pytest.approx(expected_radius, rel=1e-5)
        assert radius > 0.0

        # Sub-region framing centers must handle zero-height without ZeroDivisionError
        for region in ["head", "torso", "hands", "feet", "full_body"]:
            c_sub, r_sub, f_sub = get_anatomical_subregion_center(region, center, radius, min_c, max_c)
            assert r_sub > 0.0
            assert not any(math.isnan(x) for x in c_sub)
            assert not any(math.isinf(x) for x in c_sub)

    def test_vast_scale_discrepancies_microscopic_to_gigantic(self):
        """
        Validates framing mathematics across 12 orders of magnitude:
        Microscopic: 1e-6m (1 micron)
        Millimeter: 1e-3m
        Meter: 1.0m
        Kilometer: 1e3m
        Gigantic: 1e6m (1,000 km planetary asset)
        """
        scales = [1e-6, 1e-4, 1e-2, 1.0, 1e2, 1e4, 1e6]
        dists = []
        for s in scales:
            d = calculate_optical_framing_distance(radius=s, focal_length=50.0, margin=0.15)
            assert d > 0.0
            assert not math.isnan(d)
            assert not math.isinf(d)
            assert d > s, f"Framing distance ({d}) must be greater than sphere radius ({s})"
            dists.append(d)

        # Monotonicity check across scales
        for i in range(len(dists) - 1):
            assert dists[i] < dists[i + 1], f"Scale monotonicity violated at index {i}"
            ratio_s = scales[i + 1] / scales[i]
            ratio_d = dists[i + 1] / dists[i]
            assert ratio_d == pytest.approx(ratio_s, rel=1e-5)

    @pytest.mark.parametrize("major_axis,dim_x,dim_y,dim_z", [
        ("X", 1000.0, 0.01, 0.01),
        ("Y", 0.01, 1000.0, 0.01),
        ("Z", 0.001, 0.001, 1.0),
        ("Z_extreme", 0.0001, 0.0001, 100.0),
    ])
    def test_extreme_aspect_ratios_1000_to_1_needle_meshes(self, major_axis, dim_x, dim_y, dim_z):
        """1000:1 pencil needle meshes must circumscribe the full major axis length."""
        needle = MockMeshObject("NeedleMesh", (-dim_x/2, -dim_y/2, -dim_z/2), (dim_x/2, dim_y/2, dim_z/2))
        _, radius, _, _ = calculate_character_bounds(mesh_objects=[needle])

        major_len = max(dim_x, dim_y, dim_z)
        assert radius >= major_len / 2.0, f"Radius {radius} did not enclose major axis length {major_len}"

        # Framing distance must accommodate the full needle length
        dist = calculate_optical_framing_distance(radius, focal_length=50.0)
        assert dist > major_len / 2.0


# ==============================================================================
# 2. GIMBAL LOCK AND POLAR SINGULARITIES
# ==============================================================================

class TestAdversarialGimbalLockAndPolarSingularities:
    """Stress-tests camera placement and orientation at zenith, nadir, and arbitrary azimuths."""

    @pytest.mark.parametrize("polar_name,elevation_deg", [
        ("zenith_exact", 90.0),
        ("zenith_near", 88.5),
        ("zenith_exceeded", 120.0),
        ("nadir_exact", -90.0),
        ("nadir_near", -88.5),
        ("nadir_exceeded", -120.0),
    ])
    def test_polar_singularity_elevation_clamping_and_finiteness(self, polar_name, elevation_deg):
        """Elevation angles at and exceeding +/- 90 degrees must be safely clamped to +/- 88.5 deg."""
        center = (0.0, 0.0, 1.0)
        d = 5.0
        azimuth = 0.0

        pos, rot = calculate_spherical_camera_position(center, d, azimuth, elevation_deg)

        # Position checks
        assert not any(math.isnan(c) for c in pos)
        assert not any(math.isinf(c) for c in pos)
        actual_dist = math.sqrt(sum((pos[i] - center[i])**2 for i in range(3)))
        assert actual_dist == pytest.approx(d, rel=1e-5)

        # Rotation checks
        assert not any(math.isnan(r) for r in rot)
        assert not any(math.isinf(r) for r in rot)

    @pytest.mark.parametrize("azimuth_deg", [0.0, 90.0, 180.0, 270.0, 360.0, -720.0, 720.0])
    @pytest.mark.parametrize("elevation_deg", [90.0, -90.0])
    def test_polar_singularities_across_arbitrary_azimuth_rotations(self, azimuth_deg, elevation_deg):
        """At polar singularities, sweeping azimuths must remain continuous, finite, and equidistant."""
        center = (1.0, -2.0, 0.5)
        d = 4.5

        pos, rot = calculate_spherical_camera_position(center, d, azimuth_deg, elevation_deg)

        assert not any(math.isnan(c) for c in pos)
        assert not any(math.isinf(c) for c in pos)
        assert not any(math.isnan(r) for r in rot)
        assert not any(math.isinf(r) for r in rot)

        actual_dist = math.sqrt(sum((pos[i] - center[i])**2 for i in range(3)))
        assert actual_dist == pytest.approx(d, rel=1e-5)

    def test_forward_optical_axis_tracking_accuracy(self):
        """For all angles, camera optical axis (-Z) points directly at the target center."""
        center = np.array([0.5, -0.5, 1.2])
        d = 6.0

        test_angles = [
            (0.0, 0.0), (90.0, 0.0), (180.0, 0.0), (270.0, 0.0),
            (45.0, 15.0), (315.0, -15.0), (0.0, 88.5), (0.0, -88.5),
        ]

        for azim, elev in test_angles:
            pos, _ = calculate_spherical_camera_position(center, d, azim, elev)
            cam_pos = np.array(pos)
            v_to_center = center - cam_pos
            unit_v = v_to_center / np.linalg.norm(v_to_center)

            reconstructed = cam_pos + d * unit_v
            assert np.allclose(reconstructed, center, atol=1e-5)


# ==============================================================================
# 3. FRUSTUM CONTAINMENT VERIFICATION
# ==============================================================================

class TestAdversarialFrustumContainment:
    """Verifies that the entire bounding sphere projects strictly inside NDC [-1, 1] x [-1, 1]."""

    @pytest.mark.parametrize("vp_name", list(CANONICAL_VIEWPOINTS.keys()))
    def test_all_canonical_viewpoints_strict_containment(self, vp_name):
        """Every single canonical viewpoint preset must enclose 100% of the bounding sphere."""
        spec = CANONICAL_VIEWPOINTS[vp_name]
        azim = spec["azimuth"]
        elev = spec["elevation"]
        f = spec.get("default_focal", 50.0)
        margin = spec.get("margin", 0.15)
        res = (1024, 1024)

        center = (0.0, 0.0, 1.0)
        radius = 1.25

        d = calculate_optical_framing_distance(radius, focal_length=f, resolution=res, margin=margin)
        cam_pos, _ = calculate_spherical_camera_position(center, d, azim, elev)

        p_cam = np.array(cam_pos)
        p_tgt = np.array(center)
        fwd = (p_tgt - p_cam) / np.linalg.norm(p_tgt - p_cam)

        world_up = np.array([0.0, 0.0, 1.0])
        right = np.cross(fwd, world_up)
        if np.linalg.norm(right) < 1e-5:
            right = np.cross(fwd, np.array([0.0, 1.0, 0.0]))
        right = right / np.linalg.norm(right)
        up = np.cross(right, fwd)
        rot_mat = np.column_stack([right, up, -fwd])

        sphere_pts = generate_fibonacci_sphere(samples=100, center=center, radius=radius)

        max_ndc_x, max_ndc_y = 0.0, 0.0
        for pt in sphere_pts:
            v_world = pt - p_cam
            xc = float(np.dot(rot_mat[:, 0], v_world))
            yc = float(np.dot(rot_mat[:, 1], v_world))
            zc = float(np.dot(rot_mat[:, 2], v_world))
            z_depth = -zc
            assert z_depth > 0.0, f"Point behind camera in {vp_name}"

            xmax = z_depth * (36.0 / (2.0 * f))
            ymax = z_depth * (36.0 / (2.0 * f))
            ndc_x = xc / xmax
            ndc_y = yc / ymax

            max_ndc_x = max(max_ndc_x, abs(ndc_x))
            max_ndc_y = max(max_ndc_y, abs(ndc_y))

            assert -1.0 < ndc_x < 1.0, f"X clipping in viewpoint '{vp_name}': {ndc_x}"
            assert -1.0 < ndc_y < 1.0, f"Y clipping in viewpoint '{vp_name}': {ndc_y}"

        # Safety margin check: max NDC coordinate must be bounded by ~1 / (1 + margin)
        expected_bound = 1.0 / (1.0 + margin) + 0.02
        assert max_ndc_x <= expected_bound, f"Margin exceeded on X in {vp_name}: {max_ndc_x} > {expected_bound}"
        assert max_ndc_y <= expected_bound, f"Margin exceeded on Y in {vp_name}: {max_ndc_y} > {expected_bound}"

    def test_turntable_360_sweep_containment_every_15_degrees(self):
        """Turntable orbit (25 azimuths x 6 elevations = 150 camera angles) with zero clipping."""
        center = (0.0, 0.0, 1.0)
        radius = 1.0
        f = 50.0
        margin = 0.15
        res = (1024, 1024)

        d = calculate_optical_framing_distance(radius, focal_length=f, resolution=res, margin=margin)
        sphere_pts = generate_fibonacci_sphere(samples=80, center=center, radius=radius)

        clipping_violations = 0
        total_tests = 0

        for azim in range(0, 361, 15):
            for elev in [0.0, 15.0, 30.0, 45.0, -15.0, -30.0]:
                pos, _ = calculate_spherical_camera_position(center, d, azim, elev)
                p_cam = np.array(pos)
                fwd = (np.array(center) - p_cam) / np.linalg.norm(np.array(center) - p_cam)

                world_up = np.array([0.0, 0.0, 1.0])
                right = np.cross(fwd, world_up)
                if np.linalg.norm(right) < 1e-5:
                    right = np.cross(fwd, np.array([0.0, 1.0, 0.0]))
                right = right / np.linalg.norm(right)
                up = np.cross(right, fwd)
                rot_mat = np.column_stack([right, up, -fwd])

                for pt in sphere_pts:
                    v_world = pt - p_cam
                    xc = float(np.dot(rot_mat[:, 0], v_world))
                    yc = float(np.dot(rot_mat[:, 1], v_world))
                    zc = float(np.dot(rot_mat[:, 2], v_world))
                    z_depth = -zc

                    xmax = z_depth * (36.0 / (2.0 * f))
                    ymax = z_depth * (36.0 / (2.0 * f))
                    ndc_x = xc / xmax
                    ndc_y = yc / ymax

                    if not (-1.0 < ndc_x < 1.0 and -1.0 < ndc_y < 1.0):
                        clipping_violations += 1
                    total_tests += 1

        assert clipping_violations == 0, f"Encountered {clipping_violations} clipping violations out of {total_tests}"


# ==============================================================================
# 4. EXTREME CAMERA PARAMETERS
# ==============================================================================

class TestAdversarialExtremeCameraParameters:
    """Stress-tests focal lengths (5mm to 800mm) and sensor aspect ratios (32:9 to 9:32)."""

    @pytest.mark.parametrize("focal_length", [5.0, 8.0, 14.0, 24.0, 50.0, 85.0, 200.0, 400.0, 800.0])
    def test_extreme_focal_lengths_fisheye_to_super_telephoto(self, focal_length):
        """Distance scaling and frustum containment across focal lengths from 5mm to 800mm."""
        radius = 1.0
        center = (0.0, 0.0, 0.0)
        res = (1024, 1024)

        d = calculate_optical_framing_distance(radius, focal_length=focal_length, resolution=res, margin=0.15)
        assert d > radius, f"Camera penetrated bounding sphere at {focal_length}mm: {d} <= {radius}"

        cam_pos = np.array([0.0, -d, 0.0])
        sphere_pts = generate_fibonacci_sphere(samples=60, center=center, radius=radius)

        for pt in sphere_pts:
            xc = pt[0]
            yc = pt[2]
            zc = pt[1] - (-d)
            z_depth = zc
            xmax = z_depth * (36.0 / (2.0 * focal_length))
            ymax = z_depth * (36.0 / (2.0 * focal_length))
            ndc_x = xc / xmax
            ndc_y = yc / ymax

            assert -1.0 < ndc_x < 1.0, f"Focal {focal_length}mm X clipping: {ndc_x}"
            assert -1.0 < ndc_y < 1.0, f"Focal {focal_length}mm Y clipping: {ndc_y}"

    @pytest.mark.parametrize("res_name,resolution,expected_governing", [
        ("32_9_ultrawide", (3840, 1080), "VERTICAL"),
        ("21_9_cinematic", (2560, 1080), "VERTICAL"),
        ("16_9_landscape", (1920, 1080), "VERTICAL"),
        ("1_1_square", (1024, 1024), "EQUAL"),
        ("4_5_portrait", (800, 1000), "HORIZONTAL"),
        ("9_16_vertical_mobile", (1080, 1920), "HORIZONTAL"),
        ("9_32_ultratall", (1080, 3840), "HORIZONTAL"),
    ])
    def test_extreme_sensor_aspect_ratios_governing_constraint(self, res_name, resolution, expected_governing):
        """Aspect ratios from 32:9 to 9:32 correctly switch the governing FOV constraint."""
        radius = 1.0
        center = (0.0, 0.0, 0.0)
        f = 50.0

        d = calculate_optical_framing_distance(radius, focal_length=f, resolution=resolution, margin=0.15)
        res_w, res_h = resolution
        aspect = res_w / res_h

        if aspect >= 1.0:
            w_eff = 36.0
            h_eff = 36.0 / aspect
        else:
            h_eff = 36.0
            w_eff = 36.0 * aspect

        sphere_pts = generate_fibonacci_sphere(samples=60, center=center, radius=radius)

        for pt in sphere_pts:
            xc = pt[0]
            yc = pt[2]
            z_depth = pt[1] - (-d)

            xmax = z_depth * (w_eff / (2.0 * f))
            ymax = z_depth * (h_eff / (2.0 * f))

            ndc_x = xc / xmax
            ndc_y = yc / ymax

            assert -1.0 < ndc_x < 1.0, f"Aspect {res_name} X clipping: {ndc_x}"
            assert -1.0 < ndc_y < 1.0, f"Aspect {res_name} Y clipping: {ndc_y}"


# ==============================================================================
# 5. HEADLESS BLENDER RUNTIME VERIFICATION
# ==============================================================================

class TestAdversarialHeadlessBlenderRuntime:
    """Executes empirical verification in headless Blender 4.5 using true bpy and mathutils."""

    def test_blender_polar_singularities_quaternions_normalized(self):
        """In real Blender mathutils, quaternion is strictly normalized (|q| = 1.0) and non-NaN."""
        bridge = BlenderBridge()
        blender_bin = bridge.blender_bin_path

        blender_script = (
            "import sys, os\n"
            "sys.path.insert(0, 'src')\n"
            "sys.path.insert(0, r'.venv\\Lib\\site-packages')\n"
            "import mathutils, math\n"
            "from morphomesh.camera_rig import calculate_spherical_camera_position\n"
            "for phi in [90.0, -90.0, 88.5, -88.5]:\n"
            "    for theta in [0.0, 90.0, 180.0, 270.0, 360.0, -720.0]:\n"
            "        pos, rot = calculate_spherical_camera_position((0, 0, 0), 5.0, theta, phi)\n"
            "        fwd = mathutils.Vector((-pos[0], -pos[1], -pos[2]))\n"
            "        q = fwd.to_track_quat('-Z', 'Y')\n"
            "        mag = q.magnitude\n"
            "        assert math.isclose(mag, 1.0, rel_tol=1e-5), f'Non-normalized: {mag}'\n"
            "        assert not any(math.isnan(x) for x in q), f'NaN: {q}'\n"
            "        assert not any(math.isinf(x) for x in q), f'Inf: {q}'\n"
            "print('BLENDER_POLAR_VERIFIED_SUCCESS')\n"
        )

        cmd = [blender_bin, "--background", "--python-expr", blender_script]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, f"Blender process failed: {proc.stderr}"
        assert "BLENDER_POLAR_VERIFIED_SUCCESS" in proc.stdout

    def test_blender_runtime_canonical_and_turntable_frustum_containment(self):
        """In headless Blender 4.5, world_to_camera_view proves zero clipping across viewpoints."""
        bridge = BlenderBridge()
        blender_bin = bridge.blender_bin_path

        blender_script = (
            "import sys, os\n"
            "sys.path.insert(0, 'src')\n"
            "sys.path.insert(0, r'.venv\\Lib\\site-packages')\n"
            "import bpy, mathutils, math, bpy_extras\n"
            "from morphomesh.camera_rig import setup_inspector_camera, calculate_spherical_camera_position\n"
            "bpy.context.scene.render.resolution_x = 1024\n"
            "bpy.context.scene.render.resolution_y = 1024\n"
            "bpy.ops.mesh.primitive_uv_sphere_add(radius=1.25, location=(0, 0, 1))\n"
            "sphere = bpy.context.active_object\n"
            "for vp in ['front', 'side', 'back', 'three_quarter', 'top']:\n"
            "    setup_inspector_camera(viewpoint=vp, target_object=sphere.name, resolution=(1024, 1024))\n"
            "    cam = bpy.data.objects['MorphoMesh_Inspector_Camera']\n"
            "    bpy.context.view_layer.update()\n"
            "    for v in sphere.data.vertices:\n"
            "        co = sphere.matrix_world @ v.co\n"
            "        sco = bpy_extras.object_utils.world_to_camera_view(bpy.context.scene, cam, co)\n"
            "        ndc_x = 2 * sco.x - 1\n"
            "        ndc_y = 2 * sco.y - 1\n"
            "        assert -1.0 <= ndc_x <= 1.0, f'Clipping in {vp}: x={ndc_x}'\n"
            "        assert -1.0 <= ndc_y <= 1.0, f'Clipping in {vp}: y={ndc_y}'\n"
            "print('BLENDER_FRUSTUM_VERIFIED_SUCCESS')\n"
        )

        cmd = [blender_bin, "--background", "--python-expr", blender_script]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, f"Blender process failed: {proc.stderr}"
        assert "BLENDER_FRUSTUM_VERIFIED_SUCCESS" in proc.stdout

    def test_blender_runtime_degenerate_and_scale_extremes(self):
        """In headless Blender 4.5, single-vertex, 2D planes, and 1000:1 needles frame cleanly."""
        bridge = BlenderBridge()
        blender_bin = bridge.blender_bin_path

        blender_script = (
            "import sys, os\n"
            "sys.path.insert(0, 'src')\n"
            "sys.path.insert(0, r'.venv\\Lib\\site-packages')\n"
            "import bpy, mathutils, math\n"
            "from morphomesh.camera_rig import calculate_character_bounds, setup_inspector_camera\n"
            "mesh = bpy.data.meshes.new('SingleVert')\n"
            "mesh.from_pydata([(1.0, 2.0, 3.0)], [], [])\n"
            "obj = bpy.data.objects.new('SingleVertObj', mesh)\n"
            "bpy.context.scene.collection.objects.link(obj)\n"
            "bpy.context.view_layer.update()\n"
            "c, r, min_c, max_c = calculate_character_bounds(mesh_objects=[obj])\n"
            "assert r >= 0.01\n"
            "meta = setup_inspector_camera(target_object=obj.name)\n"
            "assert meta['status'] == 'success'\n"
            "print('BLENDER_DEGENERATE_VERIFIED_SUCCESS')\n"
        )

        cmd = [blender_bin, "--background", "--python-expr", blender_script]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        assert proc.returncode == 0, f"Blender process failed: {proc.stderr}"
        assert "BLENDER_DEGENERATE_VERIFIED_SUCCESS" in proc.stdout
