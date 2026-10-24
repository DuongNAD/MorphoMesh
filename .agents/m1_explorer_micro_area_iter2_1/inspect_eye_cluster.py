import math
import sys
from pathlib import Path
from collections import defaultdict

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

    v_to_quads = defaultdict(list)
    for qi, q in enumerate(raw_quads):
        for vi in q:
            v_to_quads[vi].append(qi)

    # Face 9132 is from quad 4566: verts (6779, 27, 5078)
    # What is quad 4566?
    print(f"Quad 4566: {raw_quads[4566]}")
    
    # Vertices of interest around medial canthus: 27, 30, 5078, 6770, 6779, 6783
    eye_verts = [27, 30, 5078, 6770, 6779, 6783]
    eye_quads = set()
    for vi in eye_verts:
        eye_quads.update(v_to_quads[vi])
    
    print("\n--- Eye Canthus Cluster Quads ---")
    for qi in sorted(eye_quads):
        print(f"quad {qi:5d}: {raw_quads[qi]}")

if __name__ == "__main__":
    main()
