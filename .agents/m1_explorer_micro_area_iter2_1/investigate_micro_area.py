import math
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from morphomesh.human_generator import load_anatomical_base_mold, generate_human_base_mesh
from morphomesh.models import HumanAnatomyConfig
from morphomesh.inference_adapter import MeshGeometry

def compute_face_area(p0, p1, p2):
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)

def audit_mesh(cfg):
    res = generate_human_base_mesh(cfg)
    mesh = res.mesh
    verts = mesh.vertices
    faces = mesh.faces
    areas = []
    for fi, f in enumerate(faces):
        a = compute_face_area(verts[f[0]], verts[f[1]], verts[f[2]])
        areas.append((a, fi, f))
    areas.sort(key=lambda x: x[0])
    return areas, mesh

def main():
    print("=== BASE AUDIT ===")
    configs = [
        ("stylized_heroine_1.65m", HumanAnatomyConfig(height=1.65, head_ratio=7.41)),
        ("stylized_heroine_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=7.41)),
        ("realistic_female_1.40m_hr7.5", HumanAnatomyConfig(height=1.40, head_ratio=7.50)),
        ("realistic_female_1.40m_hr8.0", HumanAnatomyConfig(height=1.40, head_ratio=8.00)),
        ("petite_1.40m", HumanAnatomyConfig(height=1.40, head_ratio=6.50)),
    ]

    for name, cfg in configs:
        areas, mesh = audit_mesh(cfg)
        print(f"\n--- {name} ---")
        print(f"Min face area: {areas[0][0]:.6e} m^2 at fi={areas[0][1]}, face={areas[0][2]}")
        print("Smallest 10 faces:")
        for a, fi, f in areas[:10]:
            print(f"  fi={fi:5d}: area={a:.6e}, verts={f}")

if __name__ == "__main__":
    main()
