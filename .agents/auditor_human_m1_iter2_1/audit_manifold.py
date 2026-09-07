import sys
from collections import defaultdict

sys.path.insert(0, "src")
from morphomesh.human_generator import generate_human_base_mesh

res = generate_human_base_mesh()
mesh = res.mesh
verts = mesh.vertices
faces = mesh.faces

print(f"Mesh stats: {len(verts)} vertices, {len(faces)} faces (stored as triangles)")

# 1. Edge analysis
edge_count = defaultdict(int)
directed_edge_count = defaultdict(int)

for fi, f in enumerate(faces):
    n = len(f)
    for i in range(n):
        v0, v1 = f[i], f[(i + 1) % n]
        # Undirected edge
        edge_key = tuple(sorted((v0, v1)))
        edge_count[edge_key] += 1
        # Directed edge
        directed_edge_count[(v0, v1)] += 1

boundary_edges = [e for e, count in edge_count.items() if count == 1]
non_manifold_edges = [e for e, count in edge_count.items() if count > 2]
two_manifold_edges = [e for e, count in edge_count.items() if count == 2]

print(f"Total unique edges: {len(edge_count)}")
print(f"Two-manifold edges (count == 2): {len(two_manifold_edges)}")
print(f"Boundary edges (count == 1): {len(boundary_edges)}")
print(f"Non-manifold edges (count > 2): {len(non_manifold_edges)}")

# 2. Check for zero-area faces
import math
zero_area_faces = []
for fi, f in enumerate(faces):
    p0, p1, p2 = verts[f[0]], verts[f[1]], verts[f[2]]
    # Cross product
    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
    cx = v1[1] * v2[2] - v1[2] * v2[1]
    cy = v1[2] * v2[0] - v1[0] * v2[2]
    cz = v1[0] * v2[1] - v1[1] * v2[0]
    area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
    if area < 1e-8:
        zero_area_faces.append(fi)

print(f"Zero-area faces: {len(zero_area_faces)}")

# 3. Check connected components
# Build adjacency graph
adj = defaultdict(set)
for e in edge_count.keys():
    adj[e[0]].add(e[1])
    adj[e[1]].add(e[0])

visited = set()
components = []
for v in range(len(verts)):
    if v not in visited:
        comp = []
        q = [v]
        visited.add(v)
        while q:
            curr = q.pop()
            comp.append(curr)
            for neighbor in adj[curr]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    q.append(neighbor)
        components.append(comp)

print(f"Connected components: {len(components)}")
for ci, comp in enumerate(components):
    print(f"  Component {ci}: {len(comp)} vertices")

# Assertions
assert len(boundary_edges) == 0, f"Found {len(boundary_edges)} boundary edges!"
assert len(non_manifold_edges) == 0, f"Found {len(non_manifold_edges)} non-manifold edges!"
assert len(zero_area_faces) == 0, f"Found {len(zero_area_faces)} zero-area faces!"
print("PASS: Closed 2-manifold check on MeshGeometry PASSED!")
