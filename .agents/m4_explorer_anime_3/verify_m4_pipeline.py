"""
verify_m4_pipeline.py
Standalone Verification Harness for Milestone 4:
- Feature F18: Headless Full HD Video Exporter (video_exporter.py)
- Feature F19: Master Unified CLI Entrypoint (pipeline.py)

Can be executed via:
    uv run python verify_m4_pipeline.py
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

# Path setup: add working directory and project directory to sys.path
AGENT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline")
if str(AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(AGENT_DIR))
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

# Import proposed blueprints
import proposed_video_exporter as video_exporter
import proposed_pipeline as pipeline


def print_banner(text: str) -> None:
    line = "=" * 70
    print(f"\n{line}\n  {text}\n{line}")


def test_1_video_export_config_and_presets() -> bool:
    """Test 1: Verifies VideoExportConfig defaults, invariants, and resolution presets."""
    print("Test 1: VideoExportConfig and Resolution Presets...")

    cfg = video_exporter.VideoExportConfig()
    assert cfg.resolution_x == 1920, f"Expected 1920, got {cfg.resolution_x}"
    assert cfg.resolution_y == 1080, f"Expected 1080, got {cfg.resolution_y}"
    assert cfg.fps >= 30, f"Expected fps >= 30, got {cfg.fps}"
    assert cfg.engine == "BLENDER_EEVEE_NEXT", f"Expected BLENDER_EEVEE_NEXT, got {cfg.engine}"
    assert cfg.file_format == "FFMPEG", f"Expected FFMPEG, got {cfg.file_format}"
    assert cfg.video_format == "MPEG4", f"Expected MPEG4, got {cfg.video_format}"
    assert cfg.video_codec == "H264", f"Expected H264, got {cfg.video_codec}"
    assert cfg.min_size_bytes >= 1024 * 1024, "Minimum size threshold must be >= 1MB"
    assert cfg.min_duration_s >= 3.0, "Minimum duration must be >= 3.0s"

    # Test presets
    p1080 = video_exporter.VideoExportConfig.from_resolution_string("1080p")
    assert (p1080.resolution_x, p1080.resolution_y) == (1920, 1080)

    p720 = video_exporter.VideoExportConfig.from_resolution_string("720p")
    assert (p720.resolution_x, p720.resolution_y) == (1280, 720)

    p4k = video_exporter.VideoExportConfig.from_resolution_string("4k")
    assert (p4k.resolution_x, p4k.resolution_y) == (3840, 2160)

    d = cfg.to_dict()
    assert d["resolution_x"] == 1920 and d["resolution_y"] == 1080
    assert d["fps"] == 30
    assert d["video_codec"] == "H264"
    assert d["output_path"].endswith(".mp4")

    print("  -> PASSED: VideoExportConfig compliant with all F18 specifications.")
    return True


def test_2_iso_bmff_parser() -> bool:
    """Test 2: Verifies pure Python ISO BMFF parser logic on simulated headers."""
    print("Test 2: Pure Python ISO BMFF MP4 Box Parser...")

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        tmp_name = tf.name
        # Construct synthetic ftyp box (24 bytes)
        # ftyp box length 24, type 'ftyp', major_brand 'isom', minor_version 0x200, brand 'iso2', 'mp41'
        ftyp_bytes = (
            (24).to_bytes(4, "big") +
            b"ftyp" +
            b"isom" +
            (0x00000200).to_bytes(4, "big") +
            b"iso2" +
            b"mp41"
        )
        # moov box with mvhd
        # mvhd box: 4 size, 4 'mvhd', 1 ver(0), 3 flags, 4 creation, 4 mod, 4 timescale(1000), 4 duration(4000) = 28 bytes
        mvhd_payload = (
            (0).to_bytes(1, "big") + (0).to_bytes(3, "big") +
            (0).to_bytes(4, "big") +
            (0).to_bytes(4, "big") +
            (1000).to_bytes(4, "big") +
            (4000).to_bytes(4, "big")
        )
        mvhd_box = (len(mvhd_payload) + 8).to_bytes(4, "big") + b"mvhd" + mvhd_payload
        moov_box = (len(mvhd_box) + 8).to_bytes(4, "big") + b"moov" + mvhd_box
        tf.write(ftyp_bytes + moov_box)

    try:
        header = video_exporter.parse_iso_bmff_mp4_header(tmp_name)
        assert header["valid_container"] is True, "Expected valid container"
        assert header["major_brand"] == "isom", f"Expected isom, got {header['major_brand']}"
        assert "iso2" in header["compatible_brands"]
        assert header["duration_s"] == 4.0, f"Expected 4.0s duration, got {header['duration_s']}"
        print("  -> PASSED: Pure Python ISO BMFF header parser correctly decoded box hierarchy.")
    finally:
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass

    return True


def test_3_pipeline_cli_parser() -> bool:
    """Test 3: Verifies CLI argument parser in pipeline.py (Feature F19)."""
    print("Test 3: Master Pipeline CLI Argument Parser...")

    parser = pipeline.build_cli_parser()

    # Test full flags
    args = parser.parse_args(["--action", "action_anime_walk_cycle", "--render", "--fps", "30", "--resolution", "1080p"])
    assert args.action == "action_anime_walk_cycle"
    assert args.render is True
    assert args.fps == 30
    assert args.resolution == "1080p"
    assert args.output_dir == "./output"

    # Test stage flags
    args_all = parser.parse_args(["--all"])
    assert args_all.all is True

    args_mesh = parser.parse_args(["--mesh"])
    assert args_mesh.mesh is True

    args_rig = parser.parse_args(["--rig"])
    assert args_rig.rig is True

    args_anim = parser.parse_args(["--anim"])
    assert args_anim.anim is True

    args_shade = parser.parse_args(["--shade"])
    assert args_shade.shade is True

    print("  -> PASSED: Master CLI argument parser conforms to all F19 requirements.")
    return True


def test_4_blender_eevee_next_settings_live() -> bool:
    """Test 4: Verifies live Blender EEVEE-Next and FFMPEG configuration."""
    print("Test 4: Live Blender 4.5 EEVEE-Next & FFMPEG Settings Verification...")

    blender_bin = video_exporter.find_blender_binary()
    assert blender_bin.exists(), f"Blender binary not found at {blender_bin}"

    test_script = """import bpy, sys, os
