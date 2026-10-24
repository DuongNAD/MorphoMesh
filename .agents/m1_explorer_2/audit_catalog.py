import json
from pathlib import Path

catalog_path = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(catalog_path, encoding="utf-8") as f:
    data = json.load(f)

print(f"Total species: {len(data['species'])}")
categories = {}
for sp in data["species"]:
    cat = sp["category_id"]
    categories.setdefault(cat, []).append(sp)

for cat_id, species_list in categories.items():
    print(f"\n==================== CATEGORY: {cat_id} ({len(species_list)} species) ====================")
    for sp in species_list:
        pos = sp["meshy_spec"]["positive_prompt"]
        neg = sp["meshy_spec"]["negative_prompt"]
        dim = sp["dimensions"]
        morph = sp["morphology"]
        
        # Validation checks
        pos_lower = pos.lower()
        has_standalone = "standalone" in pos_lower
        has_ground = "ground" in pos_lower or "rooted" in pos_lower or "growing" in pos_lower
        has_natural = "natural" in pos_lower or "photorealistic" in pos_lower
        
        # Blacklist checks
        neg_lower = neg.lower()
        mandatory_neg_terms = [
            "pot", "planter", "flowerpot", "terracotta", "container", "vase",
            "pedestal", "base stand", "platform", "human", "hands", "person",
            "artificial plastic", "floating leaves", "disconnected branches"
        ]
        missing_neg = [term for term in mandatory_neg_terms if term not in neg_lower]
        
        print(f"ID: {sp['species_id']} | Common: {sp['common_name']} | Scientific: {sp['scientific_name']}")
        print(f"   Family: {sp['family']} | Biome: {sp['biome']}")
        print(f"   Metric Dimensions: Height={dim['height_m']}m (range: {dim.get('height_range_m')}), Canopy Spread={dim['canopy_spread_m']}m, Trunk/Stem Dia={dim['trunk_stem_diameter_m']}m")
        print(f"   Morphology:")
        print(f"     Growth Habit: {morph.get('growth_habit')}")
        print(f"     Branching: {morph.get('branching_pattern')}")
        print(f"     Trunk/Bark: {morph.get('trunk_bark_texture')}")
        print(f"     Leaf Type & Shape: {morph.get('leaf_type')} | {morph.get('leaf_shape')}")
        print(f"     Foliage Density: {morph.get('foliage_density')}")
        print(f"     Reproductive Accents: {morph.get('floral_reproductive_accents')}")
        print(f"   Prompt Conditioning:")
        print(f"     Positive Prompt: {pos[:100]}...")
        print(f"     Standalone Anchor: {has_standalone} | Ground Rooted: {has_ground}")
        print(f"     Missing Negative Tokens: {missing_neg if missing_neg else 'NONE (All present)'}")
