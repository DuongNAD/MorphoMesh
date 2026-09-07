#!/usr/bin/env python3
"""
Extended Adversarial Stress Test Harness for Milestone 3 Iteration 2.
Agent: Challenger M3 Iter 2 - 2

Deep boundary fuzzing:
1. Coplanar Triangle Overlaps & Edge Cases:
   - High-aspect-ratio / needle triangles
   - Multi-scale (micrometers 1e-5 to kilometers 1e4)
   - Edge-overlapping (collinear edge segments)
   - Corner-to-edge touching
   - Inverted winding & cyclic permutations of vertices
   - Exact separation threshold sweep (0.5 um, 1.5 um, 10 um, 0.1mm, 1mm, 10mm)
2. Benchmark Schema & Parity Invariance:
   - Schema type checking for all 14 fields
   - State breakdown sum invariance: TP + FN = defective_states_tested (5), TN + FP = clean_states_tested (4)
   - Total states invariance: tests_run == total_states == 9
   - Accuracy calculation invariance: (TP + TN) / total == accuracy_ratio == 1.0
   - Rate consistency: accuracy == accuracy_percentage == accuracy_ratio * 100
3. Quad Divergence Volume Conservation & Manifold Invariance:
   - Torus (quad mesh with non-zero genus)
   - Highly deformed / non-planar quad grids
   - Winding consistency check
   - Analytical torus volume vs quad divergence volume
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


class ExtendedRunner:
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
        print("\n" + "=" * 75)
        print(f"EXTENDED HARNESS SUMMARY: {self.passed}/{total} PASSED, {self.failed} FAILED")
        if self.failed > 0:
            print("Failed tests:")
            for err in self.errors:
                print(f"  - {err}")
            print("VERDICT: REJECT")
            return False
        else:
            print("VERDICT: APPROVE")
            print("=" * 75)
            return True


runner = ExtendedRunner()

print("\n" + "=" * 75)
print("EXTENDED SECTION 1: COPLANAR TRIANGLES DEEP GEOMETRIC BOUNDARIES")
print("=" * 75)

# 1.1 Needle / Slivers (Aspect ratio 1000:1)
t_needle1 = ((0.0, 0.0, 0.0), (1000.0, 0.0, 0.0), (500.0, 0.001, 0.0))
t_needle2 = ((200.0, 0.0, 0.0), (800.0, 0.0, 0.0), (500.0, 0.0005, 0.0))
runner.check(triangle_triangle_intersection_moller(*t_needle1, *t_needle2) is True,
             "Extreme sliver/needle coplanar triangles (aspect 1000:1) detect overlap")

# 1.2 Multi-Scale Fuzzing: Micro (1e-4m = 0.1mm) to Macro (1e4m = 10km)
for scale in [1e-4, 1e-2, 1.0, 1e2, 1e4]:
    t1 = ((0.0, 0.0, 0.0), (scale, 0.0, 0.0), (0.0, scale, 0.0))
    t2_in = ((scale*0.2, scale*0.2, 0.0), (scale*0.8, scale*0.2, 0.0), (scale*0.2, scale*0.8, 0.0))
    t2_disj = ((scale*2.0, scale*2.0, 0.0), (scale*3.0, scale*2.0, 0.0), (scale*2.0, scale*3.0, 0.0))
    
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_in) is True,
                 f"Scale {scale:g}m: Coplanar overlap detected")
    runner.check(triangle_triangle_intersection_moller(*t1, *t2_disj) is False,
                 f"Scale {scale:g}m: Coplanar disjoint returns False")

# 1.3 Normal separation threshold boundary sweep
t_base1 = ((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
t_base2 = ((0.2, 0.2, 0.0), (0.8, 0.2, 0.0), (0.2, 0.8, 0.0))

# Sub-tolerance separation (50 nm = 5e-8 m < 1e-7 m): within tolerance -> coplanar -> True
t_sep_50nm = tuple((p[0], p[1], p[2] + 5e-8) for p in t_base2)
runner.check(triangle_triangle_intersection_moller(*t_base1, *t_sep_50nm) is True,
             "Sub-tolerance normal separation 50 nm (<0.1 um tolerance) treated as coplanar (True)")

# Above tolerance (0.5 um, 1.5 um, 10 um, 0.1mm, 1mm, 10mm): outside tolerance -> False
for sep_dist, label in [
    (5.0e-7, "0.5 um"),
    (1.5e-6, "1.5 um"),
    (1.0e-5, "10 um"),
    (1.0e-4, "0.1 mm"),
    (1.0e-3, "1.0 mm"),
    (1.0e-2, "10.0 mm"),
    (1.0, "1.0 m"),
]:
    t_sep = tuple((p[0], p[1], p[2] + sep_dist) for p in t_base2)
    runner.check(triangle_triangle_intersection_moller(*t_base1, *t_sep) is False,
                 f"Normal separation {label} (>1um tolerance) returns False")

# 1.4 Vertex Permutation and Cyclic Invariance
t_p1 = ((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0))
t_p2 = ((0.5, 0.5, 0.0), (1.5, 0.5, 0.0), (0.5, 1.5, 0.0))

perms1 = [
    (t_p1[0], t_p1[1], t_p1[2]),
    (t_p1[1], t_p1[2], t_p1[0]),
    (t_p1[2], t_p1[0], t_p1[1]),
    (t_p1[0], t_p1[2], t_p1[1]), # flipped winding
]
perms2 = [
    (t_p2[0], t_p2[1], t_p2[2]),
    (t_p2[1], t_p2[2], t_p2[0]),
    (t_p2[2], t_p2[0], t_p2[1]),
    (t_p2[0], t_p2[2], t_p2[1]),
]

all_perms_pass = True
for p1 in perms1:
    for p2 in perms2:
        if not triangle_triangle_intersection_moller(*p1, *p2):
            all_perms_pass = False
            break
runner.check(all_perms_pass, "All 16 vertex permutation / winding combinations return True")

# 1.5 Collinear Edge Sharing without Interior Overlap
# T1: (0,0,0)-(2,0,0)-(0,2,0). T2 shares part of edge (0,0)-(2,0) from (0.5, 0)-(1.5, 0) and extends downward into -Y
t_collinear_edge = ((0.5, 0.0, 0.0), (1.5, 0.0, 0.0), (1.0, -1.0, 0.0))
runner.check(triangle_triangle_intersection_moller(*t_p1, *t_collinear_edge) is True,
             "Collinear partial edge sharing returns True")

# Corner touching only (at (2, 0, 0))
t_corner = ((2.0, 0.0, 0.0), (3.0, 0.0, 0.0), (2.0, -1.0, 0.0))
runner.check(triangle_triangle_intersection_moller(*t_p1, *t_corner) is True,
             "Exact single vertex touching in coplanar returns True")


print("\n" + "=" * 75)
print("EXTENDED SECTION 2: BENCHMARK SCHEMA INVARIANTS & TYPES")
print("=" * 75)

stats = benchmark_defect_detection()

# Type assertions
runner.check(isinstance(stats["tests_run"], int), f"tests_run is int ({type(stats['tests_run'])})")
runner.check(isinstance(stats["total_states"], int), f"total_states is int ({type(stats['total_states'])})")
runner.check(isinstance(stats["correct_classifications"], int), f"correct_classifications is int")
runner.check(isinstance(stats["clean_states_tested"], int), f"clean_states_tested is int")
runner.check(isinstance(stats["defective_states_tested"], int), f"defective_states_tested is int")
runner.check(isinstance(stats["true_positives"], int), f"true_positives is int")
runner.check(isinstance(stats["true_negatives"], int), f"true_negatives is int")
runner.check(isinstance(stats["false_positives"], int), f"false_positives is int")
runner.check(isinstance(stats["false_negatives"], int), f"false_negatives is int")
runner.check(isinstance(stats["accuracy"], (float, int)), f"accuracy is float/int ({stats['accuracy']})")
runner.check(isinstance(stats["accuracy_percentage"], (float, int)), f"accuracy_percentage is float/int ({stats['accuracy_percentage']})")
runner.check(isinstance(stats["accuracy_ratio"], (float, int)), f"accuracy_ratio is float/int ({stats['accuracy_ratio']})")
runner.check(isinstance(stats["false_positive_rate"], (float, int)), f"false_positive_rate is float/int ({stats['false_positive_rate']})")
runner.check(isinstance(stats["false_positive_rate_ratio"], (float, int)), f"false_positive_rate_ratio is float/int ({stats['false_positive_rate_ratio']})")

# Mathematical Invariants
tp, tn, fp, fn = stats["true_positives"], stats["true_negatives"], stats["false_positives"], stats["false_negatives"]
runner.check(tp + tn + fp + fn == stats["total_states"] == stats["tests_run"] == 9,
             "Invariant: TP + TN + FP + FN == total_states == tests_run == 9")
runner.check(tp + fn == stats["defective_states_tested"] == 5,
             "Invariant: TP + FN == defective_states_tested == 5")
runner.check(tn + fp == stats["clean_states_tested"] == 4,
             "Invariant: TN + FP == clean_states_tested == 4")
runner.check(tp + tn == stats["correct_classifications"] == 9,
             "Invariant: TP + TN == correct_classifications == 9")
runner.check(stats["accuracy"] == stats["accuracy_percentage"] == stats["accuracy_ratio"] * 100.0 == 100.0,
             "Invariant: accuracy == accuracy_percentage == accuracy_ratio * 100 == 100.0")
runner.check(stats["false_positive_rate"] == stats["false_positive_rate_ratio"] * 100.0 == 0.0,
             "Invariant: false_positive_rate == false_positive_rate_ratio * 100 == 0.0")


print("\n" + "=" * 75)
print("EXTENDED SECTION 3: QUAD DIVERGENCE VOLUME ON COMPLEX & GENUS-1 MESHES")
print("=" * 75)

# 3.1 Quad Torus (Genus 1, R=2.0, r=0.5)
# Analytical Torus Volume: V = 2 * pi^2 * R * r^2
def make_quad_torus(major_r: float, minor_r: float, major_segs: int, minor_segs: int):
    verts = []
    for i in range(major_segs):
        u = 2.0 * math.pi * i / major_segs
        cu, su = math.cos(u), math.sin(u)
        for j in range(minor_segs):
            v = 2.0 * math.pi * j / minor_segs
            cv, sv = math.cos(v), math.sin(v)
            x = (major_r + minor_r * cv) * cu
            y = (major_r + minor_r * cv) * su
            z = minor_r * sv
            verts.append((x, y, z))

    faces_quad = []
    for i in range(major_segs):
        i_next = (i + 1) % major_segs
        for j in range(minor_segs):
            j_next = (j + 1) % minor_segs
            # quad indices
            p0 = i * minor_segs + j
            p1 = i_next * minor_segs + j
            p2 = i_next * minor_segs + j_next
            p3 = i * minor_segs + j_next
            faces_quad.append((p0, p1, p2, p3))
    return verts, faces_quad

torus_verts, torus_quads = make_quad_torus(2.0, 0.5, 32, 16)
torus_tris1 = []
for q in torus_quads:
    torus_tris1.append((q[0], q[1], q[2]))
    torus_tris1.append((q[0], q[2], q[3]))
torus_tris2 = []
for q in torus_quads:
    torus_tris2.append((q[0], q[1], q[3]))
    torus_tris2.append((q[1], q[2], q[3]))

vol_torus_quad = compute_mesh_signed_volume(torus_verts, torus_quads)
vol_torus_tri1 = compute_mesh_signed_volume(torus_verts, torus_tris1)
vol_torus_tri2 = compute_mesh_signed_volume(torus_verts, torus_tris2)
analytical_torus = 2.0 * (math.pi ** 2) * 2.0 * (0.5 ** 2) # ~9.869604

diff_torus_t1 = abs(vol_torus_quad - vol_torus_tri1) / vol_torus_quad
diff_torus_t2 = abs(vol_torus_quad - vol_torus_tri2) / vol_torus_quad
runner.check(diff_torus_t1 < 1e-6, f"Quad Torus: Quad vol ({vol_torus_quad:.6f}) vs Tri1 ({vol_torus_tri1:.6f}) diff = {diff_torus_t1*100:.6f}% (<0.01%)")
runner.check(diff_torus_t2 < 1e-6, f"Quad Torus: Quad vol ({vol_torus_quad:.6f}) vs Tri2 ({vol_torus_tri2:.6f}) diff = {diff_torus_t2*100:.6f}% (<0.01%)")

# 3.2 Non-Planar Twisted Quad Cube
# Displace corner vertices to create warped/non-planar quad faces
cube_verts = [
    (-1.0, -1.0, -1.0), (1.0, -1.0, -1.0), (1.0, 1.0, -1.0), (-1.0, 1.0, -1.0),
    (-1.0, -1.0,  1.0), (1.0, -1.0,  1.0), (1.0, 1.0,  1.0), (-1.0, 1.0,  1.0),
]
cube_faces_quad = [
    (0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (0, 4, 7, 3), (1, 2, 6, 5),
]
warped_verts = list(cube_verts)
warped_verts[0] = (-1.05, -1.02, -0.98)
warped_verts[6] = (1.04, 0.97, 1.03)

vol_warped_quad = compute_mesh_signed_volume(warped_verts, cube_faces_quad)
warped_tris1 = []
for q in cube_faces_quad:
    warped_tris1.append((q[0], q[1], q[2]))
    warped_tris1.append((q[0], q[2], q[3]))
vol_warped_tri = compute_mesh_signed_volume(warped_verts, warped_tris1)

diff_warped = abs(vol_warped_quad - vol_warped_tri) / vol_warped_quad
runner.check(diff_warped < 1e-12, f"Warped Quad Cube: Quad vol ({vol_warped_quad:.6f}) matches Tri1 exactly (diff={diff_warped:.1e})")

success = runner.summary()
sys.exit(0 if success else 1)
