import bpy, math, mathutils
from pathlib import Path

bpy.ops.wm.read_factory_settings(use_empty=True)
glb_path = r"E:\tool\mcp\MorphoMesh\output\anime_girl_v2\anime_girl_anim_28.glb"
bpy.ops.import_scene.gltf(filepath=glb_path)
scene = bpy.context.scene

mesh = bpy.data.objects['char1']
armature = [obj for obj in scene.objects if obj.type == 'ARMATURE'][0]

# 1. Dual Quaternion Skinning
for mod in mesh.modifiers:
    if mod.type == 'ARMATURE':
        mod.use_deform_preserve_volume = True

# 2. Skirt Weight Transfer: Bind outer skirt vertices to Hips
l_leg_idx = mesh.vertex_groups['LeftUpLeg'].index
r_leg_idx = mesh.vertex_groups['RightUpLeg'].index
for v in mesh.data.vertices:
    r = (v.co.x**2 + v.co.y**2)**0.5
    if 71.0 <= v.co.z <= 93.0 and r > 7.0:
        leg_w = 0.0
        for g in v.groups:
            if g.group in (l_leg_idx, r_leg_idx):
                leg_w += g.weight
                g.weight = 0.0
        if leg_w > 0:
            mesh.vertex_groups['Hips'].add([v.index], leg_w, 'ADD')

# 3. Shoes & Feet Stance: Clean, stable, flat on ground
for b_name in ['LeftFoot', 'RightFoot']:
    pb = armature.pose.bones.get(b_name)
    if pb:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        c = pb.constraints.new('LIMIT_ROTATION')
        c.owner_space = 'LOCAL'
        c.use_limit_x = True
        c.min_x = math.radians(-10)
        c.max_x = math.radians(10)
        c.use_limit_y = True
        c.min_y = math.radians(-5)
        c.max_y = math.radians(5)
        c.use_limit_z = True
        c.min_z = math.radians(-5)
        c.max_z = math.radians(5)
        c.influence = 0.85

for b_name in ['LeftToeBase', 'RightToeBase']:
    pb = armature.pose.bones.get(b_name)
    if pb:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        c = pb.constraints.new('LIMIT_ROTATION')
        c.owner_space = 'LOCAL'
        c.use_limit_x = True
        c.min_x = math.radians(-2)
        c.max_x = math.radians(2)
        c.influence = 0.95

# 4. CEL-SHADING & TOON SHADER (Shader to RGB -> 2-Tone Anime ColorRamp)
orig_mat = mesh.data.materials[0]
orig_mat.use_nodes = True
nt = orig_mat.node_tree
nodes = nt.nodes
links = nt.links

# Find Base Texture
tex_node = None
for n in nodes:
    if n.type == 'TEX_IMAGE' and n.image and 'texture_0' in n.image.name:
        tex_node = n
        break
if not tex_node:
    for n in nodes:
        if n.type == 'TEX_IMAGE':
            tex_node = n
            break

# Rebuild Node Tree for Crisp 2-Tone Anime Cel-Shading
saved_image = tex_node.image if tex_node else None
nodes.clear()

out_node = nodes.new('ShaderNodeOutputMaterial')
out_node.location = (800, 0)

diffuse = nodes.new('ShaderNodeBsdfDiffuse')
diffuse.location = (0, 100)
diffuse.inputs['Roughness'].default_value = 0.0

s2rgb = nodes.new('ShaderNodeShaderToRGB')
s2rgb.location = (200, 100)
links.new(diffuse.outputs['BSDF'], s2rgb.inputs['Shader'])

cramp = nodes.new('ShaderNodeValToRGB')
cramp.location = (400, 100)
cramp.color_ramp.interpolation = 'LINEAR'
cramp.color_ramp.elements[0].position = 0.35
cramp.color_ramp.elements[0].color = (0.75, 0.72, 0.80, 1.0)
cramp.color_ramp.elements[1].position = 0.50
cramp.color_ramp.elements[1].color = (1.0, 1.0, 1.0, 1.0)
links.new(s2rgb.outputs['Color'], cramp.inputs['Fac'])

mix = nodes.new('ShaderNodeMix')
mix.data_type = 'RGBA'
mix.blend_type = 'MULTIPLY'
mix.inputs['Factor'].default_value = 1.0
mix.location = (600, 0)
links.new(cramp.outputs['Color'], mix.inputs[6])

