"""
Comprehensive Standalone Verification Suite for Milestone 4 Features F14 & F15:
- Stepped Cel-Shading Node Trees (F14)
- Procedural Hair Angel Ring (F15)

Executes headless in Blender 4.5.4 LTS.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure our blueprints are importable
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

import bpy
import mathutils

from proposed_toon_materials import (
    SKIN_BASE_COLOR,
    SKIN_SHADOW_COLOR,
    CLOTHES_PRESETS,
    OUTLINE_COLOR,
    build_anime_skin_material,
    build_anime_clothes_material,
    build_anime_eye_material,
    build_anime_outline_material,
    apply_all_toon_materials,
)
from proposed_angel_ring import (
    DEFAULT_CROWN_Z_MIN,
    DEFAULT_CROWN_Z_MAX,
    ANGEL_RING_COLOR,
    build_procedural_angel_ring_material,
    apply_angel_ring_to_hair,
    compute_hair_crown_z_bounds,
)


def verify_f14_skin_cel_shading():
    """Validates F14 M_Anime_Skin node graph and color invariants."""
    print("\n--- [TEST 1] Verifying F14: M_Anime_Skin Cel-Shading Node Tree ---")
    mat = build_anime_skin_material("Test_M_Anime_Skin")
    assert mat is not None, "Failed to create M_Anime_Skin material"
    assert mat.use_nodes is True, "use_nodes must be True"
    nt = mat.node_tree

    # Check nodes
    diffuse = nt.nodes.get("Diffuse_BSDF")
    assert diffuse is not None, "Missing Diffuse_BSDF node"
    assert diffuse.type == "BSDF_DIFFUSE", f"Diffuse node has wrong type {diffuse.type}"
    assert diffuse.inputs["Roughness"].default_value == 1.0, "Roughness must be 1.0 for matte skin"

    s2rgb = nt.nodes.get("Shader_To_RGB")
    assert s2rgb is not None, "Missing Shader_To_RGB node"
    assert s2rgb.type in ("SHADERTORGB", "SHADER_TO_RGB"), f"ShaderToRGB has wrong type {s2rgb.type}"

    ramp = nt.nodes.get("ColorRamp")
    assert ramp is not None, "Missing ColorRamp node"
    assert ramp.type == "VALTORGB", f"ColorRamp has wrong type {ramp.type}"
    assert ramp.color_ramp.interpolation == "CONSTANT", "ColorRamp must use CONSTANT interpolation"

    elements = ramp.color_ramp.elements
    assert len(elements) >= 2, f"ColorRamp must have at least 2 elements, got {len(elements)}"

    shadow_col = elements[0].color
    print(f"Skin Shadow Color: {tuple(round(c, 3) for c in shadow_col)}")
    # Invariant from test_tier1_features.py line 319:
    # assert shadow_color[0] > 0.90 and shadow_color[1] > 0.70 and shadow_color[2] < 0.75
    assert shadow_col[0] > 0.90, f"Shadow R must be > 0.90, got {shadow_col[0]}"
    assert shadow_col[1] > 0.70, f"Shadow G must be > 0.70, got {shadow_col[1]}"
    assert shadow_col[2] < 0.75, f"Shadow B must be < 0.75 (warm peach, no muddy gray), got {shadow_col[2]}"

    base_col = elements[1].color
    print(f"Skin Base Color: {tuple(round(c, 3) for c in base_col)}")
    assert base_col[0] >= 0.95 and base_col[1] >= 0.85, "Base skin color is not fair porcelain"

    # Check links
    assert diffuse.outputs["BSDF"].is_linked, "Diffuse BSDF not linked"
    assert s2rgb.inputs["Shader"].is_linked, "ShaderToRGB input not linked"
    assert ramp.inputs["Fac"].is_linked, "ColorRamp Fac not linked"
    
    out = nt.nodes.get("Material_Output")
    assert out is not None and out.inputs["Surface"].is_linked, "Material Output not linked"
    print(">>> [PASS] F14: M_Anime_Skin verified successfully.")


def verify_f14_clothes_and_eyes():
    """Validates F14 Clothes presets and Eye material."""
    print("\n--- [TEST 2] Verifying F14: Clothes Presets & Eye Materials ---")
    for garment in ["SHIRT", "SKIRT", "SHOES"]:
        mat = build_anime_clothes_material(f"Test_Clothes_{garment}", garment_type=garment)
        nt = mat.node_tree
        ramp = nt.nodes["ColorRamp"]
        assert ramp.color_ramp.interpolation == "CONSTANT"
        print(f"Verified garment preset {garment}: base={CLOTHES_PRESETS[garment]['base'][:3]}")

    eye_mat = build_anime_eye_material("Test_M_Anime_Eye")
    assert eye_mat is not None
    assert eye_mat.node_tree.nodes.get("Radial_Distance") is not None
    assert eye_mat.node_tree.nodes.get("Iris_ColorRamp") is not None
    assert eye_mat.node_tree.nodes.get("Eye_Emission") is not None
    print(">>> [PASS] F14: Clothes and Eye materials verified successfully.")


def verify_f15_angel_ring():
    """Validates F15 Procedural Hair Angel Ring node tree & diffuse gating."""
    print("\n--- [TEST 3] Verifying F15: Procedural Hair Angel Ring ---")
    mat = build_procedural_angel_ring_material("Test_M_Anime_Hair")
    assert mat is not None
    nt = mat.node_tree

    # TextureCoordinate
    tex_coord = nt.nodes.get("TextureCoordinate")
    assert tex_coord is not None and tex_coord.type == "TEX_COORD", "Missing TextureCoordinate node"

    # ObjectSpaceZBand (MAP_RANGE)
    map_range = nt.nodes.get("ObjectSpaceZBand")
    assert map_range is not None and map_range.type == "MAP_RANGE", "Missing ObjectSpaceZBand node"
    assert abs(map_range.inputs["From Min"].default_value - 1.45) < 1e-4, "From Min must be 1.45"
    assert abs(map_range.inputs["From Max"].default_value - 1.55) < 1e-4, "From Max must be 1.55"

    # DiffuseGating (MATH MULTIPLY)
    diffuse_gating = nt.nodes.get("DiffuseGating")
    assert diffuse_gating is not None and diffuse_gating.type == "MATH", "Missing DiffuseGating node"
    assert diffuse_gating.operation == "MULTIPLY", f"Diffuse gating operation must be MULTIPLY, got {diffuse_gating.operation}"

    # Angel Ring Color
    ring_ramp = nt.nodes.get("AngelRing_ColorRamp")
    assert ring_ramp is not None and ring_ramp.type == "VALTORGB", "Missing AngelRing_ColorRamp"
    peak_color = ring_ramp.color_ramp.elements[1].color
    assert peak_color[0] >= 0.95 and peak_color[1] >= 0.95 and peak_color[2] >= 0.90, "Angel Ring color not white/cream"

    # Composite Mix Node
    mix_node = nt.nodes.get("AngelRing_Mix")
    assert mix_node is not None and mix_node.type == "MIX", "Missing AngelRing_Mix node"
    assert mix_node.data_type == "RGBA", "Mix node data_type must be RGBA"

    # Link integrity
    assert diffuse_gating.outputs["Value"].is_linked, "Diffuse gating value must be linked"
    assert mix_node.inputs[0].is_linked, "Mix Factor must be driven by diffuse gating"
    assert mix_node.inputs[6].is_linked, "Mix input A must receive base cel-shading"
    assert mix_node.outputs[2].is_linked, "Mix output Result must connect to Material Output"

    print(">>> [PASS] F15: Procedural Hair Angel Ring verified successfully.")


def verify_character_integration_and_render(blend_path: str):
    """Applies materials to character submeshes in anime_animated.blend and tests render."""
    print("\n--- [TEST 4] Full Character Scene Integration & Headless Render ---")
    if not os.path.exists(blend_path):
        print(f"Warning: Blend file not found at {blend_path}, skipping live scene render.")
        return

    bpy.ops.wm.open_mainfile(filepath=blend_path)
    print(f"Opened mainfile: {blend_path}")

    # Verify submesh objects exist
    submesh_names = [
        "Anime_Head", "Anime_Torso", "Anime_Arms",
        "Anime_Legs", "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    for name in submesh_names:
        assert bpy.data.objects.get(name) is not None, f"Submesh {name} missing from blend"

    # Apply materials
    apply_all_toon_materials(separate_garments=True)
    apply_angel_ring_to_hair("Anime_Hair", "M_Anime_Hair")

    # Verify material slots on all objects
    for name in submesh_names:
        obj = bpy.data.objects[name]
        assert len(obj.material_slots) >= 1, f"Object {name} has no material slots"
        slot0_mat = obj.material_slots[0].material
        assert slot0_mat is not None, f"Object {name} slot 0 material is None"
        print(f"Object {name:12s} -> Slot 0: {slot0_mat.name:18s} (use_nodes={slot0_mat.use_nodes})")

    # Add 3-point lights
    key_data = bpy.data.lights.new(name="Key_Light", type="SUN")
    key_data.energy = 5.0
    key_data.color = (1.0, 0.98, 0.95)
    key_obj = bpy.data.objects.new(name="Key_Light", object_data=key_data)
    key_obj.rotation_euler = (mathutils.Euler((0.6, 0.2, 0.5)))
    bpy.context.scene.collection.objects.link(key_obj)

    fill_data = bpy.data.lights.new(name="Fill_Light", type="SUN")
    fill_data.energy = 2.0
    fill_data.color = (0.90, 0.95, 1.0)
    fill_obj = bpy.data.objects.new(name="Fill_Light", object_data=fill_data)
    fill_obj.rotation_euler = (mathutils.Euler((0.6, -0.3, -0.7)))
    bpy.context.scene.collection.objects.link(fill_obj)

    rim_data = bpy.data.lights.new(name="Rim_Light", type="SUN")
    rim_data.energy = 4.0
    rim_data.color = (1.0, 0.90, 0.80)
    rim_obj = bpy.data.objects.new(name="Rim_Light", object_data=rim_data)
    rim_obj.rotation_euler = (mathutils.Euler((-0.8, 0.0, 3.14)))
    bpy.context.scene.collection.objects.link(rim_obj)

    # Add Camera
    cam_data = bpy.data.cameras.new(name="Anime_Camera")
    cam_data.lens = 65.0
    cam_obj = bpy.data.objects.new(name="Anime_Camera", object_data=cam_data)
    cam_obj.location = (0.0, -3.2, 1.2)
    cam_obj.rotation_euler = (mathutils.Euler((1.5708, 0.0, 0.0)))
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Render settings
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.resolution_x = 960
    scene.render.resolution_y = 540
    output_png = str(CURRENT_DIR / "standalone_test_render.png")
    scene.render.filepath = output_png

    print(f"Rendering full character verification frame to: {output_png}")
    bpy.ops.render.render(write_still=True)

    assert os.path.exists(output_png), "Render output file was not created"
    file_size = os.path.getsize(output_png)
    assert file_size > 50000, f"Rendered image file too small ({file_size} bytes)"
    print(f">>> [PASS] Live Render Successful: {file_size} bytes written.")


def run_all_tests():
    print("=" * 70)
    print("RUNNING STANDALONE MATERIAL VERIFICATION SUITE (BLENDER 4.5.4 LTS)")
    print("=" * 70)
    verify_f14_skin_cel_shading()
    verify_f14_clothes_and_eyes()
    verify_f15_angel_ring()

    blend_file = r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\anime_animated.blend"
    verify_character_integration_and_render(blend_file)

    print("\n" + "=" * 70)
    print("ALL TESTS PASSED SUCCESSFULLY! (100% INVARIANT COMPLIANCE)")
    print("=" * 70)


if __name__ == "__main__":
    run_all_tests()
