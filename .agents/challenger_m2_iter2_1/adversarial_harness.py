"""
MorphoMesh: Milestone 2 Iteration 2 Adversarial Test Harness.
Agent: Challenger M2 Iteration 2 - 1 (Look-at Ray & Gimbal Lock Adversarial Challenger)
Parent Orchestrator ID: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9

Empirically tests:
1. Ray target collision across 72+ spherical viewpoints (theta in 0..360 deg every 15 deg,
   phi in [-80, -45, 0, 15, 45, 88] deg). Reconstructed target must have error < 1e-5m for every angle.
2. Bit-for-bit Euler angle parity against Blender's mathutils.Vector.to_track_quat('-Z', 'Y').to_euler('XYZ')
   on key viewpoints ('three_quarter', 'top', 'bottom', 'front', 'side', 'back').
3. Hierarchy bounds solver across deeply nested hierarchies:
   Armature -> Empty -> Empty -> 3 Child Meshes with offset world transforms in both mock and Blender 4.5.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
from typing import Any, Dict, List, Tuple

import numpy as np

# Ensure src is in python path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from morphomesh.camera_rig import (
    CANONICAL_VIEWPOINTS,
    calculate_hierarchy_bounds,
    calculate_spherical_camera_position,
    setup_inspector_camera,
)

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"


def test_1_ray_target_collision_standalone() -> Dict[str, Any]:
    """
    Stress-tests ray collision in standalone Python pure math environment.
    Grid: theta in 0..360 every 15 deg (25 values), phi in [-80, -45, 0, 15, 45, 88] (6 values).
    Total: 150 spherical viewpoints (well exceeding 72).
    """
    print("\n--- Test 1.1: Standalone Pure-Python Ray Collision Grid ---")
    target = (3.14159, -2.71828, 1.41421)
    distance = 6.28318
    phis = [-80.0, -45.0, 0.0, 15.0, 45.0, 88.0]
    thetas = [i * 15.0 for i in range(25)]

    max_err = 0.0
    worst_case = None
    count = 0
    passed = 0

    for phi in phis:
        for theta in thetas:
            count += 1
            cam_pos, cam_rot = calculate_spherical_camera_position(target, distance, theta, phi)
            R = np.array(cam_rot.to_matrix())[:3, :3]
            forward_ray = R @ np.array([0.0, 0.0, -1.0])
            reconstructed_tgt = np.array(cam_pos) + distance * forward_ray
            err = float(np.linalg.norm(reconstructed_tgt - np.array(target)))

            if err > max_err:
                max_err = err
                worst_case = (theta, phi, err)

            assert err < 1e-5, f"Ray missed target at theta={theta}, phi={phi}: err={err}"
            passed += 1

    print(f"Standalone: {passed}/{count} viewpoints PASSED. Max error: {max_err:.3e}m. Worst case: {worst_case}")
    return {
        "status": "PASS" if passed == count else "FAIL",
        "total": count,
        "passed": passed,
        "max_error_m": max_err,
        "worst_case": worst_case,
    }


def test_1_ray_target_collision_blender() -> Dict[str, Any]:
    """
    Stress-tests ray collision in real headless Blender 4.5 C-engine mathutils.
    Grid: theta in 0..360 every 15 deg (25 values), phi in [-80, -45, 0, 15, 45, 88] (6 values).
    Total: 150 spherical viewpoints.
    """
    print("\n--- Test 1.2: Headless Blender 4.5 C-Engine Ray Collision Grid ---")
    script = """
import sys, os, json, math
import numpy as np
sys.path.insert(0, 'src')
import mathutils
from morphomesh.camera_rig import calculate_spherical_camera_position

target = (3.14159, -2.71828, 1.41421)
distance = 6.28318
phis = [-80.0, -45.0, 0.0, 15.0, 45.0, 88.0]
thetas = [i * 15.0 for i in range(25)]

max_err = 0.0
worst_case = None
count = 0
passed = 0

for phi in phis:
    for theta in thetas:
        count += 1
        cam_pos, cam_rot = calculate_spherical_camera_position(target, distance, theta, phi)
        R = np.array(cam_rot.to_matrix())[:3, :3]
        forward_ray = R @ np.array([0.0, 0.0, -1.0])
        reconstructed_tgt = np.array(cam_pos) + distance * forward_ray
        err = float(np.linalg.norm(reconstructed_tgt - np.array(target)))

        if err > max_err:
            max_err = err
            worst_case = (theta, phi, err)

        if err >= 1e-5:
            print(f"FAIL at theta={theta}, phi={phi}: err={err}")
        else:
            passed += 1

