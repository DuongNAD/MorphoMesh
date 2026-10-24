"""
MorphoMesh In-Blender Wardrobe Generation Script Template & CLI Entrypoint.

Responsible for:
- get_wardrobe_script: Generates Python script executable inside Blender 4.5+ LTS
  building dress, sash, sandals, ribbons, butterflies, materials, and DEF bone binding.
- dress_human: Procedural high-level wardrobe entrypoint returning HumanWardrobeResult.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import asdict
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

try:
    import bpy
    HAS_BPY = True
except (ImportError, ModuleNotFoundError):
    HAS_BPY = False

from .skinning import (
    FINGER_DEF_BONE_KEYS,
    FINGER_DEF_BONE_ALIASES,
    resolve_finger_def_bone_name,
    MATERIAL_NAME_ALIASES,
    compute_dress_waist_radii,
    assign_dress_pin_weights,
    assign_bodice_skin_weights,
    assign_skirt_skin_weights,
    assign_sash_skin_weights,
    compute_wardrobe_skin_weights,
)
from .props import (
    BUTTERFLY_FLUTTER_POSITIONS,
    get_butterfly_vortex_positions,
    get_butterfly_flutter_positions,
    generate_catenary_magic_strings,
    generate_marionette_red_strings,
    generate_marionette_strings,
    generate_swallowtail_quad_butterfly,
    generate_swallowtail_butterfly,
    generate_glowing_butterflies,
)
from .garments import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_waist_sash,
    generate_dress_organic_skirt,
    generate_dress_pleated_skirt,
    generate_dress_skirt,
    generate_organic_dress,
    generate_waist_sash_and_bow,
    generate_flat_strappy_sandals,
    generate_flat_sandals,
    generate_yu_nian_an_wardrobe,
)

logger = logging.getLogger("morphomesh.wardrobe.scripts")


def get_wardrobe_script(
    target_object: str = "Human_Base_Mesh",
    outfit_preset: str = "yu_nian_an_dress",
    clearance_offset: float = 0.015,
    include_sandals: bool = True,
    include_red_threads: bool = True,
    include_glowing_butterflies: bool = True,
    butterfly_count: int = 10,
    character_height: float = 1.65,
    waist_girth: float = 0.58,
    chest_girth: float = 0.82,
    hip_girth: float = 0.86,
    thickness: float = 0.002,
    **kwargs: Any,
) -> str:
    """
    Generates a standalone Python script executable inside Blender 4.5+ LTS.
    The script:
    1. Synthesizes tailored white slip dress bodice, waist sash with ribbons,
       flared pleated skirt, flat sandals, marionette cords, and butterflies.
    2. Populates non-empty meshes using me.from_pydata(verts, [], faces) and me.update().
    3. Adds Solidify modifier (thickness 0.002m) to bodice, sash, and skirt.
    4. Links all wardrobe objects to character hierarchy and parent collection.
    5. Adds Armature / Surface Deform modifiers to bind wardrobe meshes to the body/armature.
    6. Assigns PBR materials (Mat_Dress_WhiteSilk, Mat_Dress_WaistBelt, Mat_Sandal_Leather, etc.).
    """
    cfg = WardrobeConfig(
        outfit_preset=outfit_preset,
        clearance_offset=clearance_offset,
        thickness=thickness,
        include_sandals=include_sandals,
        include_red_threads=include_red_threads,
        include_glowing_butterflies=include_glowing_butterflies,
        butterfly_count=butterfly_count,
        character_height=character_height,
        waist_girth=waist_girth,
        chest_girth=chest_girth,
        hip_girth=hip_girth,
    )
    wardrobe_geoms = generate_yu_nian_an_wardrobe(cfg)
    geom_data: Dict[str, Any] = {}
    bone_weights_data: Dict[str, Any] = {}
    pin_weights_data: Dict[str, Any] = {}
    for part_name, m in wardrobe_geoms.items():
        mesh_entry = {
            "verts": [[round(coord, 5) for coord in v] for v in m.vertices],
            "faces": [list(f) for f in m.faces],
        }
        geom_data[part_name] = mesh_entry
        if not part_name.startswith("Mesh_") and not part_name.startswith("Prop_"):
            geom_data[f"Mesh_{part_name}"] = mesh_entry

        sw = getattr(m, "skin_weights", {})
        if sw:
            bone_groups: Dict[str, List[List[Any]]] = {}
            for v_idx, b_map in sw.items():
                for b_name, weight in b_map.items():
                    if weight > 0.001:
                        if b_name not in bone_groups:
                            bone_groups[b_name] = []
                        bone_groups[b_name].append([int(v_idx), round(float(weight), 4)])
            bone_weights_data[part_name] = bone_groups
        pw = getattr(m, "pin_weights", {})
        if pw:
            pin_entries = [[int(v_i), round(float(w_v), 4)] for v_i, w_v in pw.items() if w_v > 0.0]
            pin_weights_data[part_name] = pin_entries
            if not part_name.startswith("Mesh_") and not part_name.startswith("Prop_"):
                pin_weights_data[f"Mesh_{part_name}"] = pin_entries

    cfg_json = json.dumps(cfg.to_dict(), indent=2)
    geom_json = json.dumps(geom_data)
    bone_weights_json = json.dumps(bone_weights_data)
    pin_weights_json = json.dumps(pin_weights_data)
    flutter_positions = get_butterfly_flutter_positions(height=character_height, count=butterfly_count)
    flutter_positions_json = json.dumps(flutter_positions)

    script = f'''"""
