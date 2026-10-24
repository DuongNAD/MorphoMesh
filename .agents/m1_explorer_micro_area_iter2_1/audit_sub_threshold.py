import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import generate_human_base_mesh
from morphomesh.models import HumanAnatomyConfig

def compute_face_area(p0, p1, p2):
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)

def find_sub_threshold_faces(h=1.40, head_ratio=8.0, threshold=1.15e-7):
    cfg = HumanAnatomyConfig(height=h, head_ratio=head_ratio)
    res = generate_human_base_mesh(cfg)
    mesh = res.mesh
    verts = mesh.vertices
    faces = mesh.faces
    sub_faces = []
    for fi, f in enumerate(faces):
        a = compute_face_area(verts[f[0]], verts[f[1]], verts[f[2]])
        if a <= threshold:
            sub_faces.append((a, fi, f))
    sub_faces.sort(key=lambda x: x[0])
    return sub_faces, mesh

def main():
    print("=== Sub-Threshold Faces Audit (Threshold = 1.15e-7 m^2) ===")
    
    cases = [
        ("h=1.40m, hr=8.0", 1.40, 8.0),
        ("h=1.40m, hr=7.5", 1.40, 7.5),
        ("h=1.40m, hr=7.41", 1.40, 7.41),
        ("h=1.40m, hr=6.5", 1.40, 6.5),
    ]
    
    for label, h, hr in cases:
        sub, mesh = find_sub_threshold_faces(h, hr, threshold=1.15e-7)
        print(f"\n{label}: Found {len(sub)} faces with area <= 1.15e-7 m^2")
        # Group by vertex sets or print unique left-side faces (x <= 0)
        unique_left = []
        for a, fi, f in sub:
            c = (mesh.vertices[f[0]][0] + mesh.vertices[f[1]][0] + mesh.vertices[f[2]][0]) / 3.0
            if c <= 0:
                unique_left.append((a, fi, f))
        print(f"  Left-side unique faces ({len(unique_left)}):")
        for a, fi, f in unique_left[:20]:
            print(f"    fi={fi:5d}: area={a:.6e}, verts={f}")

if __name__ == "__main__":
    main()
