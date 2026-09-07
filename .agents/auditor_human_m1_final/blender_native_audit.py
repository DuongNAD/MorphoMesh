import sys
import os
import tempfile
import subprocess

sys.path.insert(0, 'src')

from morphomesh.blender_bridge import BlenderBridge

bb = BlenderBridge()

base_script = bb._generate_create_human_asset_script({'character_name': 'AuditHumanBody'})

# Now append our detailed bmesh and polygon audits before the final emission or after
audit_check_snippet = """
import bmesh

obj = bpy.data.objects.get("AuditHumanBody_Base_Mesh") or bpy.data.objects.get("AuditHumanBody")
assert obj is not None, f"AuditHumanBody object not found in scene! Existing: {[o.name for o in bpy.data.objects]}"
me = obj.data

print("=== BLENDER NATIVE AUDIT START ===")
print(f"Object: {obj.name}")
print(f"Vertices: {len(me.vertices)}")
print(f"Edges: {len(me.edges)}")
print(f"Polygons: {len(me.polygons)}")

# 1. Quads verification
quad_polys = [p for p in me.polygons if len(p.vertices) == 4]
tri_polys = [p for p in me.polygons if len(p.vertices) == 3]
ngon_polys = [p for p in me.polygons if len(p.vertices) > 4]

print(f"Quads: {len(quad_polys)}, Tris: {len(tri_polys)}, Ngons: {len(ngon_polys)}")
dyn_quad_ratio = len(quad_polys) / len(me.polygons)
print(f"Dynamic quad ratio: {dyn_quad_ratio:.6f}")
assert len(tri_polys) == 0, f"Found {len(tri_polys)} triangles!"
assert len(ngon_polys) == 0, f"Found {len(ngon_polys)} ngons!"
assert len(quad_polys) == 2036, f"Expected 2036 quads, got {len(quad_polys)}"
assert dyn_quad_ratio == 1.0, f"Quad ratio is {dyn_quad_ratio}, expected 1.0"

# 2. Watertight closed 2-manifold check via BMesh
bm = bmesh.new()
bm.from_mesh(me)

boundary_edges = [e for e in bm.edges if e.is_boundary]
non_manifold_edges = [e for e in bm.edges if not e.is_manifold]
non_manifold_verts = [v for v in bm.verts if not v.is_manifold]

print(f"Total BMesh edges: {len(bm.edges)}")
print(f"Boundary edges (open holes): {len(boundary_edges)}")
print(f"Non-manifold edges: {len(non_manifold_edges)}")
print(f"Non-manifold vertices: {len(non_manifold_verts)}")

assert len(boundary_edges) == 0, f"Mesh is NOT watertight! {len(boundary_edges)} boundary edges found!"
assert len(non_manifold_edges) == 0, f"{len(non_manifold_edges)} non-manifold edges found!"
assert len(non_manifold_verts) == 0, f"{len(non_manifold_verts)} non-manifold vertices found!"

# Zero area faces check
zero_area_faces = [f for f in bm.faces if f.calc_area() < 1e-8]
print(f"Zero-area faces: {len(zero_area_faces)}")
assert len(zero_area_faces) == 0, f"Found {len(zero_area_faces)} degenerate zero-area faces!"

bm.free()

# 3. Vertex Groups Population Check (29 groups)
print("\\n=== VERTEX GROUPS CHECK ===")
print(f"Total vertex groups on object: {len(obj.vertex_groups)}")
empty_groups = []
group_stats = {}
for vg in obj.vertex_groups:
    idx = vg.index
    assigned_count = 0
    for v in me.vertices:
        for g in v.groups:
            if g.group == idx and g.weight > 0.0:
                assigned_count += 1
                break
    group_stats[vg.name] = assigned_count
    if assigned_count == 0:
        empty_groups.append(vg.name)
    print(f"  - Group '{vg.name}': {assigned_count} vertices")

print(f"Empty groups count: {len(empty_groups)}")
assert len(obj.vertex_groups) == 29, f"Expected 29 vertex groups, got {len(obj.vertex_groups)}"
assert len(empty_groups) == 0, f"Found empty vertex groups: {empty_groups}"

# 4. Outward Normal Vectors on Limbs
print("\\n=== OUTWARD NORMAL VECTORS CHECK ===")
limb_checks = [
    ("arm_upper_L", 0.35, 0.0),
    ("arm_lower_L", 0.50, 0.0),
    ("arm_upper_R", -0.35, 0.0),
    ("arm_lower_R", -0.50, 0.0),
    ("leg_upper_L", 0.10, 0.0),
    ("leg_lower_L", 0.10, 0.0),
    ("leg_upper_R", -0.10, 0.0),
    ("leg_lower_R", -0.10, 0.0),
]

for gname, cx, cy in limb_checks:
    vg = obj.vertex_groups.get(gname)
    if not vg:
        continue
    idx = vg.index
    v_indices = {v.index for v in me.vertices for g in v.groups if g.group == idx and g.weight > 0.0}
    inward_count = 0
    total_group_polys = 0
    for p in me.polygons:
        if all(vi in v_indices for vi in p.vertices):
            total_group_polys += 1
            nx, ny, nz = p.normal
            fcx = p.center.x
            fcy = p.center.y
            rx = fcx - cx
            ry = fcy - cy
            dot_xy = nx * rx + ny * ry
            if dot_xy < 0:
                inward_count += 1
    print(f"Limb '{gname}': {inward_count} inward out of {total_group_polys} faces (XY plane dot product)")
    assert inward_count == 0, f"Found {inward_count} inward-facing polygons on {gname}!"

# 5. Landmarks Check
landmarks = dict(obj.get("morphomesh_landmarks", {}))
print(f"\\nTotal landmarks stored: {len(landmarks)}")
assert len(landmarks) == 24, f"Expected 24 landmarks, got {len(landmarks)}"

print("=== BLENDER NATIVE AUDIT END ===")
"""

full_script = base_script + "\n" + audit_check_snippet

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(full_script)
    tmp_path = f.name

cmd = [bb.blender_bin_path, "--background", "--python-exit-code", "1", "--python", tmp_path]
proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

try:
    os.unlink(tmp_path)
except Exception:
    pass

print("STDOUT:")
print(proc.stdout)
print("STDERR:")
print(proc.stderr)
print(f"Return code: {proc.returncode}")

assert proc.returncode == 0, f"Blender script execution failed with return code {proc.returncode}"
assert "=== BLENDER NATIVE AUDIT END ===" in proc.stdout, "Audit end marker not reached!"
print("\n>>> BLENDER NATIVE AUDIT PASSED 100% WITH RETURN CODE 0! <<<")
