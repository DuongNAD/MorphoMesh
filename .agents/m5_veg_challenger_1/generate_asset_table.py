"""
Generate markdown verification table from asset_metrics.json
"""
import json
from pathlib import Path

metrics_file = Path(__file__).parent / "asset_metrics.json"
with open(metrics_file, "r", encoding="utf-8") as f:
    data = json.load(f)

lines = []
lines.append("| Species ID | Category | Target H (m) | Measured H (m) | Dev (%) | Z_min (m) | Base Offset (m) | Verts | Rigging Invariants | 20/20 Checks |")
lines.append("|---|---|---|---|---|---|---|---|---|---|")

for r in data:
    sp_id = r["species_id"]
    cat = r["category"]
    th = f"{r['target_h']:.2f}"
    mh = f"{r['measured_h']:.2f}"
    dev = f"{r['dev_pct']:.2f}%"
    z_min = f"{r['z_min']:.4f}"
    offset = f"{r['base_offset']:.4f}"
    verts = f"{r['n_verts']:,}"
    rig = "PASS (0)" if (r["n_skins"] == 0 and r["n_anims"] == 0 and r["node_skins"] == 0 and r["joint_weight_attrs"] == 0 and r["obj_bones"] == 0) else "FAIL"
    val = "PASS (20/20)" if (r["is_valid"] and r["checks_passed"] == 20) else f"FAIL ({r['checks_passed']}/20)"
    lines.append(f"| `{sp_id}` | {cat} | {th} | {mh} | {dev} | {z_min} | {offset} | {verts} | {rig} | {val} |")

out_table = Path(__file__).parent / "asset_table.md"
with open(out_table, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")

print(f"Wrote {len(data)} asset rows to {out_table}")
