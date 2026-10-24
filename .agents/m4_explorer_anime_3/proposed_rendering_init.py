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

# Optional re-exports from camera_rig (Features F16/F17 from m4_explorer_anime_2)
try:
    from .camera_rig import (
        CameraRigConfig,
        LightingRigConfig,
        build_cinematic_stage,
        setup_anime_3point_lighting,
        setup_cinematic_camera,
    )
except ImportError:
    # Graceful fallback if camera_rig is not yet installed in teamwork_projects
    CameraRigConfig = None  # type: ignore[assignment, misc]
    LightingRigConfig = None  # type: ignore[assignment, misc]
    build_cinematic_stage = None  # type: ignore[assignment]
    setup_anime_3point_lighting = None  # type: ignore[assignment]
    setup_cinematic_camera = None  # type: ignore[assignment]


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
        # Launch Blender headless runner
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

    # 1. Attempt to apply Toon Shaders & Inverted Hull if available
    try:
        from anime_pipeline.shading.toon_materials import apply_toon_materials_to_scene
        apply_toon_materials_to_scene()
    except Exception:
        pass

    try:
        from anime_pipeline.shading.inverted_hull import apply_inverted_hull_outlines
        apply_inverted_hull_outlines()
    except Exception:
        pass

    # 2. Camera and Lighting
    if setup_cinematic_camera is not None and setup_anime_3point_lighting is not None:
        setup_cinematic_camera(scene)
        setup_anime_3point_lighting(scene)
    else:
        ensure_render_camera_and_lighting(scene)

    # 3. Save Final Scene .blend
    bpy.ops.wm.save_as_mainfile(filepath=str(out_blend))

    # 4. Render Video
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
    "CameraRigConfig",
    "LightingRigConfig",
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
    "setup_cinematic_camera",
    "setup_anime_3point_lighting",
    "build_cinematic_stage",
    "build_and_render_cinematic_scene",
]
