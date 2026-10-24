import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import load_anatomical_base_mold, generate_human_base_mesh
from morphomesh.models import HumanAnatomyConfig

def main():
    raw_verts, raw_quads, raw_uvs = load_anatomical_base_mold()
    
    # Check bilateral pairs in base mold
    print(f"Total raw verts: {len(raw_verts)}, total raw quads: {len(raw_quads)}")
    
    # Faces to inspect
    target_faces = [6702, 19941, 6617, 19854, 534, 13789, 6558, 19797, 9132, 22591]
    
    res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
    mesh = res.mesh
    
    print("\n--- Face Details (at h=1.65m) ---")
    for fi in target_faces:
        f = mesh.faces[fi]
        pts = [mesh.vertices[vi] for vi in f]
        cx = sum(p[0] for p in pts) / 3.0
        cy = sum(p[1] for p in pts) / 3.0
        cz = sum(p[2] for p in pts) / 3.0
        print(f"fi={fi:5d}, verts={f}, center=({cx:.4f}, {cy:.4f}, {cz:.4f})")
        for vi in f:
            v = mesh.vertices[vi]
            print(f"    v[{vi}]: ({v[0]:.6f}, {v[1]:.6f}, {v[2]:.6f})")

if __name__ == "__main__":
    main()
