import json
from pathlib import Path
import re

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

for i, sp in enumerate(data["species"], 1):
    pos = sp["meshy_spec"]["positive_prompt"]
    # Regex search for grounding in the introductory clause
    m = re.search(r"(ground|soil|gravel|floor|base|earth|rocky ground)", pos[:150], re.IGNORECASE)
    if m:
        print(f"[{i:02d}] {sp['species_id']}: FOUND '{m.group(0)}' in prefix -> {pos[:95]}...")
    else:
        print(f"[{i:02d}] {sp['species_id']}: ** NO GROUNDING WORD IN FIRST 150 CHARS ** -> {pos[:120]}...")
