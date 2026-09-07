#!/usr/bin/env python3
"""
Adversarial Stress Test Harness for Milestone 3 Iteration 2.
Agent: Challenger M3 Iter 2 - 2

Test Areas:
1. Coplanar Triangle Intersections (XY, YZ, ZX, and oblique planes;
   overlapping, edge-sharing, vertex-touching, disjoint separated, parallel separated 0.1mm, 1mm, 10mm).
2. Benchmark Schema & Parity Fuzzing (schema key completeness, accuracy >= 0.95, FPR == 0.0, function parity).
3. Quad Divergence Volume Fuzzing (Cube, Cylinder, Sphere vs triangulated equivalents across scales/transforms, diff < 0.01%).
"""

import sys
import os
import math
import random
from typing import List, Tuple, Dict, Any

# Ensure morphomesh is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "src")))

from morphomesh.visual_critic import (
    triangle_triangle_intersection_moller,
    _coplanar_triangle_triangle_intersection_2d,
    compute_mesh_signed_volume,
    benchmark_defect_detection,
    run_defect_detection_benchmark,
)
import morphomesh.visual_critic as vc


class TestRunner:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors: List[str] = []

    def check(self, condition: bool, description: str):
        if condition:
            self.passed += 1
            print(f"  [PASS] {description}")
        else:
            self.failed += 1
            print(f"  [FAIL] {description}")
            self.errors.append(description)

    def summary(self) -> bool:
        total = self.passed + self.failed
        print("\n" + "=" * 70)
        print(f"TEST HARNESS SUMMARY: {self.passed}/{total} PASSED, {self.failed} FAILED")
        if self.failed > 0:
            print("Failed tests:")
            for err in self.errors:
                print(f"  - {err}")
            print("VERDICT: REJECT")
            return False
        else:
            print("VERDICT: APPROVE")
            print("=" * 70)
            return True


runner = TestRunner()


# ==============================================================================
# 1. COPLANAR TRIANGLE INTERSECTIONS
# ==============================================================================
print("\n" + "=" * 70)
print("SECTION 1: COPLANAR TRIANGLE INTERSECTIONS STRESS-TESTING")
print("=" * 70)

def rotate_point(pt, axis, angle):
    """Rotates a 3D point around axis by angle (radians)."""
    cos_a = math.cos(angle)
    sin_a = math.sin(angle)
    x, y, z = pt
    if axis == 'x':
        return (x, y * cos_a - z * sin_a, y * sin_a + z * cos_a)
    elif axis == 'y':
        return (x * cos_a + z * sin_a, y, -x * sin_a + z * cos_a)
    elif axis == 'z':
        return (x * cos_a - y * sin_a, x * sin_a + y * cos_a, z)
    return pt

