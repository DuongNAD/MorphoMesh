import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import load_anatomical_base_mold, generate_human_base_mesh
from morphomesh.models import HumanAnatomyConfig

def main():
    res = generate_human_base_mesh(HumanAnatomyConfig(height=1.65))
    mesh = res.mesh
    
    # Find face with verts containing 4870, 66, 69
    for fi, f in enumerate(mesh.faces):
        if set(f) == {4870, 66, 69}:
            pts = [mesh.vertices[vi] for vi in f]
            cx = sum(p[0] for p in pts) / 3.0
            cy = sum(p[1] for p in pts) / 3.0
            cz = sum(p[2] for p in pts) / 3.0
            print(f"fi={fi}, verts={f}, center=({cx:.4f}, {cy:.4f}, {cz:.4f})")

if __name__ == "__main__":
    main()
