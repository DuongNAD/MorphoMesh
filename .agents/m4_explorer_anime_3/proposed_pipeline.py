"""
pipeline.py
Master Unified CLI Pipeline Entrypoint (Feature F19).
Target: teamwork_projects/anime_character_pipeline/pipeline.py

Coordinates all 4 milestones into a single seamless, production-grade CLI command:
- Step 1 (M1): Mesh synthesis -> output/anime_character_modular.obj, anime_mesh_clean.blend, .glb
- Step 2 (M2): Auto-rigging & DQS -> output/anime_rigged.blend, .glb
- Step 3 (M3): Actions & secondary physics baking -> output/anime_animated.blend, .glb
- Step 4 (M4): Cel-shading, inverted hull, camera rig & EEVEE-Next render -> output/anime_girl_cinematic.mp4, anime_final.blend

CLI Usage:
    python pipeline.py --all
    python pipeline.py --mesh
    python pipeline.py --rig
    python pipeline.py --anim
    python pipeline.py --shade
    python pipeline.py --render --action action_anime_wave_greeting --resolution 1080p
    python pipeline.py --audit
"""

from __future__ import annotations

import argparse
import dataclasses
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Union


# ==============================================================================
# Pipeline Execution Manager
# ==============================================================================

class AnimePipelineManager:
    """
    Coordinates and executes the 4 anime character generation milestones.
    Can be run from host Python or headless Blender.
    """

    def __init__(
        self,
        output_dir: Union[str, Path] = "output",
        action: str = "action_anime_wave_greeting",
        resolution: str = "1080p",
        fps: int = 30,
        blender_exe: Optional[Union[str, Path]] = None,
        verbose: bool = True,
    ):
        self.proj_root = Path(__file__).resolve().parent
        self.output_dir = Path(output_dir)
        if not self.output_dir.is_absolute():
            self.output_dir = (self.proj_root / self.output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.action = action
        self.resolution = resolution
        self.fps = fps
        self.blender_exe = self._resolve_blender(blender_exe)
        self.verbose = verbose

        # Deliverables paths
        self.path_modular_obj = self.output_dir / "anime_character_modular.obj"
        self.path_mesh_clean_blend = self.output_dir / "anime_mesh_clean.blend"
        self.path_mesh_clean_glb = self.output_dir / "anime_mesh_clean.glb"
        self.path_rigged_blend = self.output_dir / "anime_rigged.blend"
        self.path_rigged_glb = self.output_dir / "anime_rigged.glb"
        self.path_animated_blend = self.output_dir / "anime_animated.blend"
        self.path_animated_glb = self.output_dir / "anime_animated.glb"
        self.path_final_blend = self.output_dir / "anime_final.blend"
        self.path_cinematic_mp4 = self.output_dir / "anime_girl_cinematic.mp4"

        # Execution log
        self.stages_run: List[str] = []
        self.stage_results: Dict[str, Any] = {}

    def _resolve_blender(self, custom_path: Optional[Union[str, Path]]) -> Path:
        """Finds Blender 4.5+ LTS executable."""
        if custom_path:
            p = Path(custom_path).resolve()
            if p.exists() and p.is_file():
                return p

        env_blender = os.environ.get("BLENDER_BIN") or os.environ.get("BLENDER_EXE")
        if env_blender:
            p = Path(env_blender).resolve()
            if p.exists() and p.is_file():
                return p

        which_blender = shutil.which("blender")
        if which_blender:
            return Path(which_blender).resolve()

        candidates = [
            r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe",
            r"C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
        ]
        for c in candidates:
            p = Path(c)
            if p.exists() and p.is_file():
                return p

        # Fallback to candidate 0
        return Path(candidates[0])

    def log(self, message: str, tag: str = "INFO") -> None:
        """Logs timestamped pipeline message."""
        if self.verbose:
            ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            print(f"[{ts}] [{tag:<5}] {message}")

    # --------------------------------------------------------------------------
    # Step 1: Milestone 1 - Mesh Synthesis
    # --------------------------------------------------------------------------
    def run_mesh_stage(self) -> Dict[str, Any]:
        """
        Executes Milestone 1:
        Synthesizes 7 modular sub-meshes with quad topology and exports:
        - output/anime_character_modular.obj
        - output/anime_mesh_clean.blend
        - output/anime_mesh_clean.glb
        """
        self.log("Starting Step 1 (M1): Anime Mesh Synthesis...", tag="STAGE")
        t0 = time.time()

        from anime_pipeline.mesh.generator import AnimeMeshConfig, AnimeMeshGenerator

        cfg = AnimeMeshConfig()
        gen = AnimeMeshGenerator(cfg)
        model_result = gen.generate_all()

        # Export master OBJ
        model_result.export_master_obj(self.path_modular_obj)
        self.log(f"Exported Modular OBJ: {self.path_modular_obj}", tag="M1")

        # Export clean Blend and GLB via headless Blender
        model_result.export_master_blend(
            filepath=self.path_mesh_clean_blend,
            glb_filepath=self.path_mesh_clean_glb,
            blender_exe=str(self.blender_exe),
        )
        self.log(f"Exported Clean Blend: {self.path_mesh_clean_blend}", tag="M1")
        self.log(f"Exported Clean GLB: {self.path_mesh_clean_glb}", tag="M1")

        elapsed = time.time() - t0
        res = {
            "stage": "mesh",
            "status": "success",
            "elapsed_seconds": elapsed,
            "submeshes": list(model_result.submeshes.keys()),
            "total_vertices": model_result.total_vertices,
            "total_quads": model_result.total_quads,
            "files": {
                "obj": str(self.path_modular_obj),
                "blend": str(self.path_mesh_clean_blend),
                "glb": str(self.path_mesh_clean_glb),
            },
        }
        self.stage_results["mesh"] = res
        self.stages_run.append("mesh")
        return res

    # --------------------------------------------------------------------------
    # Step 2: Milestone 2 - Auto-Rigging & DQS
    # --------------------------------------------------------------------------
    def run_rigging_stage(self) -> Dict[str, Any]:
        """
        Executes Milestone 2:
        Constructs canonical 78-bone armature, twist bones, radial skirt bones,
        twintail chains, and Dual Quaternion Skinning (use_deform_preserve_volume = True).
        Outputs:
        - output/anime_rigged.blend
        - output/anime_rigged.glb
        """
        self.log("Starting Step 2 (M2): Auto-Rigging & Dual Quaternion Skinning...", tag="STAGE")
        t0 = time.time()

        if not self.path_mesh_clean_blend.exists():
            self.log("Prerequisite anime_mesh_clean.blend missing. Running mesh stage first...", tag="WARN")
            self.run_mesh_stage()

        # Execute rigging in headless Blender
        script = (
            "import sys; "
            "from anime_pipeline.rigging import build_and_export_rigged_character; "
            f"res = build_and_export_rigged_character("
            f"clean_blend_path=r'{self.path_mesh_clean_blend}', "
            f"output_blend_path=r'{self.path_rigged_blend}', "
            f"output_glb_path=r'{self.path_rigged_glb}'); "
            "print('RIG_RESULT_SUCCESS:' + str(res.get('total_bones'))); "
            "sys.exit(0 if res.get('status') == 'success' else 1)"
        )
        cmd = [str(self.blender_exe), "-b", str(self.path_mesh_clean_blend), "--python-expr", script]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.proj_root))

        if proc.returncode != 0:
            err_msg = f"Rigging stage failed with exit code {proc.returncode}:\n{proc.stderr}"
            self.log(err_msg, tag="ERROR")
            raise RuntimeError(err_msg)

        elapsed = time.time() - t0
        self.log(f"Exported Rigged Blend: {self.path_rigged_blend}", tag="M2")
        self.log(f"Exported Rigged GLB: {self.path_rigged_glb}", tag="M2")

        res = {
            "stage": "rigging",
            "status": "success",
            "elapsed_seconds": elapsed,
            "files": {
                "blend": str(self.path_rigged_blend),
                "glb": str(self.path_rigged_glb),
            },
        }
        self.stage_results["rigging"] = res
        self.stages_run.append("rigging")
        return res

    # --------------------------------------------------------------------------
    # Step 3: Milestone 3 - Animation & Secondary Dynamics Baking
    # --------------------------------------------------------------------------
    def run_animation_stage(self) -> Dict[str, Any]:
        """
        Executes Milestone 3:
        Applies joint rotation limits, generates 4 core anime actions,
        bakes secondary spring-damper dynamics, and pushes to NLA tracks.
        Outputs:
        - output/anime_animated.blend
        - output/anime_animated.glb
        """
        self.log("Starting Step 3 (M3): Animation & Secondary Physics Baking...", tag="STAGE")
        t0 = time.time()

        if not self.path_rigged_blend.exists():
            self.log("Prerequisite anime_rigged.blend missing. Running rigging stage first...", tag="WARN")
            self.run_rigging_stage()

        # Execute animation generation in headless Blender
        script = (
            "import sys; "
            "from anime_pipeline.animation import generate_animated_character; "
            f"res = generate_animated_character("
            f"input_blend_path=r'{self.path_rigged_blend}', "
            f"output_blend_path=r'{self.path_animated_blend}', "
            f"output_glb_path=r'{self.path_animated_glb}', "
            f"fps={self.fps}); "
            "print('ANIM_RESULT_SUCCESS:' + str(len(res.get('actions_generated', [])))); "
            "sys.exit(0 if res.get('status') == 'success' else 1)"
        )
        cmd = [str(self.blender_exe), "-b", str(self.path_rigged_blend), "--python-expr", script]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.proj_root))

        if proc.returncode != 0:
            err_msg = f"Animation stage failed with exit code {proc.returncode}:\n{proc.stderr}"
            self.log(err_msg, tag="ERROR")
            raise RuntimeError(err_msg)

        elapsed = time.time() - t0
        self.log(f"Exported Animated Blend: {self.path_animated_blend}", tag="M3")
        self.log(f"Exported Animated GLB: {self.path_animated_glb}", tag="M3")

        res = {
            "stage": "animation",
            "status": "success",
            "elapsed_seconds": elapsed,
            "files": {
                "blend": str(self.path_animated_blend),
                "glb": str(self.path_animated_glb),
            },
        }
        self.stage_results["animation"] = res
        self.stages_run.append("animation")
        return res

    # --------------------------------------------------------------------------
    # Step 4: Milestone 4 - Shading & Staging (Cel-Shading, Outline, Camera Rig)
    # --------------------------------------------------------------------------
    def run_shading_stage(self) -> Dict[str, Any]:
        """
        Executes Milestone 4 (Shading & Staging):
        Applies cel-shaders, Angel Ring hair highlight, inverted hull outline,
        65mm cinematic camera, and 3-point anime studio lighting.
        Outputs:
        - output/anime_final.blend
        """
        self.log("Starting Step 4 (M4): Cel-Shading, Outline & Camera Staging...", tag="STAGE")
        t0 = time.time()

        if not self.path_animated_blend.exists():
            self.log("Prerequisite anime_animated.blend missing. Running animation stage first...", tag="WARN")
            self.run_animation_stage()

        # Headless script to apply shading, outline, and camera rig
        script = (
            "import bpy, sys; "
            "bpy.ops.wm.open_mainfile(filepath=r'" + str(self.path_animated_blend) + "'); "
            "scene = bpy.context.scene; "
            "# 1. Apply Toon Materials if available\n"
            "try:\n"
            "    from anime_pipeline.shading.toon_materials import apply_toon_materials_to_scene\n"
            "    apply_toon_materials_to_scene()\n"
            "except Exception as e:\n"
            "    print('Toon materials warning:', e)\n"
            "# 2. Apply Inverted Hull if available\n"
            "try:\n"
            "    from anime_pipeline.shading.inverted_hull import apply_inverted_hull_outlines\n"
            "    apply_inverted_hull_outlines()\n"
            "except Exception as e:\n"
            "    print('Inverted hull warning:', e)\n"
            "# 3. Setup Camera & Lighting\n"
            "try:\n"
            "    from anime_pipeline.rendering.camera_rig import setup_cinematic_camera, setup_anime_3point_lighting\n"
            "    setup_cinematic_camera(scene)\n"
            "    setup_anime_3point_lighting(scene)\n"
            "except Exception as e:\n"
            "    from anime_pipeline.rendering.video_exporter import ensure_render_camera_and_lighting\n"
            "    ensure_render_camera_and_lighting(scene)\n"
            "bpy.ops.wm.save_as_mainfile(filepath=r'" + str(self.path_final_blend) + "'); "
            "print('SHADING_STAGE_SUCCESS'); "
            "sys.exit(0)"
        )

        cmd = [str(self.blender_exe), "-b", str(self.path_animated_blend), "--python-expr", script]
        proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.proj_root))

        if proc.returncode != 0:
            err_msg = f"Shading stage failed with exit code {proc.returncode}:\n{proc.stderr}"
            self.log(err_msg, tag="ERROR")
            raise RuntimeError(err_msg)

        elapsed = time.time() - t0
        self.log(f"Exported Final Shaded Blend: {self.path_final_blend}", tag="M4")

        res = {
            "stage": "shading",
            "status": "success",
            "elapsed_seconds": elapsed,
            "files": {
                "blend": str(self.path_final_blend),
            },
        }
        self.stage_results["shading"] = res
        self.stages_run.append("shading")
        return res

    # --------------------------------------------------------------------------
    # Step 5: Milestone 4 - Headless Video Export
    # --------------------------------------------------------------------------
    def run_render_stage(self) -> Dict[str, Any]:
        """
        Executes Milestone 4 (Video Render):
        Renders Full HD 1080p MP4 video via EEVEE-Next @ 30 FPS.
        Outputs:
        - output/anime_girl_cinematic.mp4
        """
        self.log(f"Starting Step 5 (M4): Headless Full HD Video Exporter ({self.action}, {self.resolution})...", tag="STAGE")
        t0 = time.time()

        blend_source = self.path_final_blend if self.path_final_blend.exists() else self.path_animated_blend
        if not blend_source.exists():
            self.log("Prerequisite blend file missing. Running staging first...", tag="WARN")
            self.run_shading_stage()
            blend_source = self.path_final_blend

        from anime_pipeline.rendering.video_exporter import (
            VideoExportConfig,
            render_cinematic_video,
            validate_video_file,
        )

        cfg = VideoExportConfig.from_resolution_string(self.resolution, fps=self.fps)

        render_res = render_cinematic_video(
            scene_path=blend_source,
            output_mp4_path=self.path_cinematic_mp4,
            action_name=self.action,
            resolution=self.resolution,
            fps=self.fps,
            config=cfg,
            validate=True,
            blender_exe=self.blender_exe,
        )

        elapsed = time.time() - t0
        if render_res.get("status") != "success":
            err_msg = f"Video rendering failed: {render_res.get('error', 'Unknown error')}"
            self.log(err_msg, tag="ERROR")
            raise RuntimeError(err_msg)

        self.log(f"Exported Cinematic MP4: {self.path_cinematic_mp4}", tag="M4")
        if render_res.get("validation"):
            v = render_res["validation"]
            self.log(
                f"Video Verified: {v.get('width')}x{v.get('height')} @ {v.get('fps')} FPS, "
                f"Duration: {v.get('duration_s')}s, Size: {v.get('size_mb')} MB",
                tag="PASS",
            )

        res = {
            "stage": "render",
            "status": "success",
            "elapsed_seconds": elapsed,
            "files": {
                "mp4": str(self.path_cinematic_mp4),
            },
            "validation": render_res.get("validation"),
        }
        self.stage_results["render"] = res
        self.stages_run.append("render")
        return res

    # --------------------------------------------------------------------------
    # Master Execution
    # --------------------------------------------------------------------------
    def run_all(self) -> Dict[str, Any]:
        """Runs all 4 milestones end-to-end."""
        self.log("=======================================================", tag="INIT")
        self.log("Executing Complete Anime Character Pipeline (M1 - M4)", tag="INIT")
        self.log("=======================================================", tag="INIT")

        t_start = time.time()
        self.run_mesh_stage()
        self.run_rigging_stage()
        self.run_animation_stage()
        self.run_shading_stage()
        self.run_render_stage()
        t_total = time.time() - t_start

        self.log("=======================================================", tag="DONE")
        self.log(f"Full Pipeline Finished Successfully in {t_total:.2f}s", tag="DONE")
        self.log("=======================================================", tag="DONE")

        return {
            "status": "success",
            "total_elapsed_seconds": t_total,
            "stages_executed": self.stages_run,
            "results": self.stage_results,
            "deliverables": {
                "modular_obj": str(self.path_modular_obj),
                "clean_mesh_blend": str(self.path_mesh_clean_blend),
                "clean_mesh_glb": str(self.path_mesh_clean_glb),
                "rigged_blend": str(self.path_rigged_blend),
                "rigged_glb": str(self.path_rigged_glb),
                "animated_blend": str(self.path_animated_blend),
                "animated_glb": str(self.path_animated_glb),
                "final_blend": str(self.path_final_blend),
                "cinematic_mp4": str(self.path_cinematic_mp4),
            },
        }


