import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir

def main():
    templates_dir = _get_templates_dir()
    obj_path = templates_dir / "makehuman_clean_body.obj"

    raw_verts = []
    s_scale = 1.65 / 1.66589

    with open(obj_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                cx, cy, cz = float(parts[1]), float(parts[2]), float(parts[3])
                bx = 0.1 * cx * s_scale
                by = -0.1 * cz * s_scale
                bz = 0.1 * (cy + 8.1676) * s_scale
                raw_verts.append(np.array([bx, by, bz]))

    # Find bilateral pairs: for each vertex with x < -1e-5, find vertex with x' ≈ -x, y' ≈ y, z' ≈ z
    verts_arr = np.array(raw_verts)
    
    test_verts = [24, 27, 30, 422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3703, 3704, 3705, 3706, 3734, 3735, 4856, 5078, 6779, 6780, 6781, 6783]
    
    pairs = {}
    for vi in test_verts:
        v = verts_arr[vi]
        # Target is (-v[0], v[1], v[2])
        target = np.array([-v[0], v[1], v[2]])
        dists = np.linalg.norm(verts_arr - target, axis=1)
        best_match = np.argmin(dists)
        best_dist = dists[best_match]
        pairs[vi] = (best_match, best_dist)
        print(f"Vertex {vi:5d} -> Pair {best_match:5d} (dist = {best_dist:.8f} m)")

if __name__ == "__main__":
    main()
