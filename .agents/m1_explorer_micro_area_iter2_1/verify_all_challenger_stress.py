import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir, compute_relaxed_vertex_normals

def compute_tri_area(p0, p1, p2):
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)

def test_proposed_offsets_full():
    templates_dir = _get_templates_dir()
    obj_path = templates_dir / "makehuman_clean_body.obj"

    raw_verts = []
    raw_quads = []
    s_scale = 1.65 / 1.66589

    with open(obj_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                cx, cy, cz = float(parts[1]), float(parts[2]), float(parts[3])
                bx = 0.1 * cx * s_scale
                by = -0.1 * cz * s_scale
                bz = 0.1 * (cy + 8.1676) * s_scale
                raw_verts.append((bx, by, bz))
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                v_idx = [int(pt.split("/")[0]) - 1 for pt in parts]
                if len(v_idx) == 4:
                    raw_quads.append(tuple(v_idx))

    relaxation_offsets = {
        24: (0.000330, -0.000050, 0.000000),
        27: (0.000000, 0.000000, 0.000100),
        30: (0.000070, -0.000290, 0.000000),
        422: (-0.000150, -0.000100, -0.000100),
        423: (-0.000330, 0.000170, 0.000000),
        425: (-0.000370, 0.000100, 0.000350),
        426: (-0.000500, -0.000050, -0.000300),
        428: (0.000280, 0.000000, 0.000250),
        429: (0.000130, 0.000000, -0.000250),
        431: (0.000350, 0.000000, 0.000300),
        432: (0.000330, 0.000000, -0.000300),
        500: (-0.000180, 0.000000, 0.000250),
        501: (-0.000330, 0.000050, -0.000250),
        3703: (0.000050, 0.000000, 0.000000),
        3705: (-0.000100, -0.000050, 0.000000),
        3734: (-0.000050, 0.000000, 0.000050),
        3735: (-0.000200, 0.000000, 0.000100),
        5078: (-0.000080, -0.000070, 0.000000),
        6780: (0.000100, 0.000000, 0.000000),
        6781: (-0.000020, 0.000020, 0.000000),
    }
    relaxation_pairs = {
        24: 6808, 27: 6811, 30: 6814,
        422: 7182, 423: 7183, 425: 7185, 426: 7186, 428: 7188, 429: 7189,
        431: 7191, 432: 7192, 500: 7249, 501: 7250,
        3703: 10371, 3705: 10373, 3734: 10402, 3735: 10403,
        5078: 11693, 6780: 13376, 6781: 13377,
    }

    mut_verts = [list(v) for v in raw_verts]
    for vi, (dx, dy, dz) in relaxation_offsets.items():
        mut_verts[vi][0] += dx
        mut_verts[vi][1] += dy
        mut_verts[vi][2] += dz
        ri = relaxation_pairs[vi]
        mut_verts[ri][0] -= dx
        mut_verts[ri][1] += dy
        mut_verts[ri][2] += dz
    relaxed_base_verts = [(v[0], v[1], v[2]) for v in mut_verts]

    # Quads to triangles
    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))

    # Test sweep across:
    # heights: 1.40m, 1.50m, 1.65m, 1.68m, 1.80m, 1.95m
    # head_ratios: 6.50, 7.41, 7.50, 7.80, 8.00
    print("Running 30-case parametric sweep across (h, hr)...")
    min_overall_area = float("inf")
    min_overall_dot = 1.0
    max_inv_count = 0
    worst_case = None

    for h in [1.40, 1.50, 1.65, 1.68, 1.80, 1.95]:
        for hr in [6.50, 7.00, 7.41, 7.50, 8.00]:
            s = h / 1.65
            target_head_height = h / hr
            head_scale = target_head_height / (0.2227 * s)

            tv = [list(v) for v in relaxed_base_verts]
            for i in range(len(tv)):
                tv[i][0] *= s
                tv[i][1] *= s
                tv[i][2] *= s
                z = tv[i][2]
                if z >= 1.36 * s:
                    t_head = max(0.0, min(1.0, (z - 1.36 * s) / (0.08 * s)))
                    w_head = t_head * t_head * (3.0 - 2.0 * t_head)
                    curr_scale = 1.0 + (head_scale - 1.0) * w_head
                    tv[i][0] *= curr_scale
                    tv[i][1] *= curr_scale
                    tv[i][2] = 1.36 * s + (z - 1.36 * s) * curr_scale

            tv_tuple = [tuple(v) for v in tv]
            normals, _ = compute_relaxed_vertex_normals(tv_tuple, raw_quads)

            # Area & dot audit
            for fi, f in enumerate(raw_tris):
                a = compute_tri_area(tv_tuple[f[0]], tv_tuple[f[1]], tv_tuple[f[2]])
                if a < min_overall_area:
                    min_overall_area = a
                    worst_case = (h, hr, fi, f)

                # Normal check on head
                if tv_tuple[f[0]][2] >= 1.30 * s:
                    p0, p1, p2 = tv_tuple[f[0]], tv_tuple[f[1]], tv_tuple[f[2]]
                    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
                    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
                    fn = (
                        v1[1] * v2[2] - v1[2] * v2[1],
                        v1[2] * v2[0] - v1[0] * v2[2],
                        v1[0] * v2[1] - v1[1] * v2[0],
                    )
                    l = math.sqrt(fn[0]**2 + fn[1]**2 + fn[2]**2) or 1.0
                    fn_u = (fn[0] / l, fn[1] / l, fn[2] / l)
                    vn_avg = [
                        (normals[f[0]][k] + normals[f[1]][k] + normals[f[2]][k]) / 3.0
                        for k in range(3)
                    ]
                    vl = math.sqrt(sum(k * k for k in vn_avg)) or 1.0
                    vn_u = (vn_avg[0] / vl, vn_avg[1] / vl, vn_avg[2] / vl)
                    dot = fn_u[0] * vn_u[0] + fn_u[1] * vn_u[1] + fn_u[2] * vn_u[2]
                    if dot < min_overall_dot:
                        min_overall_dot = dot
                    if dot < -0.05:
                        max_inv_count += 1

    print("==================================================================")
    print("PARAMETRIC SWEEP RESULTS (30 configurations):")
    print(f"  Absolute Minimum Face Area: {min_overall_area:.6e} m^2")
    print(f"  Worst-case configuration:   h={worst_case[0]}m, hr={worst_case[1]}, fi={worst_case[2]}, face={worst_case[3]}")
    print(f"  Minimum Normal Dot Product: {min_overall_dot:.4f}")
    print(f"  Total Inverted Faces:       {max_inv_count}")
    print("==================================================================")
    assert min_overall_area > 1.15e-7, f"Min area {min_overall_area} <= 1.15e-7"
    assert min_overall_dot > -0.05, f"Min dot {min_overall_dot} <= -0.05"
    assert max_inv_count == 0, f"Found {max_inv_count} inverted faces"
    print("ALL 30 PARAMETRIC CONFIGURATIONS PASSED WITH FLYING COLORS!")

if __name__ == "__main__":
    test_proposed_offsets_full()
