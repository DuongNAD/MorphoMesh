import json
from pathlib import Path

p = Path(r"E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\vegetation_pipeline\taxonomy_catalog.json")
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"File exists: {p.is_file()}")
print(f"Size: {p.stat().st_size} bytes")
print(f"Keys in root: {list(data.keys())}")
print(f"Total species reported: {data.get('total_species')}")
print(f"Actual species count in list: {len(data.get('species', []))}")
print(f"Total categories reported: {data.get('total_categories')}")
print(f"Actual categories in list: {len(data.get('categories', []))}")

categories = [c['category_id'] for c in data['categories']]
print(f"Categories ({len(categories)}): {categories}")

species_by_cat = {}
for s in data['species']:
    cat = s['category_id']
    species_by_cat.setdefault(cat, []).append((s['species_id'], s['common_name'], s['scientific_name'], s['family']))

for cat, splist in species_by_cat.items():
    print(f"\nCategory: {cat} (Count: {len(splist)})")
    for sp_id, cname, sname, fam in splist:
        print(f"  - {sp_id}: {cname} ({sname}) [{fam}]")
