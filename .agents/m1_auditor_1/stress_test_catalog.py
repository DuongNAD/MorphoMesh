"""
Adversarial Stress Test Suite for Milestone 1: Botanical Taxonomy & Catalog Specification
Author: Forensic Auditor (m1_auditor_1)
"""
from __future__ import annotations

import sys
from pathlib import Path

# Add project root and vegetation_library to sys.path
PROJECT_DIR = Path(__file__).resolve().parent.parent.parent / "teamwork_projects" / "vegetation_library"
REPO_ROOT = PROJECT_DIR.parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pytest
from pydantic import ValidationError

from vegetation_pipeline import (
    get_catalog,
    get_species,
    get_species_by_category,
    list_categories,
    list_species_ids,
    list_species,
    load_catalog,
    DimensionsSpec,
    MorphologySpec,
    MeshyPromptSpec,
    VerificationCriteria,
    PlantSpecies,
    BotanicalCategory,
    VegetationLibraryCatalog,
    CATEGORY_ALIASES,
    UNIVERSAL_NEGATIVE_BLACKLIST,
)


def run_all_stress_tests():
    passed = 0
    total = 0

    def record_test(name, success, detail=""):
        nonlocal passed, total
        total += 1
        if success:
            passed += 1
            print(f"[PASS] {name} {detail}")
        else:
            print(f"[FAIL] {name} - {detail}")
            raise AssertionError(f"Stress test failed: {name} - {detail}")

    print("=== ADVERSARIAL STRESS TESTING: SCHEMA INTEGRITY & NEGATIVE BOUNDARIES ===")

    # 1. Negative & Zero Height validation
    try:
        DimensionsSpec(height_m=0.0, height_range_m=(0.0, 10.0), canopy_spread_m=5.0, trunk_stem_diameter_m=0.5)
        record_test("Height zero rejection", False, "Failed to reject height_m=0.0")
    except ValidationError:
        record_test("Height zero rejection", True, "Successfully raised ValidationError on height_m=0.0")

    try:
        DimensionsSpec(height_m=-1.5, height_range_m=(1.0, 10.0), canopy_spread_m=5.0, trunk_stem_diameter_m=0.5)
        record_test("Negative height rejection", False, "Failed to reject negative height")
    except ValidationError:
        record_test("Negative height rejection", True, "Successfully raised ValidationError on negative height")

    # 2. Inverted height range validation
    try:
        DimensionsSpec(height_m=5.0, height_range_m=(10.0, 2.0), canopy_spread_m=5.0, trunk_stem_diameter_m=0.5)
        record_test("Inverted height range rejection", False, "Failed to reject min > max")
    except ValidationError:
        record_test("Inverted height range rejection", True, "Successfully rejected min > max")

    # 3. Negative canopy spread & trunk diameter
    try:
        DimensionsSpec(height_m=5.0, height_range_m=(2.0, 10.0), canopy_spread_m=-2.0, trunk_stem_diameter_m=0.5)
        record_test("Negative canopy spread rejection", False, "Failed to reject canopy_spread_m <= 0")
    except ValidationError:
        record_test("Negative canopy spread rejection", True, "Successfully rejected canopy_spread_m <= 0")

    try:
        DimensionsSpec(height_m=5.0, height_range_m=(2.0, 10.0), canopy_spread_m=5.0, trunk_stem_diameter_m=0.0)
        record_test("Zero trunk diameter rejection", False, "Failed to reject trunk_stem_diameter_m <= 0")
    except ValidationError:
        record_test("Zero trunk diameter rejection", True, "Successfully rejected trunk_stem_diameter_m <= 0")

    # 4. Invalid Species ID patterns
    invalid_ids = [
        "OakTree",
        "veg-tree-oak",
        "plant_01",
        "veg_TREE_OAK_01",
        "veg_tree oak_01",
        "veg_tree@oak",
        "",
        "veg_",
    ]
    valid_base = get_species("veg_tree_oak_01").model_dump()
    for inv_id in invalid_ids:
        try:
            bad_data = dict(valid_base)
            bad_data["species_id"] = inv_id
            PlantSpecies.model_validate(bad_data)
            record_test(f"Invalid ID regex rejection for '{inv_id}'", False, "Accepted invalid ID")
        except ValidationError:
            record_test(f"Invalid ID regex rejection for '{inv_id}'", True)

    # 5. Short prompt rejection
    try:
        MeshyPromptSpec(
            positive_prompt="too short",
            negative_prompt=UNIVERSAL_NEGATIVE_BLACKLIST
        )
        record_test("Short positive prompt rejection", False, "Accepted prompt < 20 chars")
    except ValidationError:
        record_test("Short positive prompt rejection", True)

    try:
        MeshyPromptSpec(
            positive_prompt="Valid long positive prompt with more than 20 characters",
            negative_prompt="short neg"
        )
        record_test("Short negative prompt rejection", False, "Accepted negative prompt < 20 chars")
    except ValidationError:
        record_test("Short negative prompt rejection", True)

    # 6. Polycount bounds rejection
    try:
        MeshyPromptSpec(
            positive_prompt="Valid long positive prompt with more than 20 characters",
            negative_prompt=UNIVERSAL_NEGATIVE_BLACKLIST,
            target_polycount=5000  # < 10000
        )
        record_test("Low polycount rejection", False, "Accepted target_polycount < 10000")
    except ValidationError:
        record_test("Low polycount rejection", True)

    try:
        MeshyPromptSpec(
            positive_prompt="Valid long positive prompt with more than 20 characters",
            negative_prompt=UNIVERSAL_NEGATIVE_BLACKLIST,
            target_polycount=60000  # > 45000
        )
        record_test("High polycount rejection", False, "Accepted target_polycount > 45000")
    except ValidationError:
        record_test("High polycount rejection", True)

    # 7. Invalid foliage density Literal
    try:
        MorphologySpec(
            growth_habit="tree",
            branching_pattern="deliquescent",
            trunk_bark_texture="rough",
            leaf_type="broadleaf",
            leaf_shape="lobed",
            foliage_density="super_dense",  # not in Literal
            floral_reproductive_accents="none"
        )
        record_test("Invalid foliage density literal rejection", False, "Accepted invalid foliage_density")
    except ValidationError:
        record_test("Invalid foliage density literal rejection", True)

    # 8. VerificationCriteria bounds
    try:
        VerificationCriteria(min_vertices=1000)  # < 3000
        record_test("min_vertices < 3000 rejection", False, "Accepted min_vertices < 3000")
    except ValidationError:
        record_test("min_vertices < 3000 rejection", True)

    try:
        VerificationCriteria(max_vertices=50000)  # > 45000
        record_test("max_vertices > 45000 rejection", False, "Accepted max_vertices > 45000")
    except ValidationError:
        record_test("max_vertices > 45000 rejection", True)

    print("\n=== ADVERSARIAL STRESS TESTING: QUERY API ROBUSTNESS ===")

    # 9. Query casing & trimming
    test_queries = [
        ("  veg_tree_oak_01  ", "veg_tree_oak_01"),
        ("VEG_TREE_OAK_01", "veg_tree_oak_01"),
        ("  Quercus robur  ", "veg_tree_oak_01"),
        ("QUERCUS_ROBUR", "veg_tree_oak_01"),
        ("quercus robur", "veg_tree_oak_01"),
        ("English Oak", "veg_tree_oak_01"),
        ("ENGLISH OAK", "veg_tree_oak_01"),
        ("  english_oak  ", "veg_tree_oak_01"),
        ("sAgUaRo cAcTuS", "veg_succulent_saguaro_01"),
        ("pinus_sylvestris", "veg_conifer_pine_01"),
    ]
    for q, expected_id in test_queries:
        res = get_species(q)
        record_test(f"Query '{q}' -> {expected_id}", res.species_id == expected_id)

    # 10. Non-existent query strings raising KeyError
    adversarial_queries = [
        "",
        "   ",
        "12345",
        "'; DROP TABLE vegetation; --",
        "null",
        "None",
        "veg_tree_nonexistent_99",
        "Quercus nonexistus",
        "Unknown Bush",
    ]
    for aq in adversarial_queries:
        try:
            get_species(aq)
            record_test(f"Rejection of adversarial query '{aq}'", False, "Should raise KeyError")
        except KeyError:
            record_test(f"Rejection of adversarial query '{aq}'", True)

    # 11. Category Aliases exhaustive resolution
    for alias, canonical in CATEGORY_ALIASES.items():
        species_list = get_species_by_category(alias)
        all_match = all(s.category_id == canonical for s in species_list) and len(species_list) == 5
        record_test(f"Category alias '{alias}' -> '{canonical}' (5 species)", all_match)

    # 12. Unknown category query
    try:
        get_species_by_category("fungi_mushrooms")
        record_test("Rejection of unknown category", False, "Should raise KeyError")
    except KeyError:
        record_test("Rejection of unknown category", True)

    # 13. File not found on load_catalog
    try:
        load_catalog("nonexistent_path/catalog.json")
        record_test("load_catalog non-existent file rejection", False, "Should raise FileNotFoundError")
    except FileNotFoundError:
        record_test("load_catalog non-existent file rejection", True)

    # 14. Reload catalog test
    cat1 = get_catalog()
    cat2 = get_catalog(reload=True)
    record_test("get_catalog(reload=True) functionality", len(cat1) == 35 and len(cat2) == 35)

    print("\n=== ADVERSARIAL STRESS TESTING: METRIC PLAUSIBILITY ACROSS 35 SPECIES ===")

    # 15. Real botanical plausibility checks across all 35 species
    cat = get_catalog()
    for sp in cat.species:
        dim = sp.dimensions
        # Height within range
        h_ok = dim.height_range_m[0] <= dim.height_m <= dim.height_range_m[1]
        record_test(f"Height containment {sp.species_id} ({dim.height_range_m[0]} <= {dim.height_m} <= {dim.height_range_m[1]})", h_ok)

        # Proportion checks
        d_vs_w = dim.trunk_stem_diameter_m <= dim.canopy_spread_m + 1e-6
        record_test(f"Trunk vs Spread {sp.species_id} (D={dim.trunk_stem_diameter_m} <= W={dim.canopy_spread_m})", d_vs_w)

        # Static mesh invariants
        crit = sp.verification
        record_test(f"Zero armature enforced {sp.species_id}", crit.enforce_zero_armature is True)
        record_test(f"Root pivot enforced {sp.species_id}", crit.enforce_root_pivot is True)
        record_test(f"Vertex bounds {sp.species_id} [3k, 45k]", crit.min_vertices >= 3000 and crit.max_vertices <= 45000)

        # Morphology richness
        m = sp.morphology
        record_test(f"Morphology non-empty {sp.species_id}", all([
            len(m.growth_habit) > 3,
            len(m.branching_pattern) > 3,
            len(m.trunk_bark_texture) > 3,
            len(m.leaf_type) > 3,
            len(m.leaf_shape) > 3,
            len(m.floral_reproductive_accents) > 3,
        ]))

    print(f"\n==========================================")
    print(f"ADVERSARIAL STRESS TEST SUMMARY: {passed}/{total} PASSED")
    print(f"==========================================")


if __name__ == "__main__":
    run_all_stress_tests()
