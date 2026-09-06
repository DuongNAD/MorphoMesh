#!/usr/bin/env python3
"""
MorphoMesh: Armored War Bear Master Scene Assembly, Production Export & Beauty Renderer.

Milestone M4 Canonical Asset Generator:
1. Assembles complete Armored War Bear in Blender 5.2.1 LTS:
   - Bear_Base_Mesh with plantigrade stance, articulated facial features, 20 curved claws,
     and all 18 standardized vertex groups populated.
   - 5 Principled BSDF v2 PBR materials (Mat_Bear_Fur, Mat_Bear_Skin_Nose, Mat_Bear_Claws,
     Mat_Armor_WeatheredSteel, Mat_Armor_BrassTrim).
   - Multi-layer volumetric fur particle systems (Undercoat_Fur: 8,000 strands,
     Guard_Hairs_Fur: 4,000 strands, total 12,000 >= 10,000 parent guide strands,
     interpolated children > 100,000 render strands, zero-fur density masks).
   - Evaluated fur curve ribbon mesh (Bear_Fur_Ribbons) with normalized UVs and Mat_Bear_Fur.
   - 6 fitted war armor plates (Armor_Pauldron_L, Armor_Pauldron_R, Armor_Gorget,
     Armor_Bracer_L, Armor_Bracer_R, Armor_Backplate) with clearance >= 0.015m,
     watertight 2-manifold shells, and outward face normals.
   - Studio lighting rig (Key, Fill, Rim/Kicker) and pedestal.
   - 4 specialized cinematic camera setups.
2. Saves master scene to examples/Armored_War_Bear_HD.blend.
3. Exports production glTF 2.0 asset to examples/Armored_War_Bear_HD.glb.
4. Renders 4 high-resolution beauty shots via Cycles to examples/renders/:
   - bear_front_three_quarter.png
   - bear_head_closeup.png
   - bear_paw_claws_closeup.png
   - bear_full_body.png
"""

import math
import os
import sys
import time

# Ensure dependencies in user site-packages and src/ are importable
sys.path.insert(0, "/Users/duongnad/.local/lib/python3.13/site-packages")
sys.path.insert(0, os.path.abspath("src"))

import bmesh
import bpy
import mathutils

from morphomesh.creature_generator import generate_bear_base_mesh
from morphomesh.grooming import CreatureGroomingEngine
from morphomesh.materials import CreaturePBRSuite
from morphomesh.armor import ProceduralArmorEngine


def log(msg: str):
    print(f"[M4 ASSEMBLY] {msg}", flush=True)


def clean_scene():
    """Remove default startup objects."""
    log("Cleaning startup scene...")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in bpy.data.meshes:
        bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        bpy.data.materials.remove(block)
    for block in bpy.data.lights:
        bpy.data.lights.remove(block)
    for block in bpy.data.cameras:
        bpy.data.cameras.remove(block)


def build_bear_base_mesh() -> bpy.types.Object:
    """Builds anatomically authentic Bear_Base_Mesh with all 18 vertex groups."""
    log("Synthesizing Bear_Base_Mesh geometry and vertex groups...")
    res = generate_bear_base_mesh()
    mesh_data = bpy.data.meshes.new("Bear_Base_Mesh")
    mesh_data.from_pydata(res.mesh.vertices, [], res.mesh.faces)
    mesh_data.update()

    bear_obj = bpy.data.objects.new("Bear_Base_Mesh", mesh_data)
    bpy.context.scene.collection.objects.link(bear_obj)

    # Populate all 18 standardized vertex groups
    for vg_name, indices in res.vertex_groups.items():
        vg = bear_obj.vertex_groups.new(name=vg_name)
        if indices:
            vg.add(indices, 1.0, "REPLACE")

    # Set smooth shading
    for poly in mesh_data.polygons:
        poly.use_smooth = True

    log(f"Bear_Base_Mesh created: {len(mesh_data.vertices)} vertices, {len(mesh_data.polygons)} polygons, {len(bear_obj.vertex_groups)} vertex groups.")
    return bear_obj


