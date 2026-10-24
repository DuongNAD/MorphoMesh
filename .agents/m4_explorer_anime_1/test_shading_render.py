"""
Test script to verify Toon Cel-Shading and Angel Ring in Blender 4.5.4 LTS headless.
Loads anime_animated.blend, builds materials, adds test lights & camera, and renders a test frame.
"""
import os
import sys
import bpy
import mathutils

def hex_to_rgb(hex_str: str) -> tuple[float, float, float, float]:
    hex_clean = hex_str.lstrip('#')
    r = int(hex_clean[0:2], 16) / 255.0
    g = int(hex_clean[2:4], 16) / 255.0
    b = int(hex_clean[4:6], 16) / 255.0
    return (r, g, b, 1.0)

def setup_toon_skin_material(mat_name: str = "M_Anime_Skin") -> bpy.types.Material:
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    # Diffuse BSDF (captures light irradiance)
    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.name = "Diffuse_BSDF"
    diffuse.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    diffuse.inputs["Roughness"].default_value = 1.0

    # Shader to RGB
    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.name = "Shader_To_RGB"

    # ColorRamp (Stepped CONSTANT cel-shading)
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.name = "ColorRamp"
    ramp.color_ramp.interpolation = "CONSTANT"
    # Element 0: Warm peach shadow tint (#DE8971 / #E5A898, conforms to test_tier1: R>0.90, G>0.70, B<0.75)
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = (0.98, 0.74, 0.68, 1.0)
    # Element 1: Base fair porcelain tone (#FFE2D4 / #FFF0E8)
    ramp.color_ramp.elements[1].position = 0.48
    ramp.color_ramp.elements[1].color = (1.0, 0.92, 0.88, 1.0)

    # Material Output
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    # Links
    nt.links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], out.inputs["Surface"])

    return mat

def setup_toon_hair_material(
    mat_name: str = "M_Anime_Hair",
    base_color: tuple[float, float, float, float] = (0.24, 0.25, 0.36, 1.0), # #3D405B
    shadow_color: tuple[float, float, float, float] = (0.12, 0.13, 0.20, 1.0),
    crown_z_min: float = 1.45,
    crown_z_max: float = 1.55,
) -> bpy.types.Material:
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    # 1. Base Diffuse Cel Shading
    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.name = "Diffuse_BSDF"
    diffuse.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    diffuse.inputs["Roughness"].default_value = 1.0

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.name = "Shader_To_RGB"

    cel_ramp = nt.nodes.new("ShaderNodeValToRGB")
    cel_ramp.name = "Cel_ColorRamp"
    cel_ramp.color_ramp.interpolation = "CONSTANT"
    cel_ramp.color_ramp.elements[0].position = 0.0
    cel_ramp.color_ramp.elements[0].color = shadow_color
    cel_ramp.color_ramp.elements[1].position = 0.45
    cel_ramp.color_ramp.elements[1].color = base_color

    # 2. Procedural Angel Ring (Object-space Z-band)
    tex_coord = nt.nodes.new("ShaderNodeTexCoord")
    tex_coord.name = "TextureCoordinate"

    sep_xyz = nt.nodes.new("ShaderNodeSeparateXYZ")
    sep_xyz.name = "SeparateXYZ"

    map_range = nt.nodes.new("ShaderNodeMapRange")
    map_range.name = "ObjectSpaceZBand"
    map_range.inputs["From Min"].default_value = crown_z_min
    map_range.inputs["From Max"].default_value = crown_z_max
    map_range.inputs["To Min"].default_value = 0.0
    map_range.inputs["To Max"].default_value = 1.0

    ring_ramp = nt.nodes.new("ShaderNodeValToRGB")
    ring_ramp.name = "AngelRing_ColorRamp"
    ring_ramp.color_ramp.interpolation = "LINEAR"
    ring_ramp.color_ramp.elements[0].position = 0.35
    ring_ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ring_ramp.color_ramp.elements[1].position = 0.50
    ring_ramp.color_ramp.elements[1].color = (1.0, 1.0, 0.95, 1.0)
    e_close = ring_ramp.color_ramp.elements.new(0.65)
    e_close.color = (0.0, 0.0, 0.0, 1.0)

    # 3. Light / Diffuse Gating (MATH: MULTIPLY)
    math_gate = nt.nodes.new("ShaderNodeMath")
    math_gate.name = "DiffuseGating"
    math_gate.operation = "MULTIPLY"

    # 4. Composite Mix onto Base Hair
    mix_final = nt.nodes.new("ShaderNodeMix")
    mix_final.name = "AngelRing_Mix"
    mix_final.data_type = "RGBA"
    mix_final.blend_type = "MIX"
    # B input is the highlight color
    mix_final.inputs[7].default_value = (1.0, 1.0, 0.95, 1.0)

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    # Link node tree
    nt.links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], cel_ramp.inputs["Fac"])

    nt.links.new(tex_coord.outputs["Object"], sep_xyz.inputs["Vector"])
    nt.links.new(sep_xyz.outputs["Z"], map_range.inputs["Value"])
    nt.links.new(map_range.outputs["Result"], ring_ramp.inputs["Fac"])

    nt.links.new(ring_ramp.outputs["Color"], math_gate.inputs[0])
    nt.links.new(s2rgb.outputs["Color"], math_gate.inputs[1])

    # Gated factor controls blend between base cel color (A) and highlight (B)
    nt.links.new(math_gate.outputs["Value"], mix_final.inputs[0])
    nt.links.new(cel_ramp.outputs["Color"], mix_final.inputs[6])
    nt.links.new(mix_final.outputs[2], out.inputs["Surface"])

    return mat

