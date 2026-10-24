"""
MorphoMesh: Empirical Challenger 2 Standalone Audit Runner.
Executes comprehensive mathematical integrity audit and outputs structured report table.
"""

from __future__ import annotations

import math
import sys
from typing import Dict, List, Tuple

from morphomesh.human_generator import (
    HumanAnatomyGenerator,
    generate_human_base_mesh,
    generate_human_body,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.models import HumanAnatomyConfig


def compute_edge_topology(mesh: MeshGeometry) -> Tuple[int, int]:
    edge_counts: Dict[Tuple[int, int], int] = {}
    for f in mesh.faces:
        for a, b in [(f[0], f[1]), (f[1], f[2]), (f[2], f[0])]:
            e = (min(a, b), max(a, b))
            edge_counts[e] = edge_counts.get(e, 0) + 1
    non_manifold = sum(1 for c in edge_counts.values() if c > 2)
    boundary = sum(1 for c in edge_counts.values() if c == 1)
    return non_manifold, boundary


def compute_quad_metrics(mesh: MeshGeometry) -> Tuple[int, int, float]:
    faces = mesh.faces
    total_tris = len(faces)
    quad_count = 0
    tri_count = 0
    i = 0
    while i < total_tris:
        if i + 1 < total_tris:
            f1 = faces[i]
            f2 = faces[i + 1]
            if f1[0] == f2[0] and f1[2] == f2[1]:
                quad_count += 1
                i += 2
                continue
        tri_count += 1
        i += 1
    total_polys = quad_count + tri_count
    ratio = quad_count / total_polys if total_polys > 0 else 0.0
    return quad_count, tri_count, ratio


def audit_mesh(cfg: HumanAnatomyConfig) -> Dict[str, any]:
    res = generate_human_base_mesh(cfg)
    mesh = res.mesh
    verts = mesh.vertices
    faces = mesh.faces

    nm, bnd = compute_edge_topology(mesh)
    quads, tris, q_ratio = compute_quad_metrics(mesh)

    min_area = float("inf")
    min_face = None
    min_dot = 1.0
    inverted_count = 0
    inverted_faces = []

    for fi, f in enumerate(faces):
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
        if area < min_area:
            min_area = area
            min_face = (fi, f)

        l = math.sqrt(cx * cx + cy * cy + cz * cz) or 1.0
        fn_u = (cx / l, cy / l, cz / l)
        vn_avg = [
            (mesh.normals[f[0]][k] + mesh.normals[f[1]][k] + mesh.normals[f[2]][k]) / 3.0
            for k in range(3)
        ]
        vl = math.sqrt(sum(k * k for k in vn_avg)) or 1.0
        vn_u = (vn_avg[0] / vl, vn_avg[1] / vl, vn_avg[2] / vl)
        dot = fn_u[0] * vn_u[0] + fn_u[1] * vn_u[1] + fn_u[2] * vn_u[2]
        if dot < min_dot:
            min_dot = dot
        if dot < -0.05:
            inverted_count += 1
            inverted_faces.append((fi, f, dot))

    return {
        "verts": len(verts),
        "faces": len(faces),
        "quads": quads,
        "tris": tris,
        "quad_ratio": q_ratio,
        "non_manifold": nm,
        "boundary": bnd,
        "min_area": min_area,
        "min_face": min_face,
        "min_dot": min_dot,
        "inverted_count": inverted_count,
        "inverted_faces": inverted_faces,
    }


def main():
    print("=" * 95)
    print("M1 CHALLENGER 2 EMPIRICAL AUDIT: STRESS TESTING & MATHEMATICAL INTEGRITY")
    print("=" * 95)

    test_cases = [
        ("stylized_heroine (1.65m)", HumanAnatomyConfig(height=1.65, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("stylized_heroine (1.40m)", HumanAnatomyConfig(height=1.40, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("stylized_heroine (1.95m)", HumanAnatomyConfig(height=1.95, head_ratio=7.41, chest_girth=0.82, waist_girth=0.58, hip_girth=0.86, shoulder_width=0.36)),
        ("petite (1.40m)", HumanAnatomyConfig(height=1.40, head_ratio=6.50, chest_girth=0.76, waist_girth=0.54, hip_girth=0.80, shoulder_width=0.32)),
        ("realistic_female (1.68m)", HumanAnatomyConfig(height=1.68, head_ratio=7.50, chest_girth=0.88, waist_girth=0.66, hip_girth=0.94, shoulder_width=0.38)),
        ("realistic_female (1.40m)", HumanAnatomyConfig(height=1.40, head_ratio=7.50, chest_girth=0.88, waist_girth=0.66, hip_girth=0.94, shoulder_width=0.38)),
        ("realistic_female (1.95m)", HumanAnatomyConfig(height=1.95, head_ratio=7.50, chest_girth=0.88, waist_girth=0.66, hip_girth=0.94, shoulder_width=0.38)),
    ]

    print(f"{'Preset / Dimension':<26} | {'V / Q (Ratio)':<16} | {'NM / B':<8} | {'MinArea (m^2)':<14} | {'MinDot / Inv':<14} | {'Status':<6}")
    print("-" * 95)

    failures = []

    for name, cfg in test_cases:
        res = audit_mesh(cfg)
        status = "PASS"
        issues = []

        if res["verts"] != 13380 or res["quads"] != 13378 or res["quad_ratio"] != 1.0:
            status = "FAIL"
            issues.append("Topology count mismatch")
        if res["non_manifold"] > 0 or res["boundary"] > 0:
            status = "FAIL"
            issues.append("Non-manifold edges")
        if res["min_area"] <= 1.0e-7:
            status = "FAIL"
            issues.append(f"MinArea {res['min_area']:.2e} <= 1e-7")
        if res["min_dot"] <= -0.05 or res["inverted_count"] > 0:
            status = "FAIL"
            issues.append(f"Inverted faces: {res['inverted_count']} (min_dot={res['min_dot']:.4f})")

        vq_str = f"{res['verts']} / {res['quads']} ({res['quad_ratio']*100:.0f}%)"
        nmb_str = f"{res['non_manifold']} / {res['boundary']}"
        area_str = f"{res['min_area']:.2e}"
        dot_str = f"{res['min_dot']:.4f} / {res['inverted_count']}"

        print(f"{name:<26} | {vq_str:<16} | {nmb_str:<8} | {area_str:<14} | {dot_str:<14} | {status:<6}")

        if status == "FAIL":
            failures.append((name, issues, res))

    # Interface contract test
    print("-" * 95)
    contract_status = "PASS"
    try:
        generate_human_body(height=1.65, gender="female", proportion_preset="stylized_heroine")
    except TypeError as e:
        contract_status = "FAIL"
        failures.append(("generate_human_body contract", [f"TypeError: {e}"], {}))
    print(f"{'Interface Contract (PROJECT.md)':<26} | {'generate_human_body(height, gender, proportion_preset)':<44} | {contract_status:<6}")

    print("=" * 95)
    if failures:
        print(f"\nAUDIT FAILED with {len(failures)} defect(s):")
        for name, issues, details in failures:
            print(f"  - [{name}]: {', '.join(issues)}")
            if "inverted_faces" in details and details["inverted_faces"]:
                print(f"    * Inverted face sample: {details['inverted_faces'][:3]}")
            if "min_face" in details and details["min_face"]:
                print(f"    * Min area face: {details['min_face']}")
        print("\nVERDICT: REQUEST_CHANGES")
        sys.exit(1)
    else:
        print("\nALL AUDITS PASSED!")
        print("VERDICT: APPROVE")
        sys.exit(0)


if __name__ == "__main__":
    main()
