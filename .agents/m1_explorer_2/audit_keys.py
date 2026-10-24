import json
from pathlib import Path
from collections import Counter

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

morphology_keys = Counter()
dimensions_keys = Counter()
meshy_spec_keys = Counter()
verification_keys = Counter()
species_top_keys = Counter()

for sp in data["species"]:
    species_top_keys.update(sp.keys())
    dimensions_keys.update(sp.get("dimensions", {}).keys())
    morphology_keys.update(sp.get("morphology", {}).keys())
    meshy_spec_keys.update(sp.get("meshy_spec", {}).keys())
    verification_keys.update(sp.get("verification", {}).keys())

print("Top-level keys:", species_top_keys)
print("Dimensions keys:", dimensions_keys)
print("Morphology keys:", morphology_keys)
print("Meshy spec keys:", meshy_spec_keys)
print("Verification keys:", verification_keys)
