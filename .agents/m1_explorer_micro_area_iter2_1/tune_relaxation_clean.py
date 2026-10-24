import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir, compute_relaxed_vertex_normals

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

def eval_config(raw_verts, quads, tris, offsets, pairs, h=1.40, hr=8.0, check_normals=True):
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

    areas = compute_tri_areas(tv, tris)
    min_idx = np.argmin(areas)
    min_area = areas[min_idx]

    if not check_normals:
        return min_area, 1.0, 0, min_idx

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

    return min_area, min_dot, inverted, min_idx

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

    # Baseline offsets
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

    # Active vertices to tune
    active_verts = [
        # Oral cluster
        422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3735, 3703, 3704, 3705, 3734,
        # Canthus cluster
        24, 27, 30, 5078, 6779, 6780, 6781, 6783
    ]
    for vi in active_verts:
        if vi not in offsets:
            offsets[vi] = np.zeros(3)

    # Pre-select sub-triangles (only head/face triangles, z >= 1.35 * 1.4/1.65)
    z_thresh = 1.35 * (1.40 / 1.65)
    p0 = raw_verts[raw_tris[:, 0]] * (1.40 / 1.65)
    head_mask = p0[:, 2] >= z_thresh
    head_tris = raw_tris[head_mask]
    print(f"Head triangles for fast evaluation: {len(head_tris)} (out of {len(raw_tris)})")

    base_min, base_dot, inv, idx = eval_config(raw_verts, raw_quads, head_tris, offsets, pairs, check_normals=True)
    print(f"Starting: min_area={base_min:.4e} m^2, min_dot={base_dot:.4f}, inv={inv}")

    # Step schedule: [0.10mm, 0.05mm, 0.02mm]
    step_sizes = [0.00010, 0.00005, 0.00002]
    current_best_area = base_min

    for step in step_sizes:
        print(f"\n--- Running pass with step = {step*1000:.3f} mm ---")
        for iteration in range(5):
            improved = False
            for vi in active_verts:
                for dim in range(3):
                    best_dir = 0
                    for d in [-1.0, 1.0]:
                        offsets[vi][dim] += d * step
                        # Max displacement constraint: 0.65 mm
                        if np.linalg.norm(offsets[vi]) > 0.00065:
                            offsets[vi][dim] -= d * step
                            continue
                        
                        # First check fast area without normals
                        ma, _, _, _ = eval_config(raw_verts, raw_quads, head_tris, offsets, pairs, check_normals=False)
                        if ma > current_best_area + 1e-12:
                            # If area improved, verify normals
                            _, mdot, inv_count, _ = eval_config(raw_verts, raw_quads, head_tris, offsets, pairs, check_normals=True)
                            if mdot >= 0.22 and inv_count == 0:
                                current_best_area = ma
                                best_dir = d
                        offsets[vi][dim] -= d * step

                    if best_dir != 0:
                        offsets[vi][dim] += best_dir * step
                        improved = True

            print(f"  Iteration {iteration + 1}: min_area = {current_best_area:.4e} m^2")
            if not improved:
                break

    # Full mesh evaluation
    full_min, full_dot, full_inv, full_idx = eval_config(raw_verts, raw_quads, raw_tris, offsets, pairs, check_normals=True)
    print(f"\n=======================================================")
    print(f"FINAL FULL MESH at h=1.40, hr=8.0:")
    print(f"  min_face_area = {full_min:.6e} m^2 (fi={full_idx})")
    print(f"  min_normal_dot = {full_dot:.4f}")
    print(f"  inverted_faces = {full_inv}")
    print(f"=======================================================")

    print("\nNon-zero offsets dictionary:")
    print("relaxation_offsets = {")
    for vi in sorted(active_verts):
        if np.linalg.norm(offsets[vi]) > 1e-6:
            print(f"    {vi}: ({offsets[vi][0]:.6f}, {offsets[vi][1]:.6f}, {offsets[vi][2]:.6f}),")
    print("}")

if __name__ == "__main__":
    main()
