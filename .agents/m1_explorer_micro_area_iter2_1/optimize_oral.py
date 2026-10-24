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

def compute_normals(verts, tris):
    p0 = verts[tris[:, 0]]
    p1 = verts[tris[:, 1]]
    p2 = verts[tris[:, 2]]
    v1 = p1 - p0
    v2 = p2 - p0
    c = np.cross(v1, v2)
    norm = np.linalg.norm(c, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    return c / norm

def main():
    raw_verts, raw_quads = load_raw_mh_base()

    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))
    raw_tris = np.array(raw_tris, dtype=np.int64)

    # Let's select oral cluster vertices
    variable_verts = [422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3735]
    n_vars = len(variable_verts)
    
    # All triangles containing ANY of these vertices
    tri_mask = np.isin(raw_tris[:, 0], variable_verts) | np.isin(raw_tris[:, 1], variable_verts) | np.isin(raw_tris[:, 2], variable_verts)
    tri_indices = np.where(tri_mask)[0]
    sub_tris = raw_tris[tri_indices]

    print(f"Variable vertices ({n_vars}): {variable_verts}")
    print(f"Incident triangles: {len(sub_tris)}")

    # Initial offsets from current implementation
    curr_offsets = {
        422: [0.000000, -0.000100, -0.000100],
        423: [-0.000350, 0.000050, 0.000000],
        425: [-0.000350, 0.000100, 0.000300],
        426: [-0.000350, -0.000050, -0.000300],
        428: [0.000280, 0.000000, 0.000250],
        429: [0.000280, 0.000000, -0.000250],
        431: [0.000350, 0.000000, 0.000300],
        432: [0.000350, 0.000000, -0.000300],
        500: [-0.000280, 0.000000, 0.000250],
        501: [-0.000280, 0.000000, -0.000250],
        3735: [-0.000150, 0.000000, 0.000100],
    }
    x0 = np.zeros((n_vars, 3))
    for i, vi in enumerate(variable_verts):
        if vi in curr_offsets:
            x0[i] = curr_offsets[vi]

    # Target area at canonical 1.65m: 2.10e-7 m^2
    target_area = 2.10e-7

    def loss_fn(params):
        # params is (n_vars, 3)
        v = np.copy(raw_verts)
        for i, vi in enumerate(variable_verts):
            v[vi] += params[i]
        
        areas = compute_tri_areas(v, sub_tris)
        
        # Softplus / barrier penalty for areas < target_area
        diff = target_area - areas
        # Smooth penalty: sum of exp(k * diff) or sum of max(0, diff)^2
        pen = np.sum(np.maximum(0.0, diff) ** 2) * 1e18
        
        # Maximize minimum area directly: penalty = (min_area - target)^2
        min_a = np.min(areas)
        min_pen = (max(0.0, target_area - min_a) ** 2) * 1e18
        
        # Regularization on displacement magnitude
        reg = np.sum(params ** 2) * 1e6
        
        return pen + min_pen + reg

    # Gradient descent with Adam
    params = np.copy(x0)
    m = np.zeros_like(params)
    v_opt = np.zeros_like(params)
    lr = 1e-6
    eps = 1e-7

    print("Initial min area:", np.min(compute_tri_areas(raw_verts + (lambda v: [params[variable_verts.index(vi)] if vi in variable_verts else [0,0,0] for vi in range(len(v))])(raw_verts), sub_tris)))

if __name__ == "__main__":
    main()
