"""
verify_outline_camera_headless.py
Standalone headless verification script for Milestone 4 Features F16 & F17 in Blender 4.5.4 LTS.

Usage:
    & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python "E:\tool\mcp\MorphoMesh\.agents\m4_explorer_anime_2\verify_outline_camera_headless.py"
"""

import os
import sys
import math

try:
    import bpy
    HAS_BPY = True
except ImportError:
    print("FATAL: This script must be executed inside Blender (blender.exe -b --python ...)")
    sys.exit(1)

# Ensure our agent folder is on path to import blueprints
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

import blueprint_inverted_hull as bih
import blueprint_camera_rig as bcr

def run_headless_verification():
    print("\n" + "=" * 80)
    print("STARTING MILESTONE 4 (F16 & F17) HEADLESS BLENDER VERIFICATION")
    print("=" * 80)

    # 1. LOAD TARGET ANIMATED SCENE
    blend_path = "E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline/output/anime_animated.blend"
    assert os.path.exists(blend_path), f"Asset blend file not found at: {blend_path}"
    print(f"\n[Step 1] Loading blend file: {blend_path}")
    bpy.ops.wm.open_mainfile(filepath=blend_path)

    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    print(f"  Render Engine: {scene.render.engine}")

    # 2. VERIFY & APPLY INVERTED HULL OUTLINE (F16)
    print("\n[Step 2] Applying Inverted Hull Outline Modifier & Material (F16)...")
    outline_cfg = bih.OutlineConfig(
        modifier_name="Anime_Outline",
        thickness=-0.0035,
        offset=1.0,
        use_flip_normals=True,
        use_rim=False,
    )
    outline_res = bih.apply_inverted_hull_outline(config=outline_cfg)
    assert outline_res.success is True, f"Outline application failed: {outline_res.errors}"
    print(f"  Modified meshes: {outline_res.modified_objects}")

    # Inspect material
    outline_mat = bpy.data.materials.get("M_Anime_Outline")
    assert outline_mat is not None, "Material M_Anime_Outline missing"
    assert outline_mat.use_backface_culling is True, "Backface culling must be enabled"
    print(f"  Verified M_Anime_Outline: use_backface_culling={outline_mat.use_backface_culling}")

    # Verify each canonical sub-mesh
    for name in bih.CANONICAL_MESH_NAMES:
        obj = bpy.data.objects.get(name)
        assert obj is not None, f"Canonical sub-mesh {name} missing"
        mod = obj.modifiers.get("Anime_Outline")
        assert mod is not None, f"Modifier Anime_Outline missing on {name}"
        assert mod.type == "SOLIDIFY", f"Modifier type must be SOLIDIFY, got {mod.type}"
        assert -0.004 <= mod.thickness <= -0.003, f"Thickness {mod.thickness} not in [-0.004, -0.003]"
        assert mod.offset == 1.0, f"Offset must be 1.0, got {mod.offset}"
        assert mod.use_flip_normals is True, "Normals must be flipped"
        assert mod.use_rim is False, "Rim must be disabled"
        
        # Verify modifier order (after Armature)
        arm_idx = next((i for i, m in enumerate(obj.modifiers) if m.type == "ARMATURE"), -1)
        out_idx = next((i for i, m in enumerate(obj.modifiers) if m.name == "Anime_Outline"), -1)
        if arm_idx != -1:
            assert out_idx > arm_idx, f"Anime_Outline modifier ({out_idx}) must come AFTER Armature ({arm_idx}) on {name}"

        # Verify material slot assignment
        slot_idx = mod.material_offset
        assert 0 <= slot_idx < len(obj.material_slots), f"Invalid material offset {slot_idx} on {name}"
        assert obj.material_slots[slot_idx].material.name == "M_Anime_Outline", (
            f"Slot {slot_idx} is not M_Anime_Outline on {name}"
        )
        print(f"  [OK] Sub-mesh {name}: Solidify thickness={mod.thickness:.4f}, order={out_idx}/{len(obj.modifiers)}, slot={slot_idx}")

    # 3. VERIFY & APPLY CINEMATIC CAMERA & 3-POINT LIGHTING (F17)
    print("\n[Step 3] Applying Cinematic Camera Rig & 3-Point Lighting (F17)...")
    cam_cfg = bcr.CameraConfig(
        name="Anime_Camera",
        focal_length_mm=65.0,
        sensor_width_mm=36.0,
        sensor_height_mm=20.25,
        position=(0.0, -2.6, 1.25),
        target_armature="Anime_Armature",
        target_bone="Spine2",
    )
    light_cfg = bcr.LightingRigConfig()
    stage_res = bcr.setup_cinematic_stage(camera_config=cam_cfg, lighting_config=light_cfg)
    assert stage_res.success is True, f"Stage setup failed: {stage_res.errors}"

    # Verify Camera object & constraints
    cam_obj = bpy.data.objects.get("Anime_Camera")
    assert cam_obj is not None, "Anime_Camera object missing"
    assert cam_obj.data.lens == 65.0, f"Camera lens must be 65mm, got {cam_obj.data.lens}"
    assert cam_obj.data.sensor_width == 36.0, f"Sensor width must be 36mm, got {cam_obj.data.sensor_width}"
    assert scene.camera == cam_obj, "Anime_Camera must be active scene camera"
    
    con = cam_obj.constraints.get("Track_Spine2")
    assert con is not None, "TRACK_TO constraint missing on camera"
    assert con.target.name == "Anime_Armature", f"Constraint target must be Anime_Armature, got {con.target.name}"
    assert con.subtarget == "Spine2", f"Constraint subtarget must be Spine2, got {con.subtarget}"
    assert con.track_axis == "TRACK_NEGATIVE_Z", f"Track axis must be TRACK_NEGATIVE_Z, got {con.track_axis}"
    assert con.up_axis == "UP_Y", f"Up axis must be UP_Y, got {con.up_axis}"
    print(f"  [OK] Camera: lens=65mm, loc={cam_obj.location[:]}, track_target={con.target.name}.{con.subtarget}")

    # Verify 3-Point Lighting Rig
    expected_lights = {
        "Light_Key": (650.0, (1.8, -2.0, 2.5)),
        "Light_Fill": (200.0, (-1.5, -1.8, 1.8)),
        "Light_Rim": (800.0, (-0.5, 1.5, 2.2)),
    }
    for lname, (exp_energy, exp_loc) in expected_lights.items():
        lobj = bpy.data.objects.get(lname)
        assert lobj is not None, f"Light object {lname} missing"
        assert abs(lobj.data.energy - exp_energy) < 1.0, f"Light {lname} energy mismatch: {lobj.data.energy} != {exp_energy}"
        assert math.dist(lobj.location, exp_loc) < 0.01, f"Light {lname} location mismatch: {lobj.location} != {exp_loc}"
        lcon = lobj.constraints.get("Track_Spine2")
        assert lcon is not None, f"Light {lname} missing TRACK_TO constraint"
        print(f"  [OK] Light {lname}: energy={lobj.data.energy}W, loc={lobj.location[:]}, target={lcon.subtarget}")

    # 4. RENDER TEST FULL HD FRAME
    print("\n[Step 4] Executing Headless Full HD Render Test...")
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.fps = 30
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = "Standard"

    output_render_path = os.path.join(SCRIPT_DIR, "headless_verified_frame.png")
    scene.render.filepath = output_render_path
    
    bpy.context.view_layer.update()
    bpy.ops.render.render(write_still=True)
    assert os.path.exists(output_render_path), f"Rendered image not found at {output_render_path}"
    file_size_kb = os.path.getsize(output_render_path) / 1024.0
    print(f"  Rendered snapshot successfully: {output_render_path} ({file_size_kb:.1f} KB)")
    assert file_size_kb > 50.0, f"Render file too small ({file_size_kb:.1f} KB), possible empty frame"

    print("\n" + "=" * 80)
    print("ALL MILESTONE 4 (F16 & F17) VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 80 + "\n")
    return True

if __name__ == "__main__":
    run_headless_verification()
