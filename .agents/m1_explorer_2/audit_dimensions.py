import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"{'ID':<30} | {'Scientific Name':<28} | {'H (m)':<6} | {'H Range (m)':<12} | {'Spread (m)':<10} | {'Trunk (m)':<10}")
print("-" * 105)

for sp in data["species"]:
    dim = sp["dimensions"]
    h = dim["height_m"]
    hr = str(dim.get("height_range_m", "N/A"))
    s = dim["canopy_spread_m"]
    t = dim["trunk_stem_diameter_m"]
    print(f"{sp['species_id']:<30} | {sp['scientific_name']:<28} | {h:<6.2f} | {hr:<12} | {s:<10.2f} | {t:<10.2f}")
