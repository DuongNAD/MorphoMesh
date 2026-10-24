"""
Forensic Integrity Empirical Verification Script for Milestone M2.
Executes rigorous dynamic parameter perturbations, AST inspection,
and geometric invariant checks on src/morphomesh/wardrobe.py.
"""

import ast
import inspect
import math
import sys
from collections import defaultdict
from typing import Dict, List, Tuple

import numpy as np

from morphomesh.human_generator import (
    HumanAnatomyConfig,
    generate_human_base_mesh,
    generate_human_body,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.visual_critic import PurePythonBVHTree
import morphomesh.wardrobe as wardrobe
from morphomesh.wardrobe import (
    compute_dress_waist_radii,
    generate_dress_bodice,
    generate_dress_organic_skirt,
    generate_dress_waist_sash,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_yu_nian_an_wardrobe,
)


def run_ast_and_source_forensics():
    print("=== Phase 1: AST and Source Code Forensics ===")
    src_path = inspect.getfile(wardrobe)
    with open(src_path, "r", encoding="utf-8") as f:
        src_text = f.read()

    tree = ast.parse(src_text, filename=src_path)

    # 1. Look for forbidden names or function calls
    forbidden_names = {
        "sys._getframe", "_getframe", "inspect.stack", "currentframe",
        "mock", "MagicMock", "unittest.mock", "pytest.fail", "xfail",
    }
    found_forbidden = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in forbidden_names:
            found_forbidden.append((node.id, node.lineno))
        elif isinstance(node, ast.Attribute):
            full_attr = ""
            curr = node
            parts = []
            while isinstance(curr, ast.Attribute):
                parts.append(curr.attr)
                curr = curr.value
            if isinstance(curr, ast.Name):
                parts.append(curr.id)
                full_attr = ".".join(reversed(parts))
                if any(fn in full_attr for fn in forbidden_names):
                    found_forbidden.append((full_attr, node.lineno))

    assert len(found_forbidden) == 0, f"Found forbidden AST tokens: {found_forbidden}"
    print("[PASS] Zero forbidden inspection / stack sniffing tokens in wardrobe.py.")

    # 2. Check all If conditions in wardrobe.py to ensure no test name / caller sniffing
    suspicious_comparisons = []
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            test_str = ast.unparse(node.test)
            if any(term in test_str.lower() for term in ["test", "caller", "frame", "mock", "patch", "pytest"]):
                suspicious_comparisons.append((test_str, node.lineno))

    assert len(suspicious_comparisons) == 0, f"Found suspicious branch conditions: {suspicious_comparisons}"
    print("[PASS] Zero test-sniffing or caller-sniffing branches in wardrobe.py.")


def run_remediation_1_skirt_winding_audit():
    print("\n=== Phase 2: Remediation 1 - Skirt Normal Winding Order ===")
    # Test multiple parameter variations and resolutions
    configs = [
        {"height": 1.65, "rings_count": 16, "sectors": 48},
        {"height": 1.50, "rings_count": 12, "sectors": 36},
        {"height": 1.80, "rings_count": 20, "sectors": 60},
        {"height": 1.65, "waist_girth": 0.45, "hip_girth": 0.70},
        {"height": 1.65, "waist_girth": 0.85, "hip_girth": 1.10},
    ]

    for cfg in configs:
        skirt = generate_dress_organic_skirt(**cfg)
        outward_faces = 0
        inward_faces = 0
        zero_area_faces = 0

        for f_idx, f in enumerate(skirt.faces):
            v0, v1, v2 = skirt.vertices[f[0]], skirt.vertices[f[1]], skirt.vertices[f[2]]
            # Centroid in XY
            cx = (v0[0] + v1[0] + v2[0]) / 3.0
            cy = (v0[1] + v1[1] + v2[1]) / 3.0

            # Outward normal via CCW edge cross product
            e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
            nx = e1[1] * e2[2] - e1[2] * e2[1]
            ny = e1[2] * e2[0] - e1[0] * e2[2]
            nz = e1[0] * e2[1] - e1[1] * e2[0]

            nlen = math.sqrt(nx * nx + ny * ny + nz * nz)
            if nlen < 1e-8:
                zero_area_faces += 1
                continue

            # Dot product with outward radial direction from body axis (0, 0, Z)
            dot = cx * nx + cy * ny
            if dot > 0:
                outward_faces += 1
            else:
                inward_faces += 1

        total = len(skirt.faces)
        assert zero_area_faces == 0, f"Config {cfg}: {zero_area_faces} zero area faces!"
        assert inward_faces == 0, f"Config {cfg}: {inward_faces} inward faces out of {total}!"
        assert outward_faces == total, f"Config {cfg}: outward {outward_faces} != total {total}"
        print(f"[PASS] Config {cfg}: 100.0% outward normals ({outward_faces}/{total} faces).")


def run_remediation_2_sash_flare_audit():
    print("\n=== Phase 3: Remediation 2 - Posterior Sash Flare Compensation ===")
    for h in [1.40, 1.55, 1.65, 1.75, 1.85]:
        s = h / 1.65
        w = generate_yu_nian_an_wardrobe(wardrobe.WardrobeConfig(character_height=h))
        sash = w["Dress_WaistSash"]
        skirt = w["Dress_PleatedSkirt"]

        # Lowest sash ring posterior vertices (around vertex index 6 on ring 0)
        # Ring 0 has sectors=24 vertices, theta = 2pi*i/24. i=6 is theta = pi/2 (posterior midline)
        v_sash_post = sash.vertices[6]
        assert abs(v_sash_post[0]) < 0.005, f"Expected X approx 0, got {v_sash_post[0]}"
        assert v_sash_post[1] > 0.08 * s, f"Expected posterior Y > 0, got {v_sash_post[1]}"

        # Compare against skirt at elevation v_sash_post[2]
        # Skirt vertices on posterior midline: i = 12 on each ring (sectors=48 -> i=12 is theta=pi/2)
        skirt_ring0_post = skirt.vertices[12]
        skirt_ring1_post = skirt.vertices[49 + 12]

        t_interp = (skirt_ring0_post[2] - v_sash_post[2]) / (skirt_ring0_post[2] - skirt_ring1_post[2])
        skirt_y_at_z = skirt_ring0_post[1] + t_interp * (skirt_ring1_post[1] - skirt_ring0_post[1])

        clearance_mm = (v_sash_post[1] - skirt_y_at_z) * 1000.0
        assert clearance_mm >= 2.5, f"Height {h}m: Posterior clearance {clearance_mm:.2f}mm < 2.5mm!"
        print(f"[PASS] Height {h:.2f}m: Posterior sash-skirt clearance = +{clearance_mm:.2f}mm (>= +2.5mm requirement).")


def run_remediation_3_and_4_bodice_and_strap_audit():
    print("\n=== Phase 4: Remediation 3 & 4 - Bodice Chord Buffers & Strap Decoupling ===")
    # 1. Canonical Bodice signed distance profile
    body, _ = generate_human_body(height=1.65)
    bvh = PurePythonBVHTree.FromPolygons(body.vertices, body.faces)

    bodice = generate_dress_bodice(height=1.65, clearance=0.0018)
    penetrations = []
    signed_distances = []

    for idx, v in enumerate(bodice.vertices):
        loc, norm, f_idx, dist = bvh.find_nearest(v)
        offset = (v[0] - loc[0], v[1] - loc[1], v[2] - loc[2])
        dot = offset[0] * norm[0] + offset[1] * norm[1] + offset[2] * norm[2]
        s_dist = dist if dot >= 0.0 else -dist
        signed_distances.append(s_dist)
        if dot < -0.0001:
            penetrations.append((idx, v, s_dist))

    min_s_dist_mm = min(signed_distances) * 1000.0
    assert len(penetrations) == 0, f"Canonical bodice has {len(penetrations)} penetrations!"
    assert min_s_dist_mm >= 1.5, f"Canonical bodice min clearance {min_s_dist_mm:.2f}mm < 1.5mm"
    print(f"[PASS] Canonical Bodice: 0 penetrations (0/352 verts), min signed clearance = +{min_s_dist_mm:.2f}mm.")

    # 2. Extreme bust scaling parameter sweep for straps
    kc_values = [0.65, 0.70, 0.85, 1.00, 1.15, 1.30, 1.45]
    for kc in kc_values:
        cfg = HumanAnatomyConfig(height=1.65, chest_girth=0.82 * kc)
        body_scaled = generate_human_base_mesh(config=cfg).mesh
        bvh_scaled = PurePythonBVHTree.FromPolygons(body_scaled.vertices, body_scaled.faces)

        bodice_scaled = generate_dress_bodice(height=1.65, chest_girth=0.82 * kc, clearance=0.0018)
        strap_verts = bodice_scaled.vertices[320:]

        strap_pens = []
        strap_dists = []
        for idx, sv in enumerate(strap_verts):
            loc, norm, _, dist = bvh_scaled.find_nearest(sv)
            offset = (sv[0] - loc[0], sv[1] - loc[1], sv[2] - loc[2])
            dot = offset[0] * norm[0] + offset[1] * norm[1] + offset[2] * norm[2]
            s_dist = dist if dot >= 0.0 else -dist
            strap_dists.append(s_dist)
            if dot < -0.0001:
                strap_pens.append((idx, sv, s_dist))

        min_strap_d_mm = min(strap_dists) * 1000.0
        assert len(strap_pens) == 0, f"k_chest={kc}: {len(strap_pens)} strap penetrations!"
        assert min_strap_d_mm >= 1.5, f"k_chest={kc}: strap clearance {min_strap_d_mm:.2f}mm < 1.5mm"
        print(f"[PASS] k_chest={kc:.2f}: 0 strap penetrations, min strap clearance = +{min_strap_d_mm:.2f}mm.")

    # 3. Verify Strap Decoupling Math: X position invariant to k_chest
    b_slender = generate_dress_bodice(height=1.65, chest_girth=0.82 * 0.70)
    b_full = generate_dress_bodice(height=1.65, chest_girth=0.82 * 1.40)
    x_apex_slender = max(v[0] for v in b_slender.vertices[320:])
    x_apex_full = max(v[0] for v in b_full.vertices[320:])
    assert math.isclose(x_apex_slender, x_apex_full, abs_tol=1e-4), (
        f"Strap X apex must be decoupled from chest girth: {x_apex_slender} vs {x_apex_full}"
    )
    print(f"[PASS] Strap X apex strictly decoupled: slender X={x_apex_slender:.5f}m == full X={x_apex_full:.5f}m.")


def run_remediation_5_knot_manifold_caps_audit():
    print("\n=== Phase 5: Remediation 5 - Barrel Knot 3-Quad Closed Manifold Caps ===")
    for h in [1.40, 1.65, 1.85]:
        sash = generate_dress_waist_sash(height=h)
        knot_faces = [f for f in sash.faces if all(120 <= idx < 152 for idx in f)]
        assert len(knot_faces) == 60, f"Expected 60 faces for 30 quads, got {len(knot_faces)}"

        edge_counts = defaultdict(int)
        for f in knot_faces:
            edges = [
                (min(f[0], f[1]), max(f[0], f[1])),
                (min(f[1], f[2]), max(f[1], f[2])),
                (min(f[2], f[0]), max(f[2], f[0])),
            ]
            for e in edges:
                edge_counts[e] += 1

        boundary_edges = [e for e, c in edge_counts.items() if c == 1]
        non_manifold = [e for e, c in edge_counts.items() if c > 2]

        assert len(boundary_edges) == 0, f"Height {h}: Found {len(boundary_edges)} boundary edges!"
        assert len(non_manifold) == 0, f"Height {h}: Found {len(non_manifold)} non-manifold edges!"

        # Euler characteristic
        V = 32
        E = len(edge_counts)
        F = len(knot_faces)
        chi = V - E + F
        assert chi == 2, f"Height {h}: Euler characteristic chi={chi} != 2 (V={V}, E={E}, F={F})"
        print(f"[PASS] Height {h:.2f}m: Barrel knot has 0 boundary edges, 0 non-manifold edges, chi = {chi} (closed 2-manifold).")


def run_remediation_6_streamer_tip_bias_audit():
    print("\n=== Phase 6: Remediation 6 - Streamer Tip Bias Cut ===")
    for h in [1.40, 1.65, 1.85]:
        s = h / 1.65
        sash = generate_dress_waist_sash(height=h)

        # Left streamer tip: vertices 296, 297, 298
        tip_L = sash.vertices[296:299]
        # Right streamer tip: vertices 347, 348, 349
        tip_R = sash.vertices[347:350]

        delta_z_L = max(v[2] for v in tip_L) - min(v[2] for v in tip_L)
        delta_z_R = max(v[2] for v in tip_R) - min(v[2] for v in tip_R)

        # Theoretical delta_z: ribbon width w = (0.024 - 0.005) * s = 0.019 * s
        expected_w = 0.019 * s
        assert math.isclose(delta_z_L, expected_w, abs_tol=1e-4), f"Left tip delta_z {delta_z_L} != {expected_w}"
        assert math.isclose(delta_z_R, expected_w, abs_tol=1e-4), f"Right tip delta_z {delta_z_R} != {expected_w}"

        # Verify intermediate steps have ZERO tip bias (flat horizontal cross sections before tip)
        for step in range(16):
            start_idx = 248 + step * 3
            pts = sash.vertices[start_idx : start_idx + 3]
            # In intermediate steps, Z should be invariant across the cross section
            z_spread = max(v[2] for v in pts) - min(v[2] for v in pts)
            assert math.isclose(z_spread, 0.0, abs_tol=1e-4), f"Intermediate step {step} has premature bias: {z_spread}"

        print(f"[PASS] Height {h:.2f}m: Tip delta_Z = {delta_z_L*1000:.2f}mm == ribbon width {expected_w*1000:.2f}mm (exact 45.0 deg bias cut).")


def run_procedural_responsiveness_audit():
    print("\n=== Phase 7: Dynamic Parameter Perturbation & Procedural Responsiveness ===")
    # Check that outputs respond smoothly and non-trivially to parameter perturbations
    # 1. Scaling test: height scaling from 1.2 to 2.0
    h_sweep = [1.20, 1.40, 1.60, 1.80, 2.00]
    skirt_weights = []
    bodice_max_zs = []
    for h in h_sweep:
        b = generate_dress_bodice(height=h)
        bodice_max_zs.append(max(v[2] for v in b.vertices))

    # Should be strictly monotonically increasing and linear
    for i in range(len(h_sweep) - 1):
        assert bodice_max_zs[i + 1] > bodice_max_zs[i]
        ratio_z = bodice_max_zs[i + 1] / bodice_max_zs[i]
        ratio_h = h_sweep[i + 1] / h_sweep[i]
        assert math.isclose(ratio_z, ratio_h, rel_tol=1e-3), f"Non-linear scaling: {ratio_z} vs {ratio_h}"
    print("[PASS] Bodice Z dimensions scale strictly linearly with height.")

    # 2. Waist girth expansion
    w_sweep = [0.45, 0.58, 0.70, 0.85]
    waist_radii = []
    for wg in w_sweep:
        sash = generate_dress_waist_sash(height=1.65, waist_girth=wg)
        # Mid-band radius
        r_mid = max(math.hypot(v[0], v[1]) for v in sash.vertices[48:72])
        waist_radii.append(r_mid)

    for i in range(len(w_sweep) - 1):
        assert waist_radii[i + 1] > waist_radii[i], "Waist radius must expand monotonically with waist_girth"
    print("[PASS] Sash radius expands strictly monotonically with waist_girth.")

    # 3. Bust cup scale expansion
    bust_sweep = [0.7, 1.0, 1.3, 1.6]
    cup_projections = []
    for bs in bust_sweep:
        bodice = generate_dress_bodice(height=1.65, bust_cup_scale=bs)
        # Find minimum Y (forward most point) in bust region Z in [1.16, 1.22]
        min_y = min(v[1] for v in bodice.vertices if 1.16 <= v[2] <= 1.22)
        cup_projections.append(-min_y)

    for i in range(len(bust_sweep) - 1):
        assert cup_projections[i + 1] > cup_projections[i], "Bust projection must increase monotonically with bust_cup_scale"
    print("[PASS] Bodice breast cup forward projection increases monotonically with bust_cup_scale.")


if __name__ == "__main__":
    try:
        run_ast_and_source_forensics()
        run_remediation_1_skirt_winding_audit()
        run_remediation_2_sash_flare_audit()
        run_remediation_3_and_4_bodice_and_strap_audit()
        run_remediation_5_knot_manifold_caps_audit()
        run_remediation_6_streamer_tip_bias_audit()
        run_procedural_responsiveness_audit()
        print("\n>>> ALL FORENSIC AUDIT CHECKS PASSED: VERDICT = CLEAN <<<")
    except Exception as e:
        print(f"\n>>> FORENSIC AUDIT FAILURE: {e} <<<")
        sys.exit(1)
