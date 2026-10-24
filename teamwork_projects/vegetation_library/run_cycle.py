# Append loop logic to meshy_cloud_manager.py
import sys
from pathlib import Path
SCRIPT_DIR = Path("teamwork_projects/vegetation_library")
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from meshy_cloud_manager import (
    get_catalog, get_all_account_tasks, match_task_to_species,
    submit_preview, submit_refine, download_and_record_asset,
    parse_glb_vertex_and_face_counts, OUTPUT_ROOT, request_with_retry, API_BASE,
    CONCURRENCY_LIMIT
)

def run_manager_cycle():
    catalog = get_catalog()
    all_species = catalog.species
    print(f"Loaded {len(all_species)} catalog species.", flush=True)

    # State map
    state = {}
    for s in all_species:
        # Check if already completed on disk
        s_dir = OUTPUT_ROOT / s.short_category / s.species_id
        raw_glb = s_dir / "raw_meshy_model.glb"
        manifest_p = s_dir / "asset_manifest.json"
        is_done = False
        tid = None
        if raw_glb.is_file() and manifest_p.is_file():
            try:
                import json
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

    # Query Meshy account tasks
    account_tasks = get_all_account_tasks()
    print(f"Retrieved {len(account_tasks)} tasks from Meshy account.", flush=True)

    # Map account tasks to species
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

    # Summary
    completed = [sid for sid, v in state.items() if v["downloaded"]]
    refine_done = [sid for sid, v in state.items() if v["refine_status"] == "SUCCEEDED" and not v["downloaded"]]
    refine_running = [sid for sid, v in state.items() if v["refine_status"] == "IN_PROGRESS"]
    preview_done = [sid for sid, v in state.items() if v["preview_status"] == "SUCCEEDED" and v["refine_id"] is None]
    preview_running = [sid for sid, v in state.items() if v["preview_status"] == "IN_PROGRESS"]
    pending = [sid for sid, v in state.items() if v["preview_id"] is None and not v["downloaded"]]

    print(f"\n--- MESHY PIPELINE STATE ---", flush=True)
    print(f"Downloaded & Complete: {len(completed)}/35", flush=True)
    print(f"Refine SUCCEEDED (to download): {len(refine_done)}", flush=True)
    print(f"Refine IN_PROGRESS: {len(refine_running)} ({refine_running})", flush=True)
    print(f"Preview SUCCEEDED (to refine): {len(preview_done)} ({preview_done})", flush=True)
    print(f"Preview IN_PROGRESS: {len(preview_running)} ({preview_running})", flush=True)
    print(f"Pending submission: {len(pending)}", flush=True)

    # 1. Download any newly succeeded refine tasks
    for sid in refine_done:
        v = state[sid]
        r_task = next((t for t in account_tasks if t.get("id") == v["refine_id"]), None)
        if not r_task:
            r_task = request_with_retry("GET", f"{API_BASE}/{v['refine_id']}")
        if r_task:
            ok = download_and_record_asset(v["species"], r_task, preview_task_id=v["preview_id"])
            if ok:
                v["downloaded"] = True

    # 2. Submit refine for any preview SUCCEEDED
    for sid in preview_done:
        v = state[sid]
        try:
            r_id = submit_refine(v["preview_id"], sid)
            v["refine_id"] = r_id
            v["refine_status"] = "IN_PROGRESS"
        except Exception as e:
            print(f"[ERROR] Failed submitting refine for {sid}: {e}", flush=True)

    # 3. Submit preview if active tasks < CONCURRENCY_LIMIT
    active_count = len(refine_running) + len(preview_running) + len(preview_done)
    slots = max(0, CONCURRENCY_LIMIT - active_count)
    if slots > 0 and pending:
        for sid in pending[:slots]:
            v = state[sid]
            try:
                p_id = submit_preview(v["species"])
                v["preview_id"] = p_id
                v["preview_status"] = "IN_PROGRESS"
            except Exception as e:
                print(f"[ERROR] Failed submitting preview for {sid}: {e}", flush=True)

if __name__ == "__main__":
    run_manager_cycle()
