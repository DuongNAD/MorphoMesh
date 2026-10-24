
import bpy, math, mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"E:/tool/mcp/MorphoMesh/output/anime_girl_v2/anime_girl_anim_28.glb")
scene = bpy.context.scene

# Evaluated bounds at frame 30
scene.frame_set(30)
mesh = [obj for obj in scene.objects if obj.type == 'MESH'][0]
dg = bpy.context.evaluated_depsgraph_get()
eval_obj = mesh.evaluated_get(dg)
eval_mesh = eval_obj.to_mesh()
verts = [eval_obj.matrix_world @ v.co for v in eval_mesh.vertices]
min_z = min(v.z for v in verts)
max_z = max(v.z for v in verts)
min_y = min(v.y for v in verts)
max_y = max(v.y for v in verts)
min_x = min(v.x for v in verts)
max_x = max(v.x for v in verts)
eval_obj.to_mesh_clear()

height = max_z - min_z
center_x = (min_x + max_x) / 2.0
center_y = (min_y + max_y) / 2.0
center_z = (min_z + max_z) / 2.0

# Frame range
start_frame = 1
end_frame = 60
if bpy.data.actions:
    for act in bpy.data.actions:
        start_frame = min(start_frame, int(act.frame_range[0]))
        end_frame = max(end_frame, int(act.frame_range[1]))
end_frame = min(end_frame, 150)
scene.frame_start = start_frame
scene.frame_end = end_frame
scene.render.fps = 30

# Studio World & Floor
studio_color = (0.11, 0.12, 0.15, 1.0)
scene.world = bpy.data.worlds.new('World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = studio_color
scene.world.node_tree.nodes['Background'].inputs[1].default_value = 1.0

bpy.ops.mesh.primitive_plane_add(size=30, location=(center_x, center_y, min_z - 0.02))
floor = bpy.context.active_object
mat = bpy.data.materials.new('StudioFloor')
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = studio_color
bsdf.inputs['Roughness'].default_value = 0.5
floor.data.materials.append(mat)

# Target
target = bpy.data.objects.new('Target', None)
scene.collection.objects.link(target)
target.location = (center_x, center_y, center_z)

# Camera with subtle orbit
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 55.0
cam_obj = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

dist = height * 1.85
total_f = end_frame - start_frame + 1
for i in range(total_f):
    f = start_frame + i
    t = i / max(total_f - 1, 1)
    ang = math.radians(-10.0 + 20.0 * math.sin(t * math.pi))
    cx = center_x + dist * math.sin(ang)
    cy = center_y - dist * math.cos(ang)
    cz = center_z + 0.12
    cam_obj.location = (cx, cy, cz)
    cam_obj.keyframe_insert(data_path="location", frame=f)

ttc = cam_obj.constraints.new('TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'

# Studio 3-point Lighting
key_data = bpy.data.lights.new('Key', 'AREA')
key_data.energy = 650.0
key_data.size = 2.0
key_data.color = (1.0, 0.96, 0.92)
key_obj = bpy.data.objects.new('Key', key_data)
scene.collection.objects.link(key_obj)
key_obj.location = (center_x + 1.8, center_y - 2.2, center_z + 1.5)
key_obj.constraints.new('TRACK_TO').target = target

fill_data = bpy.data.lights.new('Fill', 'AREA')
fill_data.energy = 280.0
fill_data.size = 2.5
fill_data.color = (0.88, 0.93, 1.0)
fill_obj = bpy.data.objects.new('Fill', fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (center_x - 2.2, center_y - 1.8, center_z + 0.8)
fill_obj.constraints.new('TRACK_TO').target = target

rim_data = bpy.data.lights.new('Rim', 'AREA')
rim_data.energy = 550.0
rim_data.size = 1.5
rim_data.color = (1.0, 0.88, 0.78)
rim_obj = bpy.data.objects.new('Rim', rim_data)
scene.collection.objects.link(rim_obj)
rim_obj.location = (center_x + 0.4, center_y + 1.9, center_z + 1.3)
rim_obj.constraints.new('TRACK_TO').target = target

# Render settings
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
scene.render.filepath = r"E:/tool/mcp/MorphoMesh/output/anime_girl_v2/anime_girl_perfect_wave.mp4"

print('Rendering animation frames...')
bpy.ops.render.render(animation=True)
print('Blender render complete!')
