"""
MorphoMesh: Character Assembly Scene Builder Subsystem.

Manages in-Blender collection hierarchy (7-tier architecture),
calibrated studio 3-point lighting setups, multi-angle camera rigs
(turntable, front/side ortho, hero 3/4 portrait, canonical beauty cameras),
and authoritative master assembly script generation for Yu Nian An.
"""

from __future__ import annotations

import logging
import os
import sys
import json
import math
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

logger = logging.getLogger("morphomesh.character_assembler")

try:
    import bpy
    HAS_BPY = True
except (ImportError, ModuleNotFoundError):
    HAS_BPY = False

try:
    import mathutils
    from mathutils import Euler, Matrix, Vector
except (ImportError, ModuleNotFoundError):
    class _MockVector(list):
        """Lightweight 3D Vector for mathutils simulation."""
        def __init__(self, co=(0.0, 0.0, 0.0)):
            super().__init__([float(c) for c in co])

        @property
        def x(self) -> float:
            return self[0]

        @property
        def y(self) -> float:
            return self[1]

        @property
        def z(self) -> float:
            return self[2]

        @x.setter
        def x(self, val: float):
            self[0] = float(val)

        @y.setter
        def y(self, val: float):
            self[1] = float(val)

        @z.setter
        def z(self, val: float):
            self[2] = float(val)

    class _MockEuler(list):
        """Lightweight Euler angles for mathutils simulation."""
        def __init__(self, angles=(0.0, 0.0, 0.0), order: str = "XYZ"):
            super().__init__([float(a) for a in angles])
            self.order = order

    class _MockMatrix:
        """Lightweight 4x4 Transformation Matrix for mathutils simulation."""
        @classmethod
        def Identity(cls, size: int = 4):
            return cls()

    class _MockMathutils:
        """Safe mock container providing mathutils types."""
        Vector = _MockVector
        Euler = _MockEuler
        Matrix = _MockMatrix

    mathutils = _MockMathutils()
    Vector = _MockVector
    Euler = _MockEuler
    Matrix = _MockMatrix

from morphomesh.human_generator import (
    ARKIT_52_BLENDSHAPES,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    HumanAnatomyConfig,
    HumanMeshResult,
    generate_human_base_mesh,
    get_human_generation_script,
)
from morphomesh.human_grooming import (
    HairGroomConfig,
    get_default_hime_cut_layers,
    get_grooming_script,
)
from morphomesh.human_materials import (
    STANDARD_HUMAN_MATERIALS,
    HumanMaterialConfig,
    HumanPBRSuite,
    get_material_setup_script,
)
from morphomesh.human_rigging import (
    ALL_163_DEF_BONES,
    BODY_DEF_BONES,
    FACIAL_DEF_BONES,
    HumanRigConfig,
    generate_rigify_human_metarig,
    get_default_human_landmarks,
    get_rigging_script,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.wardrobe import (
    WardrobeConfig,
    generate_dress_bodice,
    generate_dress_pleated_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
    generate_yu_nian_an_wardrobe,
    get_wardrobe_script,
)

# ==============================================================================
# AUTHORITATIVE CONSTANTS & 7-TIER COLLECTION SPECIFICATION
# ==============================================================================

ROOT_COLLECTION_NAME = "Yu_Nian_An_Master"

TIER_COLLECTION_NAMES: Tuple[str, ...] = (
    "01_Body",
    "02_Hair",
    "03_Wardrobe",
    "04_Props",
    "05_Armature",
    "06_Lights_Camera",
)

SEVEN_TIER_COLLECTION_HIERARCHY: Dict[str, List[str]] = {
    ROOT_COLLECTION_NAME: list(TIER_COLLECTION_NAMES)
}

ALL_SEVEN_COLLECTIONS: Tuple[str, ...] = (ROOT_COLLECTION_NAME,) + TIER_COLLECTION_NAMES

FINGER_LANDMARK_KEYS: Tuple[str, ...] = (
    "thumb_L", "index_L", "middle_L", "ring_L", "pinky_L",
    "thumb_R", "index_R", "middle_R", "ring_R", "pinky_R",
)

FINGER_DEF_BONE_KEYS: Tuple[str, ...] = (
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
)

MATERIAL_NAMES: Tuple[str, ...] = (
    "Mat_Human_Skin_SSS",
    "Mat_Human_Eye_Outer_Cornea",
    "Mat_Human_Eye_Inner_Iris",
    "Mat_Human_Eye_Sclera",
    "Mat_Human_Hair",
    "Mat_Dress_WhiteSilk",
    "Mat_Dress_WaistBelt",
    "Mat_Sandal_Leather",
    "Mat_Marionette_RedString",
    "Mat_Magic_Butterfly",
)


# ==============================================================================
# CONFIGURATION DATA STRUCTURE
# ==============================================================================

@dataclass
class MasterAssemblyConfig:
    """Parametric specification for full Yu Nian An master character scene assembly."""

    character_name: str = "Yu_Nian_An"
    height: float = 1.65
    head_ratio: float = 7.41
    waist_girth: float = 0.58
    chest_girth: float = 0.82
    hip_girth: float = 0.86
    shoulder_width: float = 0.36
    arm_span: float = 1.62
    leg_length: float = 0.88
    poly_budget: int = 25000
    style: str = "stylized_photorealism"
    gender: str = "female"
    outfit_preset: str = "yu_nian_an_dress"
    hair_style: str = "hime_cut_long"
    hair_color: str = "silky_black"
    hair_strand_count: int = 15000
    butterfly_count: int = 10
    string_count: int = 10
    string_thickness: float = 0.00075
    wardrobe_thickness: float = 0.002
    clearance_offset: float = 0.015
    render_engine: str = "CYCLES"
    cycles_samples: int = 128
    color_management: str = "AgX"
    camera_lens: float = 85.0
    camera_distance: float = 2.0
    camera_target_z: float = 1.55
    camera_fullbody_lens: float = 50.0
    camera_fullbody_distance: float = 5.5
    camera_fullbody_target_z: float = 0.825
    key_light_temperature: float = 5500.0
    key_light_energy: float = 500.0
    fill_light_temperature: float = 6500.0
    fill_light_energy: float = 250.0
    rim_light_temperature: float = 4500.0
    rim_light_energy: float = 450.0
    include_body: bool = True
    include_hair: bool = True
    include_wardrobe: bool = True
    include_props: bool = True
    include_armature: bool = True
    include_lighting_camera: bool = True
    save_blend: bool = True
    output_blend_path: str = "output/yu_nian_an/Yu_Nian_An_Master.blend"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)



