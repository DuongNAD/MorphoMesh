"""
Pipeline to generate a 3D anime girl, auto-rig it, and apply animation via Meshy AI.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ.get("MESHY_API_KEY")
if not API_KEY:
    print("Error: MESHY_API_KEY not found in environment or .env file!")
    sys.exit(1)

API_BASE = "https://api.meshy.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "MorphoMesh-Pipeline/2.0"
}

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "anime_girl"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def post_json(endpoint: str, payload: dict) -> dict:
    url = f"{API_BASE}{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=HEADERS, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code} on POST {url}: {body}")
        raise


def get_json(endpoint: str) -> dict:
    url = f"{API_BASE}{endpoint}"
    req = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        print(f"HTTP Error {e.code} on GET {url}: {body}")
        raise


def download_file(url: str, dest_path: Path):
    print(f"Downloading: {url} -> {dest_path}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())
    print(f"Saved: {dest_path} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")


def poll_task(endpoint_prefix: str, task_id: str, desc: str, max_wait: int = 600, interval: int = 5) -> dict:
    print(f"Polling {desc} (Task ID: {task_id})...")
    start = time.time()
    while time.time() - start < max_wait:
        res = get_json(f"{endpoint_prefix}/{task_id}")
        status = res.get("status")
        progress = res.get("progress", 0)
        elapsed = int(time.time() - start)
        print(f"[{elapsed}s] {desc}: status={status}, progress={progress}%")
        if status == "SUCCEEDED":
            return res
        if status in ("FAILED", "EXPIRED"):
            err_msg = res.get("task_error", {}).get("message") or res.get("message") or "Unknown error"
            raise RuntimeError(f"{desc} failed with status {status}: {err_msg}")
        time.sleep(interval)
    raise TimeoutError(f"{desc} timed out after {max_wait} seconds")


def step1_text_to_3d(existing_preview_id: str = None):
    print("\n" + "="*60)
    print("STEP 1: TEXT-TO-3D VIA MESHY AI (Model: meshy-6)")
    print("="*60)

    prompt = (
        "full body beautiful cute anime girl, female anime character with stylish twintails hair, "
        "charming face with expressive anime eyes, wearing cute modern school idol outfit, "
        "standing in neutral A-pose with arms slightly open, symmetric, facing forward, "
        "clean topology, game-ready 3D model, highly detailed vibrant texture"
    )
    neg_prompt = "low quality, deformed, mutated, extra limbs, ugly, bad anatomy, blur, non-humanoid"

    if existing_preview_id:
        print(f"Using existing Preview task ID: {existing_preview_id}")
        preview_task_id = existing_preview_id
    else:
        # 1a. Preview
        preview_payload = {
            "mode": "preview",
            "prompt": prompt,
            "negative_prompt": neg_prompt,
            "ai_model": "meshy-6"
        }
        print("Submitting Text-to-3D Preview task...")
        res = post_json("/openapi/v2/text-to-3d", preview_payload)
        preview_task_id = res["result"]
        print(f"Preview task ID: {preview_task_id}")

    preview_res = poll_task("/openapi/v2/text-to-3d", preview_task_id, "Text-to-3D Preview")
    preview_model_urls = preview_res.get("model_urls", {})
    print(f"Preview complete! Model URLs: {preview_model_urls}")

    # 1b. Refine
    refine_payload = {
        "mode": "refine",
        "preview_task_id": preview_task_id,
        "enable_pbr": True,
        "texture_resolution": "2k",
        "texture_prompt": "vibrant cute anime girl colors, detailed school idol outfit, anime face texture with sparkling eyes and blushing cheeks"
    }
    print("\nSubmitting Text-to-3D Refine (Texturing) task...")
    res = post_json("/openapi/v2/text-to-3d", refine_payload)
    refine_task_id = res["result"]
    print(f"Refine task ID: {refine_task_id}")

    refine_res = poll_task("/openapi/v2/text-to-3d", refine_task_id, "Text-to-3D Refine")
    model_urls = refine_res.get("model_urls", {})
    glb_url = model_urls.get("glb")
    print(f"Refine complete! Textured GLB URL: {glb_url}")

    if glb_url:
        local_glb = OUTPUT_DIR / "anime_girl_textured.glb"
        download_file(glb_url, local_glb)

    manifest = {
        "preview_task_id": preview_task_id,
        "refine_task_id": refine_task_id,
        "glb_url": glb_url,
        "model_urls": model_urls
    }
    with open(OUTPUT_DIR / "step1_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return refine_task_id, glb_url


def step2_auto_rig(refine_task_id: str, glb_url: str):
    print("\n" + "="*60)
    print("STEP 2: MESHY AUTO-RIGGING")
    print("="*60)

    rig_payload = {
        "input_task_id": refine_task_id,
        "height_meters": 1.65
    }
    print("Submitting Rigging task...")
    res = post_json("/openapi/v1/rigging", rig_payload)
    rig_task_id = res["result"]
    print(f"Rigging task ID: {rig_task_id}")

    rig_res = poll_task("/openapi/v1/rigging", rig_task_id, "Meshy Rigging")
    result_obj = rig_res.get("result", {})
    rigged_glb_url = result_obj.get("rigged_character_glb_url")
    rigged_fbx_url = result_obj.get("rigged_character_fbx_url")
    basic_anims = result_obj.get("basic_animations", {})

    print(f"Rigging succeeded! Rigged GLB: {rigged_glb_url}")
    if rigged_glb_url:
        download_file(rigged_glb_url, OUTPUT_DIR / "anime_girl_rigged.glb")
    if rigged_fbx_url:
        download_file(rigged_fbx_url, OUTPUT_DIR / "anime_girl_rigged.fbx")

    for name, a_url in basic_anims.items():
        if isinstance(a_url, str) and a_url.startswith("http"):
            download_file(a_url, OUTPUT_DIR / f"basic_anim_{name}.glb")

    manifest = {
        "rig_task_id": rig_task_id,
        "rigged_glb_url": rigged_glb_url,
        "rigged_fbx_url": rigged_fbx_url,
        "basic_animations": basic_anims
    }
    with open(OUTPUT_DIR / "step2_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return rig_task_id


def step3_animate(rig_task_id: str, action_id: int = 28):
    print("\n" + "="*60)
    print(f"STEP 3: MESHY ANIMATION (Action ID: {action_id} - Big Wave Hello)")
    print("="*60)

    anim_payload = {
        "rig_task_id": rig_task_id,
        "action_id": action_id,
        "post_process": {
            "operation_type": "change_fps",
            "fps": 30
        }
    }
    print("Submitting Animation task...")
    res = post_json("/openapi/v1/animations", anim_payload)
    anim_task_id = res["result"]
    print(f"Animation task ID: {anim_task_id}")

    anim_res = poll_task("/openapi/v1/animations", anim_task_id, f"Meshy Animation (Action {action_id})")
    result_obj = anim_res.get("result", {})
    anim_glb_url = result_obj.get("animation_glb_url")
    anim_fbx_url = result_obj.get("animation_fbx_url") or result_obj.get("processed_animation_fps_fbx_url")

    print(f"Animation succeeded! Animated GLB URL: {anim_glb_url}")
    local_anim_glb = OUTPUT_DIR / f"anime_girl_anim_{action_id}.glb"
    if anim_glb_url:
        download_file(anim_glb_url, local_anim_glb)
    if anim_fbx_url:
        download_file(anim_fbx_url, OUTPUT_DIR / f"anime_girl_anim_{action_id}.fbx")

    manifest = {
        "anim_task_id": anim_task_id,
        "action_id": action_id,
        "anim_glb_url": anim_glb_url,
        "anim_fbx_url": anim_fbx_url,
        "local_anim_glb": str(local_anim_glb)
    }
    with open(OUTPUT_DIR / "step3_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    return local_anim_glb


def step4_render_blender(anim_glb_path: Path):
    print("\n" + "="*60)
    print("STEP 4: BLENDER 4.5 STUDIO RENDERING (EEVEE Next)")
    print("="*60)

    blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    script_path = Path(__file__).parent / "render_blender_video.py"
    output_mp4 = OUTPUT_DIR / "anime_girl_wave.mp4"

    cmd = [
        blender_exe,
        "-b",
        "--python", str(script_path),
        "--",
        str(anim_glb_path),
        str(output_mp4),
        "1080",
        "1080"
    ]
    print(f"Running Blender render: {' '.join(cmd)}")
    import subprocess
    result = subprocess.run(cmd, capture_output=True, text=True)
    print(result.stdout[-1500:] if len(result.stdout) > 1500 else result.stdout)
    if result.returncode != 0:
        print("[Blender Error Output]:", result.stderr)
        raise RuntimeError(f"Blender render failed with code {result.returncode}")

    print(f"\nRendered video saved to: {output_mp4} ({output_mp4.stat().st_size / 1024 / 1024:.2f} MB)")

    # Also generate a smooth animated GIF via FFmpeg for rich visual preview
    output_gif = OUTPUT_DIR / "anime_girl_wave.gif"
    ffmpeg_exe = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.EXE"
    if os.path.exists(ffmpeg_exe):
        print(f"Generating preview GIF via FFmpeg: {output_gif}")
        gif_cmd = [
            ffmpeg_exe, "-y", "-i", str(output_mp4),
            "-vf", "fps=20,scale=512:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            str(output_gif)
        ]
        subprocess.run(gif_cmd, capture_output=True)
        if output_gif.exists():
            print(f"Preview GIF generated: {output_gif} ({output_gif.stat().st_size / 1024 / 1024:.2f} MB)")

    return output_mp4, output_gif


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Meshy AI Anime Girl Pipeline")
    parser.add_argument("--preview-id", type=str, default=None, help="Existing Preview task ID")
    parser.add_argument("--action-id", type=int, default=28, help="Meshy animation action ID (default 28: Big Wave Hello)")
    args = parser.parse_args()

    print("Starting Anime Girl 3D Generation Pipeline via Meshy AI...")
    refine_id, glb_url = step1_text_to_3d(existing_preview_id=args.preview_id)
    rig_id = step2_auto_rig(refine_id, glb_url)
    anim_path = step3_animate(rig_id, action_id=args.action_id)
    mp4_path, gif_path = step4_render_blender(anim_path)

    print("\n" + "="*60)
    print("ALL PIPELINE STEPS COMPLETED!")
    print(f"1. Textured Model: {OUTPUT_DIR / 'anime_girl_textured.glb'}")
    print(f"2. Rigged Model:   {OUTPUT_DIR / 'anime_girl_rigged.glb'}")
    print(f"3. Animated Model: {anim_path}")
    print(f"4. Rendered Video: {mp4_path}")
    print(f"5. Preview GIF:    {gif_path}")
    print("="*60)

