import json
from pathlib import Path

catalog_path = Path("teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json")
with open(catalog_path, "r", encoding="utf-8") as f:
    data = json.load(f)

targets = [
    "veg_tree_willow_01",
    "veg_tree_beech_01",
    "veg_conifer_spruce_01",
    "veg_conifer_cypress_01",
    "veg_ground_moss_01",
    "veg_epiphyte_spanishmoss_01",
    "veg_tree_oak_01",
    "veg_tropical_palm_01",
    "veg_succulent_saguaro_01",
    "veg_vine_ivy_01"
]

for s in data["species"]:
    if s["species_id"] in targets:
        print(f"=== {s['species_id']} ({s['common_name']}) ===")
        print(f"POSITIVE: {s['meshy_spec']['positive_prompt']}")
        print(f"NEGATIVE (prefix 80 chars): {s['meshy_spec']['negative_prompt'][:80]}...\n")
