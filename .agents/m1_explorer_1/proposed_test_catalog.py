"""
Unit and integration tests for vegetation_pipeline/catalog.py
"""
import pytest
from pathlib import Path
import sys

# Add working directory to sys.path to test proposed_catalog
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))

import proposed_catalog as catalog_module
from proposed_catalog import (
    DimensionsSpec,
    MorphologySpec,
    MeshyPromptSpec,
    VerificationCriteria,
    PlantSpecies,
    BotanicalCategory,
    VegetationLibraryCatalog,
    get_catalog,
    get_species,
    get_species_by_category,
    list_categories,
    list_species_ids,
    CATEGORY_ALIASES,
)

SURVEY_JSON_PATH = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")


@pytest.fixture(autouse=True)
def setup_catalog():
    # Force reload pointing to survey JSON path
    return get_catalog(reload=True, json_path=SURVEY_JSON_PATH)


class TestCatalogCore:
    def test_catalog_structure_and_counts(self, setup_catalog):
        cat = setup_catalog
        assert isinstance(cat, VegetationLibraryCatalog)
        assert cat.total_species == 35
        assert cat.total_categories == 7
        assert len(cat.species) == 35
        assert len(cat.categories) == 7
        assert len(cat) == 35

    def test_list_categories(self):
        cats = list_categories()
        assert len(cats) == 7
        expected_cats = [
            "broadleaf_deciduous_trees",
            "conifers_evergreens",
            "tropical_foliage_palms",
            "flowering_shrubs_ornamentals",
            "ferns_grasses_groundcover",
            "succulents_cacti",
            "climbing_vines_epiphytes",
        ]
        assert cats == expected_cats

    def test_list_species_ids(self):
        ids = list_species_ids()
        assert len(ids) == 35
        assert len(set(ids)) == 35
        assert all(s.startswith("veg_") for s in ids)

    def test_species_category_distribution(self):
        for cat_id in list_categories():
            species_in_cat = get_species_by_category(cat_id)
            assert len(species_in_cat) == 5, f"Category {cat_id} should have 5 species"
            for s in species_in_cat:
                assert s.category_id == cat_id
                assert s.category == cat_id


class TestSpeciesLookups:
    def test_lookup_by_species_id(self):
        sp = get_species("veg_tree_oak_01")
        assert sp.species_id == "veg_tree_oak_01"
        assert sp.id == "veg_tree_oak_01"
        assert sp.common_name == "English Oak"
        assert sp.scientific_name == "Quercus robur"

    def test_lookup_by_scientific_slug(self):
        sp1 = get_species("quercus_robur")
        assert sp1.species_id == "veg_tree_oak_01"

        sp2 = get_species("Pinus sylvestris")
        assert sp2.species_id == "veg_conifer_pine_01"

    def test_lookup_by_common_name(self):
        sp = get_species("English Oak")
        assert sp.species_id == "veg_tree_oak_01"

        sp2 = get_species("saguaro_cactus")
        assert sp2.species_id == "veg_succulent_saguaro_01"

    def test_lookup_case_insensitivity(self):
        sp_upper = get_species("VEG_TREE_OAK_01")
        assert sp_upper.species_id == "veg_tree_oak_01"

        sp_mixed = get_species("eNgLiSh OaK")
        assert sp_mixed.species_id == "veg_tree_oak_01"

    def test_lookup_invalid_species_raises_keyerror(self):
        with pytest.raises(KeyError) as exc_info:
            get_species("non_existent_plant_xyz")
        assert "not found in catalog" in str(exc_info.value)


class TestCategoryLookupsAndAliases:
    @pytest.mark.parametrize(
        "alias,canonical",
        [
            ("broadleaf_trees", "broadleaf_deciduous_trees"),
            ("conifers", "conifers_evergreens"),
            ("tropical", "tropical_foliage_palms"),
            ("shrubs", "flowering_shrubs_ornamentals"),
            ("groundcover", "ferns_grasses_groundcover"),
            ("succulents", "succulents_cacti"),
            ("vines", "climbing_vines_epiphytes"),
        ]
    )
    def test_category_aliases(self, alias, canonical):
        species_alias = get_species_by_category(alias)
        species_canonical = get_species_by_category(canonical)
        assert len(species_alias) == 5
        assert [s.species_id for s in species_alias] == [s.species_id for s in species_canonical]

    def test_invalid_category_raises_keyerror(self):
        with pytest.raises(KeyError) as exc_info:
            get_species_by_category("invalid_biome_desert_mars")
        assert "not found" in str(exc_info.value)


class TestSchemaValidation:
    def test_dimensions_validations(self):
        sp = get_species("veg_tree_oak_01")
        assert sp.dimensions.height_m == 12.0
        assert sp.dimensions.canopy_spread_m == 14.0
        assert sp.dimensions.trunk_stem_diameter_m == 0.90
        assert sp.dimensions.height_range_m == (10.0, 15.0)

        # Inverted range check
        with pytest.raises(ValueError, match="cannot be greater than max height"):
            DimensionsSpec(
                height_m=5.0,
                height_range_m=(10.0, 5.0),
                canopy_spread_m=3.0,
                trunk_stem_diameter_m=0.2
            )

    def test_morphology_properties(self):
        sp = get_species("veg_tree_oak_01")
        assert sp.morphology.branching_habit == sp.morphology.branching_pattern
        assert sp.morphology.bark_texture == sp.morphology.trunk_bark_texture
        assert sp.morphology.foliage_density in ["dense", "medium", "airy", "compact", "open"]

    def test_meshy_prompt_spec(self):
        for s_id in list_species_ids():
            sp = get_species(s_id)
            m = sp.meshy_spec
            assert len(m.positive_prompt) >= 20
            assert len(m.negative_prompt) >= 20
            assert m.prompt == m.positive_prompt
            assert m.ai_model == "meshy-4"
            assert m.art_style == "realistic"
            assert m.topology in ["quad", "triangle"]
            assert 10000 <= m.target_polycount <= 45000
            assert m.enable_pbr is True
            assert m.texture_richness == "high"
            assert m.boost is True

            # Universal negative prompt check
            neg = m.negative_prompt.lower()
            for kw in ["pot", "planter", "container", "pedestal", "human", "person"]:
                assert kw in neg, f"Species {s_id} missing negative keyword '{kw}'"

    def test_verification_criteria(self):
        for s_id in list_species_ids():
            sp = get_species(s_id)
            v = sp.verification
            assert v.min_vertices >= 3000
            assert v.max_vertices <= 45000
            assert v.enforce_zero_armature is True
            assert v.enforce_root_pivot is True
            for rmap in ["baseColor", "normal", "roughness", "metallic"]:
                assert rmap in v.required_pbr_maps

    def test_catalog_serialization_roundtrip(self, setup_catalog):
        cat = setup_catalog
        json_str = cat.model_dump_json()
        assert len(json_str) > 50000
        cat_reloaded = VegetationLibraryCatalog.model_validate_json(json_str)
        assert cat_reloaded.total_species == 35
        assert cat_reloaded.total_categories == 7
        assert cat_reloaded.species[0].species_id == cat.species[0].species_id
