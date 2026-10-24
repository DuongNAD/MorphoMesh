import sys
from pathlib import Path

mesh_path = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\meshes\Anime_Arms.obj")

verts = []
normals = []
with open(mesh_path, "r") as f:
    for line in f:
        if line.startswith("v "):
            verts.append([float(x) for x in line.strip().split()[1:4]])
        elif line.startswith("vn "):
            normals.append([float(x) for x in line.strip().split()[1:4]])

print(f"Total verts: {len(verts)}, normals: {len(normals)}")

# Filter vertices in left hand region: x > 0.38, y < -0.15, z < 1.06
hand_verts = []
for i, v in enumerate(verts):
    if v[0] > 0.38 and v[1] < -0.18 and v[2] < 1.06:
        n = normals[i] if i < len(normals) else [0, 0, 0]
        hand_verts.append((v, n))

print(f"Hand vertices count: {len(hand_verts)}")
# Find center of hand vertices
cx = sum(v[0][0] for v in hand_verts) / len(hand_verts)
cy = sum(v[0][1] for v in hand_verts) / len(hand_verts)
cz = sum(v[0][2] for v in hand_verts) / len(hand_verts)
print(f"Hand center: ({cx:.4f}, {cy:.4f}, {cz:.4f})")

# Look at normals on the index finger:
# Knuckle at (0.445, -0.262, 1.010), Tip at (0.449, -0.316, 0.966)
# Vertices near index finger mid-shaft: x ~ 0.449, y ~ -0.29, z ~ 0.99
idx_verts = [vn for vn in hand_verts if abs(vn[0][0] - 0.449) < 0.015 and abs(vn[0][1] - (-0.29)) < 0.02]
print(f"\nIndex finger segment verts: {len(idx_verts)}")
for v, n in idx_verts[:10]:
    print(f"  v: ({v[0]:.4f}, {v[1]:.4f}, {v[2]:.4f}) | n: ({n[0]:.4f}, {n[1]:.4f}, {n[2]:.4f})")
