import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Schema Version: {data.get('schema_version')}")
print(f"Total Categories: {len(data.get('categories', []))}")
print(f"Total Species: {len(data.get('species', []))}\n")

for cat in data["categories"]:
    print(f"Category: {cat['category_id']} ({cat['display_name']}) - {cat['species_count']} species")

print("\n--- Species List ---")
for i, s in enumerate(data["species"], 1):
    dim = s["dimensions"]
    print(f"{i:2d}. {s['species_id']:<25} | {s['common_name']:<22} | {s['scientific_name']:<24} | Cat: {s['category_id']:<28} | H={dim['height_m']}m Spread={dim['canopy_spread_m']}m")
