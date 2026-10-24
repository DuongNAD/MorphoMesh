import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

target_ids = [
    "veg_tree_willow_01",
    "veg_tree_beech_01",
    "veg_conifer_spruce_01",
    "veg_conifer_cypress_01",
    "veg_ground_moss_01",
    "veg_epiphyte_spanishmoss_01"
]

for sp in data["species"]:
    if sp["species_id"] in target_ids:
        print(f"=== {sp['species_id']} ({sp['common_name']}) ===")
        print(sp["meshy_spec"]["positive_prompt"])
        print()