out = {
    "total": count,
    "passed": passed,
    "max_error_m": max_err,
    "worst_case": worst_case,
    "status": "PASS" if passed == count else "FAIL"
}
print("__BLENDER_JSON_RESULT__:" + json.dumps(out))
"""
    cmd = [BLENDER_EXE, "--background", "--python-expr", script]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=REPO_ROOT)
    assert proc.returncode == 0, f"Blender failed: {proc.stderr}"

    for line in proc.stdout.splitlines():
        if line.startswith("__BLENDER_JSON_RESULT__:"):
            data = json.loads(line.split("__BLENDER_JSON_RESULT__:")[1])
            print(f"Blender: {data['passed']}/{data['total']} viewpoints PASSED. Max error: {data['max_error_m']:.3e}m. Worst case: {data['worst_case']}")
            return data
    raise RuntimeError("Failed to parse Blender JSON output")


def test_2_euler_angle_parity_blender() -> Dict[str, Any]:
    """
    Tests bit-for-bit Euler angle parity inside Blender 4.5 comparing camera_rig.py
    against Blender's mathutils.Vector.to_track_quat('-Z', 'Y').to_euler('XYZ')
    on key viewpoints: three_quarter, top, bottom, front, side, back.
    """
    print("\n--- Test 2: Bit-for-bit Euler Angle Parity in Blender 4.5 ---")
    script = """
import sys, os, json, math
sys.path.insert(0, 'src')
import mathutils
from morphomesh.camera_rig import setup_inspector_camera, calculate_spherical_camera_position, CANONICAL_VIEWPOINTS

key_viewpoints = [
    ("three_quarter", 45.0, 15.0),
    ("top", 0.0, 88.0),
    ("bottom", 0.0, -88.0),
    ("front", 0.0, 0.0),
    ("side", 90.0, 0.0),
    ("back", 180.0, 0.0),
]

center = (0.5, -0.5, 1.0)
dist = 5.0
results = []

all_bit_identical = True

for name, az, el in key_viewpoints:
    pos, rot = calculate_spherical_camera_position(center, dist, az, el)
    fwd = mathutils.Vector((center[0] - pos[0], center[1] - pos[1], center[2] - pos[2]))
    ref_rot = fwd.to_track_quat('-Z', 'Y').to_euler('XYZ')

    rot_list = [float(r) for r in rot]
    ref_list = [float(r) for r in ref_rot]
    diff = [abs(a - b) for a, b in zip(rot_list, ref_list)]
    max_diff = max(diff)
    is_bit_id = (rot_list == ref_list)

    if not is_bit_id:
        all_bit_identical = False

    results.append({
        "viewpoint": name,
        "azimuth": az,
        "elevation": el,
        "camera_rig_euler": rot_list,
        "ref_euler": ref_list,
        "max_diff": max_diff,
        "bit_identical": is_bit_id
    })
    print(f"VP {name:15}: rig_euler={rot_list}, ref_euler={ref_list}, bit_identical={is_bit_id}")

