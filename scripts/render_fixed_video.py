"""
Blender 4.5 Python script to render the fixed, high-quality anime girl animation:
- Dual Quaternion Skinning (Preserve Volume = True) to prevent shoulder, torso, and joint collapse
- Skirt Weight Correction: Transfer outer skirt weights from UpLegs to Hips so skirt stays crisp and undistorted
- Fixed shoes: Foot & ToeBase rotation limits to keep shoes flat and firm on the ground
- Soft Matte Anime Shading: Specular = 0.04, Roughness = 0.85, Subsurface Scattering for warm skin
- Soft diffuse studio lighting with elegant twilight backdrop
"""

import os
import sys
import math
import subprocess
from pathlib import Path
import bpy
import mathutils

def render_animation():
    glb_path = r"E:\tool\mcp\MorphoMesh\output\anime_girl_v2\anime_girl_anim_28.glb"
    out_mp4 = r"E:\tool\mcp\MorphoMesh\output\anime_girl_v2\anime_girl_fixed_cinematic.mp4"
    art_dir = Path(r"C:\Users\Admin\.gemini\antigravity\brain\c6634b96-78a4-4cad-9283-f7f70e7bb3a4")
    art_mp4 = art_dir / "anime_girl_fixed_cinematic.mp4"
    art_gif = art_dir / "anime_girl_fixed_cinematic.gif"
    art_snapshot = art_dir / "anime_girl_fixed_snapshot.png"

    print("[Blender] Resetting scene & importing GLB...")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    scene = bpy.context.scene

    armature = [obj for obj in scene.objects if obj.type == 'ARMATURE'][0]
    mesh = bpy.data.objects['char1']

    # 1. DUAL QUATERNION PRESERVE VOLUME (prevents joint/torso volume collapse)
    arm_mod = [m for m in mesh.modifiers if m.type == 'ARMATURE'][0]
    arm_mod.use_deform_preserve_volume = True

    # 2. SKIRT WEIGHT TRANSFER: Bind outer skirt to Hips instead of thighs
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

    # 3. FIX SHOES: Stabilize foot & toe bones
    for b_name in ['LeftFoot', 'RightFoot']:
        pb = armature.pose.bones.get(b_name)
        if pb:
            c = pb.constraints.new('LIMIT_ROTATION')
            c.owner_space = 'LOCAL'
            c.use_limit_y = True
            c.min_y = math.radians(-5)
            c.max_y = math.radians(5)
            c.use_limit_z = True
            c.min_z = math.radians(-10)
            c.max_z = math.radians(10)
            c.influence = 0.9

    for b_name in ['LeftToeBase', 'RightToeBase']:
        pb = armature.pose.bones.get(b_name)
        if pb:
            c = pb.constraints.new('LIMIT_ROTATION')
            c.owner_space = 'LOCAL'
            c.use_limit_x = True
            c.min_x = math.radians(-3)
            c.max_x = math.radians(3)
            c.influence = 0.95

    # 4. FIX MATERIAL: Soft Matte Anime Shading, No Plastic/Doll Sheen
    mat = mesh.data.materials[0]
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Roughness'].default_value = 0.85
        bsdf.inputs['Specular IOR Level'].default_value = 0.04
        if 'Subsurface Weight' in bsdf.inputs:
            bsdf.inputs['Subsurface Weight'].default_value = 0.05
            bsdf.inputs['Subsurface Scale'].default_value = 0.02
            bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.4, 0.3)

    # 5. Studio World & Floor (Seamless twilight gradient)
    studio_color = (0.16, 0.17, 0.22, 1.0)
    scene.world = bpy.data.worlds.new('World')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = studio_color
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 1.1

    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0.0))
    floor = bpy.context.active_object
    fmat = bpy.data.materials.new('FMat')
    fmat.use_nodes = True
    fmat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = studio_color
    fmat.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = 0.6
    floor.data.materials.append(fmat)

    # 6. Soft Anime Studio Lighting
    target = bpy.data.objects.new('Target', None)
    scene.collection.objects.link(target)
    target.location = (0.05, 0.0, 0.95)

    key = bpy.data.lights.new('Key', 'AREA')
    key.energy = 260.0
    key.size = 3.5
    key.color = (1.0, 0.97, 0.94)
    k_obj = bpy.data.objects.new('Key', key)
    scene.collection.objects.link(k_obj)
    k_obj.location = (1.2, -2.5, 1.8)
    k_obj.constraints.new('TRACK_TO').target = target

    fill = bpy.data.lights.new('Fill', 'AREA')
    fill.energy = 160.0
    fill.size = 4.0
    fill.color = (0.9, 0.94, 1.0)
    f_obj = bpy.data.objects.new('Fill', fill)
    scene.collection.objects.link(f_obj)
    f_obj.location = (-1.5, -2.0, 1.2)
    f_obj.constraints.new('TRACK_TO').target = target

    rim = bpy.data.lights.new('Rim', 'AREA')
    rim.energy = 300.0
    rim.size = 2.5
    rim.color = (1.0, 0.90, 0.82)
    r_obj = bpy.data.objects.new('Rim', rim)
    scene.collection.objects.link(r_obj)
    r_obj.location = (0.3, 1.8, 1.6)
    r_obj.constraints.new('TRACK_TO').target = target

    # 7. Camera Setup & Animation
    cam_data = bpy.data.cameras.new('Cam')
    cam_data.lens = 50.0
    cam = bpy.data.objects.new('Cam', cam_data)
    scene.collection.objects.link(cam)
    scene.camera = cam

    ttc = cam.constraints.new('TRACK_TO')
    ttc.target = target
    ttc.track_axis = 'TRACK_NEGATIVE_Z'
    ttc.up_axis = 'UP_Y'

    start_frame = 0
    end_frame = 128
    scene.frame_start = start_frame
    scene.frame_end = end_frame
    scene.render.fps = 30

    dist = 2.65
    total_f = end_frame - start_frame + 1
    for i in range(total_f):
        f = start_frame + i
        t = i / max(total_f - 1, 1)
        ang = math.radians(-3.0 + 6.0 * math.sin(t * math.pi))
        cx = 0.05 + dist * math.sin(ang)
        cy = -dist * math.cos(ang)
        cz = 1.05 + 0.02 * math.sin(t * math.pi * 2)
        cam.location = (cx, cy, cz)
        cam.keyframe_insert(data_path="location", frame=f)

    # 8. Render Configuration
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1080
    scene.render.image_settings.file_format = 'FFMPEG'
    scene.render.ffmpeg.format = 'MPEG4'
    scene.render.ffmpeg.codec = 'H264'
    scene.render.ffmpeg.constant_rate_factor = 'HIGH'
    scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
    scene.render.filepath = out_mp4

    print("[Blender] Rendering animation frames...")
    bpy.ops.render.render(animation=True)
    print(f"[Blender] Render finished! Saved to {out_mp4}")


if __name__ == "__main__":
    render_animation()
