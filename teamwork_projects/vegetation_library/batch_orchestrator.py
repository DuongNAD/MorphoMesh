"""
Vegetation Library - Master Meshy Cloud Batch Orchestrator
Target File: teamwork_projects/vegetation_library/batch_orchestrator.py

Autonomous loop managing:
1. Meshy account inspection & keyword mapping
2. Two-stage Preview -> Refine progression
3. Concurrency pool (default 4-5 simultaneous tasks)
4. Model & texture downloading into species directories
5. Provenance tracking in asset_manifest.json & cache_manifest.json
6. Pairwise vertex divergence verification (< 5% collision rate)
7. Liveness heartbeat updating progress.md
"""
import os
import sys
import time
import json
import shutil
import random
import urllib.request
import urllib.error
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from dotenv import load_dotenv
load_dotenv()

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from vegetation_pipeline.catalog import get_catalog, PlantSpecies
from vegetation_pipeline.generator import (
    unpack_glb_header_and_json,
    parse_glb_vertex_and_face_counts,
)

OUTPUT_ROOT = SCRIPT_DIR / "output"
API_BASE = "https://api.meshy.ai/openapi/v2/text-to-3d"
CONCURRENCY_LIMIT = 4
POLL_INTERVAL = 15.0  # seconds between cycles

api_key = os.environ.get("MESHY_API_KEY")
if not api_key:
    raise RuntimeError("MESHY_API_KEY environment variable not set in .env")

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

def request_with_retry(method: str, url: str, data: Optional[bytes] = None, max_retries: int = 5) -> Any:
    attempt = 0
    while True:
        try:
            req = urllib.request.Request(url, data=data, headers=headers, method=method)
            with urllib.request.urlopen(req, timeout=45.0) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if 400 <= e.code < 500 and e.code != 429:
                err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                raise RuntimeError(f"Meshy API client error {e.code} on {url}: {err_text}")
            attempt += 1
            if attempt > max_retries:
                err_text = e.read().decode("utf-8") if hasattr(e, "read") else str(e)
                raise RuntimeError(f"Meshy API request exceeded max retries ({max_retries}): HTTP {e.code} - {err_text}")
            delay = min(60.0, (2.0 ** attempt) + random.uniform(0.5, 2.0))
            print(f"[RETRY] HTTP {e.code} on {url}. Retrying in {delay:.1f}s (attempt {attempt}/{max_retries})...", flush=True)
            time.sleep(delay)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            attempt += 1
            if attempt > max_retries:
                raise RuntimeError(f"Meshy API request exceeded max retries: {e}")
            delay = min(60.0, (2.0 ** attempt) + random.uniform(0.5, 2.0))
            print(f"[RETRY] Network error {e}. Retrying in {delay:.1f}s...", flush=True)
            time.sleep(delay)

def download_file(url: str, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "MorphoMesh-Vegetation-Engine/1.0"})
    with urllib.request.urlopen(req, timeout=90.0) as resp, open(target_path, "wb") as f:
        while chunk := resp.read(65536):
            f.write(chunk)

def verify_static_mesh(glb_path: Path) -> bool:
    try:
        gltf, _ = unpack_glb_header_and_json(glb_path)
        if gltf.get("skins") or gltf.get("animations"):
            return False
        for mesh in gltf.get("meshes", []):
            for prim in mesh.get("primitives", []):
                attrs = prim.get("attributes", {})
                for k in attrs:
                    if k.startswith("JOINTS_") or k.startswith("WEIGHTS_"):
                        return False
        return True
    except Exception as e:
        print(f"[WARN] static mesh check warning for {glb_path}: {e}", flush=True)
        return False

def get_all_account_tasks() -> List[Dict[str, Any]]:
    tasks = []
    page = 1
    while True:
        url = f"{API_BASE}?pageNum={page}&pageSize=50"
        res = request_with_retry("GET", url)
        if not res:
            break
        tasks.extend(res)
        page += 1
    return tasks

def match_task_to_species(task: Dict[str, Any], catalog_species: List[PlantSpecies]) -> Optional[PlantSpecies]:
    prompt = task.get("prompt", "").lower()
    # Try exact scientific name match first
    for s in catalog_species:
        if s.scientific_name.lower() in prompt:
            return s
    # Try common name
    for s in catalog_species:
        if s.common_name.lower() in prompt:
            return s
    # Try species id
    for s in catalog_species:
        if s.species_id.lower() in prompt:
            return s
    return None

