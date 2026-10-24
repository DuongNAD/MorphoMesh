import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir, compute_relaxed_vertex_normals
from morphomesh.models import HumanAnatomyConfig

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
                raw_verts.append([bx, by, bz])
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                v_idx = [int(pt.split("/")[0]) - 1 for pt in parts]
                if len(v_idx) == 4:
                    raw_quads.append(tuple(v_idx))

    return np.array(raw_verts, dtype=np.float64), raw_quads

def compute_tri_areas(verts, tris):
    p0 = verts[tris[:, 0]]
    p1 = verts[tris[:, 1]]
    p2 = verts[tris[:, 2]]
    v1 = p1 - p0
    v2 = p2 - p0
    c = np.cross(v1, v2)
    return 0.5 * np.linalg.norm(c, axis=1)

def transform_and_eval(raw_verts, quads, tris, offsets, pairs, h=1.40, hr=8.0):
    # Apply relaxation
    v_mut = np.copy(raw_verts)
    for vi, off in offsets.items():
        v_mut[vi] += off
        if vi in pairs:
            ri = pairs[vi]
            v_mut[ri] += np.array([-off[0], off[1], off[2]])
    
    # Scale to h and hr
    s = h / 1.65
    target_head_height = h / hr
    head_scale = target_head_height / (0.2227 * s)

    tv = np.copy(v_mut) * s
    z_mask = tv[:, 2] >= 1.36 * s
    z_vals = tv[z_mask, 2]
    t_head = np.clip((z_vals - 1.36 * s) / (0.08 * s), 0.0, 1.0)
    w_head = t_head * t_head * (3.0 - 2.0 * t_head)
    curr_scale = 1.0 + (head_scale - 1.0) * w_head
    
    tv[z_mask, 0] *= curr_scale
    tv[z_mask, 1] *= curr_scale
    tv[z_mask, 2] = 1.36 * s + (z_vals - 1.36 * s) * curr_scale

    areas = compute_tri_areas(tv, tris)
    min_idx = np.argmin(areas)
    min_area = areas[min_idx]
    
    # Check normals
    verts_list = [tuple(v) for v in tv]
    normals, _ = compute_relaxed_vertex_normals(verts_list, quads)
    
    p0 = tv[tris[:, 0]]
    p1 = tv[tris[:, 1]]
    p2 = tv[tris[:, 2]]
    v1 = p1 - p0
    v2 = p2 - p0
    fn = np.cross(v1, v2)
    fn_len = np.linalg.norm(fn, axis=1, keepdims=True)
    fn_len[fn_len == 0] = 1.0
    fn_u = fn / fn_len

    vn = np.array(normals)
    vn_avg = (vn[tris[:, 0]] + vn[tris[:, 1]] + vn[tris[:, 2]]) / 3.0
    vn_len = np.linalg.norm(vn_avg, axis=1, keepdims=True)
    vn_len[vn_len == 0] = 1.0
    vn_u = vn_avg / vn_len

    dots = np.sum(fn_u * vn_u, axis=1)
    min_dot = np.min(dots)
    inverted = np.sum(dots < -0.05)

    return min_area, min_idx, tris[min_idx], min_dot, inverted

def main():
    raw_verts, raw_quads = load_raw_mh_base()
    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))
    raw_tris = np.array(raw_tris, dtype=np.int64)

    pairs = {
        24: 6808, 27: 6811, 30: 6814,
        422: 7182, 423: 7183, 425: 7185, 426: 7186, 428: 7188, 429: 7189,
        431: 7191, 432: 7192, 500: 7249, 501: 7250,
        3703: 10371, 3704: 10372, 3705: 10373, 3706: 10374,
        3734: 10402, 3735: 10403, 4856: 11474, 5078: 11693,
        6779: 13375, 6780: 13376, 6781: 13377, 6783: 13379
    }

    curr_offsets = {
        30: np.array([0.000000, -0.000200, 0.000000]),
        422: np.array([0.000000, -0.000100, -0.000100]),
        423: np.array([-0.000350, 0.000050, 0.000000]),
        425: np.array([-0.000350, 0.000100, 0.000300]),
        426: np.array([-0.000350, -0.000050, -0.000300]),
        428: np.array([0.000280, 0.000000, 0.000250]),
        429: np.array([0.000280, 0.000000, -0.000250]),
        431: np.array([0.000350, 0.000000, 0.000300]),
        432: np.array([0.000350, 0.000000, -0.000300]),
        500: np.array([-0.000280, 0.000000, 0.000250]),
        501: np.array([-0.000280, 0.000000, -0.000250]),
        3735: np.array([-0.000150, 0.000000, 0.000100]),
    }

    min_a, idx, tri, mdot, inv = transform_and_eval(raw_verts, raw_quads, raw_tris, curr_offsets, pairs, h=1.40, hr=8.0)
    print(f"Current baseline at h=1.40, hr=8.0: min_area={min_a:.4e} m^2 (fi={idx}, tri={tri}), min_dot={mdot:.4f}, inverted={inv}")

if __name__ == "__main__":
    main()