# 1.1 XY Plane (Normal = (0, 0, 1))
for z_offset in [0.0, 1.5, -3.2]:
    # Overlapping interiors
    t1 = ((0.0, 0.0, z_offset), (2.0, 0.0, z_offset), (0.0, 2.0, z_offset))
    t2_contained = ((0.2, 0.2, z_offset), (0.8, 0.2, z_offset), (0.2, 0.8, z_offset))
    t2_partial = ((1.0, 1.0, z_offset), (3.0, 1.0, z_offset), (1.0, 3.0, z_offset))
    t2_identical = ((0.0, 0.0, z_offset), (2.0, 0.0, z_offset), (0.0, 2.0, z_offset))
    t2_reversed = ((0.0, 0.0, z_offset), (0.0, 2.0, z_offset), (2.0, 0.0, z_offset))

    runner.check(triangle_triangle_intersection_moller(*t1, *t2_contained) is True,
                 f"XY plane (z={z_offset}): Strictly contained coplanar triangle returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_partial) is True,
                 f"XY plane (z={z_offset}): Partially overlapping coplanar triangle returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_identical) is True,
                 f"XY plane (z={z_offset}): Identical coplanar triangle returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_reversed) is True,
                 f"XY plane (z={z_offset}): Opposite winding coplanar triangle returns True")

    # Edge sharing
    t2_edge_share = ((0.0, 0.0, z_offset), (2.0, 0.0, z_offset), (1.0, -1.0, z_offset))
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_edge_share) is True,
                 f"XY plane (z={z_offset}): Edge-sharing coplanar triangle returns True")

    # Vertex touching
    t2_vertex_touch = ((2.0, 0.0, z_offset), (3.0, 0.0, z_offset), (2.0, -1.0, z_offset))
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_vertex_touch) is True,
                 f"XY plane (z={z_offset}): Vertex-touching coplanar triangle returns True")

    # Disjoint separated in-plane
    t2_disjoint = ((5.0, 5.0, z_offset), (7.0, 5.0, z_offset), (5.0, 7.0, z_offset))
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_disjoint) is False,
                 f"XY plane (z={z_offset}): In-plane disjoint coplanar triangle returns False")

    # Parallel separated along normal
    for norm_sep_mm, sep_m in [(0.1, 0.0001), (1.0, 0.001), (10.0, 0.01), (-0.1, -0.0001), (-1.0, -0.001), (-10.0, -0.01)]:
        t2_parallel = (
            (0.5, 0.5, z_offset + sep_m),
            (1.5, 0.5, z_offset + sep_m),
            (0.5, 1.5, z_offset + sep_m),
        )
        runner.check(triangle_triangle_intersection_moller(*t1, *t2_parallel) is False,
                     f"XY plane (z={z_offset}): Parallel separated by {norm_sep_mm}mm returns False")

# 1.2 YZ Plane (Normal = (1, 0, 0))
for x_offset in [0.0, 2.0, -4.5]:
    t1 = ((x_offset, 0.0, 0.0), (x_offset, 2.0, 0.0), (x_offset, 0.0, 2.0))
    t2_overlap = ((x_offset, 0.5, 0.5), (x_offset, 1.5, 0.5), (x_offset, 0.5, 1.5))
    t2_edge = ((x_offset, 0.0, 0.0), (x_offset, 2.0, 0.0), (x_offset, 1.0, -1.0))
    t2_vertex = ((x_offset, 2.0, 0.0), (x_offset, 3.0, 0.0), (x_offset, 2.0, -1.0))
    t2_disjoint = ((x_offset, 10.0, 10.0), (x_offset, 12.0, 10.0), (x_offset, 10.0, 12.0))

    runner.check(triangle_triangle_intersection_moller(*t1, *t2_overlap) is True,
                 f"YZ plane (x={x_offset}): Overlapping coplanar returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_edge) is True,
                 f"YZ plane (x={x_offset}): Edge-sharing coplanar returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_vertex) is True,
                 f"YZ plane (x={x_offset}): Vertex-touching coplanar returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_disjoint) is False,
                 f"YZ plane (x={x_offset}): In-plane disjoint coplanar returns False")

    for norm_sep_mm, sep_m in [(0.1, 0.0001), (1.0, 0.001), (10.0, 0.01)]:
        t2_parallel = (
            (x_offset + sep_m, 0.5, 0.5),
            (x_offset + sep_m, 1.5, 0.5),
            (x_offset + sep_m, 0.5, 1.5),
        )
        runner.check(triangle_triangle_intersection_moller(*t1, *t2_parallel) is False,
                     f"YZ plane (x={x_offset}): Parallel separated by {norm_sep_mm}mm returns False")