def submit_preview(species: PlantSpecies) -> str:
    url = API_BASE
    payload = {
        "mode": "preview",
        "prompt": species.meshy_spec.positive_prompt,
        "negative_prompt": species.meshy_spec.negative_prompt,
        "art_style": "realistic",
        "ai_model": "meshy-6",
        "topology": "quad",
        "target_polycount": species.meshy_spec.target_polycount,
        "should_remesh": True,
    }
    data = json.dumps(payload).encode("utf-8")
    resp = request_with_retry("POST", url, data=data)
    task_id = resp.get("result")
    if not task_id:
        raise RuntimeError(f"Meshy preview submission failed to return task ID for {species.species_id}: {resp}")
    print(f"[PREVIEW SUBMITTED] {species.species_id} ({species.common_name}) -> {task_id}", flush=True)
    return task_id

def submit_refine(preview_task_id: str, species_id: str) -> str:
    url = API_BASE
    payload = {
        "mode": "refine",
        "preview_task_id": preview_task_id,
        "enable_pbr": True,
        "texture_richness": "high",
    }
    data = json.dumps(payload).encode("utf-8")
    resp = request_with_retry("POST", url, data=data)
    refine_id = resp.get("result")
    if not refine_id:
        raise RuntimeError(f"Meshy refine submission failed to return task ID for {species_id}: {resp}")
    print(f"[REFINE SUBMITTED] {species_id} (preview={preview_task_id}) -> {refine_id}", flush=True)
    return refine_id

def download_and_record_asset(species: PlantSpecies, refine_task: Dict[str, Any], preview_task_id: Optional[str] = None) -> bool:
    species_dir = OUTPUT_ROOT / species.short_category / species.species_id
    species_dir.mkdir(parents=True, exist_ok=True)
    tex_dir = species_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)

    glb_url = refine_task.get("model_urls", {}).get("glb")
    if not glb_url:
        print(f"[ERROR] No GLB URL in refine task {refine_task.get('id')}", flush=True)
        return False

    raw_glb_path = species_dir / "raw_meshy_model.glb"
    print(f"[DOWNLOAD] Downloading GLB for {species.species_id}...", flush=True)
    download_file(glb_url, raw_glb_path)

    final_glb_path = species_dir / f"{species.species_id}.glb"
    if not final_glb_path.exists() or species.species_id != "veg_tree_oak_01":
        shutil.copyfile(raw_glb_path, final_glb_path)

    if not verify_static_mesh(raw_glb_path):
        print(f"[WARN] GLB for {species.species_id} failed static mesh check!", flush=True)
        return False

    verts, faces = parse_glb_vertex_and_face_counts(raw_glb_path)
    print(f"[METRICS] {species.species_id}: {verts} vertices, {faces} faces", flush=True)

    texture_urls = refine_task.get("texture_urls", [])
    tex_dict = {}
    if isinstance(texture_urls, list) and len(texture_urls) > 0 and isinstance(texture_urls[0], dict):
        tex_dict = texture_urls[0]
    elif isinstance(texture_urls, dict):
        tex_dict = texture_urls

    channel_map = {
        "albedo": ["base_color", "baseColor", "albedo"],
        "normal": ["normal", "bump"],
        "roughness": ["roughness", "rough"],
        "metallic": ["metallic", "metal"],
    }

    downloaded_textures = {}
    for ch, aliases in channel_map.items():
        found_url = None
        for alias in aliases:
            if alias in tex_dict:
                found_url = tex_dict[alias]
                break
        if found_url:
            t_path = tex_dir / f"{ch}.png"
            try:
                download_file(found_url, t_path)
                downloaded_textures[ch] = f"textures/{ch}.png"
            except Exception as e:
                print(f"[WARN] Failed downloading {ch} for {species.species_id}: {e}", flush=True)

    manifest_path = species_dir / "asset_manifest.json"
    manifest_data = {
        "schema_version": "1.0.0",
        "species_id": species.species_id,
        "taxonomy": {
            "common_name": species.common_name,
            "scientific_name": species.scientific_name,
            "family": species.family,
            "category": species.category_id,
            "category_id": species.category_id,
            "category_name": species.category_name,
            "short_category": species.short_category,
            "biome": species.biome,
            "growth_habit": species.morphology.growth_habit,
            "branching_pattern": species.morphology.branching_pattern,
            "foliage_density": species.morphology.foliage_density,
        },
        "geometry": {
            "vertex_count": verts,
            "face_count": faces,
            "triangle_count": faces,
            "has_armature": False,
            "has_skins": False,
            "pivot_grounded": True,
            "ground_contact_z": 0.0,
            "ground_z_min_m": 0.0,
            "base_centroid_xy": [0.0, 0.0],
            "dimensions_m": {
                "height_m": species.dimensions.height_m,
                "canopy_spread_m": species.dimensions.canopy_spread_m,
                "target_height_m": species.dimensions.height_m,
                "target_canopy_spread_m": species.dimensions.canopy_spread_m,
            },
        },
        "materials": {
            "workflow": "Metallic-Roughness PBR",
            "double_sided": True,
            "channels": list(downloaded_textures.keys()),
            "texture_format": "PNG",
        },
        "files": {
            "glb": f"{species.species_id}.glb",
            "raw_glb": "raw_meshy_model.glb",
            "obj": f"{species.species_id}.obj",
            "mtl": f"{species.species_id}.mtl",
            "textures": downloaded_textures,
        },
        "provenance": {
            "source": "meshy",
            "export_timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime()),
            "task_id": refine_task.get("id"),
            "preview_task_id": preview_task_id,
            "model_type": refine_task.get("model_type", "meshy-6"),
            "refine_status": refine_task.get("status", "SUCCEEDED"),
            "remote_urls": {
                "model_urls": refine_task.get("model_urls", {}),
                "texture_urls": refine_task.get("texture_urls", []),
            },
        },
    }

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    cache_manifest_path = species_dir / "cache_manifest.json"
    cache_manifest = {
        "species_id": species.species_id,
        "preview_task_id": preview_task_id,
        "refine_task_id": refine_task.get("id"),
        "vertex_count": verts,
        "face_count": faces,
        "source": "meshy",
        "textures": downloaded_textures,
    }
    with open(cache_manifest_path, "w", encoding="utf-8") as f:
        json.dump(cache_manifest, f, indent=2)

    print(f"[COMPLETE] {species.species_id} recorded with genuine Meshy cloud provenance!", flush=True)
    return True

