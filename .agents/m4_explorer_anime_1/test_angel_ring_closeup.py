"""
Full test of Hair Angel Ring closeup and analysis.
"""
import os
import sys
sys.path.insert(0, r"E:\tool\mcp\MorphoMesh\.agents\m4_explorer_anime_1")

import bpy
import mathutils

# Import material setup from test_shading_render
from test_shading_render import setup_toon_skin_material, setup_toon_hair_material, setup_toon_clothes_material

def run():
    print("Setting up materials...")
    skin_mat = setup_toon_skin_material("M_Anime_Skin")
    hair_mat = setup_toon_hair_material(
        "M_Anime_Hair",
        base_color=(0.18, 0.20, 0.32, 1.0), # #2E3352 rich anime hair
        shadow_color=(0.08, 0.09, 0.16, 1.0),
        crown_z_min=1.45,
        crown_z_max=1.56,
    )
    clothes_mat = setup_toon_clothes_material("M_Anime_Clothes")

    # Add 3-point lights
    key_data = bpy.data.lights.new(name="Key_Light", type='SUN')
    key_data.energy = 5.0
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new(name="Key_Light", object_data=key_data)
    key_obj.rotation_euler = (mathutils.Euler((0.6, 0.2, 0.5)))
    bpy.context.scene.collection.objects.link(key_obj)

    fill_data = bpy.data.lights.new(name="Fill_Light", type='SUN')
    fill_data.energy = 1.5
    fill_data.color = (0.90, 0.95, 1.0)
    fill_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_data)
    fill_obj.rotation_euler = (mathutils.Euler((0.6, -0.3, -0.7)))
    bpy.context.scene.collection.objects.link(fill_obj)

    # Set camera for portrait closeup on crown & face
    cam_data = bpy.data.cameras.new("Anime_Camera")
    cam_data.lens = 85.0
    cam = bpy.data.objects.new("Anime_Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    # Character head is around Z=1.52m, Y~0.0m
    cam.location = (0.0, -1.2, 1.52)
    cam.rotation_euler = (mathutils.Euler((1.5708, 0.0, 0.0)))

    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.render.resolution_x = 800
    scene.render.resolution_y = 800
    output_png = r"E:\tool\mcp\MorphoMesh\.agents\m4_explorer_anime_1\test_angel_ring_closeup.png"
    scene.render.filepath = output_png

    bpy.ops.render.render(write_still=True)
    print("Rendered closeup to:", output_png)

if __name__ == "__main__":
    sys.path.append(r"E:\tool\mcp\MorphoMesh\.agents\m4_explorer_anime_1")
    run()
