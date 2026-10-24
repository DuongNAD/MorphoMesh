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

def main():
    raw_verts, raw_quads = load_raw_mh_base()

    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))
    raw_tris = np.array(raw_tris, dtype=np.int64)

    # Core oral quads:
    # 267: (425, 422, 423, 426)
    # 268: (500, 425, 426, 501)
    # 269: (431, 428, 429, 432)
    # 320: (428, 500, 501, 429)
    # 3351: (426, 423, 3703, 3704)
    # 3308: (3734, 3735, 425, 500)
    # 3383: (422, 425, 3735, 3736)
    # 3279: (3705, 3706, 429, 501)
    # 3352: (501, 426, 3704, 3705)
    core_quad_indices = [267, 268, 269, 320, 3351, 3308, 3383, 3279, 3352]
    core_tri_indices = []
    for qi in core_quad_indices:
        core_tri_indices.extend([qi * 2, qi * 2 + 1])
    core_tris = raw_tris[core_tri_indices]

    areas_raw = compute_tri_areas(raw_verts, core_tris)
    print(f"Total raw area of 18 core triangles: {np.sum(areas_raw):.6e} m^2")
    print(f"Average area per triangle: {np.mean(areas_raw):.6e} m^2")
    print(f"Min raw area: {np.min(areas_raw):.6e} m^2, Max raw area: {np.max(areas_raw):.6e} m^2")

if __name__ == "__main__":
    main()
