import bpy, math, mathutils

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

# 2. HEAD WEIGHT FIX: Clean ALL rogue arm, shoulder, leg weights from head & hair!
non_head_groups = [
    'RightHand', 'RightForeArm', 'RightArm', 'RightShoulder',
    'LeftHand', 'LeftForeArm', 'LeftArm', 'LeftShoulder',
    'RightUpLeg', 'RightLeg', 'RightFoot', 'RightToeBase',
    'LeftUpLeg', 'LeftLeg', 'LeftFoot', 'LeftToeBase',
    'Hips', 'Spine', 'Spine01', 'Spine02'
]

head_vg = mesh.vertex_groups.get('Head')
group_indices = {mesh.vertex_groups[name].index: name for name in non_head_groups if name in mesh.vertex_groups}

for v in mesh.data.vertices:
    # Everything above chin level (z >= 135.0 cm) belongs exclusively to Head!
    if v.co.z >= 135.0:
        for g in list(v.groups):
            if g.group in group_indices:
                w = g.weight
                if w > 0:
                    mesh.vertex_groups[group_indices[g.group]].remove([v.index])
                    head_vg.add([v.index], w, 'ADD')

# 3. SKIRT WEIGHT TRANSFER: Bind outer skirt vertices to Hips
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

# 4. SHOES & FEET STABILITY
for b_name in ['LeftFoot', 'RightFoot']:
    pb = armature.pose.bones.get(b_name)
    if pb:
        for c in list(pb.constraints):
            pb.constraints.remove(c)
        c = pb.constraints.new('LIMIT_ROTATION')
        c.owner_space = 'LOCAL'
        c.use_limit_x = True
        c.min_x = math.radians(-5)
        c.max_x = math.radians(5)
        c.use_limit_y = True
        c.min_y = math.radians(-4)
        c.max_y = math.radians(4)
        c.use_limit_z = True
        c.min_z = math.radians(-4)
        c.max_z = math.radians(4)
        c.influence = 0.90

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

# 5. CEL-SHADING
orig_mat = mesh.data.materials[0]
orig_mat.use_nodes = True
nt = orig_mat.node_tree
nodes = nt.nodes
links = nt.links

tex_node = None
for n in nodes:
    if n.type == 'TEX_IMAGE' and n.image:
        tex_node = n
        break

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
cramp.color_ramp.elements[0].position = 0.32
cramp.color_ramp.elements[0].color = (0.78, 0.75, 0.82, 1.0)
cramp.color_ramp.elements[1].position = 0.48
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

# 6. INVERTED HULL OUTLINE
outline_mat = bpy.data.materials.new(name="Anime_Outline")
outline_mat.use_nodes = True
outline_mat.use_backface_culling = True
o_nodes = outline_mat.node_tree.nodes
o_links = outline_mat.node_tree.links
o_nodes.clear()
o_out = o_nodes.new('ShaderNodeOutputMaterial')
o_emis = o_nodes.new('ShaderNodeEmission')
o_emis.inputs['Color'].default_value = (0.16, 0.12, 0.18, 1.0)
o_emis.inputs['Strength'].default_value = 1.0
o_links.new(o_emis.outputs['Emission'], o_out.inputs['Surface'])

mesh.data.materials.append(outline_mat)
outline_mat_idx = len(mesh.data.materials) - 1

solid_mod = mesh.modifiers.new(name="Anime_Outline", type='SOLIDIFY')
solid_mod.thickness = -0.0028
solid_mod.offset = 1.0
solid_mod.use_flip_normals = True
solid_mod.material_offset = outline_mat_idx
solid_mod.use_rim = False

# 7. ENVIRONMENT
scene.world = bpy.data.worlds.new('AnimeWorld')
scene.world.use_nodes = True
wn = scene.world.node_tree.nodes
wl = scene.world.node_tree.links
wn.clear()
w_out = wn.new('ShaderNodeOutputWorld')
w_bg = wn.new('ShaderNodeBackground')
w_bg.inputs['Color'].default_value = (0.90, 0.93, 0.97, 1.0)
w_bg.inputs['Strength'].default_value = 1.0
wl.new(w_bg.outputs['Background'], w_out.inputs['Surface'])

bpy.ops.mesh.primitive_plane_add(size=25, location=(0, 0, 0.0))
floor = bpy.context.active_object
fmat = bpy.data.materials.new('AnimeFloor')
fmat.use_nodes = True
fn = fmat.node_tree.nodes
f_bsdf = fn.get('Principled BSDF')
f_bsdf.inputs['Base Color'].default_value = (0.92, 0.94, 0.97, 1.0)
f_bsdf.inputs['Roughness'].default_value = 0.9
floor.data.materials.append(fmat)

# 8. LIGHTING
target = bpy.data.objects.new('Target', None)
scene.collection.objects.link(target)
target.location = (0.05, 0.0, 0.90)

key = bpy.data.lights.new('Key', 'SUN')
key.energy = 4.2
key.color = (1.0, 0.98, 0.95)
k_obj = bpy.data.objects.new('Key', key)
scene.collection.objects.link(k_obj)
k_obj.location = (2.5, -3.5, 3.5)
k_obj.constraints.new('TRACK_TO').target = target

fill = bpy.data.lights.new('Fill', 'SUN')
fill.energy = 1.8
fill.color = (0.85, 0.92, 1.0)
f_obj = bpy.data.objects.new('Fill', fill)
scene.collection.objects.link(f_obj)
f_obj.location = (-3.5, -2.5, 2.5)
f_obj.constraints.new('TRACK_TO').target = target

rim = bpy.data.lights.new('Rim', 'SUN')
rim.energy = 4.8
rim.color = (1.0, 0.90, 0.82)
r_obj = bpy.data.objects.new('Rim', rim)
scene.collection.objects.link(r_obj)
r_obj.location = (0.5, 3.5, 2.8)
r_obj.constraints.new('TRACK_TO').target = target

# 9. CAMERA (Close-up & Upper body to inspect head and waving arm)
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 65.0
cam = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam)
scene.camera = cam

ttc = cam.constraints.new('TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'

# Focus on head & upper body at frame 60 (exact frame user showed)
target.location = (0.05, 0.0, 1.35)
cam.location = (0.05, -2.1, 1.40)

scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080

scene.frame_set(60)
scene.render.filepath = r"E:\tool\mcp\MorphoMesh\output\anime_girl_v2\head_fixed_f60.png"
bpy.ops.render.render(write_still=True)
print("[Blender] Head-fixed frame 60 rendered successfully!")
