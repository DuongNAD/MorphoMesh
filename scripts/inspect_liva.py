import bpy
import bmesh
import math
from mathutils import Vector

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"C:\Users\Admin\Downloads\_3D_Models_Assets\Liva.vrm")
scale_factor = 1.65 / 1.4649

base_arm = bpy.data.objects.get("Armature")
if base_arm:
    base_arm.scale = (scale_factor, scale_factor, scale_factor)

body = bpy.data.objects.get("Body")
# Delete fox tail (11), stockings (9), boots (10). KEEP hairback (1)!
bm = bmesh.new()
bm.from_mesh(body.data)
del_indices = {9, 10, 11}
faces_to_del = [f for f in bm.faces if f.material_index in del_indices]
bmesh.ops.delete(bm, geom=faces_to_del, context='FACES_ONLY')
verts_to_del = [v for v in bm.verts if len(v.link_faces) == 0]
bmesh.ops.delete(bm, geom=verts_to_del, context='VERTS')
bm.to_mesh(body.data)
bm.free()
body.data.update()

# Delete hair fox ears & front braids
hair = bpy.data.objects.get("Hair")
bm_h = bmesh.new()
bm_h.from_mesh(hair.data)
visited = set()
islands = []
for f in bm_h.faces:
    if f in visited: continue
    isl = [f]
    visited.add(f)
    st = [f]
    while st:
        curr = st.pop()
        for edge in curr.edges:
            for nxt in edge.link_faces:
                if nxt not in visited:
                    visited.add(nxt)
                    isl.append(nxt)
    islands.append(isl)

del_h_faces = []
for isl in islands:
    v_co = [v.co for f in isl for v in f.verts]
    max_z = max(c.z for c in v_co) * scale_factor
    min_z = min(c.z for c in v_co) * scale_factor
    max_y = max(c.y for c in v_co) * scale_factor
    min_y = min(c.y for c in v_co) * scale_factor
    center_x = sum(c.x for c in v_co) / len(v_co) * scale_factor
    center_y = sum(c.y for c in v_co) / len(v_co) * scale_factor
    center_z = sum(c.z for c in v_co) / len(v_co) * scale_factor
    if max_z > 1.48 and center_y > -0.03:
        del_h_faces.extend(isl)
    elif min_z < 1.15 and min_y < -0.05:
        del_h_faces.extend(isl)

bmesh.ops.delete(bm_h, geom=list(set(del_h_faces)), context='FACES_ONLY')
verts_to_del = [v for v in bm_h.verts if len(v.link_faces) == 0]
bmesh.ops.delete(bm_h, geom=verts_to_del, context='VERTS')
bm_h.to_mesh(hair.data)
bm_h.free()
hair.data.update()

# Shaders:
# Hair -> Silky Jet Black
hair_mats = list(hair.data.materials)
if len(body.data.materials) > 1 and body.data.materials[1]:
    hair_mats.append(body.data.materials[1])

for m in hair_mats:
    if m and m.node_tree:
        m.node_tree.nodes.clear()
        bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        out_n = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
        bsdf.inputs['Base Color'].default_value = (0.015, 0.014, 0.018, 1.0)
        bsdf.inputs['Roughness'].default_value = 0.28
        m.node_tree.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

# All clothing -> White Silk with soft shading
for m_idx in [2, 3, 4, 5, 6, 7, 9, 10]:
    if m_idx < len(body.data.materials):
        m = body.data.materials[m_idx]
        if m and m.node_tree:
            tex = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
            out_n = next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
            if not out_n: out_n = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf = next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if not bsdf: bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            m.node_tree.nodes.clear()
            out_n = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
            bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
            bsdf.inputs['Base Color'].default_value = (0.95, 0.94, 0.93, 1.0) # Ivory White Silk
            bsdf.inputs['Roughness'].default_value = 0.32
            if 'Subsurface Weight' in bsdf.inputs:
                bsdf.inputs['Subsurface Weight'].default_value = 0.10
            m.node_tree.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

