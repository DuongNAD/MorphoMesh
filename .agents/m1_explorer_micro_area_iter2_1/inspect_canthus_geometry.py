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

    canthus_tris = [9132, 8828, 1608, 1615, 9133, 9186, 1609, 8824, 1617, 8827, 1614, 8826, 1610, 1611]
    
    verts_list = [tuple(v) for v in raw_verts]
    normals, _ = compute_relaxed_vertex_normals(verts_list, raw_quads)

    print("--- RAW CANTHUS TRIANGLES & VERTICES ---")
    for ti in canthus_tris:
        t = raw_tris[ti]
        p0, p1, p2 = raw_verts[t[0]], raw_verts[t[1]], raw_verts[t[2]]
        c = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0))
        print(f"tri {ti:5d}: area={c:.6e}, verts={t}")
        for vi in t:
            v = raw_verts[vi]
            n = normals[vi]
            print(f"   v[{vi:5d}]: pos=({v[0]:.6f}, {v[1]:.6f}, {v[2]:.6f}), norm=({n[0]:.3f}, {n[1]:.3f}, {n[2]:.3f})")

if __name__ == "__main__":
    main()
