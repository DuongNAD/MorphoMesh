import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir

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

def compute_tri_areas_batch(verts, tris):
    p0 = verts[tris[:, 0]]
    p1 = verts[tris[:, 1]]
    p2 = verts[tris[:, 2]]
    v1 = p1 - p0
    v2 = p2 - p0
    c = np.cross(v1, v2)
    return 0.5 * np.linalg.norm(c, axis=1)

def smooth_min(areas, beta=1e7):
    # LogSumExp smooth minimum: -1/beta * log(sum(exp(-beta * areas)))
    min_a = np.min(areas)
    shifted = areas - min_a
    return min_a - (1.0 / beta) * np.log(np.sum(np.exp(-beta * shifted)))

def main():
    raw_verts, raw_quads = load_raw_mh_base()

    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))
    raw_tris = np.array(raw_tris, dtype=np.int64)

    # Let's inspect oral cluster
    # Vertices that can be relaxed in oral cluster:
    # 422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3703, 3704, 3705, 3706, 3734, 3735
    oral_verts = [422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3703, 3704, 3705, 3706, 3734, 3735]
    oral_tri_indices = [ti for ti, t in enumerate(raw_tris) if any(v in oral_verts for v in t)]
    oral_tri_arr = raw_tris[oral_tri_indices]

    print(f"Oral cluster has {len(oral_verts)} variable vertices and {len(oral_tri_arr)} triangles.")

    # Let's check the current relaxation in oral cluster
    curr_offsets = {
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

    test_verts = np.copy(raw_verts)
    for vi, off in curr_offsets.items():
        test_verts[vi] += off

    areas = compute_tri_areas_batch(test_verts, oral_tri_arr)
    print(f"Current Oral Min Area: {np.min(areas):.6e} m^2")
    print(f"Current Oral Smooth Min: {smooth_min(areas):.6e} m^2")

if __name__ == "__main__":
    main()
