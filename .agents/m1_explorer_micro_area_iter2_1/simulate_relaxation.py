import math
import sys
from pathlib import Path
from typing import Dict, Tuple, List

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir, compute_relaxed_vertex_normals
from morphomesh.models import HumanAnatomyConfig
from morphomesh.inference_adapter import MeshGeometry

def load_raw_mh_base():
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

    return raw_verts, raw_quads

def apply_relaxation(raw_verts, relaxation_offsets, relaxation_pairs):
    mut_verts = [list(v) for v in raw_verts]
    for vi, (dx, dy, dz) in relaxation_offsets.items():
        mut_verts[vi][0] += dx
        mut_verts[vi][1] += dy
        mut_verts[vi][2] += dz
        if vi in relaxation_pairs:
            ri = relaxation_pairs[vi]
            mut_verts[ri][0] -= dx
            mut_verts[ri][1] += dy
            mut_verts[ri][2] += dz
    return [(v[0], v[1], v[2]) for v in mut_verts]

def transform_mesh(verts, quads, cfg):
    height = cfg.height
    s = height / 1.65

    k_chest = cfg.chest_girth / 0.82
    k_waist = cfg.waist_girth / 0.58
    k_hip = cfg.hip_girth / 0.86
    k_shoulder = cfg.shoulder_width / 0.36
    k_arm = cfg.arm_span / 1.62
    k_leg = cfg.leg_length / 0.88

    target_head_ratio = cfg.head_ratio
    target_head_height = height / target_head_ratio
    head_scale = target_head_height / (0.2227 * s)

    transformed_verts = [[v[0] * s, v[1] * s, v[2] * s] for v in verts]

    for i, v in enumerate(transformed_verts):
        x, y, z = v

        # Cranial and Facial Vertical Scaling
        if z >= 1.36 * s:
            t_head = max(0.0, min(1.0, (z - 1.36 * s) / (0.08 * s)))
            w_head = t_head * t_head * (3.0 - 2.0 * t_head)
            curr_scale = 1.0 + (head_scale - 1.0) * w_head
            transformed_verts[i][0] = x * curr_scale
            transformed_verts[i][1] = y * curr_scale
            transformed_verts[i][2] = 1.36 * s + (z - 1.36 * s) * curr_scale

    # Triangulate
    faces = []
    for q in quads:
        faces.append((q[0], q[1], q[2]))
        faces.append((q[0], q[2], q[3]))

    final_verts = [(v[0], v[1], v[2]) for v in transformed_verts]
    return final_verts, faces

def compute_face_area(p0, p1, p2):
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)

def audit_areas_and_normals(verts, quads, faces):
    areas = []
    for fi, f in enumerate(faces):
        a = compute_face_area(verts[f[0]], verts[f[1]], verts[f[2]])
        areas.append((a, fi, f))
    areas.sort(key=lambda x: x[0])

    normals, _ = compute_relaxed_vertex_normals(verts, quads)
    min_dot = 1.0
    inverted = 0
    for fi, f in enumerate(faces):
        p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        fn = (
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0],
        )
        l = math.sqrt(fn[0] ** 2 + fn[1] ** 2 + fn[2] ** 2) or 1.0
        fn_u = (fn[0] / l, fn[1] / l, fn[2] / l)
        vn_avg = [
            (normals[f[0]][k] + normals[f[1]][k] + normals[f[2]][k]) / 3.0
            for k in range(3)
        ]
        vl = math.sqrt(sum(k * k for k in vn_avg)) or 1.0
        vn_u = (vn_avg[0] / vl, vn_avg[1] / vl, vn_avg[2] / vl)
        dot = fn_u[0] * vn_u[0] + fn_u[1] * vn_u[1] + fn_u[2] * vn_u[2]
        if dot < min_dot:
            min_dot = dot
        if dot < -0.05:
            inverted += 1

    return areas, min_dot, inverted

def main():
    raw_verts, raw_quads = load_raw_mh_base()

    # Current relaxation
    curr_offsets = {
        30: (0.000000, -0.000200, 0.000000),
        422: (0.000000, -0.000100, -0.000100),
        423: (-0.000350, 0.000050, 0.000000),
        425: (-0.000350, 0.000100, 0.000300),
        426: (-0.000350, -0.000050, -0.000300),
        428: (0.000280, 0.000000, 0.000250),
        429: (0.000280, 0.000000, -0.000250),
        431: (0.000350, 0.000000, 0.000300),
        432: (0.000350, 0.000000, -0.000300),
        500: (-0.000280, 0.000000, 0.000250),
        501: (-0.000280, 0.000000, -0.000250),
        3735: (-0.000150, 0.000000, 0.000100),
    }
    pairs = {
        500: 7249, 501: 7250, 428: 7188, 429: 7189,
        425: 7185, 426: 7186, 423: 7183, 431: 7191, 432: 7192,
        422: 7182, 30: 6814, 3735: 10403
    }

    print("--- CURRENT RELAXATION EVALUATION ---")
    for hr in [7.41, 7.50, 8.00]:
        cfg = HumanAnatomyConfig(height=1.40, head_ratio=hr)
        v_rel = apply_relaxation(raw_verts, curr_offsets, pairs)
        tv, faces = transform_mesh(v_rel, raw_quads, cfg)
        areas, min_dot, inverted = audit_areas_and_normals(tv, raw_quads, faces)
        print(f"hr={hr:.2f}: MinArea={areas[0][0]:.4e} m^2 (fi={areas[0][1]}), min_dot={min_dot:.4f}, inverted={inverted}")

    # Challenger 2 proposal: increase by +0.15mm for 423, 425, 426, 428, 429, 431, 432
    prop_offsets = dict(curr_offsets)
    prop_offsets[423] = (-0.000500, 0.000050, 0.000000)
    prop_offsets[425] = (-0.000500, 0.000100, 0.000450)
    prop_offsets[426] = (-0.000500, -0.000050, -0.000450)
    prop_offsets[428] = (0.000430, 0.000000, 0.000400)
    prop_offsets[429] = (0.000430, 0.000000, -0.000400)
    prop_offsets[431] = (0.000500, 0.000000, 0.000450)
    prop_offsets[432] = (0.000500, 0.000000, -0.000450)

    print("\n--- CHALLENGER 2 PROPOSAL EVALUATION ---")
    for hr in [7.41, 7.50, 8.00]:
        cfg = HumanAnatomyConfig(height=1.40, head_ratio=hr)
        v_rel = apply_relaxation(raw_verts, prop_offsets, pairs)
        tv, faces = transform_mesh(v_rel, raw_quads, cfg)
        areas, min_dot, inverted = audit_areas_and_normals(tv, raw_quads, faces)
        print(f"hr={hr:.2f}: MinArea={areas[0][0]:.4e} m^2 (fi={areas[0][1]}, face={areas[0][2]}), min_dot={min_dot:.4f}, inverted={inverted}")
        print("  Top 5 smallest faces:")
        for a, fi, f in areas[:5]:
            print(f"    fi={fi:5d}: area={a:.4e}, face={f}")

if __name__ == "__main__":
    main()
