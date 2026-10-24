import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import _get_templates_dir

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
                raw_verts.append((bx, by, bz))
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                v_idx = [int(pt.split("/")[0]) - 1 for pt in parts]
                if len(v_idx) == 4:
                    raw_quads.append(tuple(v_idx))

    # Triangulate quads as done in generate_human_base_mesh
    # Each quad (v0, v1, v2, v3) -> tri1 (v0, v1, v2), tri2 (v0, v2, v3)
    raw_tris = []
    quad_for_tri = []
    for qi, q in enumerate(raw_quads):
        raw_tris.append((q[0], q[1], q[2]))
        quad_for_tri.append(qi)
        raw_tris.append((q[0], q[2], q[3]))
        quad_for_tri.append(qi)

    print(f"Total raw verts: {len(raw_verts)}, raw quads: {len(raw_quads)}, raw tris: {len(raw_tris)}")

    def compute_tri_area(verts, t):
        p0, p1, p2 = verts[t[0]], verts[t[1]], verts[t[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)

    # Let's check areas without ANY relaxation
    raw_areas = [(compute_tri_area(raw_verts, t), ti, t, quad_for_tri[ti], raw_quads[quad_for_tri[ti]]) for ti, t in enumerate(raw_tris)]
    raw_areas.sort(key=lambda x: x[0])

    print("\n--- Top 15 Smallest Triangles in RAW MakeHuman Mesh (Before Relaxation) ---")
    for a, ti, t, qi, q in raw_areas[:15]:
        print(f"tri={ti:5d}, area={a:.6e}, tri_verts={t}, quad={qi:5d}, quad_verts={q}")

if __name__ == "__main__":
    main()