if saved_image:
    img_node = nodes.new('ShaderNodeTexImage')
    img_node.image = saved_image
    img_node.location = (200, -100)
    links.new(img_node.outputs['Color'], mix.inputs[7])

emission = nodes.new('ShaderNodeEmission')
emission.location = (700, 100)
links.new(mix.outputs[2], emission.inputs['Color'])
emission.inputs['Strength'].default_value = 1.0

links.new(emission.outputs['Emission'], out_node.inputs['Surface'])

# 5. INVERTED HULL OUTLINE (Clean anime ink lineart)
outline_mat = bpy.data.materials.new(name="Anime_Outline")
outline_mat.use_nodes = True
outline_mat.use_backface_culling = True
o_nodes = outline_mat.node_tree.nodes
o_links = outline_mat.node_tree.links
o_nodes.clear()
o_out = o_nodes.new('ShaderNodeOutputMaterial')
o_emis = o_nodes.new('ShaderNodeEmission')
o_emis.inputs['Color'].default_value = (0.15, 0.12, 0.16, 1.0)
o_emis.inputs['Strength'].default_value = 1.0
o_links.new(o_emis.outputs['Emission'], o_out.inputs['Surface'])

mesh.data.materials.append(outline_mat)
outline_mat_idx = len(mesh.data.materials) - 1

solid_mod = mesh.modifiers.new(name="Anime_Outline", type='SOLIDIFY')
solid_mod.thickness = -0.003
solid_mod.offset = 1.0
solid_mod.use_flip_normals = True
solid_mod.material_offset = outline_mat_idx
solid_mod.use_rim = False

# 6. BRIGHT, CLEAN ANIME STUDIO ENVIRONMENT
scene.world = bpy.data.worlds.new('AnimeWorld')
scene.world.use_nodes = True
wn = scene.world.node_tree.nodes
wl = scene.world.node_tree.links
wn.clear()
w_out = wn.new('ShaderNodeOutputWorld')
w_bg = wn.new('ShaderNodeBackground')
w_bg.inputs['Color'].default_value = (0.86, 0.90, 0.95, 1.0)
w_bg.inputs['Strength'].default_value = 1.0
wl.new(w_bg.outputs['Background'], w_out.inputs['Surface'])

# Floor
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0.0))
floor = bpy.context.active_object
fmat = bpy.data.materials.new('AnimeFloor')
fmat.use_nodes = True
fn = fmat.node_tree.nodes
f_bsdf = fn.get('Principled BSDF')
f_bsdf.inputs['Base Color'].default_value = (0.92, 0.94, 0.97, 1.0)
f_bsdf.inputs['Roughness'].default_value = 0.9
floor.data.materials.append(fmat)

# 7. 3-POINT ANIME LIGHTING
target = bpy.data.objects.new('Target', None)
scene.collection.objects.link(target)
target.location = (0.05, 0.0, 0.95)

key = bpy.data.lights.new('Key', 'SUN')
key.energy = 4.0
key.color = (1.0, 0.98, 0.95)
k_obj = bpy.data.objects.new('Key', key)
scene.collection.objects.link(k_obj)
k_obj.location = (2.0, -3.0, 3.0)
k_obj.constraints.new('TRACK_TO').target = target

fill = bpy.data.lights.new('Fill', 'SUN')
fill.energy = 1.5
fill.color = (0.85, 0.92, 1.0)
f_obj = bpy.data.objects.new('Fill', fill)
scene.collection.objects.link(f_obj)
f_obj.location = (-3.0, -2.0, 2.0)
f_obj.constraints.new('TRACK_TO').target = target

rim = bpy.data.lights.new('Rim', 'SUN')
rim.energy = 4.5
rim.color = (1.0, 0.92, 0.85)
r_obj = bpy.data.objects.new('Rim', rim)
scene.collection.objects.link(r_obj)
r_obj.location = (0.5, 3.0, 2.5)
r_obj.constraints.new('TRACK_TO').target = target

# 8. CINEMATIC CAMERA (Medium Close-Up Portrait, 65mm Anime lens)
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 65.0
cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

ttc = cam.constraints.new('TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'

# Medium close-up position framing anime girl beautifully
cam.location = (0.05, -2.4, 1.05)

# Render settings
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\anime_girl_v2\test_anime_cel_preview.png"

scene.frame_set(50)
print("[Blender] Rendering test frame 50 with true Anime Cel-Shading & Inverted Hull Outlines...")
bpy.ops.render.render(write_still=True)
print("[Blender] Test frame rendered successfully!")
