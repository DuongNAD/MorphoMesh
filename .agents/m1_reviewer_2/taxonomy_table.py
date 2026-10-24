import json

with open("teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"{'Species ID':<32} | {'Common Name':<25} | {'Scientific Name':<28} | {'Family':<16} | {'Category'}")
print("-" * 120)
for s in data["species"]:
    family = s["family"]
    print(f"{s['species_id']:<32} | {s['common_name']:<25} | {s['scientific_name']:<28} | {family:<16} | {s['category_id']}")