def setup_materials_and_slots(bear_obj: bpy.types.Object):
    """Constructs the 5 Principled BSDF v2 materials and assigns them to object slots and polygons."""
    log("Building 5 Principled BSDF v2 materials...")
    pbr = CreaturePBRSuite()
    pbr.create_all_materials()

    slot_order = [
        "Mat_Bear_Fur",
        "Mat_Bear_Skin_Nose",
        "Mat_Bear_Claws",
        "Mat_Armor_WeatheredSteel",
        "Mat_Armor_BrassTrim",
    ]

    bear_obj.data.materials.clear()
    for mat_name in slot_order:
        mat_ref = bpy.data.materials.get(mat_name)
        if mat_ref:
            bear_obj.data.materials.append(mat_ref)

    slot_fur = 0
    slot_skin = 1
    slot_claws = 2

    skin_vgs = {"snout", "nostrils", "mouth_cavity", "jaw", "pads_front", "pads_hind"}
    claw_vgs = {"claws_front", "claws_hind"}

    skin_verts = set()
    claw_verts = set()

    for vg in bear_obj.vertex_groups:
        if vg.name in skin_vgs:
            for v in bear_obj.data.vertices:
                try:
                    if vg.weight(v.index) > 0.1:
                        skin_verts.add(v.index)
                except Exception:
                    pass
        elif vg.name in claw_vgs:
            for v in bear_obj.data.vertices:
                try:
                    if vg.weight(v.index) > 0.1:
                        claw_verts.add(v.index)
                except Exception:
                    pass

    for poly in bear_obj.data.polygons:
        p_v = set(poly.vertices)
        if p_v.intersection(claw_verts):
            poly.material_index = slot_claws
        elif p_v.intersection(skin_verts):
            poly.material_index = slot_skin
        else:
            poly.material_index = slot_fur

    log(f"Material slots assigned to Bear_Base_Mesh: {len(bear_obj.data.materials)} slots.")


def fit_and_setup_armor(bear_obj: bpy.types.Object) -> list[str]:
    """Generates all 6 non-intersecting war armor plates with materials and outward normals."""
    log("Fitting 6 war armor plates over Bear_Base_Mesh...")
    armor_engine = ProceduralArmorEngine()
    armor_objs = armor_engine.fit_war_armor("Bear_Base_Mesh")

    # Ensure all armor plates have outward face normals, watertight topology, and materials
    mat_steel = bpy.data.materials.get("Mat_Armor_WeatheredSteel")
    mat_brass = bpy.data.materials.get("Mat_Armor_BrassTrim")

    for a_name in armor_objs:
        ao = bpy.data.objects.get(a_name)
        if not ao:
            continue
        # Ensure materials
        if len(ao.data.materials) == 0:
            if mat_steel:
                ao.data.materials.append(mat_steel)
            if mat_brass:
                ao.data.materials.append(mat_brass)
        # Recalculate outward normals via bmesh
        bm = bmesh.new()
        bm.from_mesh(ao.data)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(ao.data)
        bm.free()
        ao.data.update()

    log(f"Fitted armor plates: {armor_objs}")
    return armor_objs


def setup_fur_and_ribbons(bear_obj: bpy.types.Object) -> bpy.types.Object:
    """Sets up multi-layer volumetric fur particle systems and evaluated fur ribbons."""
    log("Configuring multi-layer volumetric fur particle systems...")
    grooming_engine = CreatureGroomingEngine()
    grooming_engine.setup_volumetric_fur("Bear_Base_Mesh", generate_gltf_ribbons=True)

    ribbon_obj = bpy.data.objects.get("Bear_Base_Mesh_Fur_Ribbons")
    if ribbon_obj:
        ribbon_obj.name = "Bear_Fur_Ribbons"
        ribbon_obj.data.name = "Bear_Fur_Ribbons_Mesh"
        fur_mat = bpy.data.materials.get("Mat_Bear_Fur")
        ribbon_obj.data.materials.clear()
        if fur_mat:
            ribbon_obj.data.materials.append(fur_mat)
        # Hide ribbons in rendering to let native Cycles volumetric hair particle systems shine
        ribbon_obj.hide_render = True
        log(f"Bear_Fur_Ribbons configured: {len(ribbon_obj.data.vertices)} vertices, {len(ribbon_obj.data.polygons)} polygons.")

    # Assign Mat_Bear_Fur to hair particle systems
    for psys in bear_obj.particle_systems:
        psys.settings.material_slot = "Mat_Bear_Fur"
    return ribbon_obj