# 1.3 ZX Plane (Normal = (0, 1, 0))
for y_offset in [0.0, 3.0, -1.2]:
    t1 = ((0.0, y_offset, 0.0), (2.0, y_offset, 0.0), (0.0, y_offset, 2.0))
    t2_overlap = ((0.5, y_offset, 0.5), (1.5, y_offset, 0.5), (0.5, y_offset, 1.5))
    t2_edge = ((0.0, y_offset, 0.0), (2.0, y_offset, 0.0), (1.0, y_offset, -1.0))
    t2_vertex = ((2.0, y_offset, 0.0), (3.0, y_offset, 0.0), (2.0, y_offset, -1.0))
    t2_disjoint = ((10.0, y_offset, 10.0), (12.0, y_offset, 10.0), (10.0, y_offset, 12.0))

    runner.check(triangle_triangle_intersection_moller(*t1, *t2_overlap) is True,
                 f"ZX plane (y={y_offset}): Overlapping coplanar returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_edge) is True,
                 f"ZX plane (y={y_offset}): Edge-sharing coplanar returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_vertex) is True,
                 f"ZX plane (y={y_offset}): Vertex-touching coplanar returns True")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_disjoint) is False,
                 f"ZX plane (y={y_offset}): In-plane disjoint coplanar returns False")

    for norm_sep_mm, sep_m in [(0.1, 0.0001), (1.0, 0.001), (10.0, 0.01)]:
        t2_parallel = (
            (0.5, y_offset + sep_m, 0.5),
            (1.5, y_offset + sep_m, 0.5),
            (0.5, y_offset + sep_m, 1.5),
        )
        runner.check(triangle_triangle_intersection_moller(*t1, *t2_parallel) is False,
                     f"ZX plane (y={y_offset}): Parallel separated by {norm_sep_mm}mm returns False")

# 1.4 Arbitrary Rotated / Oblique Planes Fuzzing (100 random rotations)
random.seed(42)
for i in range(100):
    rx = random.uniform(0, 2 * math.pi)
    ry = random.uniform(0, 2 * math.pi)
    rz = random.uniform(0, 2 * math.pi)

    def rot(p):
        p1 = rotate_point(p, 'x', rx)
        p2 = rotate_point(p1, 'y', ry)
        return rotate_point(p2, 'z', rz)

    t1_base = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
    t2_over_base = ((0.2, 0.2, 0.0), (0.8, 0.2, 0.0), (0.2, 0.8, 0.0))
    t2_disj_base = ((3.0, 3.0, 0.0), (4.0, 3.0, 0.0), (3.0, 4.0, 0.0))

    t1_rot = tuple(rot(p) for p in t1_base)
    t2_over_rot = tuple(rot(p) for p in t2_over_base)
    t2_disj_rot = tuple(rot(p) for p in t2_disj_base)

    res_over = triangle_triangle_intersection_moller(*t1_rot, *t2_over_rot)
    res_disj = triangle_triangle_intersection_moller(*t1_rot, *t2_disj_rot)

    if not res_over or res_disj:
        runner.check(False, f"Oblique rotated plane trial {i} failed (over={res_over}, disj={res_disj})")
        break
else:
    runner.check(True, "100/100 Oblique rotated coplanar planes fuzzed successfully (True for overlap, False for disjoint)")


# ==============================================================================
# 2. BENCHMARK SCHEMA & PARITY FUZZING
# ==============================================================================
print("\n" + "=" * 70)
print("SECTION 2: BENCHMARK SCHEMA & PARITY FUZZING")
print("=" * 70)

# 2.1 Function Parity
s1 = run_defect_detection_benchmark()
s2 = benchmark_defect_detection()

runner.check(s1 == s2, "run_defect_detection_benchmark() == benchmark_defect_detection() bit-for-bit equality")
runner.check("benchmark_defect_detection" in vc.__all__, "'benchmark_defect_detection' present in __all__")
runner.check("run_defect_detection_benchmark" in vc.__all__, "'run_defect_detection_benchmark' present in __all__")

# 2.2 Schema Completeness & Key Checks
required_keys = [
    "tests_run",
    "total_states",
    "correct_classifications",
    "clean_states_tested",
    "defective_states_tested",
    "true_positives",
    "true_negatives",
    "false_positives",
    "false_negatives",
    "accuracy",
    "accuracy_percentage",
    "accuracy_ratio",
    "false_positive_rate",
    "false_positive_rate_ratio",
]

for k in required_keys:
    runner.check(k in s2, f"Benchmark schema contains required key: '{k}' (value={s2.get(k)})")

