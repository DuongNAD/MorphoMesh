import json
import sys
from pathlib import Path

# Add project root and vegetation library to sys.path
repo_root = Path("E:/tool/mcp/MorphoMesh")
veg_lib = repo_root / "teamwork_projects" / "vegetation_library"
sys.path.insert(0, str(veg_lib))
sys.path.insert(0, str(repo_root))

from vegetation_pipeline.catalog import get_catalog

cat = get_catalog()
print(f"Total Species: {len(cat.species)}")
print(f"Total Categories: {len(cat.categories)}")

data = []
for s in cat.species:
    data.append({
        "species_id": s.species_id,
        "common_name": s.common_name,
        "scientific_name": s.scientific_name,
        "family": s.family,
        "category_id": s.category_id,
        "short_category": s.short_category,
        "biome": s.biome,
        "height_m": s.dimensions.height_m,
        "canopy_spread_m": s.dimensions.canopy_spread_m,
        "trunk_stem_diameter_m": s.dimensions.trunk_stem_diameter_m,
        "target_polycount": s.meshy_spec.target_polycount,
        "positive_prompt": s.meshy_spec.positive_prompt,
        "negative_prompt": s.meshy_spec.negative_prompt,
    })

with open("E:/tool/mcp/MorphoMesh/.agents/explorer_survey_1/catalog_dump.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print("Saved catalog dump to catalog_dump.json")
