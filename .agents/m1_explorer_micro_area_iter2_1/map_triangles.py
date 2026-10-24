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

    # Current relaxation
    curr_offsets = {
        30: (0.000000, -0.000200, 0.000000),
        422: (0.000000, -0.000100, -0.000100),
        423: (-0.000350, 0.000050, 0.000000),
        425: (-0.000350, 0.000100, 0.000300),
        426: (-0.000350, -0.000050, -0.000300),
        428: (0.000280, 0.000000, 0.000250),
        429: (0.000280, 0.000000, -0.000250),
        431: (0.000350, 0.000000, 0.000300),
        432: (0.000350, 0.000000, -0.000300),
        500: (-0.000280, 0.000000, 0.000250),
        501: (-0.000280, 0.000000, -0.000250),
        3735: (-0.000150, 0.000000, 0.000100),
    }
    
    # Vertices in oral commissure:
    oral_verts = {422, 423, 425, 426, 428, 429, 431, 432, 500, 501, 3703, 3704, 3705, 3706, 3734, 3735}
    oral_tris = [ti for ti, t in enumerate(raw_tris) if any(v in oral_verts for v in t)]

    # Canthus verts:
    canthus_verts = {24, 27, 30, 4856, 4857, 5078, 5127, 6770, 6779, 6780, 6781, 6783}
    canthus_tris = [ti for ti, t in enumerate(raw_tris) if any(v in canthus_verts for v in t)]

    print(f"Oral commissure triangles: {len(oral_tris)}")
    print(f"Canthus triangles: {len(canthus_tris)}")

if __name__ == "__main__":
    main()
