import json
from pathlib import Path

catalog_path = Path("teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json")
with open(catalog_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"Total species in JSON: {len(data['species'])}")
print(f"Total categories in JSON: {len(data['categories'])}")

tokens_56 = [
    "pot", "planter", "flowerpot", "flower pot", "plant pot", "terracotta", "container", "vase", "bowl",
    "bucket", "crate", "dish", "tray", "saucer", "pedestal", "base stand", "stand", "ground soil box",
    "square block", "platform", "roots in pot", "indoor room", "wall", "background", "floor", "furniture",
    "table", "human", "hands", "person", "people", "man", "woman", "character", "body", "face", "animal", "insect",
    "artificial plastic", "artificial grass", "low quality", "deformed", "floating leaves",
    "disconnected branches", "blurry", "cartoon", "toy", "miniature", "wireframe", "baked lighting shadow",
    "skeleton", "bones", "armature", "rig", "rigged", "rigging", "skinning", "joints", "watermark", "text", "logo"
]
print(f"Tokens count in list: {len(tokens_56)}")

missing_tokens = {}
for s in data["species"]:
    sid = s["species_id"]
    neg = s["meshy_spec"]["negative_prompt"].lower()
    miss = [t for t in tokens_56 if t not in neg]
    if miss:
        missing_tokens[sid] = miss

if missing_tokens:
    print("MISSING TOKENS:", missing_tokens)
else:
    print("SUCCESS: All 35 species contain all 56 negative prompt tokens!")

anchoring = []
for s in data["species"]:
    sid = s["species_id"]
    pos = s["meshy_spec"]["positive_prompt"].lower()
    has_stand = "standalone" in pos or "single" in pos
    has_grnd = any(k in pos for k in ["ground", "rooted", "soil", "base", "cushion", "climbing", "attached", "growing"])
    if not (has_stand and has_grnd):
        anchoring.append((sid, has_stand, has_grnd))

if anchoring:
    print("ANCHORING ISSUES:", anchoring)
else:
    print("SUCCESS: All 35 species have confirmed standalone and ground anchoring!")

dim_issues = []
for s in data["species"]:
    sid = s["species_id"]
    d = s["dimensions"]
    h = d["height_m"]
    hr = d["height_range_m"]
    w = d["canopy_spread_m"]
    cal = d["trunk_stem_diameter_m"]
    if not (hr[0] <= h <= hr[1]):
        dim_issues.append(f"{sid}: height {h} not in {hr}")
    if cal > w:
        dim_issues.append(f"{sid}: caliper {cal} > spread {w}")
    if s["category_id"] in ["broadleaf_deciduous_trees", "conifers_evergreens"]:
        if cal >= h:
            dim_issues.append(f"{sid}: caliper {cal} >= height {h}")
        if h < 3.0:
            dim_issues.append(f"{sid}: tree height {h} < 3m")

if dim_issues:
    print("DIMENSION ISSUES:", dim_issues)
else:
    print("SUCCESS: All 35 species passed dimension sanity checks!")

print("\n=== 35 SPECIES BOTANICAL BREAKDOWN ===")
for cat in data["categories"]:
    cid = cat["category_id"]
    cname = cat["display_name"]
    s_list = [s for s in data["species"] if s["category_id"] == cid]
    print(f"Category: {cname} ({cid}) - {len(s_list)} species")
    for s in s_list:
        d = s["dimensions"]
        print(f"  [{s['species_id']}] {s['common_name']} ({s['scientific_name']}) | {s['family']} | {s['biome']}")
        print(f"      Dimensions: H={d['height_m']}m {d['height_range_m']}, Canopy={d['canopy_spread_m']}m, Stem/Trunk={d['trunk_stem_diameter_m']}m")
