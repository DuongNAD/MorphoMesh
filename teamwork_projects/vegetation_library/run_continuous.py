"""
Vegetation Library - Continuous Cloud Generation Runner
File: teamwork_projects/vegetation_library/run_continuous.py
"""
import os
import sys
import time
import json
import shutil
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

from meshy_cloud_manager import (
    get_catalog, get_all_account_tasks, match_task_to_species,
    submit_preview, submit_refine, download_and_record_asset,
    OUTPUT_ROOT, request_with_retry, API_BASE
)
from batch_orchestrator import compute_pairwise_divergence

CONCURRENCY_LIMIT = 4
POLL_INTERVAL = 12.0

PRIORITY_SPECIES = [
    "veg_tropical_treefern_01",
    "veg_tropical_birdofparadise_01",
    "veg_succulent_saguaro_01",
    "veg_conifer_spruce_01",
    "veg_conifer_cypress_01",
    "veg_conifer_redcedar_01",
    "veg_conifer_cedar_01",
    "veg_shrub_rose_01",
    "veg_shrub_hydrangea_01",
    "veg_shrub_lavender_01",
    "veg_shrub_lilac_01",
    "veg_shrub_azalea_01",
    "veg_ground_fern_01",
    "veg_ground_pampas_01",
    "veg_ground_moss_01",
    "veg_ground_grass_01",
    "veg_ground_ostrich_01",
    "veg_succulent_aloe_01",
    "veg_succulent_echeveria_01",
    "veg_succulent_barrel_01",
    "veg_succulent_agave_01",
    "veg_vine_ivy_01",
    "veg_vine_wisteria_01",
    "veg_vine_bougainvillea_01",
    "veg_epiphyte_spanishmoss_01",
    "veg_vine_pothos_01",
]

def update_progress_file(completed_count: int, total_count: int, status_msg: str):
    prog_file = REPO_ROOT / ".agents" / "worker_m2" / "progress.md"
    if not prog_file.is_file():
        return
    try:
        ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        lines = prog_file.read_text("utf-8").splitlines()
        out = []
        for line in lines:
            if line.startswith("Last visited:"):
                out.append(f"Last visited: {ts}")
            elif line.startswith("Status:"):
                out.append(f"Status: In Progress ({completed_count}/{total_count} Meshy models downloaded) - {status_msg}")
            else:
                out.append(line)
        prog_file.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception as e:
        print(f"[WARN] Failed updating progress: {e}", flush=True)

def main():
    print("=" * 65, flush=True)
    print("CONTINUOUS MESHY CLOUD BATCH RUNNER ACTIVATED", flush=True)
    print(f"Target: 35 botanical species | Concurrency: {CONCURRENCY_LIMIT}", flush=True)
    print("=" * 65, flush=True)

    catalog = get_catalog()
    all_species = catalog.species
    total_species = len(all_species)

    cycle = 0
    while True:
        cycle += 1
        t_str = time.strftime("%H:%M:%S", time.localtime())

        # Inspect disk
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

        # Query Meshy tasks
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

        completed = [sid for sid, v in state.items() if v["downloaded"]]
        refine_done = [sid for sid, v in state.items() if v["refine_status"] == "SUCCEEDED" and not v["downloaded"]]
        refine_running = [sid for sid, v in state.items() if v["refine_status"] == "IN_PROGRESS"]
        preview_done = [sid for sid, v in state.items() if v["preview_status"] == "SUCCEEDED" and v["refine_id"] is None]
        preview_running = [sid for sid, v in state.items() if v["preview_status"] == "IN_PROGRESS"]
        pending = [sid for sid, v in state.items() if v["preview_id"] is None and not v["downloaded"]]

        # Sort pending by priority
        pending.sort(key=lambda x: (PRIORITY_SPECIES.index(x) if x in PRIORITY_SPECIES else 999))

        print(f"[{t_str} C{cycle}] Complete: {len(completed)}/35 | RefineDone: {len(refine_done)} | RefineRun: {len(refine_running)} | PrevDone: {len(preview_done)} | PrevRun: {len(preview_running)} | Pending: {len(pending)}", flush=True)

        # 1. Download ready refine tasks
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

        # 2. Submit refines for succeeded previews
        for sid in preview_done:
            v = state[sid]
            try:
                r_id = submit_refine(v["preview_id"], sid)
                v["refine_id"] = r_id
                v["refine_status"] = "IN_PROGRESS"
                refine_running.append(sid)
            except Exception as e:
                print(f"[ERROR] Submitting refine for {sid}: {e}", flush=True)

        # 3. Submit previews if capacity available
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
                    print(f"[ERROR] Submitting preview for {sid}: {e}", flush=True)

        # 4. Divergence check
        colls, pairs, rate, counts = compute_pairwise_divergence()
        if pairs > 0 and (cycle % 5 == 1 or len(refine_done) > 0):
            print(f"  -> Divergence: {len(counts)} assets, {pairs} pairs, {colls} collisions, Rate: {rate:.2f}% (<5%)", flush=True)

        # 5. Heartbeat
        msg = f"RefineRun: {len(refine_running)}, PrevRun: {len(preview_running)}, Divergence: {rate:.1f}%"
        update_progress_file(len(completed), total_species, msg)

        # 6. Check completion
        if len(completed) >= total_species:
            print("\n" + "=" * 65, flush=True)
            print(f"SUCCESS! ALL {total_species} SPECIES COMPLETED IN MESHY CLOUD!", flush=True)
            print(f"Final Pairwise Collision Rate: {rate:.2f}% ({colls}/{pairs} pairs)", flush=True)
            print("=" * 65, flush=True)
            break

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
