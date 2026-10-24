"""
Find which test in tests/ modifies manifest.json
"""
import json
import subprocess
import sys
from pathlib import Path

def get_oak_status():
    manifest_p = Path("teamwork_projects/vegetation_library/output/manifest.json")
    if not manifest_p.exists():
        return "missing_file"
    with open(manifest_p, "r", encoding="utf-8") as f:
        d = json.load(f)
    return d.get("assets", {}).get("veg_tree_oak_01", {}).get("status")

print("Initial status:", get_oak_status())

# Get all test items
cmd = ["uv", "run", "pytest", "teamwork_projects/vegetation_library/tests/", "--collect-only", "-q"]
res = subprocess.run(cmd, capture_output=True, text=True)
test_ids = [line.strip() for line in res.stdout.splitlines() if "::" in line]

print(f"Total collected tests: {len(test_ids)}")

for idx, tid in enumerate(test_ids):
    cmd = ["uv", "run", "pytest", tid, "-q"]
    subprocess.run(cmd, capture_output=True, text=True)
    status = get_oak_status()
    if status == "rendered":
        print(f"FOUND CULPRIT! Test #{idx}: {tid} set status to 'rendered'!")
        break

print("Final status:", get_oak_status())
