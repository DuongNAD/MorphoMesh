import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir, compute_relaxed_vertex_normals

def main():
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

    raw_verts = np.array(raw_verts, dtype=np.float64)
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

    proposed_offsets = {
        24: np.array([0.000650, 0.000100, 0.000000]),
        27: np.array([0.000100, -0.000300, 0.000150]),
        30: np.array([-0.000150, -0.000350, 0.000000]),
        422: np.array([-0.000150, -0.000100, -0.000200]),
        423: np.array([0.000000, 0.000200, 0.000000]),
        425: np.array([-0.000500, 0.000100, 0.000450]),
        426: np.array([-0.000500, -0.000050, -0.000300]),
        428: np.array([0.000280, 0.000000, 0.000250]),
        429: np.array([-0.000120, 0.000150, -0.000250]),
        431: np.array([0.000350, 0.000000, 0.000300]),
        432: np.array([0.000200, 0.000000, -0.000300]),
        500: np.array([-0.000280, 0.000100, 0.000550]),
        501: np.array([-0.000290, 0.000000, -0.000100]),
        3705: np.array([0.000000, -0.000100, 0.000000]),
        3734: np.array([-0.000020, 0.000000, 0.000070]),
        3735: np.array([-0.000300, 0.000000, 0.000100]),
        5078: np.array([-0.000420, -0.000170, 0.000000]),
        6781: np.array([-0.000500, 0.000000, 0.000000]),
        6783: np.array([0.000000, -0.000200, 0.000000]),
    }

    v_mut = np.copy(raw_verts)
    for vi, off in proposed_offsets.items():
        v_mut[vi] += off
        if vi in pairs:
            ri = pairs[vi]
            v_mut[ri] += np.array([-off[0], off[1], off[2]])

    verts_list = [tuple(v) for v in v_mut]
    normals, _ = compute_relaxed_vertex_normals(verts_list, raw_quads)

    p0 = v_mut[raw_tris[:, 0]]
    p1 = v_mut[raw_tris[:, 1]]
    p2 = v_mut[raw_tris[:, 2]]
    v1 = p1 - p0
    v2 = p2 - p0
    fn = np.cross(v1, v2)
    fn_len = np.linalg.norm(fn, axis=1, keepdims=True)
    fn_len[fn_len == 0] = 1.0
    fn_u = fn / fn_len

    vn = np.array(normals)
    vn_avg = (vn[raw_tris[:, 0]] + vn[raw_tris[:, 1]] + vn[raw_tris[:, 2]]) / 3.0
    vn_len = np.linalg.norm(vn_avg, axis=1, keepdims=True)
    vn_len[vn_len == 0] = 1.0
    vn_u = vn_avg / vn_len

    dots = np.sum(fn_u * vn_u, axis=1)
    worst_fi = np.argsort(dots)[:5]
    print("Worst 5 normal dots:")
    for fi in worst_fi:
        print(f"  fi={fi:5d}, dot={dots[fi]:.4f}, tri={raw_tris[fi]}")

if __name__ == "__main__":
    main()