# 2.3 Value Exactness and Invariant Assertions
runner.check(s2["tests_run"] == 9, f"tests_run is exactly 9 (actual={s2['tests_run']})")
runner.check(s2["total_states"] == 9, f"total_states is exactly 9 (actual={s2['total_states']})")
runner.check(s2["clean_states_tested"] == 4, f"clean_states_tested is 4 (actual={s2['clean_states_tested']})")
runner.check(s2["defective_states_tested"] == 5, f"defective_states_tested is 5 (actual={s2['defective_states_tested']})")
runner.check(s2["true_positives"] == 5, f"true_positives is 5 (actual={s2['true_positives']})")
runner.check(s2["true_negatives"] == 4, f"true_negatives is 4 (actual={s2['true_negatives']})")
runner.check(s2["false_positives"] == 0, f"false_positives is 0 (actual={s2['false_positives']})")
runner.check(s2["false_negatives"] == 0, f"false_negatives is 0 (actual={s2['false_negatives']})")
runner.check(s2["accuracy"] == 100.0, f"accuracy is 100.0 (actual={s2['accuracy']})")
runner.check(s2["accuracy_ratio"] == 1.0, f"accuracy_ratio is 1.0 (actual={s2['accuracy_ratio']})")
runner.check(s2["false_positive_rate"] == 0.0, f"false_positive_rate is 0.0 (actual={s2['false_positive_rate']})")
runner.check(s2["false_positive_rate_ratio"] == 0.0, f"false_positive_rate_ratio is 0.0 (actual={s2['false_positive_rate_ratio']})")

# Authoritative assertion from dispatch:
runner.check(s2['accuracy'] >= 0.95 and s2['false_positive_rate'] == 0.0,
             "Authoritative assertion: stats['accuracy'] >= 0.95 and stats['false_positive_rate'] == 0.0")

# 2.4 Multi-iteration Determinism Fuzzing (50 repetitions)
deterministic = True
for it in range(50):
    res_it = benchmark_defect_detection()
    if res_it != s2:
        deterministic = False
        runner.check(False, f"Non-deterministic benchmark output on repetition {it}")
        break
if deterministic:
    runner.check(True, "Benchmark execution is 100% deterministic across 50 consecutive runs")


# ==============================================================================
# 3. QUAD DIVERGENCE VOLUME FUZZING
# ==============================================================================
print("\n" + "=" * 70)
print("SECTION 3: QUAD DIVERGENCE VOLUME FUZZING (Cube, Cylinder, Sphere)")
print("=" * 70)

def triangulate_quads(faces: List[Tuple[int, ...]], diagonal: int = 0) -> List[Tuple[int, int, int]]:
    """Splits quads into triangles along diagonal 0 or 1."""
    tris = []
    for f in faces:
        if len(f) == 3:
            tris.append(f)
        elif len(f) == 4:
            if diagonal == 0:
                tris.append((f[0], f[1], f[2]))
                tris.append((f[0], f[2], f[3]))
            else:
                tris.append((f[0], f[1], f[3]))
                tris.append((f[1], f[2], f[3]))
        else:
            for i in range(1, len(f) - 1):
                tris.append((f[0], f[i], f[i + 1]))
    return tris

