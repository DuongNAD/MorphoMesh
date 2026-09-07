import sys
import os
import math
from collections import defaultdict

sys.path.insert(0, 'src')

from morphomesh.human_generator import HumanAnatomyGenerator, HumanAnatomyConfig, compute_quad_metrics
from morphomesh.blender_bridge import BlenderBridge

print("=== 1. VERIFYING 100% PURE QUADS ===")
gen = HumanAnatomyGenerator()
cfg_default = HumanAnatomyConfig()
res_default = gen.generate(cfg_default)
mesh_default = res_default.mesh

quad_count = sum(1 for f in mesh_default.faces if len(f) == 4)
tri_count = sum(1 for f in mesh_default.faces if len(f) == 3)
ngon_count = sum(1 for f in mesh_default.faces if len(f) > 4)
total_faces = len(mesh_default.faces)
quad_ratio = quad_count / total_faces if total_faces > 0 else 0.0

print(f"Python Generator Faces: Total={total_faces}, Quads={quad_count}, Tris={tri_count}, Ngons={ngon_count}")
print(f"Dynamic quad ratio: {quad_ratio:.4f}")
assert tri_count == 0, f"Found {tri_count} triangles!"
assert ngon_count == 0, f"Found {ngon_count} ngons!"
assert quad_ratio == 1.0, f"Quad ratio is {quad_ratio}, expected 1.0!"

metrics = compute_quad_metrics(mesh_default)
print(f"compute_quad_metrics: {metrics}")
assert metrics["quad_ratio"] == 1.0
assert metrics["tri_count"] == 0

print("\n=== 2. VERIFYING WATERTIGHT CLOSED 2-MANIFOLD SURFACES ===")
# Build edge map
edge_to_faces = defaultdict(list)
for face_idx, face in enumerate(mesh_default.faces):
    n = len(face)
    for i in range(n):
        v1 = face[i]
        v2 = face[(i + 1) % n]
        edge = tuple(sorted((v1, v2)))
        edge_to_faces[edge].append(face_idx)

total_edges = len(edge_to_faces)
boundary_edges = [edge for edge, faces in edge_to_faces.items() if len(faces) == 1]
non_manifold_edges = [edge for edge, faces in edge_to_faces.items() if len(faces) > 2]
two_manifold_edges = [edge for edge, faces in edge_to_faces.items() if len(faces) == 2]

print(f"Total Unique Edges: {total_edges}")
print(f"2-Manifold Edges: {len(two_manifold_edges)}")
print(f"Boundary Edges: {len(boundary_edges)}")
print(f"Non-Manifold Edges (>2 faces): {len(non_manifold_edges)}")

assert len(boundary_edges) == 0, f"Found {len(boundary_edges)} boundary edges! Mesh is not watertight!"
assert len(non_manifold_edges) == 0, f"Found {len(non_manifold_edges)} non-manifold edges!"
assert len(two_manifold_edges) == total_edges, "Not all edges are 2-manifold!"

# Check zero-area faces
zero_area_faces = 0
for f in mesh_default.faces:
    v0 = mesh_default.vertices[f[0]]
    v1 = mesh_default.vertices[f[1]]
    v2 = mesh_default.vertices[f[2]]
    e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
    e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
    cp = (
        e1[1]*e2[2] - e1[2]*e2[1],
        e1[2]*e2[0] - e1[0]*e2[2],
        e1[0]*e2[1] - e1[1]*e2[0]
    )
    area = 0.5 * math.sqrt(cp[0]**2 + cp[1]**2 + cp[2]**2)
    if area < 1e-8:
        zero_area_faces += 1

print(f"Zero area faces: {zero_area_faces}")
assert zero_area_faces == 0, f"Found {zero_area_faces} zero-area degenerate faces!"

print("\n=== 3. VERIFYING OUTWARD LIMB NORMAL VECTORS ===")
def check_limb_normals(vgroup_name, center_xy):
    v_indices = set(mesh_default.vertex_groups.get(vgroup_name, []))
    if not v_indices:
        print(f"Warning: {vgroup_name} not found in vertex_groups")
        return 0, 0
    inward = 0
    total = 0
    cx, cy = center_xy
    for f in mesh_default.faces:
        if all(vid in v_indices for vid in f):
            v0 = mesh_default.vertices[f[0]]
            v1 = mesh_default.vertices[f[1]]
            v2 = mesh_default.vertices[f[2]]
            e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
            e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
            nx = e1[1]*e2[2] - e1[2]*e2[1]
            ny = e1[2]*e2[0] - e1[0]*e2[2]
            nz = e1[0]*e2[1] - e1[1]*e2[0]
            fcx = sum(mesh_default.vertices[vi][0] for vi in f) / 4.0
            fcy = sum(mesh_default.vertices[vi][1] for vi in f) / 4.0
            rx = fcx - cx
            ry = fcy - cy
            dot_xy = nx * rx + ny * ry
            total += 1
            if dot_xy < 0:
                inward += 1
    return inward, total