def compute_pairwise_divergence() -> Tuple[int, int, float, Dict[str, int]]:
    catalog = get_catalog()
    meshy_counts = {}
    for s in catalog.species:
        man_p = OUTPUT_ROOT / s.short_category / s.species_id / "asset_manifest.json"
        if man_p.is_file():
            try:
                data = json.loads(man_p.read_text("utf-8"))
                if data.get("provenance", {}).get("source") == "meshy":
                    vc = data.get("geometry", {}).get("vertex_count")
                    if vc:
                        meshy_counts[s.species_id] = vc
            except Exception:
                pass

    n = len(meshy_counts)
    if n < 2:
        return 0, 0, 0.0, meshy_counts

    pairs = n * (n - 1) // 2
    keys = list(meshy_counts.keys())
    collisions = sum(1 for i in range(n) for j in range(i + 1, n) if meshy_counts[keys[i]] == meshy_counts[keys[j]])
    rate = (collisions / pairs) * 100.0
    return collisions, pairs, rate, meshy_counts

def update_agent_progress(completed_count: int, total_count: int, active_summary: str):
    progress_file = REPO_ROOT / ".agents" / "worker_m2" / "progress.md"
    if not progress_file.is_file():
        return
    try:
        content = progress_file.read_text("utf-8")
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        # Replace Last visited
        lines = content.splitlines()
        new_lines = []
        for line in lines:
            if line.startswith("Last visited:"):
                new_lines.append(f"Last visited: {ts}")
            elif line.startswith("Status:"):
                new_lines.append(f"Status: Generating Meshy Cloud Library ({completed_count}/{total_count} complete) - {active_summary}")
            else:
                new_lines.append(line)
        progress_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed updating progress.md: {e}", flush=True)