out = {
    "status": "PASS" if all_bit_identical else "FAIL",
    "all_bit_identical": all_bit_identical,
    "details": results
}
print("__EULER_JSON_RESULT__:" + json.dumps(out))
"""
    cmd = [BLENDER_EXE, "--background", "--python-expr", script]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=REPO_ROOT)
    assert proc.returncode == 0, f"Blender failed: {proc.stderr}"

    for line in proc.stdout.splitlines():
        if line.startswith("__EULER_JSON_RESULT__:"):
            data = json.loads(line.split("__EULER_JSON_RESULT__:")[1])
            print(f"Bit-for-bit Euler parity all passed: {data['all_bit_identical']}")
            return data
    raise RuntimeError("Failed to parse Euler JSON output")


def test_3_hierarchy_bounds_solver_mock() -> Dict[str, Any]:
    """
    Stress-tests hierarchy bounds solver in pure-Python mock:
    Constructs deeply nested hierarchy: Armature -> Empty1 -> Empty2 -> 3 Child Meshes with offset transforms.
    """
    print("\n--- Test 3.1: Deeply Nested Hierarchy Bounds in Mock ---")
    from morphomesh.camera_rig import Matrix, Vector

    class MockMesh:
        def __init__(self, name, min_pt, max_pt, mat_world):
            self.name = name
            self.type = 'MESH'
            min_x, min_y, min_z = min_pt
            max_x, max_y, max_z = max_pt
            self.bound_box = [
                (min_x, min_y, min_z), (min_x, min_y, max_z),
                (min_x, max_y, max_z), (min_x, max_y, min_z),
                (max_x, min_y, min_z), (max_x, min_y, max_z),
                (max_x, max_y, max_z), (max_x, max_y, min_z),
            ]
            self.matrix_world = mat_world

    class MockParent:
        def __init__(self, name, obj_type, children):
            self.name = name
            self.type = obj_type
            self.children = children
            self.bound_box = None

    # Mesh 1: translated (12.0, -3.0, 4.0)
    m1 = MockMesh('ChildMesh1', (-0.5, -0.5, -1.0), (0.5, 0.5, 1.0), Matrix([
        [1, 0, 0, 12.0],
        [0, 1, 0, -3.0],
        [0, 0, 1, 4.0],
        [0, 0, 0, 1]
    ]))

    # Mesh 2: scaled 3x and translated (-5.0, 8.0, 0.0)
    m2 = MockMesh('ChildMesh2', (-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), Matrix([
        [3, 0, 0, -5.0],
        [0, 3, 0, 8.0],
        [0, 0, 3, 0.0],
        [0, 0, 0, 1]
    ]))

    # Mesh 3: rotated 30 deg around Z and translated (0.0, 0.0, -10.0)
    cos30 = math.cos(math.radians(30))
    sin30 = math.sin(math.radians(30))
    m3 = MockMesh('ChildMesh3', (-2.0, -0.5, -0.5), (2.0, 0.5, 0.5), Matrix([
        [cos30, -sin30, 0, 0.0],
        [sin30,  cos30, 0, 0.0],
        [0,      0,     1, -10.0],
        [0,      0,     0, 1]
    ]))

    empty2 = MockParent('Empty2', 'EMPTY', [m1, m2, m3])
    empty1 = MockParent('Empty1', 'EMPTY', [empty2])
    armature = MockParent('ArmatureRoot', 'ARMATURE', [empty1])

    center, radius, min_pt, max_pt = calculate_hierarchy_bounds([armature])

    # Assert all vertices of all meshes are strictly enclosed
    violations = []
    total_corners = 0
    for m in [m1, m2, m3]:
        for corner in m.bound_box:
            total_corners += 1
            wc = m.matrix_world @ corner
            for i in range(3):
                if wc[i] < min_pt[i] - 1e-5 or wc[i] > max_pt[i] + 1e-5:
                    violations.append((m.name, corner, list(wc)))

    assert len(violations) == 0, f"Found {len(violations)} bounding box violations in mock: {violations}"
    print(f"Mock: Deeply nested hierarchy passed! All {total_corners} corners enclosed.")
    print(f"      Center: {[round(c, 4) for c in center]}, Radius: {round(radius, 4)}")
    print(f"      Min: {[round(c, 4) for c in min_pt]}, Max: {[round(c, 4) for c in max_pt]}")

    return {
        "status": "PASS",
        "total_corners_tested": total_corners,
        "violations": len(violations),
        "center": list(center),
        "radius": radius,
        "min_corner": list(min_pt),
        "max_corner": list(max_pt),
    }


def test_3_hierarchy_bounds_solver_blender() -> Dict[str, Any]:
    """
    Stress-tests hierarchy bounds solver in real headless Blender 4.5:
    Constructs real Armature -> Empty1 -> Empty2 -> 3 Child Meshes with offset local/world transforms.
    """
    print("\n--- Test 3.2: Deeply Nested Hierarchy Bounds in Blender 4.5 ---")
    script = """
import sys, os, json, math
sys.path.insert(0, 'src')
import bpy, mathutils
from morphomesh.camera_rig import calculate_hierarchy_bounds

# Reset factory scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# 1. Armature Root at (2.0, -1.0, 3.0)
arm_data = bpy.data.armatures.new('RigArmatureData')
arm_obj = bpy.data.objects.new('RigRoot', arm_data)
bpy.context.scene.collection.objects.link(arm_obj)
arm_obj.location = (2.0, -1.0, 3.0)

# 2. Empty 1 parented to Armature at local (1.5, 0.0, 0.0)
empty1 = bpy.data.objects.new('Empty1', None)
bpy.context.scene.collection.objects.link(empty1)
empty1.parent = arm_obj
empty1.location = (1.5, 0.0, 0.0)

# 3. Empty 2 parented to Empty 1 at local (0.0, 2.5, -1.0)
empty2 = bpy.data.objects.new('Empty2', None)
bpy.context.scene.collection.objects.link(empty2)
empty2.parent = empty1
empty2.location = (0.0, 2.5, -1.0)

# 4. Mesh 1 (Cube) parented to Empty 2 at local (4.0, 0.0, 0.0)
mesh1 = bpy.data.objects.new('ChildMesh1', bpy.data.meshes.new('Mesh1'))
bpy.context.scene.collection.objects.link(mesh1)
mesh1.parent = empty2
mesh1.location = (4.0, 0.0, 0.0)
bpy.ops.mesh.primitive_cube_add(size=2.0, location=(0, 0, 0))
cube = bpy.context.active_object
mesh1.data = cube.data
bpy.data.objects.remove(cube)

