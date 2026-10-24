"""
Blender 4.5 Python script to import animated GLB, set up studio lighting & camera, and render MP4 video.
"""

import os
import sys
import math
import bpy
import mathutils

def setup_scene(glb_path: str, output_video_path: str, width: int = 1080, height: int = 1080):
    print(f"[Blender] Loading animated GLB: {glb_path}")

    # 1. Clean scene
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # 2. Import GLTF/GLB
    bpy.ops.import_scene.gltf(filepath=glb_path)

    # 3. Analyze imported objects & find bounds
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == 'ARMATURE']

    if not meshes:
        print("[Blender Error] No meshes found in imported GLB!")
        return

    # Compute bounding box across all meshes
    min_x = min_y = min_z = float('inf')
    max_x = max_y = max_z = float('-inf')

    for obj in meshes:
        for corner in obj.bound_box:
            world_corner = obj.matrix_world @ mathutils.Vector(corner)
            min_x = min(min_x, world_corner.x)
            max_x = max(max_x, world_corner.x)
            min_y = min(min_y, world_corner.y)
            max_y = max(max_y, world_corner.y)
            min_z = min(min_z, world_corner.z)
            max_z = max(max_z, world_corner.z)

    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    char_height = max_z - min_z
    center_z = min_z + char_height * 0.55  # target chest/upper torso

    print(f"[Blender] Character bounds: height={char_height:.2f}m, center=({center_x:.2f}, {center_y:.2f}, {center_z:.2f})")

    # 4. Determine animation frame range
    start_frame = 1
    end_frame = 60

    if bpy.data.actions:
        for action in bpy.data.actions:
            frame_range = action.frame_range
            print(f"[Blender] Found Action '{action.name}': range={frame_range[0]} to {frame_range[1]}")
            start_frame = min(start_frame, int(frame_range[0]))
            end_frame = max(end_frame, int(frame_range[1]))
    else:
        # Check scene timeline markers or NLA tracks
        for obj in armatures:
            if obj.animation_data and obj.animation_data.action:
                act = obj.animation_data.action
                start_frame = int(act.frame_range[0])
                end_frame = int(act.frame_range[1])

    # Ensure at least 30 frames and clamp reasonable length (e.g. up to 150 frames = 5s)
    if end_frame - start_frame < 10:
        end_frame = start_frame + 60
    end_frame = min(end_frame, 150)

    scene = bpy.context.scene
    scene.frame_start = start_frame
    scene.frame_end = end_frame
    scene.render.fps = 30
    print(f"[Blender] Animation frames: {start_frame} -> {end_frame} @ 30fps")

    # 5. Add Studio Lighting
    # World background
    scene.world = bpy.data.worlds.new("StudioWorld")
    scene.world.use_nodes = True
    bg_node = scene.world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs[0].default_value = (0.08, 0.08, 0.1, 1.0)  # elegant dark slate
        bg_node.inputs[1].default_value = 0.8

    # Key Light (Warm soft front-right)
    key_light_data = bpy.data.lights.new(name="Key_Light", type='AREA')
    key_light_data.energy = 450.0
    key_light_data.color = (1.0, 0.95, 0.9)
    key_light_data.size = 1.5
    key_light_obj = bpy.data.objects.new(name="Key_Light", object_data=key_light_data)
    scene.collection.objects.link(key_light_obj)
    key_light_obj.location = (center_x + 1.8, center_y - 2.2, center_z + 1.2)

    # Fill Light (Cool soft front-left)
    fill_light_data = bpy.data.lights.new(name="Fill_Light", type='AREA')
    fill_light_data.energy = 200.0
    fill_light_data.color = (0.85, 0.92, 1.0)
    fill_light_data.size = 2.0
    fill_light_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_light_data)
    scene.collection.objects.link(fill_light_obj)
    fill_light_obj.location = (center_x - 2.0, center_y - 2.0, center_z + 0.8)

    # Rim / Back Light (Crisp rim outline from behind)
    rim_light_data = bpy.data.lights.new(name="Rim_Light", type='AREA')
    rim_light_data.energy = 380.0
    rim_light_data.color = (1.0, 0.88, 0.75)
    rim_light_data.size = 1.2
    rim_light_obj = bpy.data.objects.new(name="Rim_Light", object_data=rim_light_data)
    scene.collection.objects.link(rim_light_obj)
    rim_light_obj.location = (center_x + 0.5, center_y + 2.0, center_z + 1.5)

    # Point lights towards character center
    for l_obj in [key_light_obj, fill_light_obj, rim_light_obj]:
        ttc = l_obj.constraints.new(type='TRACK_TO')
        # Create empty at center for tracking
        empty_target = bpy.data.objects.new("LightTarget", None)
        scene.collection.objects.link(empty_target)
        empty_target.location = (center_x, center_y, center_z)
        ttc.target = empty_target
        ttc.track_axis = 'TRACK_NEGATIVE_Z'
        ttc.up_axis = 'UP_Y'

    # 6. Add Studio Backdrop Floor (curved cyclorama)
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=64,
        radius=3.0,
        depth=0.1,
        location=(center_x, center_y, min_z - 0.05)
    )
    floor_obj = bpy.context.active_object
    floor_mat = bpy.data.materials.new(name="FloorMat")
    floor_mat.use_nodes = True
    bsdf = floor_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.12, 0.13, 0.16, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.35
    floor_obj.data.materials.append(floor_mat)

    # 7. Add Camera & Smooth Camera Motion (subtle orbit)
    cam_data = bpy.data.cameras.new(name="RenderCamera")
    cam_data.lens = 55.0  # Portrait lens
    cam_data.sensor_width = 36.0
    cam_obj = bpy.data.objects.new(name="RenderCamera", object_data=cam_data)
    scene.collection.objects.link(cam_obj)
    scene.camera = cam_obj

    # Camera target empty
    cam_target = bpy.data.objects.new("CamTarget", None)
    scene.collection.objects.link(cam_target)
    cam_target.location = (center_x, center_y, center_z)

    cam_track = cam_obj.constraints.new(type='TRACK_TO')
    cam_track.target = cam_target
    cam_track.track_axis = 'TRACK_NEGATIVE_Z'
    cam_track.up_axis = 'UP_Y'

    # Camera distance based on character height to ensure full body framing
    cam_distance = max(char_height * 1.55, 2.5)

    # Animate camera subtle orbit from -15 deg to +15 deg
    total_frames = end_frame - start_frame + 1
    for i in range(total_frames):
        cur_frame = start_frame + i
        t = i / max(total_frames - 1, 1)
        # Subtle gentle sway around the front
        angle = math.radians(-12.0 + 24.0 * math.sin(t * math.pi))
        cx = center_x + cam_distance * math.sin(angle)
        cy = center_y - cam_distance * math.cos(angle)
        cz = center_z + 0.15 + 0.1 * math.cos(t * math.pi * 2)

        cam_obj.location = (cx, cy, cz)
        cam_obj.keyframe_insert(data_path="location", frame=cur_frame)

    # 8. Render Configuration
    os.makedirs(os.path.dirname(output_video_path), exist_ok=True)
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100

    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
    scene.render.ffmpeg.gopsize = 15
    scene.render.filepath = output_video_path

    print(f"[Blender] Starting render to: {output_video_path}")
    bpy.ops.render.render(animation=True)
    print(f"[Blender] Render completed successfully!")


if __name__ == "__main__":
    # Args passed after '--'
    argv = sys.argv
    if "--" in argv:
        args = argv[argv.index("--") + 1:]
    else:
        args = []

    if len(args) < 2:
        print("Usage: blender -b --python render_blender_video.py -- <input_glb> <output_mp4> [width] [height]")
        sys.exit(1)

    glb_file = args[0]
    out_video = args[1]
    res_w = int(args[2]) if len(args) > 2 else 1080
    res_h = int(args[3]) if len(args) > 3 else 1080

    setup_scene(glb_file, out_video, res_w, res_h)
