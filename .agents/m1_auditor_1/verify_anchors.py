import json
from pathlib import Path

p = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\vegetation_pipeline\taxonomy_catalog.json")
with open(p, "r", encoding="utf-8") as f:
    d = json.load(f)

checks = [
    ("veg_tree_willow_01", "growing naturally from ground base"),
    ("veg_tree_beech_01", "growing naturally from ground base"),
    ("veg_conifer_spruce_01", "rooted naturally at ground base"),
    ("veg_conifer_cypress_01", "growing naturally from ground base"),
    ("veg_ground_moss_01", "resting naturally on forest ground base"),
    ("veg_epiphyte_spanishmoss_01", "rooted at ground base with vertical self-supporting form"),
]

for sid, expected in checks:
    sp = next(s for s in d["species"] if s["species_id"] == sid)
    assert expected in sp["meshy_spec"]["positive_prompt"], f"{sid} missing {expected}"
    print(f"CONFIRMED: {sid} matches expected grounding prefix '{expected}'")

print("ALL 6 GROUND ANCHORS 100% MATCH EXPLORER 2 SPECIFICATION!")
