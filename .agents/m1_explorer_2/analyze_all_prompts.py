import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"Detailed Analysis of Positive Prompts for 35 Species:\n")

for i, sp in enumerate(data["species"], 1):
    sp_id = sp["species_id"]
    common = sp["common_name"]
    sci = sp["scientific_name"]
    pos = sp["meshy_spec"]["positive_prompt"]
    morph = sp["morphology"]
    
    # Check if common name and scientific name are in prompt
    has_common = common.lower() in pos.lower()
    has_sci = sci.lower() in pos.lower() or sci.split()[0].lower() in pos.lower()
    has_standalone = "standalone" in pos.lower()
    has_base = any(w in pos.lower() for w in ["ground", "root", "base", "soil", "gravel", "floor"])
    has_pbr = "pbr" in pos.lower()
    
    print(f"[{i:02d}] {sp_id} | {common} ({sci})")
    print(f"     Prompt ({len(pos)} chars):")
    print(f"     \"{pos}\"")
    print(f"     Checks: NameMatch={has_common and has_sci}, Standalone={has_standalone}, GroundBase={has_base}, PBR={has_pbr}")
    print()