for d in [r'E:/tool/mcp/MorphoMesh/teamwork_projects/anime_character_pipeline', r'E:/tool/mcp/MorphoMesh/.agents/m4_explorer_anime_3']:
    if d not in sys.path:
        sys.path.insert(0, d)

try:
    from anime_pipeline.rendering.video_exporter import setup_eevee_next_render_settings, VideoExportConfig
except ImportError:
    from proposed_video_exporter import setup_eevee_next_render_settings, VideoExportConfig

scene = bpy.context.scene
cfg = VideoExportConfig(resolution_x=1920, resolution_y=1080, fps=30)
res = setup_eevee_next_render_settings(scene, cfg)
assert scene.render.engine == 'BLENDER_EEVEE_NEXT', f'Engine mismatch: {scene.render.engine}'
assert scene.render.resolution_x == 1920 and scene.render.resolution_y == 1080
assert scene.render.fps == 30
assert scene.render.image_settings.file_format == 'FFMPEG'
assert scene.render.ffmpeg.format == 'MPEG4'
assert scene.render.ffmpeg.codec == 'H264'
assert scene.render.ffmpeg.constant_rate_factor == 'HIGH'
print('EEVEE_NEXT_LIVE_SETTINGS_VERIFIED')
sys.exit(0)
"""

    cmd = [str(blender_bin), "-b", "--python-expr", test_script]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"Blender EEVEE-Next verification failed:\n{proc.stdout}\n{proc.stderr}"
    assert "EEVEE_NEXT_LIVE_SETTINGS_VERIFIED" in proc.stdout

    print("  -> PASSED: Live Blender 4.5 successfully configured BLENDER_EEVEE_NEXT and FFMPEG H.264.")
    return True


def test_5_live_headless_test_render() -> bool:
    """Test 5: Executes live headless render of 10 frames to verify container and video output."""
    print("Test 5: Live Headless Render Execution on anime_animated.blend...")

    input_blend = PROJECT_DIR / "output" / "anime_animated.blend"
    assert input_blend.exists(), f"Missing input asset: {input_blend}"

    tmp_mp4 = Path(tempfile.gettempdir()) / f"verify_m4_test_{int(time.time())}.mp4"

    try:
        t0 = time.time()
        res = video_exporter.run_headless_render(
            blend_path=input_blend,
            output_mp4_path=tmp_mp4,
            action_name="action_anime_idle_cute",
            frame_start=1,
            frame_end=15,  # 15 frames for fast validation
            resolution="preview",
            fps=30,
            timeout_s=60.0,
            cwd=PROJECT_DIR,
        )
        elapsed = time.time() - t0

        assert res.get("status") == "success", f"Render failed: {res}"
        assert tmp_mp4.exists(), f"Rendered file does not exist: {tmp_mp4}"
        assert tmp_mp4.stat().st_size > 5000, f"File size too small: {tmp_mp4.stat().st_size} bytes"

        # Validate MP4 file with validator
        val_cfg = video_exporter.VideoExportConfig.from_resolution_string("preview", fps=30)
        val_cfg.min_size_bytes = 2000
        val_cfg.min_duration_s = 0.4
        report = video_exporter.validate_video_file(tmp_mp4, val_cfg)

        assert report.checks["file_exists"] is True
        assert report.checks["valid_container_header"] is True
        assert report.checks["valid_codec"] is True

        print(
            f"  -> PASSED: Rendered 15-frame preview in {elapsed:.2f}s, "
            f"Size: {report.size_bytes} bytes, Codec: {report.codec}, Container: {report.container_brand}"
        )
    finally:
        if tmp_mp4.exists():
            try:
                os.remove(tmp_mp4)
            except Exception:
                pass

    return True


def run_all_verifications() -> int:
    """Runs all 5 verification tests."""
    print_banner("Milestone 4 Verification Suite: Headless Video Exporter & CLI Entrypoint")

    tests = [
        ("Test 1: VideoExportConfig & Presets", test_1_video_export_config_and_presets),
        ("Test 2: Pure Python ISO BMFF MP4 Box Parser", test_2_iso_bmff_parser),
        ("Test 3: Master Pipeline CLI Argument Parser", test_3_pipeline_cli_parser),
        ("Test 4: Live Blender EEVEE-Next & FFMPEG Settings", test_4_blender_eevee_next_settings_live),
        ("Test 5: Live Headless Test Render", test_5_live_headless_test_render),
    ]

    passed = 0
    failed = 0

    for name, fn in tests:
        try:
            if fn():
                passed += 1
            else:
                failed += 1
                print(f"  FAILED: {name}")
        except Exception as e:
            failed += 1
            print(f"  EXCEPTION in {name}: {e}")

    print_banner(f"Verification Results: {passed}/{len(tests)} Tests Passed ({failed} Failed)")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_verifications())