# Waist Belt (material 8) -> Ice Blue Satin
if 8 < len(body.data.materials):
    m = body.data.materials[8]
    if m and m.node_tree:
        m.node_tree.nodes.clear()
        out_n = m.node_tree.nodes.new('ShaderNodeOutputMaterial')
        bsdf = m.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
        bsdf.inputs['Base Color'].default_value = (0.75, 0.85, 0.92, 1.0) # Ice blue
        bsdf.inputs['Roughness'].default_value = 0.20
        m.node_tree.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

# Skin: Porcelain SSS
m_skin = body.data.materials[0]
if m_skin and m_skin.node_tree:
    img = None
    for n in m_skin.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            img = n.image
            break
    m_skin.node_tree.nodes.clear()
    out_n = m_skin.node_tree.nodes.new('ShaderNodeOutputMaterial')
    bsdf = m_skin.node_tree.nodes.new('ShaderNodeBsdfPrincipled')
    if img:
        tex = m_skin.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = img
        m_skin.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.957, 0.894, 0.863, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.38
    if 'Subsurface Weight' in bsdf.inputs:
        bsdf.inputs['Subsurface Weight'].default_value = 0.25
        bsdf.inputs['Subsurface Radius'].default_value = (0.008, 0.004, 0.002)
    m_skin.node_tree.links.new(bsdf.outputs['BSDF'], out_n.inputs['Surface'])

# Tint EyeIris
mat_iris = bpy.data.materials.get("N00_000_00_EyeIris_00_EYE (Instance)")
if mat_iris and mat_iris.node_tree:
    em_node = next((n for n in mat_iris.node_tree.nodes if n.type == 'EMISSION'), None)
    tex_node = next((n for n in mat_iris.node_tree.nodes if n.type == 'TEX_IMAGE'), None)
    if em_node and tex_node:


        mix = mat_iris.node_tree.nodes.new('ShaderNodeMix')
        mix.data_type = 'RGBA'
        mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 0.85
        mix.inputs['B'].default_value = (0.22, 0.38, 0.32, 1.0)
        mat_iris.node_tree.links.new(tex_node.outputs['Color'], mix.inputs['A'])
        mat_iris.node_tree.links.new(mix.outputs['Result'], em_node.inputs['Color'])

# Add Camera (Portrait 85mm)
cam_data = bpy.data.cameras.new("Cam")
cam_data.lens = 85.0
cam_obj = bpy.data.objects.new("Cam", cam_data)
cam_obj.location = (0.0, -1.35, 1.48)
cam_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
bpy.context.scene.collection.objects.link(cam_obj)
bpy.context.scene.camera = cam_obj

# Add Lights
l1_d = bpy.data.lights.new("L1", 'AREA')
l1_d.energy = 300.0
l1_d.size = 1.2
l1_o = bpy.data.objects.new("L1", l1_d)
l1_o.location = (1.2, -1.8, 1.8)
bpy.context.scene.collection.objects.link(l1_o)

l2_d = bpy.data.lights.new("L2", 'AREA')
l2_d.energy = 140.0
l2_d.size = 1.2
l2_o = bpy.data.objects.new("L2", l2_d)
l2_o.location = (-1.2, -1.5, 1.6)
bpy.context.scene.collection.objects.link(l2_o)

# Rim hair light
l3_d = bpy.data.lights.new("L3", 'AREA')
l3_d.energy = 250.0
l3_d.size = 1.0
l3_o = bpy.data.objects.new("L3", l3_d)
l3_o.location = (0.0, 1.5, 2.0)
bpy.context.scene.collection.objects.link(l3_o)

# Render settings
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.samples = 64
bpy.context.scene.render.resolution_x = 720
bpy.context.scene.render.resolution_y = 960
bpy.context.scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\yu_nian_an\test_portrait_final.png"
bpy.ops.render.render(write_still=True)
print("Rendered test_portrait_final.png")
