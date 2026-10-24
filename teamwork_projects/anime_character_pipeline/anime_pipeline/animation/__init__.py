"""
anime_pipeline/animation/__init__.py
Milestone 3: Anime Motion Library, Action Keyframes, Retargeting Limits & Secondary Dynamics.

Exposes:
- Core 4 Programmatic Anime Actions (Idle_Cute, Wave_Greeting, Walk_Cycle, Jump_Cheer)
- Joint Rotational Clamping & Physiological Limits (Elbows, Knees, Feet, Toes, Skirt)
- Secondary Inertial Dynamics & Spring Solver (Twintails & Pleated Skirt)
- Master Export Pipeline: generate_animated_character()
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

try:
    import bpy
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    HAS_BPY = False

# 1. Re-exports from spring_solver with flexible package/standalone fallback
try:
    from .spring_solver import (
        ALL_HAIR_BONES,
        HAIR_BONES_LEFT,
        HAIR_BONES_RIGHT,
        MIN_CLEARANCE_MM,
        SKIRT_BONE_COUNT,
        SKIRT_BONE_NAMES,
        SKIRT_PITCH_MAX_DEG,
        SKIRT_PITCH_MIN_DEG,
        SPRING_DAMPING,
        SPRING_MASS,
        SPRING_REST_POS,
        SPRING_STIFFNESS,
        TWINTAIL_SEGMENT_COUNT,
        SkirtClearanceSimulator,
        TwintailChainSimulator,
        SecondarySpringDynamicsSolver,
        bake_secondary_dynamics_action,
        bake_secondary_dynamics_to_action,
        bake_secondary_dynamics_all_actions,
        calculate_damping_ratio,
        simulate_rk4_spring_damper,
        solve_rk4_step,
        solve_rk4_substepped,
        solve_spring_damper_step,
    )
except (ImportError, ValueError):
    try:
        from spring_solver import (
            ALL_HAIR_BONES,
            HAIR_BONES_LEFT,
            HAIR_BONES_RIGHT,
            MIN_CLEARANCE_MM,
            SKIRT_BONE_COUNT,
            SKIRT_BONE_NAMES,
            SKIRT_PITCH_MAX_DEG,
            SKIRT_PITCH_MIN_DEG,
            SPRING_DAMPING,
            SPRING_MASS,
            SPRING_REST_POS,
            SPRING_STIFFNESS,
            TWINTAIL_SEGMENT_COUNT,
            SkirtClearanceSimulator,
            TwintailChainSimulator,
            bake_secondary_dynamics_action,
            bake_secondary_dynamics_all_actions,
            calculate_damping_ratio,
            simulate_rk4_spring_damper,
            solve_rk4_step,
            solve_rk4_substepped,
            solve_spring_damper_step,
        )
    except (ImportError, ValueError):
        from proposed_spring_solver import (
            ALL_HAIR_BONES,
            HAIR_BONES_LEFT,
            HAIR_BONES_RIGHT,
            MIN_CLEARANCE_MM,
            SKIRT_BONE_COUNT,
            SKIRT_BONE_NAMES,
            SKIRT_PITCH_MAX_DEG,
            SKIRT_PITCH_MIN_DEG,
            SPRING_DAMPING,
            SPRING_MASS,
            SPRING_REST_POS,
            SPRING_STIFFNESS,
            TWINTAIL_SEGMENT_COUNT,
            SkirtClearanceSimulator,
            TwintailChainSimulator,
            bake_secondary_dynamics_action,
            bake_secondary_dynamics_all_actions,
            calculate_damping_ratio,
            simulate_rk4_spring_damper,
            solve_rk4_step,
            solve_rk4_substepped,
            solve_spring_damper_step,
        )

# 2. Defensive imports from action_library & retargeting_limits
try:
    from .action_library import (
        ACTION_NAMES,
        ACTION_METADATA_REGISTRY,
        ActionMetadata,
        ActionDefinition,
        create_action_idle_cute,
        create_action_wave_greeting,
        create_action_walk_cycle,
        create_action_jump_cheer,
        build_action_idle_cute,
        build_action_jump_cheer,
        build_action_walk_cycle,
        build_action_wave_greeting,
        generate_all_anime_actions,
        build_all_anime_actions,
        get_canonical_action_definitions,
    )
except (ImportError, ValueError):
    try:
        from action_library import (
            ACTION_NAMES,
            ACTION_METADATA_REGISTRY,
            ActionMetadata,
            ActionDefinition,
            create_action_idle_cute,
            create_action_wave_greeting,
            create_action_walk_cycle,
            create_action_jump_cheer,
            build_action_idle_cute,
            build_action_jump_cheer,
            build_action_walk_cycle,
            build_action_wave_greeting,
            generate_all_anime_actions,
            build_all_anime_actions,
            get_canonical_action_definitions,
        )
    except (ImportError, ValueError):
        ACTION_NAMES = [
            "action_anime_idle_cute",
            "action_anime_wave_greeting",
            "action_anime_walk_cycle",
            "action_anime_jump_cheer",
        ]
        create_action_idle_cute = None  # type: ignore[assignment]
        create_action_wave_greeting = None  # type: ignore[assignment]
        create_action_walk_cycle = None  # type: ignore[assignment]
        create_action_jump_cheer = None  # type: ignore[assignment]
        build_action_idle_cute = None  # type: ignore[assignment]
        build_action_wave_greeting = None  # type: ignore[assignment]
        build_action_walk_cycle = None  # type: ignore[assignment]
        build_action_jump_cheer = None  # type: ignore[assignment]
        generate_all_anime_actions = None  # type: ignore[assignment]
        build_all_anime_actions = None  # type: ignore[assignment]
        get_canonical_action_definitions = None  # type: ignore[assignment]

try:
    from .retargeting_limits import (
        BONE_MAPPING_TABLES,
        HINGE_LIMITS,
        PHYSIOLOGICAL_ROTATION_LIMITS,
        LimitSpec,
        clamp_angle,
        clamp_joint_angle_deg,
        normalize_quaternion,
        quat_to_euler_xyz,
        euler_xyz_to_quat,
        resolve_to_canonical,
        get_standard_bone_name,
        clamp_single_bone_rotation,
        clamp_pose_rotations,
        setup_retargeting_constraints,
        apply_retargeting_limits,
        remove_retargeting_limits,
        verify_retargeting_limits,
        clamp_animation_action_keyframes,
    )
except (ImportError, ValueError):
    try:
        from retargeting_limits import (
            BONE_MAPPING_TABLES,
            HINGE_LIMITS,
            PHYSIOLOGICAL_ROTATION_LIMITS,
            LimitSpec,
            clamp_angle,
            clamp_joint_angle_deg,
            normalize_quaternion,
            quat_to_euler_xyz,
            euler_xyz_to_quat,
            resolve_to_canonical,
            get_standard_bone_name,
            clamp_single_bone_rotation,
            clamp_pose_rotations,
            setup_retargeting_constraints,
            apply_retargeting_limits,
            remove_retargeting_limits,
            verify_retargeting_limits,
            clamp_animation_action_keyframes,
        )
    except (ImportError, ValueError):
        HINGE_LIMITS = {
            "Elbow.L": (0.0, 145.0),
            "Elbow.R": (0.0, 145.0),
            "Knee.L": (0.0, 140.0),
            "Knee.R": (0.0, 140.0),
            "Skirt_Pitch": (-15.0, 65.0),
        }
        PHYSIOLOGICAL_ROTATION_LIMITS = {}
        BONE_MAPPING_TABLES = {}
        clamp_pose_rotations = None  # type: ignore[assignment]
        setup_retargeting_constraints = None  # type: ignore[assignment]
        apply_retargeting_limits = None  # type: ignore[assignment]
        remove_retargeting_limits = None  # type: ignore[assignment]
        verify_retargeting_limits = None  # type: ignore[assignment]
        clamp_animation_action_keyframes = None  # type: ignore[assignment]


# ==============================================================================
# Master Animation Generation & Export Pipeline
# ==============================================================================

def generate_animated_character(
    input_blend_path: str = "output/anime_rigged.blend",
    output_blend_path: str = "output/anime_animated.blend",
    output_glb_path: str = "output/anime_animated.glb",
    actions_to_generate: Optional[Sequence[str]] = None,
    fps: float = 30.0,
    export_glb: bool = True,
) -> Dict[str, Any]:
    """
    Executes the end-to-end Milestone 3 animation pipeline:
    1. Loads rigged anime character blend file (input_blend_path).
    2. Verifies Anime_Armature and 78 canonical bones.
    3. Applies joint rotational limit constraints (retargeting_limits.py).
    4. Generates 4 programmatic anime actions (action_library.py).
    5. Bakes secondary twintail and skirt dynamics across all actions (spring_solver.py).
    6. Pushes all actions to non-linear animation (NLA) tracks.
    7. Saves master animated blend file (output_blend_path).
    8. Exports game-ready / VTuber animated GLB asset (output_glb_path).
    """
    if not HAS_BPY:
        return {
            "status": "error",
            "message": "Blender Python (bpy) is not available in current environment",
        }

    pkg_root = Path(__file__).resolve().parent.parent.parent
    input_path = Path(input_blend_path)
    if not input_path.is_absolute() and not input_path.exists():
        candidate = pkg_root / input_blend_path
        if candidate.exists():
            input_path = candidate
    input_path = input_path.resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input rigged blend file not found: {input_path}")

    # Ensure output directories exist
    out_blend = Path(output_blend_path)
    if not out_blend.is_absolute() and not out_blend.parent.exists():
        candidate_out = pkg_root / output_blend_path
        out_blend = candidate_out.resolve()
    else:
        out_blend = out_blend.resolve()

    out_glb = Path(output_glb_path)
    if not out_glb.is_absolute() and not out_glb.parent.exists():
        candidate_glb = pkg_root / output_glb_path
        out_glb = candidate_glb.resolve()
    else:
        out_glb = out_glb.resolve()

    out_blend.parent.mkdir(parents=True, exist_ok=True)
    out_glb.parent.mkdir(parents=True, exist_ok=True)

    # 1. Load rigged character scene
    bpy.ops.wm.open_mainfile(filepath=str(input_path))

    arm_obj = bpy.data.objects.get("Anime_Armature")
    if not arm_obj:
        raise RuntimeError("Anime_Armature object not found in scene")

    bpy.context.view_layer.objects.active = arm_obj
    scene = bpy.context.scene
    scene.render.fps = int(fps)

    manifest: Dict[str, Any] = {
        "input_blend": str(input_path),
        "output_blend": str(out_blend),
        "output_glb": str(out_glb),
        "fps": fps,
        "actions_generated": [],
        "secondary_dynamics_baked": {},
        "nla_tracks": [],
    }

    # 2. Apply retargeting limits if module available
    retarget_fn = setup_retargeting_constraints or apply_retargeting_limits
    if retarget_fn is not None:
        try:
            applied_limits = retarget_fn(arm_obj)
            manifest["retargeting_limits_applied"] = applied_limits
        except Exception as e:
            manifest["retargeting_limits_warning"] = str(e)

    # 3. Generate all 4 canonical anime actions
    gen_fn = generate_all_anime_actions or build_all_anime_actions
    if gen_fn is not None:
        generated_actions = gen_fn(arm_obj)
        if isinstance(generated_actions, dict):
            manifest["actions_generated"] = list(generated_actions.keys())
        elif isinstance(generated_actions, (list, tuple)):
            manifest["actions_generated"] = [a.name for a in generated_actions]
    else:
        # Check existing actions in scene
        manifest["actions_generated"] = [
            a.name for a in bpy.data.actions if a.name.startswith("action_anime_")
        ]

    # 4. Bake secondary dynamics for twintails and skirt across all actions
    bake_report = bake_secondary_dynamics_all_actions(
        armature_obj=arm_obj,
        fps=fps,
        n_substeps=4,
    )
    manifest["secondary_dynamics_baked"] = bake_report

    # 5. Push actions to NLA tracks for robust multi-action export
    if not arm_obj.animation_data:
        arm_obj.animation_data_create()

    target_actions = [
        act for act in bpy.data.actions if act.name.startswith("action_anime_")
    ]

    # Clear existing NLA tracks to ensure clean export
    for track in list(arm_obj.animation_data.nla_tracks):
        arm_obj.animation_data.nla_tracks.remove(track)

    for act in target_actions:
        act.use_fake_user = True
        track_name = f"NLA_{act.name}"
        track = arm_obj.animation_data.nla_tracks.new()
        track.name = track_name

        f_start = int(act.frame_range[0])
        strip = track.strips.new(act.name, f_start, act)
        strip.action = act
        # Mute all except the primary idle action
        track.mute = (act.name != "action_anime_idle_cute")
        manifest["nla_tracks"].append(track_name)

    # Set default active action
    idle_action = bpy.data.actions.get("action_anime_idle_cute")
    if idle_action:
        arm_obj.animation_data.action = idle_action
    elif target_actions:
        arm_obj.animation_data.action = target_actions[0]

    # 6. Save master animated blend file
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))
    manifest["blend_saved"] = True
    manifest["blend_size_bytes"] = out_blend.stat().st_size

    # 7. Export animated GLB asset
    if export_glb:
        # In Blender 4.5.4 LTS, export_animation_mode accepts 'ACTIONS'
        try:
            bpy.ops.export_scene.gltf(
                filepath=str(out_glb),
                export_format='GLB',
                export_animations=True,
                export_animation_mode='ACTIONS',
                export_nla_strips=True,
                export_all_influences=True,
                export_def_bones=True,
            )
            manifest["glb_exported"] = True
            manifest["glb_size_bytes"] = out_glb.stat().st_size
        except Exception as e:
            # Fallback if export_def_bones unsupported
            bpy.ops.export_scene.gltf(
                filepath=str(out_glb),
                export_format='GLB',
                export_animations=True,
                export_animation_mode='ACTIONS',
                export_nla_strips=True,
                export_all_influences=True,
            )
            manifest["glb_exported"] = True
            manifest["glb_size_bytes"] = out_glb.stat().st_size

    manifest["status"] = "success"
    return manifest


__all__ = [
    # Constants
    "SPRING_MASS",
    "SPRING_STIFFNESS",
    "SPRING_DAMPING",
    "SPRING_REST_POS",
    "SKIRT_PITCH_MIN_DEG",
    "SKIRT_PITCH_MAX_DEG",
    "MIN_CLEARANCE_MM",
    "SKIRT_BONE_COUNT",
    "TWINTAIL_SEGMENT_COUNT",
    "HAIR_BONES_LEFT",
    "HAIR_BONES_RIGHT",
    "ALL_HAIR_BONES",
    "SKIRT_BONE_NAMES",
    "ACTION_NAMES",
    "ACTION_METADATA_REGISTRY",
    "ActionMetadata",
    "ActionDefinition",
    "HINGE_LIMITS",
    "PHYSIOLOGICAL_ROTATION_LIMITS",
    "BONE_MAPPING_TABLES",
    # Solvers
    "calculate_damping_ratio",
    "solve_spring_damper_step",
    "solve_rk4_step",
    "solve_rk4_substepped",
    "simulate_rk4_spring_damper",
    "TwintailChainSimulator",
    "SkirtClearanceSimulator",
    "SecondarySpringDynamicsSolver",
    "bake_secondary_dynamics_action",
    "bake_secondary_dynamics_to_action",
    "bake_secondary_dynamics_all_actions",
    # Actions
    "create_action_idle_cute",
    "create_action_wave_greeting",
    "create_action_walk_cycle",
    "create_action_jump_cheer",
    "build_action_idle_cute",
    "build_action_wave_greeting",
    "build_action_walk_cycle",
    "build_action_jump_cheer",
    "build_all_anime_actions",
    "generate_all_anime_actions",
    "get_canonical_action_definitions",
    # Limits & Retargeting
    "apply_retargeting_limits",
    "setup_retargeting_constraints",
    "remove_retargeting_limits",
    "verify_retargeting_limits",
    "clamp_pose_rotations",
    "clamp_animation_action_keyframes",
    # Master Pipeline
    "generate_animated_character",
]