inward_arm_l, total_arm_l = check_limb_normals("arm_upper_L", (0.35, 0.0))
inward_arm_r, total_arm_r = check_limb_normals("arm_upper_R", (-0.35, 0.0))
inward_leg_l, total_leg_l = check_limb_normals("leg_upper_L", (0.10, 0.0))
inward_leg_r, total_leg_r = check_limb_normals("leg_upper_R", (-0.10, 0.0))

print(f"Arm L normals: {inward_arm_l} inward out of {total_arm_l} faces")
print(f"Arm R normals: {inward_arm_r} inward out of {total_arm_r} faces")
print(f"Leg L normals: {inward_leg_l} inward out of {total_leg_l} faces")
print(f"Leg R normals: {inward_leg_r} inward out of {total_leg_r} faces")
assert inward_arm_l == 0 and inward_arm_r == 0, "Inward arm normals detected!"
assert inward_leg_l == 0 and inward_leg_r == 0, "Inward leg normals detected!"

print("\n=== 4. VERIFYING PARAMETRIC RESPONSIVENESS ===")
def max_vert_delta(r1, r2):
    m1 = r1.mesh
    m2 = r2.mesh
    assert len(m1.vertices) == len(m2.vertices)
    return max(
        math.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2 + (p1[2]-p2[2])**2)
        for p1, p2 in zip(m1.vertices, m2.vertices)
    )

res_head_small = gen.generate(HumanAnatomyConfig(head_ratio=5.5))
res_head_large = gen.generate(HumanAnatomyConfig(head_ratio=8.5))
delta_head = max_vert_delta(res_head_small, res_head_large)
print(f"Delta head_ratio (5.5 vs 8.5): {delta_head:.4f}m (threshold > 0.05m)")
assert delta_head > 0.05, f"head_ratio change did not alter geometry sufficiently ({delta_head}m)"

res_waist_thin = gen.generate(HumanAnatomyConfig(waist_girth=0.45))
res_waist_thick = gen.generate(HumanAnatomyConfig(waist_girth=1.10))
delta_waist = max_vert_delta(res_waist_thin, res_waist_thick)
print(f"Delta waist_girth (0.45 vs 1.10): {delta_waist:.4f}m (threshold > 0.05m)")
assert delta_waist > 0.05, f"waist_girth change did not alter geometry sufficiently ({delta_waist}m)"

res_chest_small = gen.generate(HumanAnatomyConfig(chest_girth=0.65))
res_chest_large = gen.generate(HumanAnatomyConfig(chest_girth=1.20))
delta_chest = max_vert_delta(res_chest_small, res_chest_large)
print(f"Delta chest_girth (0.65 vs 1.20): {delta_chest:.4f}m (threshold > 0.05m)")
assert delta_chest > 0.05, f"chest_girth change did not alter geometry sufficiently ({delta_chest}m)"

res_h_low = gen.generate(HumanAnatomyConfig(height=1.50))
res_h_high = gen.generate(HumanAnatomyConfig(height=1.80))
delta_h = max_vert_delta(res_h_low, res_h_high)
print(f"Delta height (1.50 vs 1.80): {delta_h:.4f}m (threshold > 0.05m)")
assert delta_h > 0.05, f"height change did not alter geometry sufficiently ({delta_h}m)"

print("\n=== 5. VERIFYING BLENDER NATIVE GENERATION & 29 VERTEX GROUPS ===")
bb = BlenderBridge()
res_blender = bb.create_human_asset(character_name="AuditorVerifyAll")
print(f"Blender asset status: {res_blender.get('status')}")
print(f"Blender vertex_count: {res_blender.get('vertex_count')}")
print(f"Blender face_count: {res_blender.get('face_count')}")
print(f"Blender quad_ratio: {res_blender.get('quad_ratio')}")
vgroups = res_blender.get('vertex_groups', [])
print(f"Blender vertex_groups count: {len(vgroups)}")
print(f"Vertex groups sample: {vgroups[:5]} ... {vgroups[-5:]}")

assert res_blender.get("status") == "success"
assert res_blender.get("vertex_count") == 2144
assert res_blender.get("face_count") == 2036
assert res_blender.get("quad_ratio") == 1.0
assert len(vgroups) == 29

print("\n=== ALL COMPREHENSIVE INTEGRITY CHECKS PASSED EMPIRICALLY! ===")