def _get_uv_unwrapping_script_snippet() -> str:
    """
    Returns self-contained Python function string to generate UV coordinates on all scene
    meshes, strictly mapped to 4K texture atlas quadrants:
    - Yu_Nian_An_Body: Head/face (Z >= 1.45m) into Q1 [0.0, 0.5] x [0.5, 1.0];
                       Body/limbs (Z < 1.45m) into Q2 [0.5, 1.0] x [0.5, 1.0]
    - Mesh_Dress_Bodice & PleatedSkirt: Q3 [0.0, 0.5] x [0.0, 0.5]
    - Mesh_Dress_WaistSash: Q4 [0.5, 1.0] x [0.275, 0.50]
    - Mesh_Sandal_L/R: Q4 [0.50, 0.825] x [0.0, 0.275]
    - Mesh_Lips: Q1 mouth region [0.20, 0.30] x [0.60, 0.68]
    - Mesh_Eyelid_Left/Right: Q1 eye region [0.10, 0.40] x [0.72, 0.82]
    - Prop_Butterfly_*: Q4 [0.85, 0.98] x [0.35, 0.48]
    - Prop_Marionette_Strings: Q4 [0.50, 0.60] x [0.35, 0.45]
    """
    return '''
def assign_texture_atlas_uvs(s_scale=1.0):
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        name = obj.name

        uv_layer = mesh.uv_layers.get('UVMap')
        if not uv_layer:
            uv_layer = mesh.uv_layers.new(name='UVMap')
        mesh.uv_layers.active = uv_layer

        if name == 'Yu_Nian_An_Body':
            z_thresh = 1.45 * s_scale
            z_head_h = 0.20 * s_scale
            for poly in mesh.polygons:
                cz = sum(mesh.vertices[vi].co.z for vi in poly.vertices) / len(poly.vertices)
                is_head = (cz >= z_thresh)
                poly_thetas = []
                for vi in poly.vertices:
                    v = mesh.vertices[vi]
                    th = math.atan2(v.co.x, -v.co.y)
                    poly_thetas.append(th)
                if max(poly_thetas) - min(poly_thetas) > math.pi:
                    poly_thetas = [th + 2 * math.pi if th < 0 else th for th in poly_thetas]

                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    local_th = poly_thetas[list(poly.vertices).index(vi)]
                    u_norm = ((local_th / (2.0 * math.pi)) + 0.5) % 1.0
                    if is_head:
                        v_norm = max(0.0, min(1.0, (v.co.z - z_thresh) / z_head_h))
                        U = 0.0 + 0.5 * u_norm
                        V = 0.5 + 0.5 * v_norm
                    else:
                        v_norm = max(0.0, min(1.0, v.co.z / z_thresh))
                        U = 0.5 + 0.5 * u_norm
                        V = 0.5 + 0.5 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name in ('Mesh_Dress_Bodice', 'Mesh_Dress_PleatedSkirt'):
            z_min_dress = 0.50 * s_scale
            z_span_dress = 0.90 * s_scale
            for poly in mesh.polygons:
                poly_thetas = []
                for vi in poly.vertices:
                    v = mesh.vertices[vi]
                    th = math.atan2(v.co.x, -v.co.y)
                    poly_thetas.append(th)
                if max(poly_thetas) - min(poly_thetas) > math.pi:
                    poly_thetas = [th + 2 * math.pi if th < 0 else th for th in poly_thetas]

                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    local_th = poly_thetas[list(poly.vertices).index(vi)]
                    u_norm = ((local_th / (2.0 * math.pi)) + 0.5) % 1.0
                    v_norm = max(0.0, min(1.0, (v.co.z - z_min_dress) / z_span_dress))
                    U = 0.0 + 0.5 * u_norm
                    V = 0.0 + 0.5 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name == 'Mesh_Dress_WaistSash':
            z_min_sash = 0.64 * s_scale
            z_span_sash = 0.44 * s_scale
            for poly in mesh.polygons:
                poly_thetas = []
                for vi in poly.vertices:
                    v = mesh.vertices[vi]
                    th = math.atan2(v.co.x, -v.co.y)
                    poly_thetas.append(th)
                if max(poly_thetas) - min(poly_thetas) > math.pi:
                    poly_thetas = [th + 2 * math.pi if th < 0 else th for th in poly_thetas]

                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    local_th = poly_thetas[list(poly.vertices).index(vi)]
                    u_norm = ((local_th / (2.0 * math.pi)) + 0.5) % 1.0
                    v_norm = max(0.0, min(1.0, (v.co.z - z_min_sash) / z_span_sash))
                    U = 0.5 + 0.5 * u_norm
                    V = 0.28 + 0.20 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name in ('Mesh_Sandal_L', 'Mesh_Sandal_R'):
            zs = [v.co.z for v in mesh.vertices]
            ys = [v.co.y for v in mesh.vertices]
            xs = [v.co.x for v in mesh.vertices]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            for poly in mesh.polygons:
                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    u_norm = (v.co.x - min_x) / max(1e-5, max_x - min_x)
                    v_norm = (v.co.y - min_y) / max(1e-5, max_y - min_y)
                    U = 0.50 + 0.30 * u_norm
                    V = 0.01 + 0.24 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name == 'Mesh_Lips':
            xs = [v.co.x for v in mesh.vertices]
            zs = [v.co.z for v in mesh.vertices]
            min_x, max_x = min(xs), max(xs)
            min_z, max_z = min(zs), max(zs)
            span_x = max(1e-5, max_x - min_x)
            span_z = max(1e-5, max_z - min_z)
            for poly in mesh.polygons:
                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    u_norm = max(0.0, min(1.0, (v.co.x - min_x) / span_x))
                    v_norm = max(0.0, min(1.0, (v.co.z - min_z) / span_z))
                    U = 0.20 + 0.10 * u_norm
                    V = 0.60 + 0.08 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name in ('Mesh_Eyelid_Left', 'Mesh_Eyelid_Right'):
            is_left = 'Left' in name
            z_center_eye = 1.50 * s_scale
            for poly in mesh.polygons:
                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    u_norm = 0.5 + v.co.x / (0.10 * s_scale)
                    v_norm = max(0.0, min(1.0, (v.co.z - z_center_eye) / (0.04 * s_scale)))
                    if is_left:
                        U = 0.28 + 0.12 * max(0.0, min(1.0, u_norm))
                    else:
                        U = 0.10 + 0.12 * max(0.0, min(1.0, u_norm))
                    V = 0.72 + 0.10 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name.startswith('Mesh_Eye_'):
            # Dedicated planar eye UV projection centered at (0.5, 0.5) for iris & pupil procedural texturing
            xs = [v.co.x for v in mesh.vertices]
            zs = [v.co.z for v in mesh.vertices]
            cx = (min(xs) + max(xs)) * 0.5
            cz = (min(zs) + max(zs)) * 0.5
            r = max(1e-5, (max(xs) - min(xs)) * 0.5)
            for poly in mesh.polygons:
                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    u = 0.5 + 0.5 * ((v.co.x - cx) / r)
                    w = 0.5 + 0.5 * ((v.co.z - cz) / r)
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (u, w)

        elif name.startswith('Prop_Butterfly'):
            xs = [v.co.x for v in mesh.vertices]
            zs = [v.co.z for v in mesh.vertices]
            min_x, max_x = min(xs), max(xs)
            min_z, max_z = min(zs), max(zs)
            for poly in mesh.polygons:
                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    u_norm = (v.co.x - min_x) / max(1e-5, max_x - min_x)
                    v_norm = (v.co.z - min_z) / max(1e-5, max_z - min_z)
                    U = 0.85 + 0.13 * u_norm
                    V = 0.35 + 0.13 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        elif name == 'Prop_Marionette_Strings':
            for poly in mesh.polygons:
                for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                    v = mesh.vertices[vi]
                    u_norm = max(0.0, min(1.0, 0.5 + v.co.x / (0.8 * s_scale)))
                    v_norm = max(0.0, min(1.0, (v.co.z - 0.6 * s_scale) / (0.4 * s_scale)))
                    U = 0.50 + 0.10 * u_norm
                    V = 0.35 + 0.10 * v_norm
                    mesh.uv_layers['UVMap'].data[loop_idx].uv = (U, V)

        else:
            if len(mesh.vertices) > 0:
                xs = [v.co.x for v in mesh.vertices]
                ys = [v.co.y for v in mesh.vertices]
                min_x, max_x = min(xs), max(xs)
                min_y, max_y = min(ys), max(ys)
                span_x = max(1e-5, max_x - min_x)
                span_y = max(1e-5, max_y - min_y)
                for poly in mesh.polygons:
                    for loop_idx, vi in zip(poly.loop_indices, poly.vertices):
                        v = mesh.vertices[vi]
                        u_norm = (v.co.x - min_x) / span_x
                        v_norm = (v.co.y - min_y) / span_y
                        mesh.uv_layers['UVMap'].data[loop_idx].uv = (0.50 + 0.50 * u_norm, 0.00 + 0.50 * v_norm)
'''


def assign_texture_atlas_uvs(s_scale: float = 1.0) -> None:
    """
    Python entrypoint to assign UV coordinates across all scene meshes in Blender.
    """
    if HAS_BPY:
        local_scope = {"bpy": bpy, "math": math}
        exec(_get_uv_unwrapping_script_snippet() + f"\nassign_texture_atlas_uvs(s_scale={s_scale})", local_scope, local_scope)


# ==============================================================================
# STANDALONE BLENDER 4.5+ SCRIPT GENERATOR
# ==============================================================================

