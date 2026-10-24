"""
Complete Prototype Unit Test Suite for Milestone 1 (teamwork_projects/vegetation_library/tests/test_catalog.py).
Demonstrates and validates all test cases against Pydantic models, taxonomy data, and helper functions.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple

import pytest
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError


# ==============================================================================
# 1. CATALOG SCHEMAS (Simulating vegetation_pipeline/catalog.py)
# ==============================================================================

class DimensionsSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    height_m: float = Field(..., gt=0.0, description="Reference height in meters")
    height_range_m: Tuple[float, float] = Field(..., description="Min and max mature height range in meters")
    canopy_spread_m: float = Field(..., gt=0.0, description="Crown or canopy spread diameter in meters")
    trunk_stem_diameter_m: float = Field(..., gt=0.0, description="Base trunk or stem diameter in meters")

    @field_validator("height_range_m")
    @classmethod
    def validate_range(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        if v[0] > v[1]:
            raise ValueError(f"Min height {v[0]} cannot be greater than max height {v[1]}")
        return v


class MorphologySpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    growth_habit: str = Field(..., description="Overall botanical habit")
    branching_pattern: str = Field(..., description="Branching architecture")
    trunk_bark_texture: str = Field(..., description="Surface texture of trunk, stem, or pseudostem")
    leaf_type: str = Field(..., description="Broadleaf, needle, frond, scale, blade, etc.")
    leaf_shape: str = Field(..., description="Botanical leaf shape")
    foliage_density: Literal["dense", "medium", "airy", "compact", "open"] = Field("dense")
    floral_reproductive_accents: str = Field(..., description="Reproductive structures")

    @property
    def branching_habit(self) -> str:
        return self.branching_pattern

    @property
    def bark_texture(self) -> str:
        return self.trunk_bark_texture


class MeshyPromptSpec(BaseModel):
    model_config = ConfigDict(extra="ignore")

    positive_prompt: str = Field(..., min_length=20)
    negative_prompt: str = Field(..., min_length=20)
    ai_model: str = Field(default="meshy-4")
    art_style: str = Field(default="realistic")
    topology: Literal["quad", "triangle"] = Field(default="quad")
    target_polycount: int = Field(default=28000, ge=10000, le=45000)
    enable_pbr: bool = Field(default=True)
    texture_richness: str = Field(default="high")
    boost: bool = Field(default=True)

    @property
    def prompt(self) -> str:
        return self.positive_prompt


class VerificationCriteria(BaseModel):
    model_config = ConfigDict(extra="ignore")

    min_vertices: int = Field(default=3000, ge=3000)
    max_vertices: int = Field(default=45000, le=45000)
    enforce_zero_armature: bool = Field(default=True)
    enforce_root_pivot: bool = Field(default=True)
    required_pbr_maps: List[str] = Field(default_factory=lambda: ["baseColor", "normal", "roughness", "metallic"])


class PlantSpecies(BaseModel):
    model_config = ConfigDict(extra="ignore")

    species_id: str = Field(..., pattern=r"^veg_[a-z0-9_]+$")
    common_name: str
    scientific_name: str
    family: str
    category_id: str
    category_name: str
    biome: str
    ecological_niche: str
    dimensions: DimensionsSpec
    morphology: MorphologySpec
    meshy_spec: MeshyPromptSpec
    verification: VerificationCriteria = Field(default_factory=VerificationCriteria)

    @property
    def id(self) -> str:
        return self.species_id

    @property
    def category(self) -> str:
        return self.category_id

    @property
    def scientific_slug(self) -> str:
        return self.scientific_name.lower().replace(" ", "_")


class BotanicalCategory(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category_id: str
    display_name: str
    description: str
    representative_biomes: List[str]
    species_count: int


class VegetationLibraryCatalog(BaseModel):
    model_config = ConfigDict(extra="ignore")

    schema_version: str = "1.0.0"
    project: str = "MorphoMesh Vegetation Library"
    total_species: int
    total_categories: int
    categories: List[BotanicalCategory]
    species: List[PlantSpecies]


# ==============================================================================
# 2. CATALOG LOADER & HELPER FUNCTIONS
# ==============================================================================

CATEGORY_ALIASES: Dict[str, str] = {
    "broadleaf_trees": "broadleaf_deciduous_trees",
    "broadleaf": "broadleaf_deciduous_trees",
    "conifers": "conifers_evergreens",
    "tropical": "tropical_foliage_palms",
    "shrubs": "flowering_shrubs_ornamentals",
    "groundcover": "ferns_grasses_groundcover",
    "succulents": "succulents_cacti",
    "vines": "climbing_vines_epiphytes",
}

CATALOG_JSON_PATH = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")

with open(CATALOG_JSON_PATH, "r", encoding="utf-8") as f:
    _raw_dict = json.load(f)

_GLOBAL_CATALOG = VegetationLibraryCatalog.model_validate(_raw_dict)
_SPECIES_BY_ID = {s.species_id: s for s in _GLOBAL_CATALOG.species}
_SPECIES_BY_SLUG = {s.scientific_slug: s for s in _GLOBAL_CATALOG.species}
_SPECIES_BY_COMMON = {s.common_name.lower(): s for s in _GLOBAL_CATALOG.species}


def get_catalog() -> VegetationLibraryCatalog:
    return _GLOBAL_CATALOG


def get_species(identifier: str) -> PlantSpecies:
    ident = identifier.strip().lower()
    if ident in _SPECIES_BY_ID:
        return _SPECIES_BY_ID[ident]
    slug = ident.replace(" ", "_")
    if slug in _SPECIES_BY_SLUG:
        return _SPECIES_BY_SLUG[slug]
    if ident in _SPECIES_BY_COMMON:
        return _SPECIES_BY_COMMON[ident]
    raise KeyError(f"Species not found with identifier '{identifier}'.")


def get_species_by_category(category: str) -> List[PlantSpecies]:
    cat_key = category.strip().lower()
    resolved_cat = CATEGORY_ALIASES.get(cat_key, cat_key)
    results = [s for s in _GLOBAL_CATALOG.species if s.category_id == resolved_cat]
    if not results:
        raise KeyError(f"Category '{category}' not found.")
    return results


def list_categories() -> List[str]:
    return [c.category_id for c in _GLOBAL_CATALOG.categories]


def list_species_ids() -> List[str]:
    return [s.species_id for s in _GLOBAL_CATALOG.species]


def list_species() -> List[PlantSpecies]:
    return list(_GLOBAL_CATALOG.species)


# ==============================================================================
# 3. UNIT TEST CLASSES
# ==============================================================================

MANDATORY_NEGATIVE_TOKENS = [
    "pot", "planter", "flowerpot", "terracotta", "container", "vase",
    "pedestal", "base stand", "platform", "ground soil box",
    "human", "hands", "person", "animal", "insect",
    "artificial plastic", "floating leaves", "disconnected branches",
    "low quality", "deformed"
]

VALID_CATEGORY_IDS = [
    "broadleaf_deciduous_trees",
    "conifers_evergreens",
    "tropical_foliage_palms",
    "flowering_shrubs_ornamentals",
    "ferns_grasses_groundcover",
    "succulents_cacti",
    "climbing_vines_epiphytes"
]


class TestCatalogCompletenessAndScale:
    """Requirement R1: Verify >= 30 species across >= 6 categories (35 species, 7 categories)."""

    def test_get_catalog_returns_instance(self):
        catalog = get_catalog()
        assert isinstance(catalog, VegetationLibraryCatalog)
        assert catalog.schema_version == "1.0.0"
        assert catalog.project == "MorphoMesh Vegetation Library"

    def test_total_species_scale(self):
        catalog = get_catalog()
        assert len(catalog.species) >= 30
        assert len(catalog.species) == 35
        assert catalog.total_species == 35

    def test_total_categories_scale(self):
        catalog = get_catalog()
        assert len(catalog.categories) >= 6
        assert len(catalog.categories) == 7
        assert catalog.total_categories == 7

    def test_uniform_category_distribution(self):
        catalog = get_catalog()
        counts: Dict[str, int] = {}
        for sp in catalog.species:
            counts[sp.category_id] = counts.get(sp.category_id, 0) + 1

        for cat_id in VALID_CATEGORY_IDS:
            assert cat_id in counts
            assert counts[cat_id] == 5, f"Category {cat_id} has {counts[cat_id]} species, expected 5"

    def test_unique_identifiers_across_catalog(self):
        catalog = get_catalog()
        ids = [s.species_id for s in catalog.species]
        sci = [s.scientific_name.lower() for s in catalog.species]
        com = [s.common_name.lower() for s in catalog.species]

        assert len(ids) == len(set(ids)), f"Duplicate species_id: {[x for x in ids if ids.count(x) > 1]}"
        assert len(sci) == len(set(sci)), f"Duplicate scientific_name: {[x for x in sci if sci.count(x) > 1]}"
        assert len(com) == len(set(com)), f"Duplicate common_name: {[x for x in com if com.count(x) > 1]}"


class TestTaxonomyAndBotanicalNomenclature:
    """Verifies scientific binomial nomenclature, common names, family, and biomes."""

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_species_id_regex(self, sp: PlantSpecies):
        assert re.match(r"^veg_[a-z0-9_]+$", sp.species_id)

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_botanical_taxonomy_fields(self, sp: PlantSpecies):
        assert sp.common_name.strip() != ""
        assert sp.scientific_name.strip() != ""
        # Binomial name: Genus species
        tokens = sp.scientific_name.split()
        assert len(tokens) >= 2, f"Scientific name '{sp.scientific_name}' is not binomial"
        assert tokens[0][0].isupper(), f"Genus '{tokens[0]}' must be capitalized"
        assert tokens[1].islower(), f"Specific epithet '{tokens[1]}' must be lowercase"
        # Standard family name ending in -aceae
        assert sp.family.strip().endswith("aceae"), f"Family '{sp.family}' does not end in -aceae"
        assert sp.biome.strip() != ""
        assert sp.ecological_niche.strip() != ""
        assert sp.category_id in VALID_CATEGORY_IDS


class TestBotanicalMetricDimensions:
    """Verifies that height, spread, and trunk caliper are strictly positive and botanically valid."""

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_dimensions_positive_and_ordered(self, sp: PlantSpecies):
        dim = sp.dimensions
        assert dim.height_m > 0.0
        assert dim.canopy_spread_m > 0.0
        assert dim.trunk_stem_diameter_m > 0.0
        assert len(dim.height_range_m) == 2
        assert 0.0 < dim.height_range_m[0] <= dim.height_range_m[1]
        assert dim.height_range_m[0] <= dim.height_m <= dim.height_range_m[1]

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_botanical_proportions(self, sp: PlantSpecies):
        dim = sp.dimensions
        h, w, d = dim.height_m, dim.canopy_spread_m, dim.trunk_stem_diameter_m

        # Base diameter cannot exceed canopy spread
        assert d <= w + 1e-6, f"Trunk diameter {d} exceeds canopy spread {w} in {sp.species_id}"

        # Erect woody plants: trunk diameter must be strictly less than height
        if sp.category_id in ("broadleaf_deciduous_trees", "conifers_evergreens", "flowering_shrubs_ornamentals"):
            assert d < h, f"Trunk diameter {d} exceeds height {h} in {sp.species_id}"

        # Plausible global limits
        assert 0.05 <= h <= 45.0
        assert 0.05 <= w <= 30.0


class TestMeshyPromptConditioningAndBlacklists:
    """Verifies prompt conditioning, standalone anchoring, and negative blacklist tokens."""

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_positive_prompt_contents(self, sp: PlantSpecies):
        prompt = sp.meshy_spec.positive_prompt.lower()
        assert len(prompt) >= 50

        # Must mention common name or genus
        common_tokens = [t.lower() for t in sp.common_name.split() if len(t) > 3]
        genus = sp.scientific_name.split()[0].lower()
        assert any(t in prompt for t in common_tokens) or genus in prompt

        # Standalone / single plant anchor
        assert "standalone" in prompt or "single" in prompt

        # Botanical or PBR keywords
        assert any(kw in prompt for kw in ["pbr", "materials", "bark", "leaf", "leaves", "foliage", "stem", "texture"])

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_negative_prompt_blacklist(self, sp: PlantSpecies):
        neg = sp.meshy_spec.negative_prompt.lower()
        missing = [tok for tok in MANDATORY_NEGATIVE_TOKENS if tok not in neg]
        assert not missing, f"Species {sp.species_id} missing negative blacklist tokens: {missing}"

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_meshy_parameters(self, sp: PlantSpecies):
        spec = sp.meshy_spec
        assert spec.ai_model == "meshy-4"
        assert spec.art_style == "realistic"
        assert spec.topology in ("quad", "triangle")
        assert 10000 <= spec.target_polycount <= 45000
        assert spec.enable_pbr is True
        assert spec.boost is True


class TestVerificationCriteria:
    """Verifies that verification criteria meet project quality bounds."""

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_verification_criteria_bounds(self, sp: PlantSpecies):
        crit = sp.verification
        assert crit.min_vertices >= 3000
        assert crit.max_vertices <= 45000
        assert crit.min_vertices < crit.max_vertices
        assert crit.enforce_zero_armature is True
        assert crit.enforce_root_pivot is True
        required = {"baseColor", "normal", "roughness", "metallic"}
        assert required.issubset(set(crit.required_pbr_maps))


class TestQueryingHelperFunctions:
    """Verifies get_species, get_species_by_category, list_categories, list_species_ids."""

    def test_get_species_by_id(self):
        sp = get_species("veg_tree_oak_01")
        assert sp.common_name == "English Oak"
        assert sp.scientific_name == "Quercus robur"

    def test_get_species_by_scientific_slug_and_name(self):
        sp1 = get_species("quercus_robur")
        sp2 = get_species("Quercus robur")
        assert sp1.species_id == "veg_tree_oak_01"
        assert sp2.species_id == "veg_tree_oak_01"

    def test_get_species_by_common_name_case_insensitive(self):
        sp1 = get_species("English Oak")
        sp2 = get_species("english oak")
        assert sp1.species_id == "veg_tree_oak_01"
        assert sp2.species_id == "veg_tree_oak_01"

    def test_get_species_nonexistent_raises_keyerror(self):
        with pytest.raises(KeyError, match="not found"):
            get_species("veg_nonexistent_tree_99")

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
            get_species_by_category("unknown_category")

    def test_list_categories(self):
        cats = list_categories()
        assert len(cats) == 7
        assert set(cats) == set(VALID_CATEGORY_IDS)

    def test_list_species_ids(self):
        ids = list_species_ids()
        assert len(ids) == 35
        assert len(set(ids)) == 35

    def test_list_species(self):
        species = list_species()
        assert len(species) == 35
        assert all(isinstance(s, PlantSpecies) for s in species)


class TestInterfaceContractsAndAliases:
    """Verifies compatibility properties specified in PROJECT.md M1 ↔ M2 contract."""

    @pytest.mark.parametrize("sp", _GLOBAL_CATALOG.species, ids=lambda s: s.species_id)
    def test_contract_compatibility_properties(self, sp: PlantSpecies):
        # M1 ↔ M2 contract properties: .id, .category, .prompt, .branching_habit, .bark_texture
        assert sp.id == sp.species_id
        assert sp.category == sp.category_id
        assert sp.morphology.branching_habit == sp.morphology.branching_pattern
        assert sp.morphology.bark_texture == sp.morphology.trunk_bark_texture
        assert sp.meshy_spec.prompt == sp.meshy_spec.positive_prompt
        assert sp.scientific_slug == sp.scientific_name.lower().replace(" ", "_")


class TestPydanticSerializationAndValidation:
    """Verifies Pydantic v2 serialization, round-trip deserialization, and boundary validators."""

    def test_roundtrip_serialization(self):
        catalog = get_catalog()
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
