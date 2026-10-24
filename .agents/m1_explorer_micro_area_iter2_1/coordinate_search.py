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

def compute_tri_areas(verts, tris):
    p0 = verts[tris[:, 0]]
    p1 = verts[tris[:, 1]]
    p2 = verts[tris[:, 2]]
    v1 = p1 - p0
    v2 = p2 - p0
    c = np.cross(v1, v2)
    return 0.5 * np.linalg.norm(c, axis=1)

def eval_config(raw_verts, tris, offsets, pairs, h=1.40, hr=8.0, sub_tris=None):
    v_mut = np.copy(raw_verts)
    for vi, off in offsets.items():
        v_mut[vi] += off
        if vi in pairs:
            ri = pairs[vi]
            v_mut[ri] += np.array([-off[0], off[1], off[2]])
    
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

    eval_tris = tris if sub_tris is None else sub_tris
    areas = compute_tri_areas(tv, eval_tris)
    min_idx = np.argmin(areas)
    return areas[min_idx], eval_tris[min_idx]

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

    # Initial offsets
    offsets = {
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

    # Potential vertices to optimize
    active_verts = list(offsets.keys()) + [3703, 3704, 3705, 3706, 3734, 27, 5078, 6779, 6783, 24, 6780, 6781]
    for vi in active_verts:
        if vi not in offsets:
            offsets[vi] = np.zeros(3)

    # Sub-triangles to speed up evaluation: only triangles containing ANY active vertex or their neighbors
    mask = np.isin(raw_tris[:, 0], active_verts) | np.isin(raw_tris[:, 1], active_verts) | np.isin(raw_tris[:, 2], active_verts)
    sub_tris = raw_tris[mask]
    print(f"Active vertices: {len(active_verts)}, sub-triangles: {len(sub_tris)}")

    base_min, tri = eval_config(raw_verts, raw_tris, offsets, pairs, h=1.40, hr=8.0, sub_tris=sub_tris)
    print(f"Starting min area: {base_min:.4e} m^2 (tri={tri})")

    # Coordinate search passes
    step_sizes = [0.00015, 0.00010, 0.00005, 0.00002, 0.00001]
    current_best = base_min

    for step in step_sizes:
        print(f"\n--- Running pass with step size = {step*1000:.3f} mm ---")
        improved = True
        pass_iter = 0
        while improved and pass_iter < 10:
            pass_iter += 1
            improved = False
            for vi in active_verts:
                for dim in range(3):
                    best_direction = 0
                    for direction in [-1.0, 1.0]:
                        offsets[vi][dim] += direction * step
                        # Check displacement magnitude limit: 0.7mm
                        if np.linalg.norm(offsets[vi]) > 0.00075:
                            offsets[vi][dim] -= direction * step
                            continue
                        new_min, tri = eval_config(raw_verts, raw_tris, offsets, pairs, h=1.40, hr=8.0, sub_tris=sub_tris)
                        if new_min > current_best + 1e-12:
                            current_best = new_min
                            best_direction = direction
                        offsets[vi][dim] -= direction * step

                    if best_direction != 0:
                        offsets[vi][dim] += best_direction * step
                        improved = True

            print(f"  Iteration {pass_iter}: current min area = {current_best:.4e} m^2")

    # Evaluate across entire mesh
    full_min, full_tri = eval_config(raw_verts, raw_tris, offsets, pairs, h=1.40, hr=8.0)
    print(f"\nFINAL RESULT across ENTIRE MESH at h=1.40, hr=8.0:")
    print(f"Min face area: {full_min:.6e} m^2 at tri={full_tri}")

    # Print non-zero offsets
    print("\nNon-zero offsets:")
    for vi in sorted(active_verts):
        if np.linalg.norm(offsets[vi]) > 1e-6:
            print(f"  {vi:5d}: ({offsets[vi][0]:+.6f}, {offsets[vi][1]:+.6f}, {offsets[vi][2]:+.6f}), # norm = {np.linalg.norm(offsets[vi])*1000:.3f} mm")

if __name__ == "__main__":
    main()
