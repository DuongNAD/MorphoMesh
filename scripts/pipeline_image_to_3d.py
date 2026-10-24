"""
End-to-end Image-to-3D pipeline for Anime Girl using Meshy AI + Blender 4.5
"""

import os
import sys
import time
import json
import base64
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
API_KEY = os.environ.get("MESHY_API_KEY")
if not API_KEY:
    print("Error: MESHY_API_KEY not found!")
    sys.exit(1)

API_BASE = "https://api.meshy.ai"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "User-Agent": "MorphoMesh-Pipeline/2.0"
}

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "anime_girl_v2"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ART_DIR = Path(r"C:\Users\Admin\.gemini\antigravity\brain\c6634b96-78a4-4cad-9283-f7f70e7bb3a4")


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
    print(f"Downloading: {url[:80]}... -> {dest_path.name}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as f:
        f.write(resp.read())
    print(f"Saved: {dest_path.name} ({dest_path.stat().st_size / 1024 / 1024:.2f} MB)")


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


def step1_poll_image_to_3d(task_id: str):
    print("\n" + "="*60)
    print("STEP 1: IMAGE-TO-3D RECONSTRUCTION (Meshy-6)")
    print("="*60)

    res = poll_task("/openapi/v1/image-to-3d", task_id, "Image-to-3D")
    model_urls = res.get("model_urls", {})
    glb_url = model_urls.get("glb")
    print(f"Textured Model URL: {glb_url}")

    local_glb = OUTPUT_DIR / "anime_girl_textured.glb"
    if glb_url:
        download_file(glb_url, local_glb)

    with open(OUTPUT_DIR / "step1_manifest.json", "w") as f:
        json.dump(res, f, indent=2)

    return task_id, glb_url, local_glb


def step2_auto_rig(image_task_id: str):
    print("\n" + "="*60)
    print("STEP 2: HUMANOID AUTO-RIGGING")
    print("="*60)

    rig_payload = {
        "input_task_id": image_task_id,
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

    local_rigged_glb = OUTPUT_DIR / "anime_girl_rigged.glb"
    if rigged_glb_url:
        download_file(rigged_glb_url, local_rigged_glb)
    if rigged_fbx_url:
        download_file(rigged_fbx_url, OUTPUT_DIR / "anime_girl_rigged.fbx")

    with open(OUTPUT_DIR / "step2_manifest.json", "w") as f:
        json.dump(rig_res, f, indent=2)

    return rig_task_id, local_rigged_glb


def step3_animate(rig_task_id: str, action_id: int = 28):
    print("\n" + "="*60)
    print(f"STEP 3: ANIMATION RETARGETING (Action {action_id} - Big Wave Hello)")
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

    anim_res = poll_task("/openapi/v1/animations", anim_task_id, f"Animation Action {action_id}")
    result_obj = anim_res.get("result", {})
    anim_glb_url = result_obj.get("animation_glb_url")

    local_anim_glb = OUTPUT_DIR / f"anime_girl_anim_{action_id}.glb"
    if anim_glb_url:
        download_file(anim_glb_url, local_anim_glb)

    with open(OUTPUT_DIR / "step3_manifest.json", "w") as f:
        json.dump(anim_res, f, indent=2)

    return local_anim_glb


def step4_render_blender(anim_glb: Path):
    print("\n" + "="*60)
    print("STEP 4: BLENDER 4.5 STUDIO RENDERING (EEVEE Next)")
    print("="*60)

    blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
    out_mp4 = OUTPUT_DIR / "anime_girl_perfect_wave.mp4"

    # Inline Blender script for seamless render
    blender_render_script = f"""
import bpy, math, mathutils

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=r"{str(anim_glb).replace(chr(92), '/')}")
scene = bpy.context.scene

# Evaluated bounds at frame 30
scene.frame_set(30)
mesh = [obj for obj in scene.objects if obj.type == 'MESH'][0]
dg = bpy.context.evaluated_depsgraph_get()
eval_obj = mesh.evaluated_get(dg)
eval_mesh = eval_obj.to_mesh()
verts = [eval_obj.matrix_world @ v.co for v in eval_mesh.vertices]
min_z = min(v.z for v in verts)
max_z = max(v.z for v in verts)
min_y = min(v.y for v in verts)
max_y = max(v.y for v in verts)
min_x = min(v.x for v in verts)
max_x = max(v.x for v in verts)
eval_obj.to_mesh_clear()

height = max_z - min_z
center_x = (min_x + max_x) / 2.0
center_y = (min_y + max_y) / 2.0
center_z = (min_z + max_z) / 2.0

# Frame range
start_frame = 1
end_frame = 60
if bpy.data.actions:
    for act in bpy.data.actions:
        start_frame = min(start_frame, int(act.frame_range[0]))
        end_frame = max(end_frame, int(act.frame_range[1]))
end_frame = min(end_frame, 150)
scene.frame_start = start_frame
scene.frame_end = end_frame
scene.render.fps = 30

# Studio World & Floor
studio_color = (0.11, 0.12, 0.15, 1.0)
scene.world = bpy.data.worlds.new('World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = studio_color
scene.world.node_tree.nodes['Background'].inputs[1].default_value = 1.0

bpy.ops.mesh.primitive_plane_add(size=30, location=(center_x, center_y, min_z - 0.02))
floor = bpy.context.active_object
mat = bpy.data.materials.new('StudioFloor')
mat.use_nodes = True
bsdf = mat.node_tree.nodes.get('Principled BSDF')
bsdf.inputs['Base Color'].default_value = studio_color
bsdf.inputs['Roughness'].default_value = 0.5
floor.data.materials.append(mat)

# Target
target = bpy.data.objects.new('Target', None)
scene.collection.objects.link(target)
target.location = (center_x, center_y, center_z)

# Camera with subtle orbit
cam_data = bpy.data.cameras.new('Cam')
cam_data.lens = 55.0
cam_obj = bpy.data.objects.new('Cam', cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

dist = height * 1.85
total_f = end_frame - start_frame + 1
for i in range(total_f):
    f = start_frame + i
    t = i / max(total_f - 1, 1)
    ang = math.radians(-10.0 + 20.0 * math.sin(t * math.pi))
    cx = center_x + dist * math.sin(ang)
    cy = center_y - dist * math.cos(ang)
    cz = center_z + 0.12
    cam_obj.location = (cx, cy, cz)
    cam_obj.keyframe_insert(data_path="location", frame=f)

ttc = cam_obj.constraints.new('TRACK_TO')
ttc.target = target
ttc.track_axis = 'TRACK_NEGATIVE_Z'
ttc.up_axis = 'UP_Y'

# Studio 3-point Lighting
key_data = bpy.data.lights.new('Key', 'AREA')
key_data.energy = 650.0
key_data.size = 2.0
key_data.color = (1.0, 0.96, 0.92)
key_obj = bpy.data.objects.new('Key', key_data)
scene.collection.objects.link(key_obj)
key_obj.location = (center_x + 1.8, center_y - 2.2, center_z + 1.5)
key_obj.constraints.new('TRACK_TO').target = target

fill_data = bpy.data.lights.new('Fill', 'AREA')
fill_data.energy = 280.0
fill_data.size = 2.5
fill_data.color = (0.88, 0.93, 1.0)
fill_obj = bpy.data.objects.new('Fill', fill_data)
scene.collection.objects.link(fill_obj)
fill_obj.location = (center_x - 2.2, center_y - 1.8, center_z + 0.8)
fill_obj.constraints.new('TRACK_TO').target = target

rim_data = bpy.data.lights.new('Rim', 'AREA')
rim_data.energy = 550.0
rim_data.size = 1.5
rim_data.color = (1.0, 0.88, 0.78)
rim_obj = bpy.data.objects.new('Rim', rim_data)
scene.collection.objects.link(rim_obj)
rim_obj.location = (center_x + 0.4, center_y + 1.9, center_z + 1.3)
rim_obj.constraints.new('TRACK_TO').target = target

# Render settings
scene.render.engine = 'BLENDER_EEVEE_NEXT'
scene.render.resolution_x = 1080
scene.render.resolution_y = 1080
scene.render.image_settings.file_format = 'FFMPEG'
scene.render.ffmpeg.format = 'MPEG4'
scene.render.ffmpeg.codec = 'H264'
scene.render.ffmpeg.constant_rate_factor = 'HIGH'
scene.render.ffmpeg.ffmpeg_preset = 'GOOD'
scene.render.filepath = r"{str(out_mp4).replace(chr(92), '/')}"

print('Rendering animation frames...')
bpy.ops.render.render(animation=True)
print('Blender render complete!')
"""
    tmp_script = OUTPUT_DIR / "temp_render.py"
    tmp_script.write_text(blender_render_script, encoding="utf-8")

    cmd = [blender_exe, "-b", "--python", str(tmp_script)]
    subprocess.run(cmd, check=True)

    print(f"Rendered video: {out_mp4} ({out_mp4.stat().st_size / 1024 / 1024:.2f} MB)")

    # Copy to artifacts
    art_mp4 = ART_DIR / "anime_girl_perfect_wave.mp4"
    import shutil
    shutil.copy2(out_mp4, art_mp4)

    # Convert to GIF for instant chat viewing
    art_gif = ART_DIR / "anime_girl_perfect_wave.gif"
    ffmpeg_exe = r"C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.EXE"
    if os.path.exists(ffmpeg_exe):
        gif_cmd = [
            ffmpeg_exe, "-y", "-i", str(out_mp4),
            "-vf", "fps=20,scale=512:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            str(art_gif)
        ]
        subprocess.run(gif_cmd, capture_output=True)
        print(f"Generated GIF: {art_gif} ({art_gif.stat().st_size / 1024 / 1024:.2f} MB)")

    return out_mp4, art_gif


if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else "01a08628-c7fd-7665-a843-8361731032ed"
    print(f"Starting Image-to-3D pipeline with task {task_id}...")

    _, glb_url, local_glb = step1_poll_image_to_3d(task_id)
    rig_id, local_rigged = step2_auto_rig(task_id)
    anim_glb = step3_animate(rig_id, action_id=28)
    out_mp4, out_gif = step4_render_blender(anim_glb)

    print("\n" + "="*60)
    print("ALL STEPS COMPLETED!")
    print(f"MP4: {out_mp4}")
    print(f"GIF: {out_gif}")
    print("="*60)