def setup_studio_environment():
    """Sets up studio pedestal, world shader, and 3-point cinematic lighting rig."""
    log("Setting up studio environment and lighting rig...")

    # World background
    world = bpy.context.scene.world or bpy.data.worlds.new("Studio_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg_node = world.node_tree.nodes.get("Background")
    if bg_node:
        bg_node.inputs["Color"].default_value = (0.025, 0.025, 0.030, 1.0)
        bg_node.inputs["Strength"].default_value = 0.6

    # Studio Pedestal
    bpy.ops.mesh.primitive_cylinder_add(radius=2.2, depth=0.08, location=(0, 0, -0.04))
    pedestal = bpy.context.active_object
    pedestal.name = "Studio_Pedestal"
    pedestal.data.name = "Studio_Pedestal_Mesh"
    for poly in pedestal.data.polygons:
        poly.use_smooth = True

    ped_mat = bpy.data.materials.new(name="Mat_Studio_Pedestal")
    ped_mat.use_nodes = True
    bsdf = ped_mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.04, 0.04, 0.045, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.55
        bsdf.inputs["Metallic"].default_value = 0.20
    pedestal.data.materials.append(ped_mat)

    # 3-Point Studio Lighting Rig
    # 1. Key Light (Warm, bright directional area light)
    key_light = bpy.data.lights.new("KeyLight", type="AREA")
    key_light.energy = 1600.0
    key_light.size = 2.2
    key_light.color = (1.0, 0.97, 0.92)
    key_obj = bpy.data.objects.new("Studio_Key_Light", key_light)
    key_obj.location = (2.4, -2.8, 2.6)
    key_dir = mathutils.Vector((0, -0.4, 0.8)) - mathutils.Vector(key_obj.location)
    key_obj.rotation_euler = key_dir.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(key_obj)

    # 2. Fill Light (Cool, soft ambient area light)
    fill_light = bpy.data.lights.new("FillLight", type="AREA")
    fill_light.energy = 600.0
    fill_light.size = 3.5
    fill_light.color = (0.86, 0.92, 1.0)
    fill_obj = bpy.data.objects.new("Studio_Fill_Light", fill_light)
    fill_obj.location = (-2.6, -2.0, 1.8)
    fill_dir = mathutils.Vector((0, -0.4, 0.8)) - mathutils.Vector(fill_obj.location)
    fill_obj.rotation_euler = fill_dir.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(fill_obj)

    # 3. Rim / Kicker Light (High-intensity contour/rim light highlighting fur edge and armor plates)
    rim_light = bpy.data.lights.new("RimLight", type="SPOT")
    rim_light.energy = 2400.0
    rim_light.spot_size = 1.20
    rim_light.spot_blend = 0.25
    rim_light.color = (1.0, 0.98, 0.95)
    rim_obj = bpy.data.objects.new("Studio_Rim_Light", rim_light)
    rim_obj.location = (0.0, 2.8, 2.6)
    rim_dir = mathutils.Vector((0, 0.0, 0.9)) - mathutils.Vector(rim_obj.location)
    rim_obj.rotation_euler = rim_dir.to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(rim_obj)

    log("Studio environment and lighting rig created.")


def setup_beauty_cameras() -> dict[str, bpy.types.Object]:
    """Creates the 4 beauty shot cameras with precise anatomical targeting."""
    log("Configuring 4 beauty shot cameras...")
    cameras = {}

    configs = [
        (
            "CAM_Front_Three_Quarter",
            (2.40, -3.10, 1.45),
            (0.0, -0.40, 0.70),
            60.0,
            "Front 3/4 perspective hero shot",
        ),
        (
            "CAM_Head_Closeup",
            (0.45, -1.85, 1.22),
            (0.0, -0.95, 1.16),
            90.0,
            "Head and facial sculpting close-up",
        ),
        (
            "CAM_Paw_Claws_Closeup",
            (0.78, -1.05, 0.30),
            (0.38, -0.55, 0.08),
            85.0,
            "Front paw, claws, and bracer armor close-up",
        ),
        (
            "CAM_Full_Body",
            (3.60, -1.60, 1.25),
            (0.0, -0.10, 0.75),
            45.0,
            "Full body dramatic perspective",
        ),
    ]

    for name, loc, target, lens, desc in configs:
        cam_data = bpy.data.cameras.new(name)
        cam_data.lens = lens
        cam_obj = bpy.data.objects.new(name, cam_data)
        cam_obj.location = loc
        cam_dir = mathutils.Vector(target) - mathutils.Vector(loc)
        cam_obj.rotation_euler = cam_dir.to_track_quat("-Z", "Y").to_euler()
        bpy.context.scene.collection.objects.link(cam_obj)
        cameras[name] = cam_obj
        log(f"Camera '{name}' configured: lens={lens}mm, target={target} ({desc})")

    # Set default active camera
    bpy.context.scene.camera = cameras["CAM_Front_Three_Quarter"]
    return cameras


def export_master_blend(filepath: str):
    """Saves the complete master scene to .blend format."""
    log(f"Saving master scene to {filepath}...")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=filepath)
    size = os.path.getsize(filepath)
    log(f"Saved .blend: {size} bytes ({size / 1024 / 1024:.2f} MB).")
    assert size > 500 * 1024, f"Blend file size {size} is <= 500 KB!"