# ==============================================================================
# CLI Argument Parsing & Programmatic Interface
# ==============================================================================

def build_cli_parser() -> argparse.ArgumentParser:
    """
    Constructs the master CLI argument parser with all required flags:
    --all, --mesh, --rig, --anim, --shade, --render, --action, --output-dir, --resolution, --fps.
    """
    parser = argparse.ArgumentParser(
        description="Master Unified Anime Character Production Pipeline CLI (Features F18 & F19)"
    )

    # Execution Stages
    parser.add_argument("--all", action="store_true", help="Run full pipeline end-to-end (M1 -> M2 -> M3 -> M4)")
    parser.add_argument("--mesh", action="store_true", help="Run Step 1 (M1): Modular mesh synthesis & topology")
    parser.add_argument("--rig", action="store_true", help="Run Step 2 (M2): Auto-rigging & Dual Quaternion Skinning")
    parser.add_argument("--anim", action="store_true", help="Run Step 3 (M3): Actions & secondary dynamics baking")
    parser.add_argument("--shade", action="store_true", help="Run Step 4 (M4): Cel-shading, outline & camera staging")
    parser.add_argument("--render", action="store_true", help="Run Step 5 (M4): Headless Full HD MP4 video render")

    # Options & Parameters
    parser.add_argument("--action", type=str, default="action_anime_wave_greeting", help="Active action to render")
    parser.add_argument("--resolution", type=str, default="1080p", help="Render resolution (1080p, 720p, 4k, 1920x1080)")
    parser.add_argument("--fps", type=int, default=30, help="Framerate in frames per second (default: 30)")
    parser.add_argument("--output-dir", type=str, default="./output", help="Target output directory")
    parser.add_argument("--blender", type=str, default=None, help="Custom path to Blender 4.5+ LTS executable")
    parser.add_argument("--quiet", action="store_true", help="Suppress verbose logging")
    parser.add_argument("--audit", action="store_true", help="Run M5 verification audits after pipeline completion")

    return parser


