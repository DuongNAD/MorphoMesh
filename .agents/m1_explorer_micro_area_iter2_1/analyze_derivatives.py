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

    # Let's inspect face 6702: verts 426, 423, 3703
    v426 = raw_verts[426]
    v423 = raw_verts[423]
    v3703 = raw_verts[3703]

    print("--- RAW VERTICES for Face 6702 ---")
    print(f"v426:  {v426}")
    print(f"v423:  {v423}")
    print(f"v3703: {v3703}")
    print(f"Edge 426->423:  {v423 - v426} (len={np.linalg.norm(v423 - v426):.6f})")
    print(f"Edge 426->3703: {v3703 - v426} (len={np.linalg.norm(v3703 - v426):.6f})")
    print(f"Edge 423->3703: {v3703 - v423} (len={np.linalg.norm(v3703 - v423):.6f})")

    area_raw = compute_tri_area_np(v426, v423, v3703)
    print(f"Raw Area: {area_raw:.6e} m^2")

    # Gradient of area wrt v426, v423, v3703
    eps = 1e-6
    for name, v_idx, v_arr in [("v426", 426, v426), ("v423", 423, v423), ("v3703", 3703, v3703)]:
        grad = []
        for d in range(3):
            v_arr[d] += eps
            a_plus = compute_tri_area_np(raw_verts[426], raw_verts[423], raw_verts[3703])
            v_arr[d] -= 2*eps
            a_minus = compute_tri_area_np(raw_verts[426], raw_verts[423], raw_verts[3703])
            v_arr[d] += eps
            grad.append((a_plus - a_minus) / (2 * eps))
        print(f"d(Area)/d({name}): [{grad[0]:+.6f}, {grad[1]:+.6f}, {grad[2]:+.6f}]")

if __name__ == "__main__":
    main()
