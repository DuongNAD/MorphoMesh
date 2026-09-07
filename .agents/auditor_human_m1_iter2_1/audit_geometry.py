import sys
import os

sys.path.insert(0, "src")
from morphomesh.human_generator import generate_human_base_mesh, compute_quad_metrics

res = generate_human_base_mesh()
mesh = res.mesh
faces = mesh.faces
verts = mesh.vertices

print("Total vertices:", len(verts))
print("Total faces (stored as triangles):", len(faces))

# Independent verification of quads
reconstructed_quads = []
isolated_tris = []
i = 0
while i < len(faces):
    if i + 1 < len(faces):
        f1 = faces[i]
        f2 = faces[i + 1]
        # Check if f1 and f2 form a quad (i0, i1, i2, i3)
        if f1[0] == f2[0] and f1[2] == f2[1]:
            v0, v1, v2, v3 = f1[0], f1[1], f1[2], f2[2]
            # Verify all 4 vertices are distinct
            if len({v0, v1, v2, v3}) == 4:
                reconstructed_quads.append((v0, v1, v2, v3))
                i += 2
                continue
    isolated_tris.append(faces[i])
    i += 1

total_polys = len(reconstructed_quads) + len(isolated_tris)
quad_ratio = len(reconstructed_quads) / total_polys if total_polys > 0 else 0

print(f"Independent Quad Count: {len(reconstructed_quads)}")
print(f"Independent Triangle Count: {len(isolated_tris)}")
print(f"Independent Quad Ratio: {quad_ratio:.6f}")
print(f"res.quad_ratio: {res.quad_ratio}")
assert len(isolated_tris) == 0, f"Found {len(isolated_tris)} isolated triangles!"
assert quad_ratio >= 0.95, f"Quad ratio {quad_ratio} < 0.95"
print("PASS: 100% Pure Quad Topology Verified Independently!")