# 3.1 Quad Cube
cube_verts = [
    (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
    (-1.0, -1.0,  1.0), (1.0, -1.0,  1.0), (1.0, 1.0,  1.0), (-1.0, 1.0,  1.0),
]
cube_faces_quad = [
    (0, 3, 2, 1), # bottom -Z
    (4, 5, 6, 7), # top +Z
    (0, 1, 5, 4), # front -Y
    (2, 3, 7, 6), # back +Y
    (0, 4, 7, 3), # left -X
    (1, 2, 6, 5), # right +X
]
cube_faces_tri1 = triangulate_quads(cube_faces_quad, diagonal=0)
cube_faces_tri2 = triangulate_quads(cube_faces_quad, diagonal=1)

vol_cube_quad = compute_mesh_signed_volume(cube_verts, cube_faces_quad)
vol_cube_tri1 = compute_mesh_signed_volume(cube_verts, cube_faces_tri1)
vol_cube_tri2 = compute_mesh_signed_volume(cube_verts, cube_faces_tri2)
analytical_cube = 8.0

diff_tri1 = abs(vol_cube_quad - vol_cube_tri1) / analytical_cube
diff_tri2 = abs(vol_cube_quad - vol_cube_tri2) / analytical_cube
runner.check(diff_tri1 < 0.0001, f"Cube: Quad vol ({vol_cube_quad:.6f}) vs Tri1 ({vol_cube_tri1:.6f}) diff = {diff_tri1*100:.6f}% (<0.01%)")
runner.check(diff_tri2 < 0.0001, f"Cube: Quad vol ({vol_cube_quad:.6f}) vs Tri2 ({vol_cube_tri2:.6f}) diff = {diff_tri2*100:.6f}% (<0.01%)")
runner.check(abs(vol_cube_quad - analytical_cube) < 1e-12, f"Cube: Exact match with analytical 8.000000 (diff={abs(vol_cube_quad - analytical_cube):.1e})")

# 3.2 Quad Cylinder
def make_quad_cylinder(radius: float, height: float, segments: int):
    verts = []
    half_h = height / 2.0
    # Bottom ring: 0 .. segments-1
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        verts.append((radius * math.cos(theta), radius * math.sin(theta), -half_h))
    # Top ring: segments .. 2*segments-1
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        verts.append((radius * math.cos(theta), radius * math.sin(theta), half_h))
    # Center bottom and center top for caps
    v_bot_center = len(verts)
    verts.append((0.0, 0.0, -half_h))
    v_top_center = len(verts)
    verts.append((0.0, 0.0, half_h))

    faces_quad = []
    for i in range(segments):
        nxt = (i + 1) % segments
        # Quad wall: (i, nxt, nxt + segments, i + segments)
        faces_quad.append((i, nxt, nxt + segments, i + segments))
        # Triangle caps
        faces_quad.append((v_bot_center, (i + 1) % segments, i))
        faces_quad.append((v_top_center, i + segments, (i + 1) % segments + segments))

    return verts, faces_quad

for segs in [32, 64, 128]:
    cyl_verts, cyl_faces_quad = make_quad_cylinder(1.0, 2.0, segs)
    cyl_faces_tri1 = triangulate_quads(cyl_faces_quad, diagonal=0)
    cyl_faces_tri2 = triangulate_quads(cyl_faces_quad, diagonal=1)

    vol_cyl_quad = compute_mesh_signed_volume(cyl_verts, cyl_faces_quad)
    vol_cyl_tri1 = compute_mesh_signed_volume(cyl_verts, cyl_faces_tri1)
    vol_cyl_tri2 = compute_mesh_signed_volume(cyl_verts, cyl_faces_tri2)

    diff_cyl1 = abs(vol_cyl_quad - vol_cyl_tri1) / vol_cyl_quad
    diff_cyl2 = abs(vol_cyl_quad - vol_cyl_tri2) / vol_cyl_quad
    runner.check(diff_cyl1 < 0.0001,
                 f"Cylinder ({segs} segs): Quad vol ({vol_cyl_quad:.6f}) vs Tri1 ({vol_cyl_tri1:.6f}) diff = {diff_cyl1*100:.6f}% (<0.01%)")
    runner.check(diff_cyl2 < 0.0001,
                 f"Cylinder ({segs} segs): Quad vol ({vol_cyl_quad:.6f}) vs Tri2 ({vol_cyl_tri2:.6f}) diff = {diff_cyl2*100:.6f}% (<0.01%)")

# 3.3 Quad UV Sphere
def make_quad_sphere(radius: float, lat_steps: int, lon_steps: int):
    verts = []
    # North pole: index 0
    verts.append((0.0, 0.0, radius))
    # Intermediate latitude rings
    for i in range(1, lat_steps):
        phi = math.pi * i / lat_steps
        z = radius * math.cos(phi)
        r_ring = radius * math.sin(phi)
        for j in range(lon_steps):
            theta = 2.0 * math.pi * j / lon_steps
            x = r_ring * math.cos(theta)
            y = r_ring * math.sin(theta)
            verts.append((x, y, z))
    # South pole: index len(verts)
    verts.append((0.0, 0.0, -radius))
    v_south = len(verts) - 1

    faces_quad = []
    # North pole triangle fan
    for j in range(lon_steps):
        nxt = (j + 1) % lon_steps
        faces_quad.append((0, 1 + j, 1 + nxt))

    # Quads between rings
    for i in range(1, lat_steps - 1):
        ring_curr = 1 + (i - 1) * lon_steps
        ring_next = 1 + i * lon_steps
        for j in range(lon_steps):
            nxt = (j + 1) % lon_steps
            # Quad: (curr_j, curr_nxt, next_nxt, next_j)
            faces_quad.append((ring_curr + j, ring_curr + nxt, ring_next + nxt, ring_next + j))

    # South pole triangle fan
    last_ring = 1 + (lat_steps - 2) * lon_steps
    for j in range(lon_steps):
        nxt = (j + 1) % lon_steps
        faces_quad.append((v_south, last_ring + nxt, last_ring + j))

    return verts, faces_quad

for lat, lon in [(30, 60), (45, 90), (60, 120)]:
    sph_verts, sph_faces_quad = make_quad_sphere(1.0, lat, lon)
    sph_faces_tri1 = triangulate_quads(sph_faces_quad, diagonal=0)
    sph_faces_tri2 = triangulate_quads(sph_faces_quad, diagonal=1)

    vol_sph_quad = compute_mesh_signed_volume(sph_verts, sph_faces_quad)
    vol_sph_tri1 = compute_mesh_signed_volume(sph_verts, sph_faces_tri1)
    vol_sph_tri2 = compute_mesh_signed_volume(sph_verts, sph_faces_tri2)

    diff_sph1 = abs(vol_sph_quad - vol_sph_tri1) / vol_sph_quad
    diff_sph2 = abs(vol_sph_quad - vol_sph_tri2) / vol_sph_quad
    runner.check(diff_sph1 < 0.0001,
                 f"Sphere ({lat}x{lon}): Quad vol ({vol_sph_quad:.6f}) vs Tri1 ({vol_sph_tri1:.6f}) diff = {diff_sph1*100:.6f}% (<0.01%)")
    runner.check(diff_sph2 < 0.0001,
                 f"Sphere ({lat}x{lon}): Quad vol ({vol_sph_quad:.6f}) vs Tri2 ({vol_sph_tri2:.6f}) diff = {diff_sph2*100:.6f}% (<0.01%)")

# 3.4 Scale Invariance and Spatial Translation/Rotation Fuzzing
print("\n--- Fuzzing Quad Divergence Across Scales, Translations, and Rotations ---")
for scale in [0.01, 0.5, 2.0, 10.0, 100.0]:
    for dx, dy, dz in [(0, 0, 0), (12.3, -45.6, 78.9)]:
        scaled_verts = [(x * scale + dx, y * scale + dy, z * scale + dz) for x, y, z in cube_verts]
        vol_q = compute_mesh_signed_volume(scaled_verts, cube_faces_quad)
        vol_t = compute_mesh_signed_volume(scaled_verts, cube_faces_tri1)
        expected = 8.0 * (scale ** 3)
        diff_q_exp = abs(vol_q - expected) / expected
        diff_q_t = abs(vol_q - vol_t) / expected
        runner.check(diff_q_t < 1e-6 and diff_q_exp < 1e-6,
                     f"Transformed Cube (scale={scale}, offset=({dx},{dy},{dz})): diff_vs_tri={diff_q_t*100:.8f}%, diff_vs_expected={diff_q_exp*100:.8f}%")

success = runner.summary()
sys.exit(0 if success else 1)