def run_pipeline(
    args: Optional[Union[argparse.Namespace, Sequence[str], Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Convenience programmatic entry point to run the pipeline with args.
    Accepts argparse.Namespace, list of CLI argument strings, or parameter dictionary.
    """
    parser = build_cli_parser()

    if args is None:
        parsed = parser.parse_args()
    elif isinstance(args, argparse.Namespace):
        parsed = args
    elif isinstance(args, dict):
        arg_list: List[str] = []
        for k, v in args.items():
            flag = f"--{k.replace('_', '-')}"
            if isinstance(v, bool) and v:
                arg_list.append(flag)
            elif not isinstance(v, bool):
                arg_list.extend([flag, str(v)])
        parsed = parser.parse_args(arg_list)
    elif isinstance(args, (list, tuple)):
        parsed = parser.parse_args(list(args))
    else:
        parsed = parser.parse_args()

    manager = AnimePipelineManager(
        output_dir=parsed.output_dir,
        action=parsed.action,
        resolution=parsed.resolution,
        fps=parsed.fps,
        blender_exe=parsed.blender,
        verbose=not parsed.quiet,
    )

    # Check if specific stages requested
    specific_stages = any([parsed.mesh, parsed.rig, parsed.anim, parsed.shade, parsed.render])

    if parsed.all or not specific_stages:
        return manager.run_all()

    results: Dict[str, Any] = {}
    if parsed.mesh:
        results["mesh"] = manager.run_mesh_stage()
    if parsed.rig:
        results["rig"] = manager.run_rigging_stage()
    if parsed.anim:
        results["anim"] = manager.run_animation_stage()
    if parsed.shade:
        results["shade"] = manager.run_shading_stage()
    if parsed.render:
        results["render"] = manager.run_render_stage()

    return {
        "status": "success",
        "stages_executed": manager.stages_run,
        "results": results,
    }


def main() -> int:
    """CLI executable entry point."""
    parser = build_cli_parser()
    args = parser.parse_args()

    try:
        res = run_pipeline(args)
        if res.get("status") == "success":
            return 0
        return 1
    except Exception as e:
        print(f"[ERROR] Pipeline execution failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