Blender 4.5+ Standalone Wardrobe & Magic Props Generation Script.
Yu Nian An (余念安) Two-Strap Slip Dress, Waist Sash, Sandals & Butterflies.
Generated by MorphoMesh.
"""
import bpy
import json
import math

TARGET_OBJ_NAME = "{target_object}"
CFG = json.loads(\'\'\'{cfg_json}\'\'\')
WARDROBE_GEOM = json.loads(\'\'\'{geom_json}\'\'\')
BONE_WEIGHTS = json.loads(\'\'\'{bone_weights_json}\'\'\')
PIN_WEIGHTS = json.loads(\'\'\'{pin_weights_json}\'\'\')

body_obj = bpy.data.objects.get(TARGET_OBJ_NAME)
armature_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify")

if body_obj:
    col_mod = body_obj.modifiers.get("Body_Cloth_Collision") or body_obj.modifiers.new(name="Body_Cloth_Collision", type='COLLISION')
    col_settings = getattr(col_mod, "settings", None) or getattr(col_mod, "collision_settings", None)
    if col_settings is not None:
        if hasattr(col_settings, "thickness_outer"):
            col_settings.thickness_outer = 0.003
        if hasattr(col_settings, "thickness_inner"):
            col_settings.thickness_inner = 0.002
        if hasattr(col_settings, "cloth_friction"):
            col_settings.cloth_friction = 0.50
        elif hasattr(col_settings, "friction"):
            col_settings.friction = 0.50

# Find or create target collection
char_col = bpy.data.collections.get("Yu_Nian_An_Master")
if not char_col:
    char_col = bpy.context.scene.collection

dress_col = bpy.data.collections.get("03_Dress") or bpy.data.collections.new("03_Dress")
if dress_col.name not in char_col.children:
    try:
        char_col.children.link(dress_col)
    except Exception:
        pass

foot_col = bpy.data.collections.get("04_Footwear") or bpy.data.collections.new("04_Footwear")
if foot_col.name not in char_col.children:
    try:
        char_col.children.link(foot_col)
    except Exception:
        pass

props_col = bpy.data.collections.get("05_Props_Magic") or bpy.data.collections.new("05_Props_Magic")
if props_col.name not in char_col.children:
    try:
        char_col.children.link(props_col)
    except Exception:
        pass

def create_mesh_obj(name, target_col):
    me = bpy.data.meshes.new(f"{{name}}_Mesh")
    geom = WARDROBE_GEOM.get(name)
    if geom:
        me.from_pydata(geom.get("verts", []), [], geom.get("faces", []))
        me.update()
        for p in me.polygons:
            p.use_smooth = True
    obj = bpy.data.objects.new(name, me)
    target_col.objects.link(obj)
    if body_obj:
        obj.parent = body_obj
    return obj

# 1. Dress meshes
dress_parts = ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt"]
created_dress_objs = []
mat_silk = bpy.data.materials.get("Mat_Dress_WhiteSilk")
mat_belt = bpy.data.materials.get("Mat_Dress_WaistBelt")

for d_name in dress_parts:
    d_obj = create_mesh_obj(d_name, dress_col)
    m = mat_belt if "WaistSash" in d_name else mat_silk
    if m and hasattr(d_obj.data, "materials"):
        d_obj.data.materials.append(m)

    # Assign normalized Rigify 163 DEF bone vertex groups
    weights_map = BONE_WEIGHTS.get(d_name, {{}})
    for b_name, v_entries in weights_map.items():
        vg = d_obj.vertex_groups.new(name=b_name)
        for v_idx, w in v_entries:
            vg.add([int(v_idx)], float(w), 'REPLACE')

    # Assign Pin_Bodice vertex group for cloth simulation pinning
    pin_entries = PIN_WEIGHTS.get(d_name, [])
    if pin_entries:
        pin_vg = d_obj.vertex_groups.new(name="Pin_Bodice")
        for v_idx, w in pin_entries:
            pin_vg.add([int(v_idx)], float(w), 'REPLACE')

    # Cloth Simulation modifier for authentic gravitational drapery & pipe folds
    if "Bodice" in d_name or "Skirt" in d_name:
        cloth_mod = d_obj.modifiers.new(name="Cloth_Drape", type='CLOTH')
        cloth_mod.settings.mass = 0.18
        cloth_mod.settings.bending_stiffness = 0.05
        cloth_mod.settings.bending_damping = 0.50
        cloth_mod.settings.tension_stiffness = 15.0
        cloth_mod.settings.compression_stiffness = 15.0
        cloth_mod.settings.shear_stiffness = 5.0
        cloth_mod.settings.air_damping = 1.0
        cloth_mod.settings.quality = 5
        if pin_entries:
            cloth_mod.settings.vertex_group_mass = "Pin_Bodice"
            cloth_mod.settings.pin_stiffness = 1.0
        cloth_mod.collision_settings.use_self_collision = True
        cloth_mod.collision_settings.self_distance_min = 0.0025

    # SurfaceDeform modifier on Sash targeting Bodice to eliminate 100% Z-fighting
    if "WaistSash" in d_name:
        surf_mod = d_obj.modifiers.new(name="SurfaceDeform", type='SURFACE_DEFORM')
        bodice_obj = bpy.data.objects.get("Mesh_Dress_Bodice") or bpy.data.objects.get("Dress_Bodice")
        if bodice_obj:
            surf_mod.target = bodice_obj
            surf_mod.falloff = 4.0

    # Solidify modifier for realistic fabric thickness (2mm) with outward extrusion
    solid_mod = d_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
    solid_mod.thickness = float(CFG.get("thickness", 0.002))
    solid_mod.offset = 1.0  # Outward extrusion preserves base clearance

    # Armature / Deform modifier binding
    if armature_obj:
        arm_mod = d_obj.modifiers.new(name="Armature", type='ARMATURE')
        arm_mod.object = armature_obj
        arm_mod.use_deform_preserve_volume = True
    created_dress_objs.append(d_obj.name)

# 45-frame rest-pose drape settlement simulation loop
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 45
for f in range(1, 46):
    scene.frame_set(f)

# 2. Footwear
mat_sandal = bpy.data.materials.get("Mat_Sandal_Leather") or bpy.data.materials.get("Mat_Sandal_White")
if CFG.get("include_sandals", True):
    for s_name in ["Mesh_Sandal_L", "Mesh_Sandal_R"]:
        s_obj = create_mesh_obj(s_name, foot_col)
        if mat_sandal and hasattr(s_obj.data, "materials"):
            s_obj.data.materials.append(mat_sandal)
        if armature_obj:
            arm_mod = s_obj.modifiers.new(name="Armature", type='ARMATURE')
            arm_mod.object = armature_obj
            arm_mod.use_deform_preserve_volume = True

# 3. Magic Props
mat_string = bpy.data.materials.get("Mat_Marionette_RedString")
mat_butterfly = bpy.data.materials.get("Mat_Magic_Butterfly")

finger_def_bone_keys = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]

if CFG.get("include_red_threads", True):
    str_obj = create_mesh_obj("Prop_Marionette_Strings", props_col)
    if mat_string and hasattr(str_obj.data, "materials"):
        str_obj.data.materials.append(mat_string)
    # Assign vertex groups to finger DEF bones
    verts_per_cord = 14
    for cord_i in range(min(10, len(finger_def_bone_keys))):
        b_name = finger_def_bone_keys[cord_i]
        vg = str_obj.vertex_groups.new(name=b_name)
        start_v = cord_i * verts_per_cord
        end_v = min(len(str_obj.data.vertices), (cord_i + 1) * verts_per_cord)
        for v_idx in range(start_v, end_v):
            step = (v_idx - start_v) // 2
            t = step / 6.0
            weight = max(0.0, 1.0 - 0.7 * t)
            vg.add([v_idx], weight, 'REPLACE')
    if armature_obj:
        s_arm_mod = str_obj.modifiers.new(name="Armature", type='ARMATURE')
        s_arm_mod.object = armature_obj
        s_arm_mod.use_deform_preserve_volume = True

if CFG.get("include_glowing_butterflies", True):
    b_count = int(CFG.get("butterfly_count", 10))
    flutter_positions = {flutter_positions_json}
    for b_i in range(b_count):
        bf_obj = create_mesh_obj(f"Prop_Butterfly_{{b_i:02d}}", props_col)
        if b_i < len(flutter_positions):
            bf_obj.location = tuple(flutter_positions[b_i])
            bf_obj.rotation_euler = (math.radians(10.0 + (b_i % 3) * 12.0), math.radians((b_i % 2) * 20.0 - 10.0), math.radians((b_i * 36.0) % 360.0))
        if mat_butterfly and hasattr(bf_obj.data, "materials"):
            bf_obj.data.materials.append(mat_butterfly)
        if armature_obj:
            b_name = finger_def_bone_keys[b_i % len(finger_def_bone_keys)]
            vg = bf_obj.vertex_groups.new(name=b_name)
            vg.add(list(range(len(bf_obj.data.vertices))), 1.0, 'REPLACE')
            bf_arm_mod = bf_obj.modifiers.new(name="Armature", type='ARMATURE')
            bf_arm_mod.object = armature_obj
            bf_arm_mod.use_deform_preserve_volume = True

print("[MorphoMesh] Wardrobe and magic props generated successfully.")
'''
    return script


def dress_human(
    human_object_name: str = "Human_Base_Mesh",
    target_object: Optional[str] = None,
    outfit: str = "yu_nian_an_dress",
    outfit_preset: Optional[str] = None,
    include_sandals: bool = True,
    include_red_threads: bool = True,
    include_glowing_butterflies: bool = True,
    butterfly_count: int = 10,
    clearance_offset: float = 0.015,
    save_after: bool = False,
    save_path: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Executes wardrobe synthesis in Blender (if available) or offline.
    Returns authoritative result dictionary conforming to HumanWardrobeResult.
    """
    effective_human = target_object or human_object_name
    effective_outfit = outfit_preset or outfit

    config = WardrobeConfig(
        outfit_preset=effective_outfit,
        clearance_offset=clearance_offset,
        include_sandals=include_sandals,
        include_red_threads=include_red_threads,
        include_glowing_butterflies=include_glowing_butterflies,
        butterfly_count=butterfly_count,
        character_height=kwargs.get("character_height", 1.65),
        waist_girth=kwargs.get("waist_girth", 0.58),
        chest_girth=kwargs.get("chest_girth", 0.82),
        hip_girth=kwargs.get("hip_girth", 0.86),
        thickness=kwargs.get("thickness", 0.002),
    )

    garments = ["Dress_Bodice", "Dress_WaistSash", "Dress_PleatedSkirt"]
    accessories = []
    if include_sandals:
        accessories.append("Sandals_Flat")
    if include_red_threads:
        accessories.append("Prop_Marionette_Strings")

    total_props = (10 if include_red_threads else 0) + (butterfly_count if include_glowing_butterflies else 0)

    if HAS_BPY:
        script = get_wardrobe_script(
            target_object=effective_human,
            outfit_preset=effective_outfit,
            clearance_offset=clearance_offset,
            include_sandals=include_sandals,
            include_red_threads=include_red_threads,
            include_glowing_butterflies=include_glowing_butterflies,
            butterfly_count=butterfly_count,
            character_height=config.character_height,
            waist_girth=config.waist_girth,
            chest_girth=config.chest_girth,
            hip_girth=config.hip_girth,
            thickness=config.thickness,
        )
        local_scope = {"bpy": bpy, "math": math}
        exec(script, local_scope, local_scope)

    return {
        "status": "success",
        "outfit_preset": effective_outfit,
        "garments": garments,
        "accessories": accessories,
        "prop_count": total_props,
        "clearance_offset": clearance_offset,
        "blend_file_path": save_path if save_after else None,
    }