# 5. Mesh 2 (UV Sphere) parented to Empty 2 at local (0.0, -5.0, 2.0) with non-uniform scale
mesh2 = bpy.data.objects.new('ChildMesh2', bpy.data.meshes.new('Mesh2'))
bpy.context.scene.collection.objects.link(mesh2)
mesh2.parent = empty2
mesh2.location = (0.0, -5.0, 2.0)
mesh2.scale = (1.5, 2.0, 0.8)
bpy.ops.mesh.primitive_uv_sphere_add(radius=1.2, location=(0, 0, 0))
sphere = bpy.context.active_object
mesh2.data = sphere.data
bpy.data.objects.remove(sphere)

# 6. Mesh 3 (Cylinder) parented to Empty 2 at local (-2.0, 3.0, -4.0) with rotation
mesh3 = bpy.data.objects.new('ChildMesh3', bpy.data.meshes.new('Mesh3'))
bpy.context.scene.collection.objects.link(mesh3)
mesh3.parent = empty2
mesh3.location = (-2.0, 3.0, -4.0)
mesh3.rotation_euler = (math.radians(30), math.radians(45), 0.0)
bpy.ops.mesh.primitive_cylinder_add(radius=0.8, depth=2.5, location=(0, 0, 0))
cyl = bpy.context.active_object
mesh3.data = cyl.data
bpy.data.objects.remove(cyl)

bpy.context.view_layer.update()

# Run solver passing Armature root
center, radius, min_pt, max_pt = calculate_hierarchy_bounds(mesh_objects=[arm_obj])

# Verify enclosure of all vertices across all 3 meshes
violations = []
total_vertices = 0
for m in [mesh1, mesh2, mesh3]:
    for v in m.data.vertices:
        total_vertices += 1
        wc = m.matrix_world @ v.co
        for i in range(3):
            if wc[i] < min_pt[i] - 1e-4 or wc[i] > max_pt[i] + 1e-4:
                violations.append((m.name, list(v.co), list(wc)))

out = {
    "status": "PASS" if len(violations) == 0 else "FAIL",
    "total_vertices_tested": total_vertices,
    "violations": len(violations),
    "center": [round(float(c), 4) for c in center],
    "radius": round(float(radius), 4),
    "min_corner": [round(float(c), 4) for c in min_pt],
    "max_corner": [round(float(c), 4) for c in max_pt]
}
print("__BLENDER_HIERARCHY_RESULT__:" + json.dumps(out))
"""
    cmd = [BLENDER_EXE, "--background", "--python-expr", script]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=REPO_ROOT)
    assert proc.returncode == 0, f"Blender failed: {proc.stderr}"

    for line in proc.stdout.splitlines():
        if line.startswith("__BLENDER_HIERARCHY_RESULT__:"):
            data = json.loads(line.split("__BLENDER_HIERARCHY_RESULT__:")[1])
            print(f"Blender: Deeply nested hierarchy passed! All {data['total_vertices_tested']} vertices enclosed. Violations: {data['violations']}")
            print(f"         Center: {data['center']}, Radius: {data['radius']}")
            print(f"         Min: {data['min_corner']}, Max: {data['max_corner']}")
            return data
    raise RuntimeError("Failed to parse Blender hierarchy JSON output")


def main():
    print("================================================================================")
    print("STARTING ADVERSARIAL CHALLENGER VERIFICATION (M2 ITERATION 2 - 1)")
    print("================================================================================")

    results = {}

    # Test 1: Ray target collision
    res_1_1 = test_1_ray_target_collision_standalone()
    res_1_2 = test_1_ray_target_collision_blender()
    results["test_1_ray_collision_standalone"] = res_1_1
    results["test_1_ray_collision_blender"] = res_1_2

    # Test 2: Bit-for-bit Euler angle parity
    res_2 = test_2_euler_angle_parity_blender()
    results["test_2_euler_angle_parity"] = res_2

    # Test 3: Deeply nested hierarchy bounds solver
    res_3_1 = test_3_hierarchy_bounds_solver_mock()
    res_3_2 = test_3_hierarchy_bounds_solver_blender()
    results["test_3_hierarchy_bounds_mock"] = res_3_1
    results["test_3_hierarchy_bounds_blender"] = res_3_2

    # Overall Verdict
    all_passed = (
        res_1_1["status"] == "PASS"
        and res_1_2["status"] == "PASS"
        and res_2["status"] == "PASS"
        and res_3_1["status"] == "PASS"
        and res_3_2["status"] == "PASS"
    )

    verdict = "APPROVE" if all_passed else "REJECT"

    print("\n================================================================================")
    print(f"OVERALL EMPIRICAL VERDICT: {verdict}")
    print("================================================================================")

    # Save results to json for reporting
    res_path = os.path.join(os.path.dirname(__file__), "adversarial_results.json")
    with open(res_path, "w") as f:
        json.dump({"verdict": verdict, "results": results}, f, indent=2)
    print(f"Detailed results written to {res_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
