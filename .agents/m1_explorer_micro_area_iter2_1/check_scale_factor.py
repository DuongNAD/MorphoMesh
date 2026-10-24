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
                raw_verts.append(np.array([bx, by, bz]))
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                v_idx = [int(pt.split("/")[0]) - 1 for pt in parts]
                if len(v_idx) == 4:
                    raw_quads.append(tuple(v_idx))

    return np.array(raw_verts), raw_quads

def compute_tri_area(p0, p1, p2):
    v1 = p1 - p0
    v2 = p2 - p0
    c = np.cross(v1, v2)
    return 0.5 * np.linalg.norm(c)

def main():
    raw_verts, raw_quads = load_raw_mh_base()

    raw_tris = []
    for q in raw_quads:
        raw_tris.append((q[0], q[1], q[2]))
        raw_tris.append((q[0], q[2], q[3]))

    # Target: at h=1.40, hr=8.0, area scale factor is approx:
    # s = 1.40 / 1.65 = 0.848485
    # head_scale = (1.40 / 8.0) / (0.2227 * s) = 0.926136
    # Total area scale factor for facial faces = s^2 * head_scale^2 = 0.617498
    cranial_scale_sq = (1.40 / 1.65)**2 * ((1.40 / 8.0) / (0.2227 * (1.40 / 1.65)))**2
    print(f"Worst-case facial area scale factor (h=1.40, hr=8.0): {cranial_scale_sq:.6f}")
    min_canonical_target = 1.25e-7 / cranial_scale_sq
    print(f"Required min area at canonical 1.65m for > 1.25e-7 at worst-case: {min_canonical_target:.6e} m^2")

if __name__ == "__main__":
    main()