def export_production_glb(filepath: str, armor_objs: list[str]):
    """Exports production glTF 2.0 asset containing bear, armor, and fur ribbons."""
    log(f"Exporting production glTF 2.0 asset to {filepath}...")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    bpy.ops.object.select_all(action="DESELECT")
    export_names = ["Bear_Base_Mesh", "Bear_Fur_Ribbons"] + armor_objs
    for name in export_names:
        o = bpy.data.objects.get(name)
        if o:
            o.select_set(True)

    base_obj = bpy.data.objects.get("Bear_Base_Mesh")
    if base_obj:
        bpy.context.view_layer.objects.active = base_obj

    bpy.ops.export_scene.gltf(
        filepath=filepath,
        export_format="GLB",
        use_selection=True,
        export_materials="EXPORT",
        export_attributes=True,
    )
    size = os.path.getsize(filepath)
    log(f"Exported .glb: {size} bytes ({size / 1024 / 1024:.2f} MB).")
    assert size > 500 * 1024, f"GLB file size {size} is <= 500 KB!"


def render_beauty_shots(cameras: dict[str, bpy.types.Object], output_dir: str):
    """Renders 4 high-resolution beauty shots using Cycles with denoising."""
    log(f"Rendering 4 high-resolution beauty shots to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 36
    scene.cycles.use_denoising = True
    scene.render.hair_type = "STRIP"
    scene.render.hair_subdiv = 1
    if hasattr(scene.cycles, "curves_shape"):
        scene.cycles.curves_shape = "STRIP"
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 720
    scene.render.image_settings.file_format = "PNG"

    render_map = [
        ("CAM_Front_Three_Quarter", "bear_front_three_quarter.png"),
        ("CAM_Head_Closeup", "bear_head_closeup.png"),
        ("CAM_Paw_Claws_Closeup", "bear_paw_claws_closeup.png"),
        ("CAM_Full_Body", "bear_full_body.png"),
    ]

    for cam_name, filename in render_map:
        cam_obj = cameras.get(cam_name)
        if not cam_obj:
            log(f"ERROR: Camera {cam_name} not found!")
            continue

        out_path = os.path.join(output_dir, filename)
        scene.camera = cam_obj
        scene.render.filepath = out_path

        log(f"Rendering {filename} from {cam_name} (1280x720, Cycles 36 samples with OpenImageDenoise)...")
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        elapsed = time.time() - t0

        size = os.path.getsize(out_path)
        log(f"Rendered {filename} in {elapsed:.2f}s: {size} bytes ({size / 1024:.1f} KB).")
        assert size > 50 * 1024, f"Render {filename} size {size} is <= 50 KB!"


def main():
    start_time = time.time()
    log("Starting Armored War Bear production assembly and export pipeline...")

    # 1. Clean scene
    clean_scene()

    # 2. Materials
    pbr = CreaturePBRSuite()
    pbr.create_all_materials()

    # 3. Base Mesh
    bear_obj = build_bear_base_mesh()
    setup_materials_and_slots(bear_obj)

    # 4. War Armor Fitting
    armor_objs = fit_and_setup_armor(bear_obj)

    # 5. Volumetric Fur & Ribbons
    setup_fur_and_ribbons(bear_obj)

    # 6. Studio Environment & Pedestal
    setup_studio_environment()

    # 7. Cameras
    cameras = setup_beauty_cameras()

    # 8. Export .blend
    blend_path = os.path.abspath("examples/Armored_War_Bear_HD.blend")
    export_master_blend(blend_path)

    # 9. Export .glb
    glb_path = os.path.abspath("examples/Armored_War_Bear_HD.glb")
    export_production_glb(glb_path, armor_objs)

    # 10. Render beauty shots
    renders_dir = os.path.abspath("examples/renders")
    render_beauty_shots(cameras, renders_dir)

    total_time = time.time() - start_time
    log(f"All M4 deliverables completed successfully in {total_time:.2f}s!")


if __name__ == "__main__":
    main()