def setup_toon_clothes_material(
    mat_name: str = "M_Anime_Clothes",
    base_color: tuple[float, float, float, float] = (0.118, 0.165, 0.290, 1.0), # Navy Blue #1E2A4A
    shadow_color: tuple[float, float, float, float] = (0.071, 0.102, 0.188, 1.0), # #121A30
) -> bpy.types.Material:
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    diffuse = nt.nodes.new("ShaderNodeBsdfDiffuse")
    diffuse.name = "Diffuse_BSDF"
    diffuse.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    diffuse.inputs["Roughness"].default_value = 0.85

    s2rgb = nt.nodes.new("ShaderNodeShaderToRGB")
    s2rgb.name = "Shader_To_RGB"

    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.name = "ColorRamp"
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements[0].position = 0.0
    ramp.color_ramp.elements[0].color = shadow_color
    ramp.color_ramp.elements[1].position = 0.45
    ramp.color_ramp.elements[1].color = base_color

    out = nt.nodes.new("ShaderNodeOutputMaterial")
    out.name = "Material_Output"

    nt.links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])
    nt.links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], out.inputs["Surface"])

    return mat

def run_test():
    print("Setting up materials on animated character...")
    skin_mat = setup_toon_skin_material("M_Anime_Skin")
    hair_mat = setup_toon_hair_material("M_Anime_Hair")
    clothes_mat = setup_toon_clothes_material("M_Anime_Clothes")

    # Add 3-point lights
    # Key light
    key_data = bpy.data.lights.new(name="Key_Light", type='SUN')
    key_data.energy = 5.0
    key_data.color = (1.0, 0.96, 0.92)
    key_obj = bpy.data.objects.new(name="Key_Light", object_data=key_data)
    key_obj.location = (2.0, -2.5, 3.0)
    key_obj.rotation_euler = (mathutils.Euler((0.8, 0.2, 0.6)))
    bpy.context.scene.collection.objects.link(key_obj)

    # Fill light
    fill_data = bpy.data.lights.new(name="Fill_Light", type='SUN')
    fill_data.energy = 2.0
    fill_data.color = (0.88, 0.94, 1.0)
    fill_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_data)
    fill_obj.location = (-2.0, -2.0, 2.0)
    fill_obj.rotation_euler = (mathutils.Euler((0.6, -0.3, -0.7)))
    bpy.context.scene.collection.objects.link(fill_obj)

    # Rim light
    rim_data = bpy.data.lights.new(name="Rim_Light", type='SUN')
    rim_data.energy = 4.0
    rim_data.color = (1.0, 0.90, 0.80)
    rim_obj = bpy.data.objects.new(name="Rim_Light", object_data=rim_data)
    rim_obj.location = (0.0, 3.0, 2.5)
    rim_obj.rotation_euler = (mathutils.Euler((-0.8, 0.0, 3.14)))
    bpy.context.scene.collection.objects.link(rim_obj)

    # Camera
    cam_data = bpy.data.cameras.new(name="Anime_Camera")
    cam_data.lens = 65.0
    cam_obj = bpy.data.objects.new(name="Anime_Camera", object_data=cam_data)
    cam_obj.location = (0.0, -3.2, 1.2)
    cam_obj.rotation_euler = (mathutils.Euler((1.5708, 0.0, 0.0)))
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = 'BLENDER_EEVEE_NEXT'
    scene.display_settings.display_device = 'sRGB'
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    output_png = r"E:\tool\mcp\MorphoMesh\.agents\m4_explorer_anime_1\test_render_frame.png"
    scene.render.filepath = output_png

    print("Rendering test frame to:", output_png)
    bpy.ops.render.render(write_still=True)

    if os.path.exists(output_png):
        sz = os.path.getsize(output_png)
        print(f"RENDER SUCCESS! Output PNG exists, size = {sz} bytes")
    else:
        print("RENDER FAILED: File not written")

if __name__ == "__main__":
    run_test()
