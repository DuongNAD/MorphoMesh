import math
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir

def compute_tri_area_np(p0, p1, p2):
    v1 = p1 - p0
    v2 = p2 - p0
    c = np.cross(v1, v2)
    return 0.5 * np.linalg.norm(c)

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
                raw_verts.append(np.array([bx, by, bz]))
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                v_idx = [int(pt.split("/")[0]) - 1 for pt in parts]
                if len(v_idx) == 4:
                    raw_quads.append(tuple(v_idx))

    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))

    # Bottle-neck canthus triangles: 9132, 8828, 1608, 1615, 9133
    target_tris = [9132, 8828, 1608, 1615, 9133]
    active_verts = [24, 27, 30, 5078, 6779, 6780, 6781, 6783]
    
    eps = 1e-6
    for ti in target_tris:
        t = raw_tris[ti]
        a0 = compute_tri_area_np(raw_verts[t[0]], raw_verts[t[1]], raw_verts[t[2]])
        print(f"\n--- tri {ti}: verts={t}, area={a0:.6e} ---")
        for vi in t:
            if vi in active_verts:
                grad = []
                for d in range(3):
                    raw_verts[vi][d] += eps
                    a1 = compute_tri_area_np(raw_verts[t[0]], raw_verts[t[1]], raw_verts[t[2]])
                    raw_verts[vi][d] -= 2*eps
                    a2 = compute_tri_area_np(raw_verts[t[0]], raw_verts[t[1]], raw_verts[t[2]])
                    raw_verts[vi][d] += eps
                    grad.append((a1 - a2) / (2 * eps))
                print(f"  d(Area)/d(v{vi}): [{grad[0]:+.6f}, {grad[1]:+.6f}, {grad[2]:+.6f}]")

if __name__ == "__main__":
    main()
