
import bpy
import bmesh
import math
import os

bpy.ops.wm.open_mainfile(filepath=r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\Yu_Nian_An_Master.blend")
scene = bpy.context.scene

print("=== LIVE SCENE AUDIT ===")

# Audit Body Mesh
body = bpy.data.objects.get('Yu_Nian_An_Body')
assert body is not None, "Yu_Nian_An_Body missing!"
n_verts = len(body.data.vertices)
n_quads = sum(1 for p in body.data.polygons if len(p.vertices) == 4)
n_tris = sum(1 for p in body.data.polygons if len(p.vertices) == 3)
print(f"Body vertices: {n_verts} (must be 2144), quads: {n_quads} (must be 2036), tris: {n_tris} (must be 0)")
assert n_verts == 2144, f"Body verts {n_verts} != 2144"
assert n_quads == 2036, f"Body quads {n_quads} != 2036"
assert n_tris == 0, f"Body tris {n_tris} != 0"

# Audit Scalp Material on Body
scalp_mat_idx = [i for i, m in enumerate(body.data.materials) if m.name == 'Mat_Human_Scalp']
assert len(scalp_mat_idx) > 0, "Mat_Human_Scalp not in body materials!"
scalp_polys = [p for p in body.data.polygons if p.material_index == scalp_mat_idx[0]]
print(f"Body polygons with Mat_Human_Scalp: {len(scalp_polys)}")
assert len(scalp_polys) == 73, f"Expected 73 scalp polygons, got {len(scalp_polys)}"

# Audit Body Mouth Polygons: must be slot_skin
skin_mat_idx = [i for i, m in enumerate(body.data.materials) if m.name == 'Mat_Human_Skin_SSS'][0]
poly377 = body.data.polygons[377]
poly378 = body.data.polygons[378]
print(f"Poly 377 mat_idx: {poly377.material_index} (skin={skin_mat_idx}), Poly 378 mat_idx: {poly378.material_index}")
assert poly377.material_index == skin_mat_idx, "Poly 377 is not skin!"
assert poly378.material_index == skin_mat_idx, "Poly 378 is not skin!"

# Audit Mesh_Lips
lips = bpy.data.objects.get('Mesh_Lips')
assert lips is not None, "Mesh_Lips object missing!"
l_quads = sum(1 for p in lips.data.polygons if len(p.vertices) == 4)
l_tris = sum(1 for p in lips.data.polygons if len(p.vertices) == 3)
l_verts = len(lips.data.vertices)
print(f"Mesh_Lips verts: {l_verts} (expected 66), quads: {l_quads} (expected 50), tris: {l_tris} (expected 0)")
assert l_verts == 66, f"Mesh_Lips verts {l_verts} != 66"
assert l_quads == 50, f"Mesh_Lips quads {l_quads} != 50"
assert l_tris == 0, f"Mesh_Lips tris {l_tris} != 0"
assert lips.parent == body, "Mesh_Lips not parented to body!"
assert "DEF-head" in lips.vertex_groups, "DEF-head vertex group missing from Mesh_Lips!"
weights = [g.weight for g in lips.data.vertices[0].groups if g.group == lips.vertex_groups['DEF-head'].index]
print(f"Mesh_Lips DEF-head weight: {weights}")
assert weights and weights[0] == 1.0, f"Mesh_Lips DEF-head weight {weights} != 1.0"
lip_mat_names = [m.name for m in lips.data.materials]
print(f"Mesh_Lips materials: {lip_mat_names}")
assert "Mat_Human_Lips" in lip_mat_names, "Mat_Human_Lips missing from lips!"
assert "Mat_Human_Oral_Slit" in lip_mat_names, "Mat_Human_Oral_Slit missing from lips!"

# Audit Eyelids
for el_name in ['Mesh_Eyelid_Left', 'Mesh_Eyelid_Right']:
    el = bpy.data.objects.get(el_name)
    assert el is not None, f"{el_name} missing!"
    el_mats = [m.name for m in el.data.materials]
    print(f"{el_name} materials: {el_mats}")
    assert "Mat_Human_Eyeliner" in el_mats, f"Mat_Human_Eyeliner missing from {el_name}!"
    assert "Mat_Human_Skin_SSS" in el_mats, f"Mat_Human_Skin_SSS missing from {el_name}!"
    assert "DEF-head" in el.vertex_groups, f"DEF-head missing from {el_name}!"

# Audit Eye UVs
for eye_name in ['Mesh_Eye_Left_IrisPupil', 'Mesh_Eye_Right_IrisPupil']:
    eye = bpy.data.objects.get(eye_name)
    assert eye is not None, f"{eye_name} missing!"
    assert len(eye.data.uv_layers) > 0, f"{eye_name} has 0 UV layers!"
    print(f"{eye_name} UV layers: {len(eye.data.uv_layers)}")

# Audit Hair Bangs ribbon widths
bangs = bpy.data.objects.get('Hair_Hime_Bangs')
assert bangs is not None, "Hair_Hime_Bangs missing!"
widths = [max(bangs.data.vertices[v].co.x for v in p.vertices) - min(bangs.data.vertices[v].co.x for v in p.vertices) for p in bangs.data.polygons]
print(f"Hair_Hime_Bangs Quad X-widths: min={min(widths)*1000:.2f}mm, max={max(widths)*1000:.2f}mm, avg={sum(widths)/len(widths)*1000:.2f}mm")
assert sum(widths)/len(widths) >= 0.0070, f"Avg quad X-width {sum(widths)/len(widths)*1000:.2f}mm < 7.0mm!"
assert min(widths) >= 0.0050, f"Min quad X-width {min(widths)*1000:.2f}mm < 5.0mm!"

# Verify 3D ribbon cross-section width is exactly 7.50mm
bm_bangs = bmesh.new()
bm_bangs.from_mesh(bangs.data)
edge_widths = [e.calc_length() for e in bm_bangs.edges if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-4]
print(f"Hair_Hime_Bangs 3D edge widths: min={min(edge_widths)*1000:.2f}mm, avg={sum(edge_widths)/len(edge_widths)*1000:.2f}mm")
assert min(edge_widths) >= 0.00745, f"3D edge width {min(edge_widths)*1000:.2f}mm < 7.45mm!"
bm_bangs.free()

# Audit Hair Material settings
hair_mat = bpy.data.materials.get('Mat_Human_Hair')
assert hair_mat is not None, "Mat_Human_Hair missing!"
bsdf = next(n for n in hair_mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
print(f"Mat_Human_Hair: Roughness={bsdf.inputs['Roughness'].default_value}, Specular={bsdf.inputs['Specular IOR Level'].default_value}, Coat Weight={bsdf.inputs['Coat Weight'].default_value}, Coat Roughness={bsdf.inputs['Coat Roughness'].default_value}")
assert math.isclose(bsdf.inputs['Roughness'].default_value, 0.32, abs_tol=1e-4)
assert math.isclose(bsdf.inputs['Coat Weight'].default_value, 0.08, abs_tol=1e-4)
assert math.isclose(bsdf.inputs['Coat Roughness'].default_value, 0.30, abs_tol=1e-4)

# Audit Rim Light
rim = bpy.data.objects.get('Light_Rim_HairLight')
assert rim is not None, "Light_Rim_HairLight missing!"
print(f"Light_Rim_HairLight Energy={rim.data.energy}W (expected 450W), Size={rim.data.size}m (expected 1.0m)")
assert math.isclose(rim.data.energy, 450.0, abs_tol=1e-2), f"Rim energy {rim.data.energy} != 450.0"
assert math.isclose(rim.data.size, 1.0, abs_tol=1e-4), f"Rim size {rim.data.size} != 1.0"

print("AUDIT SUCCESSFUL! PROCEEDING TO RENDER...")

# Setup Render Settings
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.engine = 'CYCLES'
scene.cycles.samples = 128
scene.cycles.device = 'CPU'

# Render Portrait
cam_portrait = bpy.data.objects.get('Camera_Portrait_85mm')
assert cam_portrait is not None, "Camera_Portrait_85mm missing!"
scene.camera = cam_portrait
portrait_path = os.path.abspath("output/yu_nian_an/master_portrait_clean.png")
scene.render.filepath = portrait_path
print("Rendering portrait to:", portrait_path)
bpy.ops.render.render(write_still=True)
print("Portrait rendered! File size:", os.path.getsize(portrait_path))

# Render Fullbody
cam_fullbody = bpy.data.objects.get('Camera_FullBody')
assert cam_fullbody is not None, "Camera_FullBody missing!"
scene.camera = cam_fullbody
fullbody_path = os.path.abspath("output/yu_nian_an/master_fullbody_clean.png")
scene.render.filepath = fullbody_path
print("Rendering fullbody to:", fullbody_path)
bpy.ops.render.render(write_still=True)
print("Fullbody rendered! File size:", os.path.getsize(fullbody_path))

print("=== ALL RENDERS COMPLETE ===")