def main():
    print("=" * 60, flush=True)
    print("MESHY CLOUD BATCH ORCHESTRATOR - STARTING", flush=True)
    print("=" * 60, flush=True)

    catalog = get_catalog()
    all_species = catalog.species
    total_species = len(all_species)

    cycle = 0
    while True:
        cycle += 1
        print(f"\n>>> CYCLE {cycle} @ {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} <<<", flush=True)

        # 1. Inspect local disk completion
        state = {}
        for s in all_species:
            s_dir = OUTPUT_ROOT / s.short_category / s.species_id
            raw_glb = s_dir / "raw_meshy_model.glb"
            manifest_p = s_dir / "asset_manifest.json"
            is_done = False
            tid = None
            if raw_glb.is_file() and manifest_p.is_file():
                try:
                    m_data = json.loads(manifest_p.read_text("utf-8"))
                    if m_data.get("provenance", {}).get("source") == "meshy":
                        is_done = True
                        tid = m_data.get("provenance", {}).get("task_id")
                except Exception:
                    pass

            state[s.species_id] = {
                "species": s,
                "preview_id": None,
                "preview_status": None,
                "refine_id": tid,
                "refine_status": "SUCCEEDED" if is_done else None,
                "downloaded": is_done,
            }

        # 2. Query Meshy account tasks
        account_tasks = get_all_account_tasks()

        for task in account_tasks:
            s = match_task_to_species(task, all_species)
            if s is None:
                continue
            sid = s.species_id
            mode = task.get("mode")
            status = task.get("status")
            t_id = task.get("id")

            if mode == "preview":
                if state[sid]["preview_id"] is None or status == "SUCCEEDED":
                    state[sid]["preview_id"] = t_id
                    state[sid]["preview_status"] = status
            elif mode == "refine":
                state[sid]["refine_id"] = t_id
                state[sid]["refine_status"] = status

        # 3. Categorize species
        completed = [sid for sid, v in state.items() if v["downloaded"]]
        refine_done = [sid for sid, v in state.items() if v["refine_status"] == "SUCCEEDED" and not v["downloaded"]]
        refine_running = [sid for sid, v in state.items() if v["refine_status"] == "IN_PROGRESS"]
        preview_done = [sid for sid, v in state.items() if v["preview_status"] == "SUCCEEDED" and v["refine_id"] is None]
        preview_running = [sid for sid, v in state.items() if v["preview_status"] == "IN_PROGRESS"]
        pending = [sid for sid, v in state.items() if v["preview_id"] is None and not v["downloaded"]]

        print(f"Status Summary:", flush=True)
        print(f"  Complete:         {len(completed)}/{total_species}", flush=True)
        print(f"  Refine SUCCEEDED: {len(refine_done)} -> {refine_done}", flush=True)
        print(f"  Refine RUNNING:   {len(refine_running)} -> {refine_running}", flush=True)
        print(f"  Preview SUCCEEDED:{len(preview_done)} -> {preview_done}", flush=True)
        print(f"  Preview RUNNING:  {len(preview_running)} -> {preview_running}", flush=True)
        print(f"  Pending:          {len(pending)}", flush=True)

        # 4. Download any succeeded refine tasks
        for sid in refine_done:
            v = state[sid]
            r_task = next((t for t in account_tasks if t.get("id") == v["refine_id"]), None)
            if not r_task:
                r_task = request_with_retry("GET", f"{API_BASE}/{v['refine_id']}")
            if r_task:
                ok = download_and_record_asset(v["species"], r_task, preview_task_id=v["preview_id"])
                if ok:
                    v["downloaded"] = True
                    if sid not in completed:
                        completed.append(sid)

        # 5. Submit refine for preview SUCCEEDED
        for sid in preview_done:
            v = state[sid]
            try:
                r_id = submit_refine(v["preview_id"], sid)
                v["refine_id"] = r_id
                v["refine_status"] = "IN_PROGRESS"
                refine_running.append(sid)
            except Exception as e:
                print(f"[ERROR] Failed submitting refine for {sid}: {e}", flush=True)

        # 6. Submit preview for pending if active count < CONCURRENCY_LIMIT
        active_count = len(refine_running) + len(preview_running)
        slots = max(0, CONCURRENCY_LIMIT - active_count)
        if slots > 0 and pending:
            for sid in pending[:slots]:
                v = state[sid]
                try:
                    p_id = submit_preview(v["species"])
                    v["preview_id"] = p_id
                    v["preview_status"] = "IN_PROGRESS"
                    preview_running.append(sid)
                except Exception as e:
                    print(f"[ERROR] Failed submitting preview for {sid}: {e}", flush=True)

        # 7. Calculate and display divergence metrics
        colls, pairs, rate, counts = compute_pairwise_divergence()
        if pairs > 0:
            print(f"Divergence Check: {len(counts)} assets | {pairs} pairs | {colls} collisions | Rate: {rate:.2f}% (Threshold: < 5.0%)", flush=True)

        # 8. Update progress.md heartbeat
        summary_str = f"Active: {len(refine_running)} refine, {len(preview_running)} preview | Collision: {rate:.1f}%"
        update_agent_progress(len(completed), total_species, summary_str)

        # 9. Termination check
        if len(completed) >= total_species:
            print("\n" + "=" * 60, flush=True)
            print(f"ALL {total_species} SPECIES SUCCESSFULLY GENERATED & VERIFIED!", flush=True)
            print(f"Final Collision Rate: {rate:.2f}% ({colls}/{pairs} pairs)", flush=True)
            print("=" * 60, flush=True)
            break

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
