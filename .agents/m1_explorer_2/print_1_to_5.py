import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

for i in range(5):
    sp = data['species'][i]
    print(f"[{i+1:02d}] {sp['species_id']} | {sp['common_name']} ({sp['scientific_name']})")
    print(f"     Prompt: {sp['meshy_spec']['positive_prompt']}\n")
