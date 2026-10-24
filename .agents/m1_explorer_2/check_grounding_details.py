import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

for i, sp in enumerate(data["species"], 1):
    pos = sp["meshy_spec"]["positive_prompt"]
    # Check for grounding phrasing
    ground_phrases = [
        "from ground base", "rooted at ground", "rooted in ground", "on ground",
        "rooted on ground", "rooted in forest", "rooted in woodland", "from dry ground",
        "rooted in rocky ground", "on desert gravel", "rooted in arid ground",
        "grounded at base", "growing naturally from ground", "growing directly on ground",
        "visible at base", "at base", "ground level"
    ]
    matched = [p for p in ground_phrases if p in pos.lower()]
    print(f"[{i:02d}] {sp['species_id']}: Matched phrases: {matched}")
    if not matched:
        print(f"     --> LACKS EXPLICIT GROUND PHRASE: \"{pos[:90]}...\"")
