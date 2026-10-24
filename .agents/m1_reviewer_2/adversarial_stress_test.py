import sys
from pathlib import Path

# Add project paths
repo_root = Path.cwd()
project_dir = repo_root / "teamwork_projects" / "vegetation_library"
if str(project_dir) not in sys.path:
    sys.path.insert(0, str(project_dir))
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from vegetation_pipeline.catalog import (
    get_catalog, get_species, get_species_by_category, CATEGORY_ALIASES
)

catalog = get_catalog()

print("=== 1. PROMPT LENGTH ANALYSIS ===")
lengths = []
for s in catalog.species:
    pos_len = len(s.meshy_spec.positive_prompt)
    neg_len = len(s.meshy_spec.negative_prompt)
    lengths.append((s.species_id, pos_len, neg_len))

lengths.sort(key=lambda x: x[1], reverse=True)
print(f"Max positive prompt: {lengths[0][0]} ({lengths[0][1]} chars)")
print(f"Min positive prompt: {lengths[-1][0]} ({lengths[-1][1]} chars)")
avg_pos = sum(x[1] for x in lengths) / len(lengths)
print(f"Avg positive prompt: {avg_pos:.1f} chars")
neg_str = catalog.species[0].meshy_spec.negative_prompt
print(f"Negative prompt length (constant): {len(neg_str)} chars (~{len(neg_str.split())} words, {len(neg_str.split(','))} tokens)")

print("\n=== 2. DIMENSION ASPECT RATIO STRESS TEST ===")
extreme_aspects = []
for s in catalog.species:
    d = s.dimensions
    hw_ratio = d.height_m / d.canopy_spread_m
    extreme_aspects.append((s.species_id, s.common_name, hw_ratio, d.height_m, d.canopy_spread_m, d.trunk_stem_diameter_m))

extreme_aspects.sort(key=lambda x: x[2], reverse=True)
print("Top 5 Tallest / Narrowest (High H/W ratio):")
for item in extreme_aspects[:5]:
    print(f"  {item[0]:<30} | {item[1]:<22} | H/W={item[2]:.2f} (H={item[3]}m, W={item[4]}m)")

print("\nTop 5 Flattest / Widest (Low H/W ratio):")
for item in extreme_aspects[-5:]:
    print(f"  {item[0]:<30} | {item[1]:<22} | H/W={item[2]:.2f} (H={item[3]}m, W={item[4]}m)")

print("\n=== 3. CATEGORY ALIAS STRESS TEST ===")
test_queries = [
    ("broadleaf_trees", True),
    ("broadleaf", True),
    ("trees", True),
    ("conifers", True),
    ("tropical", True),
    ("shrubs", True),
    ("groundcover", True),
    ("succulents", True),
    ("vines", True),
    ("BROADLEAF_TREES", True),  # uppercase
    ("  shrubs  ", True),       # whitespace
    ("conifer", False),         # singular (not in alias dict)
    ("tree", False),            # singular
    ("moss", False),            # not an alias
]

for q, expected in test_queries:
    try:
        res = get_species_by_category(q)
        print(f"Query '{q}': SUCCESS ({len(res)} species)")
    except KeyError as e:
        print(f"Query '{q}': KEYERROR (Expected={not expected})")

print("\n=== 4. LOOKUP RESOLUTION STRESS TEST ===")
lookup_queries = [
    ("Quercus robur", "veg_tree_oak_01"),
    ("quercus robur", "veg_tree_oak_01"),
    ("QUERCUS ROBUR", "veg_tree_oak_01"),
    ("quercus_robur", "veg_tree_oak_01"),
    ("English Oak", "veg_tree_oak_01"),
    ("english oak", "veg_tree_oak_01"),
    ("ENGLISH OAK", "veg_tree_oak_01"),
    ("  veg_tree_oak_01  ", "veg_tree_oak_01"),
    ("Carnegiea gigantea", "veg_succulent_saguaro_01"),
    ("Tillandsia usneoides", "veg_epiphyte_spanishmoss_01"),
    ("Rosa gallica", "veg_shrub_rose_01"),
    ("Leucobryum glaucum", "veg_ground_moss_01"),
]

for q, expected_id in lookup_queries:
    try:
        sp = get_species(q)
        assert sp.species_id == expected_id, f"Wrong species: {sp.species_id} != {expected_id}"
        print(f"Lookup '{q}' -> {sp.species_id} (MATCH)")
    except Exception as e:
        print(f"Lookup '{q}' -> FAILED: {e}")
