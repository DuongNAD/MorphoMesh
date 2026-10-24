"""
anime_pipeline/rigging package
Milestone 2: Anime Auto-Rigging, Twist/Spring Bones & Dual Quaternion Skinning.

Exposes:
- ArmatureBuilder: Builds standard 78-bone canonical humanoid armature.
- SkinningDQS: Dual Quaternion Skinning & anti-pinch harmonic cosine weights.
- SecondaryBonesRig: 12-radial skirt rig & 5-bone twintail spring chains.
- build_and_export_rigged_character: Automated master assembly & export pipeline.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import bpy
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    HAS_BPY = False

from .armature_builder import (
    ALL_10_HAIR_BONES,
    ALL_30_FINGER_BONES,
    ALL_REQUIRED_ARMATURE_BONES,
    FINGER_NAMES,
    MMD_BONE_MAP,
    PHALANGES,
    RIGIFY_DEF_BONE_MAP,
    SKIRT_BONES,
    TWIST_BONES,
    UNIVERSAL_LIMB_BONES,
    UNIVERSAL_SPINE_BONES,
    VRM_1_0_BONE_MAP,
    ArmatureBuilder,
    ArmatureSpec,
    BoneSpec,
    build_anime_armature,
)
from .secondary_bones import (
    SKIRT_BONE_COUNT,
    SKIRT_BONE_NAMES,
    SKIRT_PITCH_MAX_DEG,
    SKIRT_PITCH_MIN_DEG,
    SPRING_DAMPING,
    SPRING_MASS,
    SPRING_REST_POS,
    SPRING_STIFFNESS,
    TWINTAIL_SEGMENT_COUNT,
    SecondaryBonesRig,
    add_skirt_radial_rig,
    add_twintail_secondary_chains,
    apply_hair_skin_weights,
    apply_skirt_skin_weights,
    clamp_skirt_pitch,
    evaluate_cubic_bezier_3d,
)
from .skinning_dqs import (
    MODULAR_ISOLATION_RULES,
    TWIST_BONE_CONFIGS,
    SkinningDQS,
    VertexWeightTable,
    apply_dual_quaternion_skinning,
    apply_vertex_weights_to_blender_mesh,
    calculate_submesh_skin_weights,
    configure_all_submeshes_dqs,
    harmonic_cosine_falloff,
    point_to_segment_distance_and_proj,
    setup_twist_bone_constraints,
    verify_skin_weights_normalization,
)

__all__ = [
    # Classes
    "ArmatureBuilder",
    "ArmatureSpec",
    "BoneSpec",
    "SecondaryBonesRig",
    "SkinningDQS",
    "VertexWeightTable",
    # Functions
    "add_skirt_radial_rig",
    "add_twintail_secondary_chains",
    "apply_dual_quaternion_skinning",
    "apply_hair_skin_weights",
    "apply_skirt_skin_weights",
    "apply_vertex_weights_to_blender_mesh",
    "build_and_export_rigged_character",
    "build_anime_armature",
    "calculate_submesh_skin_weights",
    "clamp_skirt_pitch",
    "configure_all_submeshes_dqs",
    "evaluate_cubic_bezier_3d",
    "harmonic_cosine_falloff",
    "point_to_segment_distance_and_proj",
    "setup_twist_bone_constraints",
    "verify_skin_weights_normalization",
    # Constants & Mappings
    "ALL_10_HAIR_BONES",
    "ALL_30_FINGER_BONES",
    "ALL_REQUIRED_ARMATURE_BONES",
    "FINGER_NAMES",
    "MMD_BONE_MAP",
    "MODULAR_ISOLATION_RULES",
    "PHALANGES",
    "RIGIFY_DEF_BONE_MAP",
    "SKIRT_BONES",
    "SKIRT_BONE_COUNT",
    "SKIRT_BONE_NAMES",
    "SKIRT_PITCH_MAX_DEG",
    "SKIRT_PITCH_MIN_DEG",
    "SPRING_DAMPING",
    "SPRING_MASS",
    "SPRING_REST_POS",
    "SPRING_STIFFNESS",
    "TWINTAIL_SEGMENT_COUNT",
    "TWIST_BONES",
    "TWIST_BONE_CONFIGS",
    "UNIVERSAL_LIMB_BONES",
    "UNIVERSAL_SPINE_BONES",
    "VRM_1_0_BONE_MAP",
]


def build_and_export_rigged_character(
    clean_blend_path: Optional[Union[str, Path]] = None,
    output_blend_path: Optional[Union[str, Path]] = None,
    output_glb_path: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Master automated assembly and export pipeline for Milestone 2:
    1. Loads clean mesh scene (output/anime_mesh_clean.blend).
    2. Constructs Anime_Armature with all 78 canonical bones.
    3. Configures twist bones (UpperArm_Twist, ForeArm_Twist with local Y 0.5 copy-rotation).
    4. Configures 12-radial skirt bones (Skirt_01..12 with [-15°, +65°] pitch limits).
    5. Configures 10 twintail secondary bones (Hair_L/R_01..05 with spring dynamics properties).
    6. Enables Dual Quaternion Skinning (use_deform_preserve_volume = True) on all 7 submeshes.
    7. Applies smooth normalized skin weights with 0% thigh weight bleeding on Anime_Skirt.
    8. Exports output/anime_rigged.blend and output/anime_rigged.glb.
    """
    if not HAS_BPY:
        raise RuntimeError("Blender Python (bpy) is required to execute build_and_export_rigged_character.")

    proj_root = Path(__file__).resolve().parent.parent.parent
    if clean_blend_path is None:
        clean_blend_path = proj_root / "output" / "anime_mesh_clean.blend"
    clean_blend_path = Path(clean_blend_path)

    if output_blend_path is None:
        output_blend_path = proj_root / "output" / "anime_rigged.blend"
    output_blend_path = Path(output_blend_path)

    if output_glb_path is None:
        output_glb_path = proj_root / "output" / "anime_rigged.glb"
    output_glb_path = Path(output_glb_path)

    # 1. Load clean mesh scene
    if not clean_blend_path.exists():
        raise FileNotFoundError(f"Clean mesh file not found: {clean_blend_path}")

    bpy.ops.wm.open_mainfile(filepath=str(clean_blend_path))

    # Identify modular sub-mesh objects
    expected_submeshes = [
        "Anime_Head", "Anime_Torso", "Anime_Arms", "Anime_Legs",
        "Anime_Hair", "Anime_Skirt", "Anime_Shoes"
    ]
    submesh_objs: Dict[str, Any] = {}
    for name in expected_submeshes:
        obj = bpy.data.objects.get(name)
        if obj and obj.type == 'MESH':
            submesh_objs[name] = obj

    if not submesh_objs:
        raise RuntimeError("No modular sub-mesh objects found in input scene.")

    # 2. Build canonical Armature
    builder = ArmatureBuilder(submeshes=submesh_objs)
    arm_obj = builder.build_in_blender()

    # 3. Setup Secondary Rig (Skirt radial bones & Twintail chains)
    sec_rig = SecondaryBonesRig(scale=builder.scale_factor)
    sec_results = sec_rig.setup_secondary_rig_and_skinning(
        armature_obj=arm_obj,
        submesh_objs=submesh_objs,
        landmarks=builder.resolved_landmarks,
    )

    # 4. Setup DQS & Skin Remaining Submeshes
    dqs = SkinningDQS(armature_obj=arm_obj)
    # Configure twist bone constraints
    twist_res = dqs.setup_twist_bone_constraints(arm_obj)
    # Synchronize sub-mesh object transforms with Armature coordinate system
    inv_world = arm_obj.matrix_world.inverted()
    for obj in submesh_objs.values():
        obj.rotation_euler = (0.0, 0.0, 0.0)
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
        obj.parent = arm_obj
        obj.matrix_parent_inverse = inv_world

    # Attach DQS modifier to all submeshes
    dqs_count = dqs.configure_all_submeshes_dqs(list(submesh_objs.values()), arm_obj)

    # Calculate and assign skin weights for non-skirt/hair submeshes
    # (Skirt and Hair were skinned with custom radial/bezier solvers in sec_rig)
    for name, obj in submesh_objs.items():
        if name in ("Anime_Skirt", "Anime_Hair"):
            continue  # Already custom-skinned with strict invariants
        verts = [(v.co.x, v.co.y, v.co.z) for v in obj.data.vertices]
        vgroups = dqs.calculate_skin_weights(name, verts, builder.resolved_landmarks)
        apply_vertex_weights_to_blender_mesh(obj, vgroups, clear_existing=True)

    # 5. Comprehensive Verification of All Sub-meshes
    audit_reports: Dict[str, Any] = {}
    for name, obj in submesh_objs.items():
        num_v = len(obj.data.vertices)
        vgroups_data: Dict[str, List[Tuple[int, float]]] = {}
        for vg in obj.vertex_groups:
            vgroups_data[vg.name] = []
        for v in obj.data.vertices:
            for g in v.groups:
                vg_name = obj.vertex_groups[g.group].name
                vgroups_data[vg_name].append((v.index, g.weight))

        valid, msg = verify_skin_weights_normalization(name, vgroups_data, num_v)
        audit_reports[name] = {"valid": valid, "message": msg, "num_vertices": num_v}
        if not valid:
            raise RuntimeError(f"Skinning validation failed for {name}: {msg}")

    # Explicit assertion: verify Anime_Skirt has 0% thigh weights
    skirt_obj = submesh_objs.get("Anime_Skirt")
    if skirt_obj:
        for vg in skirt_obj.vertex_groups:
            if "Thigh" in vg.name:
                raise RuntimeError(f"CRITICAL INVARIANT VIOLATION: {vg.name} present on Anime_Skirt")

    # 6. Save Rigged Blend file
    output_blend_path.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output_blend_path))

    # 7. Export GLB with Armature and Skins
    output_glb_path.parent.mkdir(parents=True, exist_ok=True)
    # Select all meshes and armature for export
    bpy.ops.object.select_all(action='DESELECT')
    arm_obj.select_set(True)
    for obj in submesh_objs.values():
        obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj

    bpy.ops.export_scene.gltf(
        filepath=str(output_glb_path),
        export_format='GLB',
        use_selection=True,
        export_skins=True,
        export_yup=True,
        export_apply=False,
        export_leaf_bone=False,
        export_rest_position_armature=True,
        export_reset_pose_bones=True,
    )

    return {
        "status": "success",
        "armature_name": arm_obj.name,
        "total_bones": len(arm_obj.data.bones),
        "submeshes_rigged": list(submesh_objs.keys()),
        "output_blend": str(output_blend_path),
        "output_glb": str(output_glb_path),
        "secondary_results": sec_results,
        "twist_results": twist_res,
        "dqs_modifiers_count": dqs_count,
        "audit_reports": audit_reports,
    }
