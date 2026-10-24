"""
Unit and Integration Test Suite for Milestone 1: Botanical Taxonomy & Catalog Specification
File: teamwork_projects/vegetation_library/tests/test_catalog.py

Validates:
- Catalog scale: >= 30 species across >= 6 categories (exact 35 species across 7 biomes).
- Taxonomy & nomenclature: scientific binomials, families in -aceae, common names, biomes.
- Metric dimensions: strictly positive (H > 0, W > 0, D > 0) within botanical bounds.
- Meshy prompts: standalone grounding anchors, positive morphology, and negative blacklist tokens.
- Query helpers: get_species, get_species_by_category (canonical & aliases), list_categories, list_species_ids.
- Interface contracts: compatibility properties (id, category, prompt, branching_habit, bark_texture).
- Pydantic v2 validation & serialization invariants.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple

import pytest
from pydantic import ValidationError

from vegetation_pipeline.catalog import (
    DimensionsSpec,
    MorphologySpec,
    MeshyPromptSpec,
    VerificationCriteria,
    PlantSpecies,
    BotanicalCategory,
    VegetationLibraryCatalog,
    VegetationCatalog,
    get_catalog,
    get_species,
    get_species_by_category,
    list_categories,
    list_species_ids,
    list_species,
    CATEGORY_ALIASES,
    REVERSE_CATEGORY_ALIASES,
    UNIVERSAL_NEGATIVE_BLACKLIST,
)


# ==============================================================================
# AUTHORITATIVE CONSTANTS & FIXTURES
# ==============================================================================

MANDATORY_NEGATIVE_TOKENS: List[str] = [
    "pot", "planter", "flowerpot", "terracotta", "container", "vase",
    "pedestal", "base stand", "platform", "ground soil box",
    "human", "hands", "person", "animal", "insect",
    "artificial plastic", "floating leaves", "disconnected branches",
    "low quality", "deformed"
]

VALID_CATEGORY_IDS: List[str] = [
    "broadleaf_deciduous_trees",
    "conifers_evergreens",
    "tropical_foliage_palms",
    "flowering_shrubs_ornamentals",
    "ferns_grasses_groundcover",
    "succulents_cacti",
    "climbing_vines_epiphytes",
]


@pytest.fixture(scope="session")
def catalog() -> VegetationLibraryCatalog:
    """Returns the singleton VegetationLibraryCatalog instance."""
    return get_catalog()


@pytest.fixture(scope="session")
def all_species(catalog: VegetationLibraryCatalog) -> List[PlantSpecies]:
    """Returns all 35 PlantSpecies objects."""
    return catalog.species


# ==============================================================================
# 1. CATALOG COMPLETENESS & TAXONOMY SCALE (R1)
# ==============================================================================

class TestCatalogCompletenessAndScale:
    """Verifies that the catalog defines >= 30 species across >= 6 categories (35 species, 7 categories)."""

    def test_get_catalog_returns_valid_instance(self, catalog: VegetationLibraryCatalog):
        assert isinstance(catalog, VegetationLibraryCatalog)
        assert catalog.schema_version == "1.0.0"
        assert catalog.project == "MorphoMesh Vegetation Library"
        assert len(catalog) == 35

    def test_total_species_count_meets_and_exceeds_threshold(self, catalog: VegetationLibraryCatalog):
        assert len(catalog.species) >= 30, f"Expected >= 30 species, found {len(catalog.species)}"
        assert len(catalog.species) == 35, f"Expected exactly 35 species, found {len(catalog.species)}"
        assert catalog.total_species == 35

    def test_total_categories_count_meets_and_exceeds_threshold(self, catalog: VegetationLibraryCatalog):
        assert len(catalog.categories) >= 6, f"Expected >= 6 categories, found {len(catalog.categories)}"
        assert len(catalog.categories) == 7, f"Expected exactly 7 categories, found {len(catalog.categories)}"
        assert catalog.total_categories == 7

    def test_uniform_category_partitioning(self, catalog: VegetationLibraryCatalog):
        """Verifies each category contains exactly 5 species."""
        counts: Dict[str, int] = {}
        for sp in catalog.species:
            counts[sp.category_id] = counts.get(sp.category_id, 0) + 1

        for cat_id in VALID_CATEGORY_IDS:
            assert cat_id in counts, f"Category '{cat_id}' has no species defined"
            assert counts[cat_id] == 5, f"Category '{cat_id}' has {counts[cat_id]} species, expected 5"

    def test_unique_identifiers_across_catalog(self, catalog: VegetationLibraryCatalog):
        """Verifies zero duplicate species IDs, scientific names, or common names."""
        ids = [s.species_id for s in catalog.species]
        sci = [s.scientific_name.lower() for s in catalog.species]
        com = [s.common_name.lower() for s in catalog.species]

        assert len(ids) == len(set(ids)), f"Duplicate species_id: {[x for x in ids if ids.count(x) > 1]}"
        assert len(sci) == len(set(sci)), f"Duplicate scientific_name: {[x for x in sci if sci.count(x) > 1]}"
        assert len(com) == len(set(com)), f"Duplicate common_name: {[x for x in com if com.count(x) > 1]}"


# ==============================================================================
# 2. BOTANICAL TAXONOMY & NOMENCLATURE
# ==============================================================================

class TestTaxonomyAndBotanicalNomenclature:
    """Verifies scientific binomial nomenclature, common names, family, and biomes."""

    def test_all_species_id_regex(self, all_species: List[PlantSpecies]):
        pattern = re.compile(r"^veg_[a-z0-9_]+$")
        for sp in all_species:
            assert pattern.match(sp.species_id), f"Invalid species_id format: '{sp.species_id}'"

    def test_botanical_naming_fields_populated(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            assert sp.common_name.strip() != "", f"Empty common_name for {sp.species_id}"
            assert sp.scientific_name.strip() != "", f"Empty scientific_name for {sp.species_id}"
            assert sp.biome.strip() != "", f"Empty biome for {sp.species_id}"
            assert sp.ecological_niche.strip() != "", f"Empty ecological_niche for {sp.species_id}"
            assert sp.category_id in VALID_CATEGORY_IDS, f"Invalid category_id for {sp.species_id}"

    def test_scientific_name_is_binomial(self, all_species: List[PlantSpecies]):
        """Scientific name must follow binomial rules: Capitalized Genus and lowercase specific epithet."""
        for sp in all_species:
            tokens = sp.scientific_name.split()
            assert len(tokens) >= 2, f"Scientific name '{sp.scientific_name}' is not binomial for {sp.species_id}"
            assert tokens[0][0].isupper(), f"Genus '{tokens[0]}' must be capitalized in {sp.species_id}"
            assert tokens[1].islower(), f"Specific epithet '{tokens[1]}' must be lowercase in {sp.species_id}"

    def test_botanical_family_standard_suffix(self, all_species: List[PlantSpecies]):
        """Standard botanical families end in '-aceae'."""
        for sp in all_species:
            assert sp.family.strip().endswith("aceae"), f"Family '{sp.family}' does not end in -aceae for {sp.species_id}"


# ==============================================================================
# 3. METRIC DIMENSIONS & BOTANICAL PLAUSIBILITY BOUNDS
# ==============================================================================

class TestBotanicalMetricDimensions:
    """Verifies that height, spread, and trunk caliper are strictly positive and botanically valid."""

    def test_dimensions_strictly_positive(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            dim = sp.dimensions
            assert dim.height_m > 0.0, f"Height {dim.height_m} <= 0 in {sp.species_id}"
            assert dim.canopy_spread_m > 0.0, f"Canopy spread {dim.canopy_spread_m} <= 0 in {sp.species_id}"
            assert dim.trunk_stem_diameter_m > 0.0, f"Trunk diameter {dim.trunk_stem_diameter_m} <= 0 in {sp.species_id}"

    def test_height_range_ordering_and_containment(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            dim = sp.dimensions
            assert len(dim.height_range_m) == 2, f"Height range must be (min, max) in {sp.species_id}"
            min_h, max_h = dim.height_range_m
            assert 0.0 < min_h <= max_h, f"Invalid height range ({min_h}, {max_h}) in {sp.species_id}"
            assert min_h <= dim.height_m <= max_h, (
                f"Reference height {dim.height_m} outside range [{min_h}, {max_h}] in {sp.species_id}"
            )

    def test_botanical_proportions_and_sanity(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            dim = sp.dimensions
            h = dim.height_m
            w = dim.canopy_spread_m
            d = dim.trunk_stem_diameter_m

            # Base diameter cannot exceed total canopy spread (can be equal in hemispherical cushion moss)
            assert d <= w + 1e-6, f"Base diameter {d} exceeds canopy spread {w} in {sp.species_id}"

            # Erect woody plants: trunk diameter must be strictly less than height
            if sp.category_id in ("broadleaf_deciduous_trees", "conifers_evergreens", "flowering_shrubs_ornamentals"):
                assert d < h, f"Trunk diameter {d} exceeds height {h} in {sp.species_id}"

            # Global botanical scale bounds
            assert 0.05 <= h <= 45.0, f"Height {h} outside plausible bounds [0.05m, 45.0m] in {sp.species_id}"
            assert 0.05 <= w <= 30.0, f"Canopy spread {w} outside plausible bounds [0.05m, 30.0m] in {sp.species_id}"


# ==============================================================================
# 4. MESHY PROMPT CONDITIONING & NEGATIVE BLACKLIST
# ==============================================================================

class TestMeshyPromptConditioningAndBlacklists:
    """Verifies prompt conditioning, standalone anchoring, and negative blacklist tokens."""

    def test_positive_prompt_structure_and_anchors(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            prompt = sp.meshy_spec.positive_prompt.lower()
            assert len(prompt) >= 50, f"Positive prompt too short ({len(prompt)} chars) in {sp.species_id}"

            # Must mention common name or genus
            common_tokens = [t.lower() for t in sp.common_name.split() if len(t) > 3]
            genus = sp.scientific_name.split()[0].lower()
            assert any(t in prompt for t in common_tokens) or genus in prompt, (
                f"Neither common name nor genus found in prompt for {sp.species_id}"
            )

            # Standalone ground-rooted anchoring cues
            assert "standalone" in prompt or "single" in prompt, (
                f"Missing standalone/single anchor in {sp.species_id}"
            )

            # Botanical / PBR material keywords
            pbr_morph_kws = ["pbr", "materials", "bark", "leaf", "leaves", "foliage", "stem", "texture", "canopy"]
            assert any(kw in prompt for kw in pbr_morph_kws), (
                f"Missing botanical/PBR keywords in {sp.species_id}"
            )

    def test_negative_prompt_contains_all_mandatory_tokens(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            neg = sp.meshy_spec.negative_prompt.lower()
            missing = [tok for tok in MANDATORY_NEGATIVE_TOKENS if tok not in neg]
            assert not missing, f"Species {sp.species_id} missing negative blacklist tokens: {missing}"

    def test_meshy_inference_parameters(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            spec = sp.meshy_spec
            assert spec.ai_model == "meshy-6"
            assert spec.art_style == "realistic"
            assert spec.topology in ("quad", "triangle")
            assert 10000 <= spec.target_polycount <= 45000
            assert spec.enable_pbr is True
            assert spec.texture_richness == "high"
            assert spec.boost is True

    def test_zero_blacklist_collisions_across_all_positive_prompts(self, all_species: List[PlantSpecies]):
        """Verifies zero whole-word collisions between any of the 35 positive prompts and universal negative tokens."""
        raw_tokens = [t.strip().lower() for t in UNIVERSAL_NEGATIVE_BLACKLIST.split(",") if t.strip()]
        collisions: List[Tuple[str, str, str]] = []

        for sp in all_species:
            pos_prompt = sp.meshy_spec.positive_prompt.lower()
            for tok in raw_tokens:
                pattern = r"\b" + re.escape(tok) + r"\b"
                match = re.search(pattern, pos_prompt)
                if match:
                    collisions.append((sp.species_id, tok, match.group(0)))

        assert len(collisions) == 0, (
            f"Found {len(collisions)} negative blacklist token collisions in positive prompts: {collisions}"
        )

    def test_zero_container_and_rigging_tokens_in_positive_prompts(self, all_species: List[PlantSpecies]):
        """Explicitly tests that forbidden container, floor, and rigging words do not appear in positive prompts."""
        forbidden_container_tokens = {
            "pot", "planter", "flowerpot", "terracotta", "container", "vase",
            "bowl", "bucket", "crate", "pedestal", "stand", "platform", "floor"
        }
        forbidden_rigging_tokens = {
            "skeleton", "bones", "armature", "rig", "rigged", "rigging", "skinning", "joints"
        }
        critical_forbidden = forbidden_container_tokens | forbidden_rigging_tokens

        for sp in all_species:
            pos_prompt = sp.meshy_spec.positive_prompt.lower()
            for tok in critical_forbidden:
                pattern = r"\b" + re.escape(tok) + r"\b"
                assert not re.search(pattern, pos_prompt), (
                    f"Forbidden word '{tok}' found in positive prompt for {sp.species_id}: '{pos_prompt}'"
                )


# ==============================================================================
# 5. ASSET VERIFICATION CRITERIA
# ==============================================================================

class TestAssetVerificationCriteria:
    """Verifies QA thresholds: vertex limits (3k-45k), static mesh (0 bones), root pivot."""

    def test_verification_criteria_invariants(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            crit = sp.verification
            assert crit.min_vertices >= 3000, f"min_vertices < 3000 in {sp.species_id}"
            assert crit.max_vertices <= 45000, f"max_vertices > 45000 in {sp.species_id}"
            assert crit.min_vertices < crit.max_vertices
            assert crit.enforce_zero_armature is True, f"Must enforce 0 armatures in {sp.species_id}"
            assert crit.enforce_root_pivot is True, f"Must enforce root pivot in {sp.species_id}"
            expected_maps = {"baseColor", "normal", "roughness", "metallic"}
            assert expected_maps.issubset(set(crit.required_pbr_maps)), (
                f"Missing mandatory PBR maps in {sp.species_id}"
            )


# ==============================================================================
# 6. QUERYING HELPER FUNCTIONS & API CONTRACTS
# ==============================================================================

class TestQueryingHelperFunctions:
    """Verifies get_species, get_species_by_category, list_categories, list_species_ids."""

    def test_get_species_by_id(self):
        sp = get_species("veg_tree_oak_01")
        assert sp.common_name == "English Oak"
        assert sp.scientific_name == "Quercus robur"
        assert sp.id == "veg_tree_oak_01"

    def test_get_species_by_scientific_slug_and_name(self):
        sp1 = get_species("quercus_robur")
        sp2 = get_species("Quercus robur")
        sp3 = get_species("Pinus sylvestris")
        assert sp1.species_id == "veg_tree_oak_01"
        assert sp2.species_id == "veg_tree_oak_01"
        assert sp3.species_id == "veg_conifer_pine_01"

    def test_get_species_by_common_name_case_insensitive(self):
        sp1 = get_species("English Oak")
        sp2 = get_species("english oak")
        sp3 = get_species("Saguaro Cactus")
        assert sp1.species_id == "veg_tree_oak_01"
        assert sp2.species_id == "veg_tree_oak_01"
        assert sp3.species_id == "veg_succulent_saguaro_01"

    def test_get_species_nonexistent_raises_keyerror(self):
        with pytest.raises(KeyError, match="not found"):
            get_species("veg_nonexistent_plant_99")

    def test_get_species_by_category_canonical(self):
        for cat_id in VALID_CATEGORY_IDS:
            species_list = get_species_by_category(cat_id)
            assert len(species_list) == 5
            for sp in species_list:
                assert sp.category_id == cat_id

    def test_get_species_by_category_aliases(self):
        for alias, canonical in CATEGORY_ALIASES.items():
            species_list = get_species_by_category(alias)
            assert len(species_list) == 5
            for sp in species_list:
                assert sp.category_id == canonical

    def test_get_species_by_category_unknown_raises_keyerror(self):
        with pytest.raises(KeyError, match="not found"):
            get_species_by_category("unknown_alien_category")

    def test_list_categories(self):
        cats = list_categories()
        assert len(cats) == 7
        assert set(cats) == set(VALID_CATEGORY_IDS)

    def test_list_species_ids(self):
        ids = list_species_ids()
        assert len(ids) == 35
        assert len(set(ids)) == 35
        assert all(s.startswith("veg_") for s in ids)

    def test_list_species(self):
        species = list_species()
        assert len(species) == 35
        assert all(isinstance(s, PlantSpecies) for s in species)


# ==============================================================================
# 7. INTERFACE CONTRACTS & COMPATIBILITY PROPERTIES
# ==============================================================================

class TestInterfaceContractsAndAliases:
    """Verifies compatibility properties specified in PROJECT.md M1 ↔ M2 contract."""

    def test_contract_compatibility_properties(self, all_species: List[PlantSpecies]):
        for sp in all_species:
            # PROJECT.md M1 ↔ M2 contract: .id, .category, .prompt, .branching_habit, .bark_texture
            assert sp.id == sp.species_id
            assert sp.category == sp.category_id
            assert sp.morphology.branching_habit == sp.morphology.branching_pattern
            assert sp.morphology.bark_texture == sp.morphology.trunk_bark_texture
            assert sp.meshy_spec.prompt == sp.meshy_spec.positive_prompt
            assert sp.scientific_slug == sp.scientific_name.lower().replace(" ", "_")

    def test_vegetation_catalog_type_alias_export(self):
        """Verifies VegetationCatalog type alias is exported from vegetation_pipeline and catalog.py."""
        from vegetation_pipeline import VegetationCatalog
        from vegetation_pipeline.catalog import VegetationCatalog as CatalogAlias
        import vegetation_pipeline

        assert "VegetationCatalog" in vegetation_pipeline.__all__
        assert VegetationCatalog is VegetationLibraryCatalog
        assert CatalogAlias is VegetationLibraryCatalog
        cat = get_catalog()
        assert isinstance(cat, VegetationCatalog)

    def test_species_short_category_layout_compliance(self, all_species: List[PlantSpecies], catalog: VegetationLibraryCatalog):
        """Verifies PlantSpecies.short_category and BotanicalCategory.short_category match PROJECT.md line 120 directory names."""
        valid_short_categories = {
            "broadleaf_trees", "conifers", "tropical", "shrubs",
            "groundcover", "succulents", "vines"
        }
        for sp in all_species:
            assert hasattr(sp, "short_category"), f"Missing short_category on {sp.species_id}"
            assert sp.short_category in valid_short_categories, (
                f"Invalid short_category '{sp.short_category}' for {sp.species_id}"
            )
            assert sp.category == sp.category_id

        # Verify BotanicalCategory short_category
        for cat in catalog.categories:
            assert hasattr(cat, "short_category")
            assert cat.short_category in valid_short_categories


# ==============================================================================
# 8. PYDANTIC V2 SERIALIZATION & VALIDATION
# ==============================================================================

class TestPydanticSerializationAndValidation:
    """Verifies Pydantic v2 serialization, round-trip deserialization, and boundary validators."""

    def test_roundtrip_serialization(self, catalog: VegetationLibraryCatalog):
        dumped = catalog.model_dump()
        assert isinstance(dumped, dict)
        reconstructed = VegetationLibraryCatalog.model_validate(dumped)
        assert len(reconstructed.species) == 35
        assert reconstructed.total_species == 35

    def test_json_roundtrip(self):
        sp = get_species("veg_tree_oak_01")
        json_str = sp.model_dump_json()
        reconstructed = PlantSpecies.model_validate_json(json_str)
        assert reconstructed.species_id == sp.species_id
        assert reconstructed.dimensions.height_m == sp.dimensions.height_m

    def test_invalid_height_range_raises_validation_error(self):
        with pytest.raises(ValidationError):
            DimensionsSpec(
                height_m=10.0,
                height_range_m=(15.0, 8.0),  # min > max must fail
                canopy_spread_m=5.0,
                trunk_stem_diameter_m=0.5
            )

    def test_negative_dimensions_raise_validation_error(self):
        with pytest.raises(ValidationError):
            DimensionsSpec(
                height_m=-5.0,  # Negative height must fail
                height_range_m=(4.0, 8.0),
                canopy_spread_m=5.0,
                trunk_stem_diameter_m=0.5
            )

    def test_invalid_species_id_pattern_raises_validation_error(self):
        sp_data = get_species("veg_tree_oak_01").model_dump()
        sp_data["species_id"] = "INVALID-UPPERCASE-ID"
        with pytest.raises(ValidationError):
            PlantSpecies.model_validate(sp_data)

    def test_reject_infinite_and_nan_scalar_dimensions(self):
        """Verifies DimensionsSpec rejects float('inf'), float('-inf'), and float('nan') on scalar fields."""
        fields = ["height_m", "canopy_spread_m", "trunk_stem_diameter_m"]
        for field in fields:
            for invalid_val in [float("inf"), float("-inf"), float("nan")]:
                params = {
                    "height_m": 5.0,
                    "height_range_m": (3.0, 8.0),
                    "canopy_spread_m": 3.0,
                    "trunk_stem_diameter_m": 0.3,
                }
                params[field] = invalid_val
                with pytest.raises(ValidationError) as exc_info:
                    DimensionsSpec(**params)
                assert field in str(exc_info.value) or "finite_number" in str(exc_info.value)

    def test_reject_infinite_and_nan_in_height_range_tuple(self):
        """Verifies DimensionsSpec rejects inf/-inf/nan inside height_range_m tuple."""
        bad_ranges = [
            (float("inf"), 10.0),
            (1.0, float("inf")),
            (float("-inf"), 10.0),
            (1.0, float("-inf")),
            (float("nan"), 10.0),
            (1.0, float("nan")),
            (float("-inf"), float("inf")),
        ]
        for bad_range in bad_ranges:
            with pytest.raises(ValidationError):
                DimensionsSpec(
                    height_m=5.0,
                    height_range_m=bad_range,
                    canopy_spread_m=3.0,
                    trunk_stem_diameter_m=0.3,
                )

    def test_reject_negative_or_zero_height_range_bounds(self):
        """Verifies height_range_m bounds must be strictly positive (> 0)."""
        bad_ranges = [
            (0.0, 10.0),      # min is zero
            (-5.0, 10.0),     # min is negative
            (-10.0, -2.0),    # both negative
            (5.0, 0.0),       # max is zero
            (5.0, -2.0),      # max is negative
        ]
        for bad_range in bad_ranges:
            with pytest.raises(ValidationError):
                DimensionsSpec(
                    height_m=5.0,
                    height_range_m=bad_range,
                    canopy_spread_m=3.0,
                    trunk_stem_diameter_m=0.3,
                )

    def test_reject_inverted_height_range(self):
        """Verifies min height range bound cannot exceed max height bound."""
        with pytest.raises(ValidationError) as exc_info:
            DimensionsSpec(
                height_m=10.0,
                height_range_m=(15.0, 8.0),
                canopy_spread_m=5.0,
                trunk_stem_diameter_m=0.5,
            )
        assert "cannot be greater than" in str(exc_info.value) or "less than" in str(exc_info.value)

    def test_reject_height_outside_range_containment(self):
        """Verifies height_m must be contained within [min_range, max_range]."""
        # height_m < min_range
        with pytest.raises(ValidationError) as exc_info1:
            DimensionsSpec(
                height_m=4.0,
                height_range_m=(6.0, 12.0),
                canopy_spread_m=4.0,
                trunk_stem_diameter_m=0.4,
            )
        assert "outside mature height range" in str(exc_info1.value)

        # height_m > max_range
        with pytest.raises(ValidationError) as exc_info2:
            DimensionsSpec(
                height_m=15.0,
                height_range_m=(6.0, 12.0),
                canopy_spread_m=4.0,
                trunk_stem_diameter_m=0.4,
            )
        assert "outside mature height range" in str(exc_info2.value)

    def test_valid_boundary_heights_accepted(self):
        """Verifies height_m exactly on boundary (min or max) is accepted."""
        # height_m == min_range
        d_min = DimensionsSpec(
            height_m=6.0,
            height_range_m=(6.0, 12.0),
            canopy_spread_m=4.0,
            trunk_stem_diameter_m=0.4,
        )
        assert d_min.height_m == 6.0

        # height_m == max_range
        d_max = DimensionsSpec(
            height_m=12.0,
            height_range_m=(6.0, 12.0),
            canopy_spread_m=4.0,
            trunk_stem_diameter_m=0.4,
        )
        assert d_max.height_m == 12.0

        # point range: min_range == max_range == height_m
        d_point = DimensionsSpec(
            height_m=8.0,
            height_range_m=(8.0, 8.0),
            canopy_spread_m=4.0,
            trunk_stem_diameter_m=0.4,
        )
        assert d_point.height_m == 8.0


# ==============================================================================
# 9. CATALOG CONTAINER PROTOCOL (__contains__, get, keys, values, items)
# ==============================================================================

class TestCatalogContainerProtocol:
    """Verifies Python mapping container protocol (__contains__, .get(), .keys(), .values(), .items())."""

    def test_catalog_contains_species_id(self, catalog: VegetationLibraryCatalog):
        """Verifies 'species_id in catalog' returns True for canonical IDs."""
        assert "veg_tree_oak_01" in catalog
        assert "veg_conifer_pine_01" in catalog
        assert "veg_tropical_palm_01" in catalog
        assert "veg_succulent_saguaro_01" in catalog
        assert "VEG_TREE_OAK_01" in catalog

    def test_catalog_contains_scientific_slug_and_name(self, catalog: VegetationLibraryCatalog):
        """Verifies membership by scientific name (slug and binomial format)."""
        assert "quercus_robur" in catalog
        assert "Quercus robur" in catalog
        assert "Pinus sylvestris" in catalog
        assert "carnegiea_gigantea" in catalog

    def test_catalog_contains_common_name(self, catalog: VegetationLibraryCatalog):
        """Verifies membership by vernacular common name (case-insensitive)."""
        assert "English Oak" in catalog
        assert "english oak" in catalog
        assert "Saguaro Cactus" in catalog
        assert "saguaro cactus" in catalog

    def test_catalog_contains_plant_species_instance(self, catalog: VegetationLibraryCatalog):
        """Verifies 'species in catalog' returns True when passing PlantSpecies object."""
        sp = catalog["veg_tree_oak_01"]
        assert sp in catalog
        for item in catalog.species:
            assert item in catalog

    def test_catalog_contains_invalid_keys_returns_false(self, catalog: VegetationLibraryCatalog):
        """Verifies nonexistent keys and invalid types return False without raising exceptions."""
        assert "invalid_id" not in catalog
        assert "nonexistent_species_99" not in catalog
        assert "" not in catalog
        assert 12345 not in catalog
        assert None not in catalog
        assert [] not in catalog

    def test_catalog_get_successful_lookups(self, catalog: VegetationLibraryCatalog):
        """Verifies catalog.get() returns PlantSpecies for valid species_id, scientific, and common names."""
        sp_id = catalog.get("veg_tree_oak_01")
        assert sp_id is not None
        assert isinstance(sp_id, PlantSpecies)
        assert sp_id.species_id == "veg_tree_oak_01"

        sp_sci = catalog.get("quercus_robur")
        assert sp_sci is not None
        assert sp_sci.species_id == "veg_tree_oak_01"

        sp_com = catalog.get("English Oak")
        assert sp_com is not None
        assert sp_com.species_id == "veg_tree_oak_01"

    def test_catalog_get_nonexistent_returns_default(self, catalog: VegetationLibraryCatalog):
        """Verifies catalog.get() returns default (None or custom sentinel) on missing key."""
        assert catalog.get("invalid_id") is None
        assert catalog.get("invalid_id", default=None) is None
        sentinel = object()
        assert catalog.get("invalid_id", default=sentinel) is sentinel
        assert catalog.get(999, default="fallback") == "fallback"

    def test_catalog_keys(self, catalog: VegetationLibraryCatalog):
        """Verifies catalog.keys() returns list of all 35 canonical species IDs."""
        keys = catalog.keys()
        assert len(keys) == 35
        assert len(set(keys)) == 35
        assert "veg_tree_oak_01" in keys
        assert all(isinstance(k, str) and k.startswith("veg_") for k in keys)

    def test_catalog_values(self, catalog: VegetationLibraryCatalog):
        """Verifies catalog.values() returns list of all 35 PlantSpecies instances."""
        values = catalog.values()
        assert len(values) == 35
        assert all(isinstance(v, PlantSpecies) for v in values)
        assert [v.species_id for v in values] == catalog.keys()

    def test_catalog_items(self, catalog: VegetationLibraryCatalog):
        """Verifies catalog.items() yields (species_id, PlantSpecies) pairs and enables dict() construction."""
        items = catalog.items()
        assert len(items) == 35
        for key, sp in items:
            assert isinstance(key, str)
            assert isinstance(sp, PlantSpecies)
            assert key == sp.species_id
        d = dict(items)
        assert len(d) == 35
        assert d["veg_tree_oak_01"].common_name == "English Oak"