def get_master_assembly_script(
    config: Optional[Union[MasterAssemblyConfig, Dict[str, Any]]] = None,
    output_blend_path: Optional[str] = None,
) -> str:
    """
    Generates a standalone, fully self-contained Python script executable inside
    Blender 4.5+ LTS (headless or GUI) that generates the complete Yu Nian An master scene:
    1. 7-tier collection hierarchy (Yu_Nian_An_Master + 6 children)
    2. PBR shader suite (Random Walk SSS, dual-chamber refractive eyes, hair, silk, emission)
    3. 100% quad body mesh with 29 vertex groups, 34 landmarks, 52 ARKit FACS shape keys
    4. Rigify 163 DEF bones armature with anti-pinch weights and Armature modifier
    5. Hair curves (6 strata) with GN modifiers parented to body scalp
    6. Wardrobe (dress, sash, sandals) with Solidify 0.002m and Armature binding
    7. Props (10 crimson strings anchored to fingers + 10 luminous white butterflies)
    8. Studio lighting (Key 5500K, Fill 6500K, Rim 4500K) + 85mm portrait camera
    9. Cycles 128 samples + AgX color management
    10. Automated save to output/yu_nian_an/Yu_Nian_An_Master.blend
    """
    cfg_obj: MasterAssemblyConfig
    if isinstance(config, MasterAssemblyConfig):
        cfg_obj = config
    elif isinstance(config, dict):
        cfg_obj = MasterAssemblyConfig(**config)
    else:
        cfg_obj = MasterAssemblyConfig()

    effective_output_path = (output_blend_path or cfg_obj.output_blend_path).replace("\\", "/")

    # Sub-scripts from authoritative generator modules
    body_gen_cfg = HumanAnatomyConfig(
        height=cfg_obj.height,
        head_ratio=cfg_obj.head_ratio,
        waist_girth=cfg_obj.waist_girth,
        chest_girth=cfg_obj.chest_girth,
        hip_girth=cfg_obj.hip_girth,
        shoulder_width=cfg_obj.shoulder_width,
        arm_span=cfg_obj.arm_span,
        leg_length=cfg_obj.leg_length,
        poly_budget=cfg_obj.poly_budget,
        style=cfg_obj.style,
        gender=cfg_obj.gender,
    )
    body_script = get_human_generation_script(f"{cfg_obj.character_name}_Body", body_gen_cfg)

    rig_cfg = HumanRigConfig(
        rig_type="rigify_human",
        pose="puppeteer_pose",
        export_format="fbx",
    )
    rig_script = get_rigging_script(f"{cfg_obj.character_name}_Body", config=rig_cfg)

    mat_script = get_material_setup_script(
        target_object=f"{cfg_obj.character_name}_Body",
        render_engine=cfg_obj.render_engine,
        assign_slots=True,
    )

    groom_script = get_grooming_script(
        target_object=f"{cfg_obj.character_name}_Body",
        hair_style=cfg_obj.hair_style,
        hair_color=cfg_obj.hair_color,
        strand_count=cfg_obj.hair_strand_count,
        include_eyebrows=True,
        include_eyelashes=True,
        generate_ribbons=False,
    )

    wardrobe_script = get_wardrobe_script(
        target_object=f"{cfg_obj.character_name}_Body",
        outfit_preset=cfg_obj.outfit_preset,
        clearance_offset=cfg_obj.clearance_offset,
        include_sandals=True,
        include_red_threads=True,
        include_glowing_butterflies=True,
        butterfly_count=cfg_obj.butterfly_count,
        character_height=cfg_obj.height,
        waist_girth=cfg_obj.waist_girth,
        chest_girth=cfg_obj.chest_girth,
        hip_girth=cfg_obj.hip_girth,
        thickness=cfg_obj.wardrobe_thickness,
    )

    master_script = f'''# ==============================================================================
# MORPHOMESH MASTER ASSET ASSEMBLY SCRIPT: YU NIAN AN (余念安)
# Compatible with Blender 4.5+ LTS / Blender 5.2+ LTS
# ==============================================================================
import bpy
import math
import mathutils
import bmesh
import os
import sys
import json
import tempfile

print("[MorphoMesh] Commencing Yu Nian An Master Character Assembly...")

# ------------------------------------------------------------------------------
# STEP 1: INITIALIZE 7-TIER COLLECTION HIERARCHY
# ------------------------------------------------------------------------------
root_col_name = "Yu_Nian_An_Master"
master_col = bpy.data.collections.get(root_col_name)
if not master_col:
    master_col = bpy.data.collections.new(root_col_name)
    bpy.context.scene.collection.children.link(master_col)

tier_names = [
    "01_Body",
    "02_Hair",
    "03_Wardrobe",
    "04_Props",
    "05_Armature",
    "06_Lights_Camera",
]
tier_cols = {{}}
for t_name in tier_names:
    c = bpy.data.collections.get(t_name)
    if not c:
        c = bpy.data.collections.new(t_name)
        master_col.children.link(c)
    tier_cols[t_name] = c

# Clean default startup cube/light if present in scene root
default_col = bpy.data.collections.get("Collection")
if default_col:
    for o in list(default_col.objects):
        if o.name in ("Cube", "Light", "Camera"):
            bpy.data.objects.remove(o, do_unlink=True)
    if not default_col.objects and default_col.name in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.unlink(default_col)

# Helper to organize object into designated collection tier
def organize_object(obj, target_tier_name):
    if not obj:
        return
    t_col = tier_cols.get(target_tier_name)
    if not t_col:
        return
    if obj.type == 'MESH' and hasattr(obj.data, 'polygons'):
        for p in obj.data.polygons:
            p.use_smooth = True
    if obj.name not in t_col.objects:
        t_col.objects.link(obj)
    # Unlink from scene root collection
    if obj.name in bpy.context.scene.collection.objects:
        bpy.context.scene.collection.objects.unlink(obj)
    # Unlink from any other collection except target tier
    for c in list(bpy.data.collections):
        if c.name != target_tier_name and obj.name in c.objects:
            c.objects.unlink(obj)

# ------------------------------------------------------------------------------
# STEP 2: SYNTHESIZE BODY GEOMETRY (100% QUADS, 29 VGs, 34 LANDMARKS, 52 ARKit KEYS)
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 2: Generating Body Mesh with Pure Quads and FACS Blendshapes...")
{body_script}

body_obj = bpy.data.objects.get("{cfg_obj.character_name}_Body") or bpy.context.active_object
if body_obj:
    body_obj.name = "{cfg_obj.character_name}_Body"
    organize_object(body_obj, "01_Body")

# ------------------------------------------------------------------------------
# STEP 3: BUILD PBR MATERIAL SUITE
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 3: Compiling PBR Material Suite (Random Walk SSS, Eyes, Hair, Fabrics, Props)...")
{mat_script}

# Ensure all created materials have fake user so Blender never purges them
all_mat_names = [
    "Mat_Human_Skin_SSS",
    "Mat_Human_Eye_Outer_Cornea",
    "Mat_Human_Eye_Inner_Iris",
    "Mat_Human_Eye_Sclera",
    "Mat_Human_Hair",
    "Mat_Human_Lips",
    "Mat_Dress_WhiteSilk",
    "Mat_Dress_WaistBelt",
    "Mat_Sash_Satin",
    "Mat_Sandal_Leather",
    "Mat_Sandal_White",
    "Mat_Marionette_RedString",
    "Mat_Magic_Butterfly",
]
for m_name in all_mat_names:
    m_ref = bpy.data.materials.get(m_name)
    if not m_ref:
        m_ref = bpy.data.materials.new(name=m_name)
        m_ref.use_nodes = True
        if m_name == "Mat_Human_Lips":
            bsdf = m_ref.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                if "Base Color" in bsdf.inputs:
                    bsdf.inputs["Base Color"].default_value = (0.75, 0.32, 0.35, 1.0)
                if "Roughness" in bsdf.inputs:
                    bsdf.inputs["Roughness"].default_value = 0.30
                if "Subsurface Weight" in bsdf.inputs:
                    bsdf.inputs["Subsurface Weight"].default_value = 0.25
                elif "Subsurface" in bsdf.inputs:
                    bsdf.inputs["Subsurface"].default_value = 0.25
                if "Subsurface Radius" in bsdf.inputs:
                    bsdf.inputs["Subsurface Radius"].default_value = (0.85, 0.25, 0.25)
                if "Subsurface Scale" in bsdf.inputs:
                    bsdf.inputs["Subsurface Scale"].default_value = 0.015
        elif m_name == "Mat_Sash_Satin":
            bsdf = m_ref.node_tree.nodes.get("Principled BSDF")
            if bsdf and "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.820, 0.880, 0.940, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.32
        elif m_name == "Mat_Sandal_White":
            bsdf = m_ref.node_tree.nodes.get("Principled BSDF")
            if bsdf and "Base Color" in bsdf.inputs:
                bsdf.inputs["Base Color"].default_value = (0.92, 0.92, 0.94, 1.0)
                bsdf.inputs["Roughness"].default_value = 0.45
    if m_ref:
        m_ref.use_fake_user = True

# Assign material slots to body mesh
s_scale = {cfg_obj.height} / 1.65
if body_obj and body_obj.type == 'MESH':
    mat_scalp = bpy.data.materials.get("Mat_Human_Scalp") or bpy.data.materials.new(name="Mat_Human_Scalp")
    mat_scalp.use_nodes = True
    mat_scalp.use_fake_user = True
    s_bsdf = next((n for n in mat_scalp.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if s_bsdf:
        if "Base Color" in s_bsdf.inputs:
            s_bsdf.inputs["Base Color"].default_value = (0.012, 0.011, 0.012, 1.0)
        if "Roughness" in s_bsdf.inputs:
            s_bsdf.inputs["Roughness"].default_value = 0.70
        if "Specular IOR Level" in s_bsdf.inputs:
            s_bsdf.inputs["Specular IOR Level"].default_value = 0.25
        elif "Specular" in s_bsdf.inputs:
            s_bsdf.inputs["Specular"].default_value = 0.25
        if "Coat Weight" in s_bsdf.inputs:
            s_bsdf.inputs["Coat Weight"].default_value = 0.0
        elif "Clearcoat" in s_bsdf.inputs:
            s_bsdf.inputs["Clearcoat"].default_value = 0.0

    slot_order = [
        "Mat_Human_Skin_SSS",
        "Mat_Human_Eye_Outer_Cornea",
        "Mat_Human_Eye_Inner_Iris",
        "Mat_Human_Eye_Sclera",
        "Mat_Human_Hair",
        "Mat_Human_Lips",
        "Mat_Human_Scalp",
    ]
    body_obj.data.materials.clear()
    for s_name in slot_order:
        mat_ref = bpy.data.materials.get(s_name)
        if mat_ref:
            body_obj.data.materials.append(mat_ref)

    slot_skin = 0
    slot_hair = slot_order.index("Mat_Human_Hair")
    slot_scalp = slot_order.index("Mat_Human_Scalp") if "Mat_Human_Scalp" in slot_order else slot_hair

    vg_scalp = body_obj.vertex_groups.get("scalp") or body_obj.vertex_groups.new(name="scalp")
    scalp_verts = set()
    for v in body_obj.data.vertices:
        if v.co.z >= 1.600 * s_scale or (v.co.z >= 1.55 * s_scale and v.co.y > -0.04 * s_scale):
            vg_scalp.add([v.index], 1.0, 'REPLACE')
            scalp_verts.add(v.index)

    for poly in body_obj.data.polygons:
        pts = [body_obj.data.vertices[v].co for v in poly.vertices]
        x_avg = sum(pt.x for pt in pts) / len(pts)
        y_avg = sum(pt.y for pt in pts) / len(pts)
        z_avg = sum(pt.z for pt in pts) / len(pts)

        # 1. Mouth/Lips: Base mesh quads remain slot_skin (dedicated pure-quad Mesh_Lips provides 3D anime lips)
        # 2. Cranial Scalp: assign dedicated matte Mat_Human_Scalp (Roughness 0.70, Coat 0.0) to eliminate white glare
        if all(v in scalp_verts for v in poly.vertices) or (z_avg >= 1.605 * s_scale and y_avg > -0.09 * s_scale) or (z_avg >= 1.570 * s_scale and y_avg > -0.03 * s_scale):
            poly.material_index = slot_scalp
        else:
            poly.material_index = slot_skin

# Create dual-chamber eye meshes in 01_Body
def create_uv_sphere_mesh(name, center, radius, rings=16, sectors=16):
    mesh = bpy.data.meshes.new(f"{{name}}_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=sectors, v_segments=rings, radius=radius)
    uv_layer = bm.loops.layers.uv.new("UVMap")
    cx, cy, cz = center
    for v in bm.verts:
        v.co.x += cx
        v.co.y += cy
        v.co.z += cz
    # Forward planar UV projection centered at (0.5, 0.5)
    for face in bm.faces:
        for loop in face.loops:
            u = 0.5 + 0.5 * ((loop.vert.co.x - cx) / radius)
            v_coord = 0.5 + 0.5 * ((loop.vert.co.z - cz) / radius)
            loop[uv_layer].uv = (u, v_coord)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj

def create_delicate_anime_lips_mesh(name, center, s_scale=1.0):
    """
    Creates dedicated 100% pure-quad anime mouth mesh (Mesh_Lips) matching Yu Nian An's
    aesthetic from media_1788716034772.jpg:
    - 6 rows x 11 columns = 50 pure quads, 66 vertices.
    - Width: 22mm (X in [-0.011m, +0.011m] * s_scale).
    - Features: subtle cupid's bow, recessed dark oral commissure slit, and pillowed lower vermilion.
    - Assigned 2 material slots: Mat_Human_Lips, Mat_Human_Oral_Slit.
    """
    mesh = bpy.data.meshes.new(f"{{name}}_Mesh")
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")

    n_rows = 6
    n_cols = 11
    w_half = 0.0110 * s_scale
    cx, cy_base, cz_center = center

    body_for_lips = bpy.data.objects.get("Yu_Nian_An_Body")
    bvh_lips = None
    if body_for_lips:
        try:
            bvh_lips = mathutils.bvhtree.BVHTree.FromObject(body_for_lips, bpy.context.evaluated_depsgraph_get())
        except Exception:
            bvh_lips = None

    grid_verts = []
    for r in range(n_rows):
        row_verts = []
        v_param = r / (n_rows - 1)
        for c in range(n_cols):
            u_param = c / (n_cols - 1)
            x = cx + (-w_half + 2.0 * w_half * u_param)
            x_norm = (x - cx) / w_half
            arch = max(0.0, 1.0 - x_norm * x_norm)

            # Row Z elevations
            if r == 5:    # Upper border / philtrum margin / cupid's bow
                z = cz_center + (0.0075 - 0.0012 * math.sin(math.pi * u_param) ** 2) * s_scale
            elif r == 4:  # Upper lip vermilion
                z = cz_center + (0.0042 + 0.0006 * arch) * s_scale
            elif r == 3:  # Oral fissure upper margin
                z = cz_center + (0.0010 - 0.0008 * (1.0 - arch)) * s_scale
            elif r == 2:  # Oral fissure line (slit opening)
                z = cz_center + (0.0000 - 0.0008 * (1.0 - arch)) * s_scale
            elif r == 1:  # Lower lip vermilion fullness
                z = cz_center - (0.0040 + 0.0012 * arch) * s_scale
            else:         # r == 0: Lower border / labiomental groove
                z = cz_center - 0.0080 * s_scale

            # Protrusion thickness outward along facial normal (+0.3mm to +1.5mm)
            if r == 5 or r == 0:
                thick = (0.0003 + 0.0001 * arch) * s_scale  # +0.3mm to +0.4mm flush margin
            elif r == 4:
                thick = (0.0005 + 0.0008 * arch) * s_scale  # up to +1.3mm upper vermilion
            elif r == 3:
                thick = (0.0004 + 0.0004 * arch) * s_scale  # +0.8mm
            elif r == 2:
                thick = (0.0003 + 0.0003 * arch) * s_scale  # +0.6mm oral fissure slit
            elif r == 1:
                thick = (0.0005 + 0.0010 * arch) * s_scale  # up to +1.5mm lower vermilion pillow
            else:
                thick = 0.0003 * s_scale

            placed = False
            if bvh_lips:
                probe = mathutils.Vector((x, -0.115 * s_scale, z))
                loc, norm, _, _ = bvh_lips.find_nearest(probe)
                if loc is not None and norm is not None:
                    v_co = loc + norm * thick
                    x = v_co.x
                    y = v_co.y
                    z = v_co.z
                    placed = True

            if not placed:
                # Sloped facial surface formula calibrated to Yu Nian An cranium at center_y = -0.1245 * s
                cy_local = cy_base - (z - cz_center) * 0.35
                y_curve = cy_local + (math.sqrt(max(0.0, (0.075 * s_scale)**2 - (x - cx)**2)) - 0.075 * s_scale)
                y = y_curve - thick

            vert = bm.verts.new((x, y, z))
            row_verts.append((vert, u_param, v_param))
        grid_verts.append(row_verts)

    for r in range(n_rows - 1):
        for c in range(n_cols - 1):
            v00, u00, v_00 = grid_verts[r][c]
            v10, u10, v_10 = grid_verts[r][c + 1]
            v11, u11, v_11 = grid_verts[r + 1][c + 1]
            v01, u01, v_01 = grid_verts[r + 1][c]

            face = bm.faces.new([v00, v10, v11, v01])
            # Scale & offset UVs into the mouth region of Q1 [0.20, 0.30] x [0.60, 0.68]
            for loop in face.loops:
                if loop.vert == v00: loop[uv_layer].uv = (0.20 + 0.10 * u00, 0.60 + 0.08 * v_00)
                elif loop.vert == v10: loop[uv_layer].uv = (0.20 + 0.10 * u10, 0.60 + 0.08 * v_10)
                elif loop.vert == v11: loop[uv_layer].uv = (0.20 + 0.10 * u11, 0.60 + 0.08 * v_11)
                elif loop.vert == v01: loop[uv_layer].uv = (0.20 + 0.10 * u01, 0.60 + 0.08 * v_01)

            # Material slots: 0=Mat_Human_Lips, 1=Mat_Human_Oral_Slit
            if r == 2 and 1 <= c <= n_cols - 2:
                face.material_index = 1  # Mat_Human_Oral_Slit
            else:
                face.material_index = 0  # Mat_Human_Lips

    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new(name, mesh)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj

s = {cfg_obj.height} / 1.65
ipd = 0.062 * s
eye_z = 1.520 * s
eye_y = -0.118 * s

eye_left_cornea = create_uv_sphere_mesh("Mesh_Eye_Left_CorneaSclera", (ipd / 2.0, eye_y, eye_z), 0.0125 * s)
eye_right_cornea = create_uv_sphere_mesh("Mesh_Eye_Right_CorneaSclera", (-ipd / 2.0, eye_y, eye_z), 0.0125 * s)
eye_left_iris = create_uv_sphere_mesh("Mesh_Eye_Left_IrisPupil", (ipd / 2.0, eye_y + 0.002 * s, eye_z), 0.0105 * s)
eye_right_iris = create_uv_sphere_mesh("Mesh_Eye_Right_IrisPupil", (-ipd / 2.0, eye_y + 0.002 * s, eye_z), 0.0105 * s)

# Create almond eyelids framing the eye spheres at Z ~ 1.520m, X ~ +/- 0.035m
def create_almond_eyelid_mesh(name, center, eye_radius=0.0125, s_scale=1.0, is_left=True):
    mesh = bpy.data.meshes.new(f"{{name}}_Mesh")
    bm = bmesh.new()
    sign = 1.0 if is_left else -1.0
    cx, cy, cz = center
    num_pts = 16
    inner_verts = []
    outer_verts = []

    for i in range(num_pts):
        t = 2.0 * math.pi * i / num_pts
        cos_t = math.cos(t)
        sin_t = math.sin(t)
        # Almond eye formula:
        dx = sign * cos_t * 0.0135 * s_scale
        dz = (sin_t * 0.0065 if sin_t >= 0 else sin_t * 0.0042) * s_scale
        dz += (1.0 - cos_t) * 0.0008 * s_scale
        r_sph = eye_radius * 1.02
        dist_sq = dx * dx + dz * dz
        dy = -math.sqrt(max(0.0, r_sph * r_sph - dist_sq)) if dist_sq < r_sph * r_sph else 0.0
        v_in = bm.verts.new((cx + dx, cy + dy, cz + dz))
        inner_verts.append(v_in)

        if sin_t >= -0.10:  # Upper eyelid: prominent lash band with matte eyeliner
            dx_out = dx * 1.28 + (sign * 0.0025 if cos_t > 0.6 else 0.0) * s_scale
            dz_out = dz + 0.0030 * s_scale  # 3.0mm prominent lash band
            dy_out = dy - 0.0008 * s_scale  # sitting neatly over eyeball
        else:               # Lower eyelid: tucked flush into cheek, zero eye-bag shelf
            dx_out = dx * 1.06
            dz_out = dz - 0.0010 * s_scale  # 1.0mm delicate rim
            dy_out = dy - 0.0002 * s_scale  # flush to cheek

        v_out = bm.verts.new((cx + dx_out, cy + dy_out, cz + dz_out))
        outer_verts.append(v_out)

    for i in range(num_pts):
        ni = (i + 1) % num_pts
        t_mid = 2.0 * math.pi * (i + 0.5) / num_pts
        sin_mid = math.sin(t_mid)
        face = bm.faces.new([inner_verts[i], inner_verts[ni], outer_verts[ni], outer_verts[i]])
        # Slot 0 = Mat_Human_Eyeliner (upper), Slot 1 = Mat_Human_Skin_SSS (lower)
        face.material_index = 0 if sin_mid >= -0.15 else 1

    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    for poly in mesh.polygons:
        poly.use_smooth = True
    return obj

eyelid_left = create_almond_eyelid_mesh("Mesh_Eyelid_Left", (ipd / 2.0, eye_y, eye_z), 0.0125 * s, s, True)
eyelid_right = create_almond_eyelid_mesh("Mesh_Eyelid_Right", (-ipd / 2.0, eye_y, eye_z), 0.0125 * s, s, False)

mat_cornea = bpy.data.materials.get("Mat_Human_Eye_Outer_Cornea")
mat_iris = bpy.data.materials.get("Mat_Human_Eye_Inner_Iris")
mat_skin = bpy.data.materials.get("Mat_Human_Skin_SSS")
mat_lips = bpy.data.materials.get("Mat_Human_Lips")

mat_eyeliner = bpy.data.materials.get("Mat_Human_Eyeliner") or bpy.data.materials.new(name="Mat_Human_Eyeliner")
mat_eyeliner.use_nodes = True
mat_eyeliner.use_fake_user = True
el_bsdf = next((n for n in mat_eyeliner.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if el_bsdf:
    if "Base Color" in el_bsdf.inputs:
        el_bsdf.inputs["Base Color"].default_value = (0.01, 0.01, 0.015, 1.0)
    if "Roughness" in el_bsdf.inputs:
        el_bsdf.inputs["Roughness"].default_value = 0.65
    if "Specular IOR Level" in el_bsdf.inputs:
        el_bsdf.inputs["Specular IOR Level"].default_value = 0.10
    elif "Specular" in el_bsdf.inputs:
        el_bsdf.inputs["Specular"].default_value = 0.10
    if "Coat Weight" in el_bsdf.inputs:
        el_bsdf.inputs["Coat Weight"].default_value = 0.0
    elif "Clearcoat" in el_bsdf.inputs:
        el_bsdf.inputs["Clearcoat"].default_value = 0.0

mat_oral_slit = bpy.data.materials.get("Mat_Human_Oral_Slit") or bpy.data.materials.new(name="Mat_Human_Oral_Slit")
mat_oral_slit.use_nodes = True
mat_oral_slit.use_fake_user = True
os_bsdf = next((n for n in mat_oral_slit.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
if os_bsdf:
    if "Base Color" in os_bsdf.inputs:
        os_bsdf.inputs["Base Color"].default_value = (0.08, 0.02, 0.025, 1.0)
    if "Roughness" in os_bsdf.inputs:
        os_bsdf.inputs["Roughness"].default_value = 0.60
    if "Specular IOR Level" in os_bsdf.inputs:
        os_bsdf.inputs["Specular IOR Level"].default_value = 0.10
    elif "Specular" in os_bsdf.inputs:
        os_bsdf.inputs["Specular"].default_value = 0.10
    if "Coat Weight" in os_bsdf.inputs:
        os_bsdf.inputs["Coat Weight"].default_value = 0.0
    elif "Clearcoat" in os_bsdf.inputs:
        os_bsdf.inputs["Clearcoat"].default_value = 0.0

lip_mesh = create_delicate_anime_lips_mesh("Mesh_Lips", (0.0, -0.1245 * s, 1.4625 * s), s)

for e_obj, e_mats in [(eye_left_cornea, [mat_cornea]), (eye_right_cornea, [mat_cornea]),
                      (eye_left_iris, [mat_iris]), (eye_right_iris, [mat_iris]),
                      (eyelid_left, [mat_eyeliner, mat_skin]), (eyelid_right, [mat_eyeliner, mat_skin]),
                      (lip_mesh, [mat_lips, mat_oral_slit])]:
    organize_object(e_obj, "01_Body")
    if hasattr(e_obj.data, "materials"):
        e_obj.data.materials.clear()
        for m in e_mats:
            if m:
                e_obj.data.materials.append(m)

    # Re-assign polygon material indices after materials.clear() resets them to 0
    if e_obj == lip_mesh:
        n_rows = 6
        n_cols = 11
        for r in range(n_rows - 1):
            for c in range(n_cols - 1):
                p_idx = r * (n_cols - 1) + c
                if p_idx < len(e_obj.data.polygons):
                    if r == 2 and 1 <= c <= n_cols - 2:
                        e_obj.data.polygons[p_idx].material_index = 1  # Mat_Human_Oral_Slit
                    else:
                        e_obj.data.polygons[p_idx].material_index = 0  # Mat_Human_Lips
    elif e_obj in (eyelid_left, eyelid_right):
        num_pts = len(e_obj.data.polygons)
        for i in range(num_pts):
            t_mid = 2.0 * math.pi * (i + 0.5) / num_pts
            sin_mid = math.sin(t_mid)
            # Upper quads = Mat_Human_Eyeliner (slot 0), lower quads = Mat_Human_Skin_SSS (slot 1)
            e_obj.data.polygons[i].material_index = 0 if sin_mid >= -0.15 else 1

    if body_obj:
        e_obj.parent = body_obj

# ------------------------------------------------------------------------------
# STEP 4: GENERATE ARMATURE (163 DEF BONES & ANTI-PINCH SKINNING)
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 4: Constructing Rigify Armature (163 DEF bones, landmark alignment, anti-pinch weights)...")
{rig_script}

arm_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify") or bpy.data.objects.get("rig")
if arm_obj:
    organize_object(arm_obj, "05_Armature")
    if body_obj:
        arm_mod = body_obj.modifiers.get("Armature") or body_obj.modifiers.new("Armature", 'ARMATURE')
        arm_mod.object = arm_obj
        arm_mod.use_deform_preserve_volume = True
    rigged_facial_objects = [
        eyelid_left, eyelid_right, lip_mesh,
        eye_left_cornea, eye_right_cornea,
        eye_left_iris, eye_right_iris,
    ]
    for el_obj in rigged_facial_objects:
        if el_obj and hasattr(el_obj.data, "vertices") and len(el_obj.data.vertices) > 0:
            vg_head = el_obj.vertex_groups.get("DEF-head") or el_obj.vertex_groups.new(name="DEF-head")
            vg_head.add(list(range(len(el_obj.data.vertices))), 1.0, 'REPLACE')
            el_arm = el_obj.modifiers.get("Armature") or el_obj.modifiers.new("Armature", 'ARMATURE')
            el_arm.object = arm_obj
            el_arm.use_deform_preserve_volume = True

# ------------------------------------------------------------------------------
# STEP 5: GENERATE HAIR CURVES GROOMING (6 STRATA & GN MODIFIER)
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 5: Constructing Hair Curves System (6 strata with Melanin shader)...")
{groom_script}

hair_layer_names = [
    "Hair_Hime_Bangs",
    "Hair_Hime_Sidelocks",
    "Hair_Scalp_Crown",
    "Hair_Back_Cascade",
    "Hair_Eyebrows",
    "Hair_Eyelashes",
]
mat_hair = bpy.data.materials.get("Mat_Human_Hair")
if mat_hair and mat_hair.use_nodes:
    nodes = mat_hair.node_tree.nodes
    links = mat_hair.node_tree.links
    nodes.clear()
    out_node = nodes.new(type="ShaderNodeOutputMaterial")
    out_node.location = (400, 0)
    p_bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    p_bsdf.location = (100, 0)
    if "Base Color" in p_bsdf.inputs:
        p_bsdf.inputs["Base Color"].default_value = (0.012, 0.011, 0.013, 1.0)
    if "Roughness" in p_bsdf.inputs:
        p_bsdf.inputs["Roughness"].default_value = 0.32
    if "Specular IOR Level" in p_bsdf.inputs:
        p_bsdf.inputs["Specular IOR Level"].default_value = 0.48
    elif "Specular" in p_bsdf.inputs:
        p_bsdf.inputs["Specular"].default_value = 0.48
    if "Coat Weight" in p_bsdf.inputs:
        p_bsdf.inputs["Coat Weight"].default_value = 0.08
    elif "Clearcoat" in p_bsdf.inputs:
        p_bsdf.inputs["Clearcoat"].default_value = 0.08
    if "Coat Roughness" in p_bsdf.inputs:
        p_bsdf.inputs["Coat Roughness"].default_value = 0.30
    elif "Clearcoat Roughness" in p_bsdf.inputs:
        p_bsdf.inputs["Clearcoat Roughness"].default_value = 0.30
    if "Anisotropic" in p_bsdf.inputs:
        p_bsdf.inputs["Anisotropic"].default_value = 0.70
    if "Anisotropic Rotation" in p_bsdf.inputs:
        p_bsdf.inputs["Anisotropic Rotation"].default_value = 0.25
    if "Sheen Weight" in p_bsdf.inputs:
        p_bsdf.inputs["Sheen Weight"].default_value = 0.35
    if "Sheen Roughness" in p_bsdf.inputs:
        p_bsdf.inputs["Sheen Roughness"].default_value = 0.40
    if "Transmission Weight" in p_bsdf.inputs:
        p_bsdf.inputs["Transmission Weight"].default_value = 0.0
    elif "Transmission" in p_bsdf.inputs:
        p_bsdf.inputs["Transmission"].default_value = 0.0
    if "Subsurface Weight" in p_bsdf.inputs:
        p_bsdf.inputs["Subsurface Weight"].default_value = 0.0
    elif "Subsurface" in p_bsdf.inputs:
        p_bsdf.inputs["Subsurface"].default_value = 0.0
    links.new(p_bsdf.outputs["BSDF"], out_node.inputs["Surface"])
    mat_hair.use_fake_user = True
for h_name in hair_layer_names:
    h_obj = bpy.data.objects.get(h_name)
    if h_obj:
        organize_object(h_obj, "02_Hair")
        if body_obj:
            h_obj.parent = body_obj
        if mat_hair and hasattr(h_obj.data, "materials"):
            h_obj.data.materials.clear()
            h_obj.data.materials.append(mat_hair)
        if arm_obj:
            if hasattr(h_obj.data, "vertices") and len(h_obj.data.vertices) > 0:
                vg_h = h_obj.vertex_groups.get("DEF-head") or h_obj.vertex_groups.new(name="DEF-head")
                vg_h.add(list(range(len(h_obj.data.vertices))), 1.0, 'REPLACE')
                h_arm = h_obj.modifiers.get("Armature") or h_obj.modifiers.new("Armature", 'ARMATURE')
                h_arm.object = arm_obj
                h_arm.use_deform_preserve_volume = True
            else:
                h_obj.parent = arm_obj
                h_obj.parent_type = 'BONE'
                h_obj.parent_bone = 'DEF-head'

# Hair clearance enforcement: zero penetration, >= +1.8mm clearance
if body_obj and body_obj.type == 'MESH':
    depsgraph = bpy.context.evaluated_depsgraph_get()
    bvh_wb = mathutils.bvhtree.BVHTree.FromObject(body_obj, depsgraph)
    for h_name in hair_layer_names:
        h_obj = bpy.data.objects.get(h_name)
        if h_obj and h_obj.type == 'MESH' and hasattr(h_obj.data, "vertices"):
            for v in h_obj.data.vertices:
                loc, norm, _, dist = bvh_wb.find_nearest(v.co)
                if loc is not None:
                    dot = (v.co - loc).dot(norm)
                    signed = dist if dot >= 0 else -dist
                    if signed < 0.0018:
                        v.co = loc + norm * 0.0020
            h_obj.data.update()

# ------------------------------------------------------------------------------
# STEP 6: GENERATE WARDROBE & MAGIC PROPS
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 6: Tailoring Wardrobe (Dress, Sash, Sandals) & Magic Props...")
{wardrobe_script}

# Move wardrobe meshes (dress, sash, and sandals) to 03_Wardrobe
wardrobe_mesh_names = [
    "Dress_Bodice",
    "Dress_WaistSash",
    "Dress_PleatedSkirt",
    "Mesh_Dress_Bodice",
    "Mesh_Dress_WaistSash",
    "Mesh_Dress_PleatedSkirt",
    "Mesh_Dress_RibbonTails",
    "Mesh_Sandal_Left",
    "Mesh_Sandal_Right",
    "Mesh_Sandal_L",
    "Mesh_Sandal_R",
    "Sandals_Flat",
]

mat_dress = bpy.data.materials.get("Mat_Dress_WhiteSilk")
mat_sash = bpy.data.materials.get("Mat_Sash_Satin") or bpy.data.materials.get("Mat_Dress_WaistBelt")
mat_sandal = bpy.data.materials.get("Mat_Sandal_White") or bpy.data.materials.get("Mat_Sandal_Leather")

for w_name in wardrobe_mesh_names:
    w_obj = bpy.data.objects.get(w_name)
    if w_obj:
        organize_object(w_obj, "03_Wardrobe")
        if w_obj.type == 'MESH':
            # Solidify modifier for 0.002m thickness
            sol_mod = w_obj.modifiers.get("Solidify") or w_obj.modifiers.new("Solidify", 'SOLIDIFY')
            sol_mod.thickness = {cfg_obj.wardrobe_thickness}
            sol_mod.use_rim = True
            # Bind wardrobe to armature
            if arm_obj:
                w_arm_mod = w_obj.modifiers.get("Armature") or w_obj.modifiers.new("Armature", 'ARMATURE')
                w_arm_mod.object = arm_obj
                w_arm_mod.use_deform_preserve_volume = True

        # Assign material
        if hasattr(w_obj.data, "materials"):
            w_obj.data.materials.clear()
            if "Sash" in w_name or "Ribbon" in w_name:
                if mat_sash: w_obj.data.materials.append(mat_sash)
            elif "Sandal" in w_name:
                if mat_sandal: w_obj.data.materials.append(mat_sandal)
            else:
                if mat_dress: w_obj.data.materials.append(mat_dress)

# Enforce zero mesh penetrations and minimum positive signed clearance (>= +5.0mm) for wardrobe parts against body
b_obj_for_wardrobe = bpy.data.objects.get("{cfg_obj.character_name}_Body")
if b_obj_for_wardrobe and b_obj_for_wardrobe.type == 'MESH':
    bm_body_wb = bmesh.new()
    bm_body_wb.from_mesh(b_obj_for_wardrobe.data)
    bm_body_wb.transform(b_obj_for_wardrobe.matrix_world)
    bvh_wb = mathutils.bvhtree.BVHTree.FromBMesh(bm_body_wb)
    bm_body_wb.free()

    # 1. Bodice, Sash, & Pleated Skirt clearance: resolve any chest/cleavage/waist/pelvic penetrations (>= +5.5mm)
    for part_name in ["Mesh_Dress_Bodice", "Mesh_Dress_WaistSash", "Mesh_Dress_PleatedSkirt", "Dress_Bodice", "Dress_WaistSash", "Dress_PleatedSkirt"]:
        b_part = bpy.data.objects.get(part_name)
        if b_part and b_part.type == 'MESH':
            mw_inv = b_part.matrix_world.inverted()
            for v in b_part.data.vertices:
                vw = b_part.matrix_world @ v.co
                loc, normal, _, dist = bvh_wb.find_nearest(vw)
                if loc is not None:
                    dot = (vw - loc).dot(normal)
                    signed = dist if dot >= 0 else -dist
                    if signed < 0.0055:
                        if "Skirt" in part_name:
                            push_x = vw.x * 1.03
                            push_y = vw.y * 1.03
                            push_z = max(vw.z, 0.830 * s_scale) if vw.z > 0.815 * s_scale else vw.z
                            cand = mathutils.Vector((push_x, push_y, push_z))
                            c_loc, c_norm, _, c_dist = bvh_wb.find_nearest(cand)
                            if c_loc is not None and (cand - c_loc).dot(c_norm) > 0 and c_dist >= 0.0045:
                                v.co = mw_inv @ cand
                            else:
                                v.co = mw_inv @ (loc + normal * 0.0065)
                        else:
                            new_vw = loc + normal * 0.0055
                            v.co = mw_inv @ new_vw
            b_part.data.update()

# Clean up any leftover sub-collections created by wardrobe.py (03_Dress, 04_Footwear, 05_Props_Magic)
for extra_col_name in ["03_Dress", "04_Footwear", "05_Props_Magic"]:
    extra_col = bpy.data.collections.get(extra_col_name)
    if extra_col:
        for extra_obj in list(extra_col.objects):
            if "Sandal" in extra_obj.name:
                organize_object(extra_obj, "03_Wardrobe")
            elif "Butterfly" in extra_obj.name or "String" in extra_obj.name:
                organize_object(extra_obj, "04_Props")
            elif "Dress" in extra_obj.name:
                organize_object(extra_obj, "03_Wardrobe")
        if extra_col.name in master_col.children:
            master_col.children.unlink(extra_col)
        if extra_col.name in bpy.context.scene.collection.children:
            bpy.context.scene.collection.children.unlink(extra_col)
        bpy.data.collections.remove(extra_col)

# Move props (Strings and Butterflies) to 04_Props
props_col = tier_cols["04_Props"]
strings_obj = bpy.data.objects.get("Prop_Marionette_Strings")
mat_red = bpy.data.materials.get("Mat_Marionette_RedString")

finger_def_bone_keys = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]

if strings_obj:
    organize_object(strings_obj, "04_Props")
    if mat_red and hasattr(strings_obj.data, "materials"):
        strings_obj.data.materials.clear()
        strings_obj.data.materials.append(mat_red)
    # Assign vertex group weights to the 10 finger DEF bones
    verts_per_cord = 14
    for cord_i in range(min(10, len(finger_def_bone_keys))):
        b_name = finger_def_bone_keys[cord_i]
        vg = strings_obj.vertex_groups.get(b_name) or strings_obj.vertex_groups.new(name=b_name)
        start_v = cord_i * verts_per_cord
        end_v = min(len(strings_obj.data.vertices), (cord_i + 1) * verts_per_cord)
        for v_idx in range(start_v, end_v):
            step = (v_idx - start_v) // 2
            t = step / 6.0
            weight = max(0.0, 1.0 - 0.7 * t)
            vg.add([v_idx], weight, 'REPLACE')
    if arm_obj:
        s_arm_mod = strings_obj.modifiers.get("Armature") or strings_obj.modifiers.new("Armature", 'ARMATURE')
        s_arm_mod.object = arm_obj
        s_arm_mod.use_deform_preserve_volume = True

        # Finger bone tail snapping: snap origin vertices (v0, v1) of each cord directly to the respective finger DEF bone tail
        inv_world = strings_obj.matrix_world.inverted()
        for cord_i, b_name in enumerate(finger_def_bone_keys):
            bone = arm_obj.data.bones.get(b_name)
            if bone:
                tail_world = arm_obj.matrix_world @ bone.tail_local
                local_tail = inv_world @ tail_world
                v0_idx = cord_i * verts_per_cord
                v1_idx = v0_idx + 1
                half_w = 0.0004 * s
                if v0_idx < len(strings_obj.data.vertices):
                    strings_obj.data.vertices[v0_idx].co = (local_tail[0] - half_w, local_tail[1], local_tail[2])
                if v1_idx < len(strings_obj.data.vertices):
                    strings_obj.data.vertices[v1_idx].co = (local_tail[0] + half_w, local_tail[1], local_tail[2])
        strings_obj.data.update()

for i in range({cfg_obj.string_count}):
    s_obj = bpy.data.objects.get(f"Prop_String_{{i:02d}}")
    if s_obj:
        organize_object(s_obj, "04_Props")
        if mat_red and hasattr(s_obj.data, "materials"):
            s_obj.data.materials.clear()
            s_obj.data.materials.append(mat_red)
        if arm_obj and i < len(finger_def_bone_keys):
            b_name = finger_def_bone_keys[i]
            bone = arm_obj.data.bones.get(b_name)
            if bone and len(s_obj.data.vertices) >= 2:
                tail_world = arm_obj.matrix_world @ bone.tail_local
                local_tail = s_obj.matrix_world.inverted() @ tail_world
                half_w = 0.0004 * s
                s_obj.data.vertices[0].co = (local_tail[0] - half_w, local_tail[1], local_tail[2])
                s_obj.data.vertices[1].co = (local_tail[0] + half_w, local_tail[1], local_tail[2])
                s_obj.data.update()


flutter_positions = [
    (0.37511 * s, -0.22998 * s, 0.88000 * s),
    (0.45234 * s, -0.12763 * s, 1.00226 * s),
    (0.50000 * s, 0.00000 * s, 1.07257 * s),
    (0.51009 * s, 0.14392 * s, 1.19534 * s),
    (0.47741 * s, 0.29270 * s, 1.31709 * s),
    (-0.40527 * s, -0.17134 * s, 0.88000 * s),
    (-0.46633 * s, -0.05860 * s, 1.00226 * s),
    (-0.49439 * s, 0.07472 * s, 1.07257 * s),
    (-0.48285 * s, 0.21853 * s, 1.19534 * s),
    (-0.42831 * s, 0.36076 * s, 1.31709 * s),
]

mat_bf = bpy.data.materials.get("Mat_Magic_Butterfly")
for i in range({cfg_obj.butterfly_count}):
    bf_obj = bpy.data.objects.get(f"Prop_Butterfly_{{i:02d}}")
    if bf_obj:
        pos = flutter_positions[i % len(flutter_positions)]
        bf_obj.location = pos
        scale_factor = 1.0 + 0.10 * math.sin(i * 1.7)
        bf_obj.scale = (scale_factor, scale_factor, scale_factor)
        bf_obj.rotation_euler = (
            math.radians(10.0 + (i % 3) * 12.0),
            math.radians((i % 2) * 20.0 - 10.0),
            math.radians((i * 36.0) % 360.0),
        )
        organize_object(bf_obj, "04_Props")
        if mat_bf and hasattr(bf_obj.data, "materials"):
            bf_obj.data.materials.clear()
            bf_obj.data.materials.append(mat_bf)
        if arm_obj:
            b_name = finger_def_bone_keys[i % len(finger_def_bone_keys)]
            vg = bf_obj.vertex_groups.get(b_name) or bf_obj.vertex_groups.new(name=b_name)
            vg.add(list(range(len(bf_obj.data.vertices))), 1.0, 'REPLACE')
            bf_arm_mod = bf_obj.modifiers.get("Armature") or bf_obj.modifiers.new("Armature", 'ARMATURE')
            bf_arm_mod.object = arm_obj

# ------------------------------------------------------------------------------
# STEP 7: STUDIO 3-POINT LIGHTING & 85MM PORTRAIT / FULL-BODY CAMERAS
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 7: Setting up 3-Point Studio Lighting and Calibrated Cameras...")
lights_col = tier_cols["06_Lights_Camera"]

# Empty target at Yu Nian An's chest/head center
target_light = bpy.data.objects.get("Target_Lighting_Focus")
if not target_light:
    target_light = bpy.data.objects.new("Target_Lighting_Focus", None)
    target_light.empty_display_type = 'PLAIN_AXES'
    target_light.empty_display_size = 0.1 * s
target_light.location = (0.0, 0.0, 1.25 * s)
organize_object(target_light, "06_Lights_Camera")

def aim_light_at_target(light_obj, target_obj):
    if not light_obj or not target_obj:
        return
    tt_con = light_obj.constraints.get("Track_To_Character") or light_obj.constraints.new(type='TRACK_TO')
    tt_con.name = "Track_To_Character"
    tt_con.target = target_obj
    tt_con.track_axis = 'TRACK_NEGATIVE_Z'
    tt_con.up_axis = 'UP_Y'

def create_light(name, light_type, location, color, energy, size=1.0):
    lt_data = bpy.data.lights.get(name) or bpy.data.lights.new(name=name, type=light_type)
    lt_data.color = color
    lt_data.energy = energy
    if light_type == 'AREA':
        lt_data.size = size
    lt_obj = bpy.data.objects.get(name) or bpy.data.objects.new(name=name, object_data=lt_data)
    lt_obj.location = location
    organize_object(lt_obj, "06_Lights_Camera")
    aim_light_at_target(lt_obj, target_light)
    return lt_obj

def kelvin_to_rgb(kelvin):
    temp = kelvin / 100.0
    if temp <= 66:
        red = 1.0
        green = max(0.0, min(1.0, 0.39008157876 * math.log(temp) - 0.63184144378))
    else:
        red = max(0.0, min(1.0, 1.29293618606 * ((temp - 60) ** -0.1332047592)))
        green = max(0.0, min(1.0, 1.12989086089 * ((temp - 60) ** -0.0755148492)))
    if temp >= 66:
        blue = 1.0
    elif temp <= 19:
        blue = 0.0
    else:
        blue = max(0.0, min(1.0, 0.54320678911 * math.log(temp - 10) - 1.19625408914))
    return (red, green, blue)

# Key Light: 45° front-right, warm 5500K, 500W aimed at chest/head center
key_col = kelvin_to_rgb({cfg_obj.key_light_temperature})
key_obj = create_light("Light_Key_Softbox", 'AREA', (1.8 * s, -2.0 * s, 2.2 * s), key_col, {cfg_obj.key_light_energy}, size=0.8 * s)

# Fill Light: 45° front-left, cool 6500K, 250W aimed at chest/head center
fill_col = kelvin_to_rgb({cfg_obj.fill_light_temperature})
fill_obj = create_light("Light_Fill_Softbox", 'AREA', (-1.8 * s, -2.0 * s, 1.8 * s), fill_col, {cfg_obj.fill_light_energy}, size=1.0 * s)

# Rim / Hair Light: back-top, 4500K, 450W aimed at chest/head center for angel-ring highlight (softened size 1.0m)
rim_col = kelvin_to_rgb({cfg_obj.rim_light_temperature})
rim_obj = create_light("Light_Rim_HairLight", 'AREA', (0.0, 2.2 * s, 2.5 * s), rim_col, {cfg_obj.rim_light_energy}, size=1.0 * s)

# Portrait Camera: 85mm portrait lens framed on bust/portrait centered at Z=1.55m (distance ~2.0m)
cam_data = bpy.data.cameras.get("Camera_Portrait_85mm") or bpy.data.cameras.new(name="Camera_Portrait_85mm")
cam_data.lens = {cfg_obj.camera_lens}
cam_data.sensor_width = 36.0
cam_data.sensor_height = 24.0

cam_obj = bpy.data.objects.get("Camera_Portrait_85mm") or bpy.data.objects.new(name="Camera_Portrait_85mm", object_data=cam_data)
cam_obj.location = (0.0, -{cfg_obj.camera_distance} * s, {cfg_obj.camera_target_z} * s)
cam_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
organize_object(cam_obj, "06_Lights_Camera")
bpy.context.scene.camera = cam_obj

# Full-Body Camera: Framed at Yu Nian An's full 1.65m height at distance 5.5m without cropping
cam_full_data = bpy.data.cameras.get("Camera_FullBody") or bpy.data.cameras.new(name="Camera_FullBody")
cam_full_data.lens = {cfg_obj.camera_fullbody_lens}
cam_full_data.sensor_width = 36.0
cam_full_data.sensor_height = 24.0
cam_full_obj = bpy.data.objects.get("Camera_FullBody") or bpy.data.objects.new(name="Camera_FullBody", object_data=cam_full_data)
cam_full_obj.location = (0.0, -{cfg_obj.camera_fullbody_distance} * s, {cfg_obj.camera_fullbody_target_z} * s)
cam_full_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
organize_object(cam_full_obj, "06_Lights_Camera")

# 4 Turntable View Cameras for Full-Body Inspection (distance 5.5m, 50mm lens)
turnaround_angles = [
    ("Camera_Front", (0.0, -{cfg_obj.camera_fullbody_distance} * s, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, 0.0)),
    ("Camera_ThreeQuarter", (3.889 * s, -3.889 * s, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, math.radians(45.0))),
    ("Camera_Profile", ({cfg_obj.camera_fullbody_distance} * s, 0.0, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, math.radians(90.0))),
    ("Camera_Back", (0.0, {cfg_obj.camera_fullbody_distance} * s, {cfg_obj.camera_fullbody_target_z} * s), (math.radians(90.0), 0.0, math.radians(180.0))),
]
for c_name, c_loc, c_rot in turnaround_angles:
    c_dat = bpy.data.cameras.get(c_name) or bpy.data.cameras.new(name=c_name)
    c_dat.lens = {cfg_obj.camera_fullbody_lens}
    c_dat.sensor_width = 36.0
    c_dat.sensor_height = 24.0
    c_o = bpy.data.objects.get(c_name) or bpy.data.objects.new(name=c_name, object_data=c_dat)
    c_o.location = c_loc
    c_o.rotation_euler = c_rot
    organize_object(c_o, "06_Lights_Camera")

# ------------------------------------------------------------------------------
# STEP 8: CYCLES RENDER ENGINE & AgX COLOR MANAGEMENT
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 8: Configuring Cycles Engine, 128 Samples, and AgX Color Management...")
scene = bpy.context.scene
scene.render.engine = "{cfg_obj.render_engine}"
if hasattr(scene, "cycles"):
    scene.cycles.samples = {cfg_obj.cycles_samples}
    if hasattr(scene.cycles, "preview_samples"):
        scene.cycles.preview_samples = 32
    if hasattr(scene.cycles, "use_denoising"):
        scene.cycles.use_denoising = True

if hasattr(scene, "view_settings") and hasattr(scene.view_settings, "view_transform"):
    try:
        scene.view_settings.view_transform = "{cfg_obj.color_management}"
    except Exception as e_agx:
        print(f"[MorphoMesh] AgX view transform notice: {{e_agx}}")

# ------------------------------------------------------------------------------
# STEP 8.5: UV COORDINATE GENERATION & TEXTURE ATLAS QUADRANT MAPPING
# ------------------------------------------------------------------------------
print("[MorphoMesh] Step 8.5: Generating UV Coordinates across all character meshes...")
{_get_uv_unwrapping_script_snippet()}
assign_texture_atlas_uvs(s_scale={cfg_obj.height} / 1.65)

# ------------------------------------------------------------------------------
# STEP 9: AUTOMATED MASTER .BLEND SAVE
# ------------------------------------------------------------------------------
output_blend = "{effective_output_path}"
out_dir = os.path.dirname(output_blend)
if out_dir:
    os.makedirs(out_dir, exist_ok=True)

try:
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    print(f"[MorphoMesh] Master character scene saved successfully to: {{output_blend}}")
except Exception as e_save:
    print(f"[MorphoMesh] Save error: {{e_save}}")

print("[MorphoMesh] Yu Nian An Master Asset Assembly COMPLETE.")
'''
    return master_script


__all__ = [
    "ROOT_COLLECTION_NAME",
    "TIER_COLLECTION_NAMES",
    "SEVEN_TIER_COLLECTION_HIERARCHY",
    "ALL_SEVEN_COLLECTIONS",
    "FINGER_LANDMARK_KEYS",
    "FINGER_DEF_BONE_KEYS",
    "MATERIAL_NAMES",
    "STANDARD_HUMAN_MATERIALS",
    "STANDARDIZED_HUMAN_VERTEX_GROUPS",
    "ALL_163_DEF_BONES",
    "BODY_DEF_BONES",
    "FACIAL_DEF_BONES",
    "ARKIT_52_BLENDSHAPES",
    "MasterAssemblyConfig",
    "_get_uv_unwrapping_script_snippet",
    "assign_texture_atlas_uvs",
    "get_master_assembly_script",
    "HAS_BPY",
    "_MockVector",
    "_MockEuler",
    "_MockMatrix",
    "_MockMathutils",
    "Vector",
    "Euler",
    "Matrix",
    "mathutils"
]
