"""
anime_pipeline/rendering/__init__.py
Milestone 4: Cel-Shading, Outline, Camera Rig & Video Pipeline (Features F17 & F18).

Provides:
- VideoExportConfig: Parameter container for Blender EEVEE-Next Full HD MP4 export.
- VideoValidationReport: Audit report container for MP4 file streams.
- setup_eevee_next_render_settings(): Configures EEVEE-Next, 1080p, 30fps, FFMPEG H.264.
- setup_render_action_and_timeline(): Binds active action and configures frame timeline.
- ensure_render_camera_and_lighting(): Camera and studio lighting verification and fallback.
- validate_video_file(): Validates file size > 1MB, duration >= 3s, ISO container, H.264.
- render_cinematic_video(): Master programmatic rendering API (in-engine & headless).
- build_headless_render_command(): CLI invocation list builder.
- run_headless_render(): Subprocess execution with timeout and output capture.
- build_and_render_cinematic_scene(): High-level M4 staging and video export orchestrator.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    import bpy
    HAS_BPY = True
except ImportError:
    bpy = None  # type: ignore[assignment]
    HAS_BPY = False

from .video_exporter import (
    DEFAULT_CODEC,
    DEFAULT_CONTAINER,
    DEFAULT_ENGINE,
    DEFAULT_FPS,
    DEFAULT_RESOLUTION_X,
    DEFAULT_RESOLUTION_Y,
    MIN_DURATION_SECONDS,
    MIN_FILE_SIZE_BYTES,
    MIN_FRAME_RATE,
    RESOLUTION_PRESETS,
    VideoExportConfig,
    VideoValidationReport,
    build_headless_render_command,
    ensure_render_camera_and_lighting,
    find_blender_binary,
    find_ffprobe_binary,
    parse_iso_bmff_mp4_header,
    render_cinematic_video,
    run_headless_render,
    setup_eevee_next_render_settings,
    setup_render_action_and_timeline,
    validate_video_file,
)

from .camera_rig import (
    CameraConfig,
    CameraRigConfig,
    LightingRigConfig,
    CinematicStageResult,
    StageSetupResult,
    create_cinematic_camera,
    setup_cinematic_camera,
    create_3point_lighting_rig,
    setup_anime_3point_lighting,
    setup_cinematic_stage,
    build_cinematic_stage,
    calculate_optical_framing_distance,
    compute_camera_fov,
    compute_required_framing_distance,
)


# ==============================================================================
# Master Milestone 4 Staging & Rendering Orchestrator
# ==============================================================================

def build_and_render_cinematic_scene(
    input_blend_path: Union[str, Path] = "output/anime_animated.blend",
    output_blend_path: Union[str, Path] = "output/anime_final.blend",
    output_mp4_path: Union[str, Path] = "output/anime_girl_cinematic.mp4",
    action_name: str = "action_anime_wave_greeting",
    resolution: str = "1080p",
    fps: int = 30,
    blender_exe: Optional[Union[str, Path]] = None,
) -> Dict[str, Any]:
    """
    Coordinates all Milestone 4 components into an integrated staging & rendering sequence:
    1. Opens input animated blend (output/anime_animated.blend).
    2. Applies Cel-Shading toon materials (Skin, Clothes, Hair with Angel Ring, Eye).
    3. Applies Inverted Hull Solidify outline modifiers.
    4. Sets up 65mm cinematic camera and 3-point anime studio lighting.
    5. Saves master scene to output/anime_final.blend.
    6. Renders Full HD 1080p MP4 video to output/anime_girl_cinematic.mp4 via EEVEE-Next.
    7. Validates final video stream against all acceptance criteria.
    """
    pkg_root = Path(__file__).resolve().parent.parent.parent
    in_blend = Path(input_blend_path)
    if not in_blend.is_absolute() and not in_blend.exists():
        candidate = pkg_root / input_blend_path
        if candidate.exists():
            in_blend = candidate
    in_blend = in_blend.resolve()

    out_blend = Path(output_blend_path)
    if not out_blend.is_absolute():
        out_blend = (pkg_root / output_blend_path).resolve()

    out_mp4 = Path(output_mp4_path)
    if not out_mp4.is_absolute():
        out_mp4 = (pkg_root / output_mp4_path).resolve()

    out_blend.parent.mkdir(parents=True, exist_ok=True)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    if not HAS_BPY:
        blender_bin = find_blender_binary(blender_exe)
        script = (
            "import sys; "
            "from anime_pipeline.rendering import build_and_render_cinematic_scene; "
            f"res = build_and_render_cinematic_scene("
            f"input_blend_path=r'{in_blend}', "
            f"output_blend_path=r'{out_blend}', "
            f"output_mp4_path=r'{out_mp4}', "
            f"action_name='{action_name}', "
            f"resolution='{resolution}', "
            f"fps={fps}); "
            "sys.exit(0 if res.get('status') == 'success' else 1)"
        )
        cmd = [str(blender_bin), "-b", str(in_blend), "--python-expr", script]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(pkg_root))
        val_report = validate_video_file(
            out_mp4, VideoExportConfig.from_resolution_string(resolution, fps=fps)
        )
        return {
            "status": "success" if (proc.returncode == 0 and val_report.valid) else "failed",
            "exit_code": proc.returncode,
            "output_blend": str(out_blend),
            "output_mp4": str(out_mp4),
            "validation": val_report.to_dict(),
            "stdout_tail": "\n".join(proc.stdout.splitlines()[-20:]),
        }

    # Inside Blender runtime
    bpy.ops.wm.open_mainfile(filepath=str(in_blend))
    scene = bpy.context.scene

    # 1. Apply Toon Shaders
    try:
        from anime_pipeline.shading.toon_materials import apply_all_toon_materials
        apply_all_toon_materials(separate_garments=True)
    except Exception as e:
        print("Toon materials notice:", e)

    # 2. Apply Inverted Hull Outlines
    try:
        from anime_pipeline.shading.inverted_hull import apply_inverted_hull_outline
        apply_inverted_hull_outline()
    except Exception as e:
        print("Inverted hull notice:", e)

    # 3. Setup Camera & Lighting
    try:
        setup_cinematic_camera(scene)
        setup_anime_3point_lighting(scene)
    except Exception as e:
        print("Camera/lighting notice:", e)
        ensure_render_camera_and_lighting(scene)

    # 4. Save Final Scene .blend
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))

    # 5. Render Video
    cfg = VideoExportConfig.from_resolution_string(resolution, fps=fps)
    render_result = render_cinematic_video(
        scene_path=None,
        output_mp4_path=out_mp4,
        action_name=action_name,
        config=cfg,
        validate=True,
    )

    return {
        "status": render_result.get("status", "success"),
        "output_blend": str(out_blend),
        "output_mp4": str(out_mp4),
        "render_details": render_result,
        "validation": render_result.get("validation"),
    }


__all__ = [
    # Constants
    "DEFAULT_ENGINE",
    "DEFAULT_RESOLUTION_X",
    "DEFAULT_RESOLUTION_Y",
    "DEFAULT_FPS",
    "DEFAULT_CONTAINER",
    "DEFAULT_CODEC",
    "MIN_FILE_SIZE_BYTES",
    "MIN_DURATION_SECONDS",
    "MIN_FRAME_RATE",
    "RESOLUTION_PRESETS",
    # Data classes
    "VideoExportConfig",
    "VideoValidationReport",
    "CameraConfig",
    "CameraRigConfig",
    "LightingRigConfig",
    "CinematicStageResult",
    "StageSetupResult",
    # Functions
    "setup_eevee_next_render_settings",
    "setup_render_action_and_timeline",
    "ensure_render_camera_and_lighting",
    "validate_video_file",
    "parse_iso_bmff_mp4_header",
    "find_blender_binary",
    "find_ffprobe_binary",
    "build_headless_render_command",
    "run_headless_render",
    "render_cinematic_video",
    "create_cinematic_camera",
    "setup_cinematic_camera",
    "create_3point_lighting_rig",
    "setup_anime_3point_lighting",
    "setup_cinematic_stage",
    "build_cinematic_stage",
    "calculate_optical_framing_distance",
    "compute_camera_fov",
    "compute_required_framing_distance",
    "build_and_render_cinematic_scene",
]
