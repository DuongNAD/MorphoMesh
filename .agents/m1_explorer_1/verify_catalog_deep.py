import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, "r", encoding="utf-8") as f:
    data = json.load(f)

print("=== Running Comprehensive Botanical Catalog Verification ===")

# 1. Total counts
assert data["total_species"] == 35, f"Expected 35 total_species, got {data['total_species']}"
assert data["total_categories"] == 7, f"Expected 7 total_categories, got {data['total_categories']}"
assert len(data["categories"]) == 7
assert len(data["species"]) == 35

# 2. Category distribution
cat_counts = {}
for s in data["species"]:
    cat_counts[s["category_id"]] = cat_counts.get(s["category_id"], 0) + 1

for cat in data["categories"]:
    cid = cat["category_id"]
    assert cat_counts.get(cid) == 5, f"Category {cid} does not have exactly 5 species (got {cat_counts.get(cid)})"

# 3. Uniqueness
ids = [s["species_id"] for s in data["species"]]
commons = [s["common_name"] for s in data["species"]]
scis = [s["scientific_name"] for s in data["species"]]
assert len(ids) == len(set(ids)) == 35, "Duplicate species_id detected"
assert len(commons) == len(set(commons)) == 35, "Duplicate common_name detected"
assert len(scis) == len(set(scis)) == 35, "Duplicate scientific_name detected"

# 4. Dimensions inspection
for s in data["species"]:
    sid = s["species_id"]
    dim = s["dimensions"]
    assert dim["height_m"] > 0, f"{sid}: height_m must be > 0"
    assert dim["height_range_m"][0] > 0, f"{sid}: min height must be > 0"
    assert dim["height_range_m"][1] >= dim["height_range_m"][0], f"{sid}: min height > max height"
    assert dim["canopy_spread_m"] > 0, f"{sid}: canopy_spread_m must be > 0"
    assert dim["trunk_stem_diameter_m"] > 0, f"{sid}: trunk_stem_diameter_m must be > 0"

# 5. Morphology inspection
for s in data["species"]:
    sid = s["species_id"]
    morph = s["morphology"]
    assert morph["growth_habit"], f"{sid}: growth_habit empty"
    assert morph["branching_pattern"], f"{sid}: branching_pattern empty"
    assert morph["trunk_bark_texture"], f"{sid}: trunk_bark_texture empty"
    assert morph["leaf_type"], f"{sid}: leaf_type empty"
    assert morph["leaf_shape"], f"{sid}: leaf_shape empty"
    assert morph["foliage_density"] in ["dense", "medium", "airy", "compact", "open"], f"{sid}: invalid foliage_density"
    assert morph["floral_reproductive_accents"], f"{sid}: floral accents empty"

# 6. Meshy prompt inspection
for s in data["species"]:
    sid = s["species_id"]
    mp = s["meshy_spec"]
    assert len(mp["positive_prompt"]) >= 20, f"{sid}: positive_prompt too short"
    assert len(mp["negative_prompt"]) >= 20, f"{sid}: negative_prompt too short"
    assert mp["ai_model"] == "meshy-4", f"{sid}: unexpected ai_model"
    assert mp["art_style"] == "realistic", f"{sid}: unexpected art_style"
    assert mp["topology"] in ["quad", "triangle"], f"{sid}: unexpected topology"
    assert 10000 <= mp["target_polycount"] <= 45000, f"{sid}: target_polycount out of range"
    assert mp["enable_pbr"] is True, f"{sid}: enable_pbr must be True"
    assert mp["texture_richness"] == "high", f"{sid}: texture_richness not high"
    assert mp["boost"] is True, f"{sid}: boost must be True"
    
    # Check negative prompt eliminates pots/stands/humans
    neg = mp["negative_prompt"].lower()
    for blacklist in ["pot", "planter", "container", "vase", "pedestal", "human", "person", "table", "room"]:
        assert blacklist in neg, f"{sid}: negative prompt missing '{blacklist}' blacklist item"

# 7. Verification criteria inspection
for s in data["species"]:
    sid = s["species_id"]
    vc = s["verification"]
    assert vc["min_vertices"] >= 3000, f"{sid}: min_vertices < 3000"
    assert vc["max_vertices"] <= 45000, f"{sid}: max_vertices > 45000"
    assert vc["enforce_zero_armature"] is True, f"{sid}: enforce_zero_armature must be True"
    assert vc["enforce_root_pivot"] is True, f"{sid}: enforce_root_pivot must be True"
    for rmap in ["baseColor", "normal", "roughness", "metallic"]:
        assert rmap in vc["required_pbr_maps"], f"{sid}: missing required map {rmap}"

print("All 35 species and 7 categories passed 100% of deep botanical & structural checks!")
