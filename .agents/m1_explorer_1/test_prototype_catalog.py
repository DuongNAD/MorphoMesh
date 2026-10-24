"""
Prototype and verification test for vegetation_pipeline/catalog.py schema & API design.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator


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

    growth_habit: str = Field(..., description="Overall botanical habit (tree, shrub, herb, tussock, rosette, liana, epiphyte)")
    branching_pattern: str = Field(..., description="Branching architecture (deliquescent, excurrent, fastigiate, fountain, twining)")
    trunk_bark_texture: str = Field(..., description="Surface texture and color of trunk, stem, or pseudostem")
    leaf_type: str = Field(..., description="Broadleaf, needle, frond, scale, blade, succulent blade")
    leaf_shape: str = Field(..., description="Botanical leaf shape (lobed, ovate, lanceolate, palmate, bipinnate, etc.)")
    foliage_density: Literal["dense", "medium", "airy", "compact", "open"] = Field("dense")
    floral_reproductive_accents: str = Field(..., description="Flowers, cones, berries, sori, or reproductive structures")

    # Compatibility properties with PROJECT.md contracts
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

    # Compatibility properties with PROJECT.md contracts
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

    # Compatibility properties with PROJECT.md contracts
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

# Test loading from survey artifact
survey_json = Path(r"E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json")
with open(survey_json, "r", encoding="utf-8") as f:
    raw_catalog_dict = json.load(f)

catalog = VegetationLibraryCatalog.model_validate(raw_catalog_dict)
print(f"Validated Catalog: {catalog.total_species} species, {catalog.total_categories} categories.")

# Test lookups and API functions
species_by_id = {s.species_id: s for s in catalog.species}
species_by_scientific = {s.scientific_slug: s for s in catalog.species}
species_by_common = {s.common_name.lower(): s for s in catalog.species}

def get_species(identifier: str) -> PlantSpecies:
    ident = identifier.strip().lower()
    if ident in species_by_id:
        return species_by_id[ident]
    # Check scientific slug
    slug = ident.replace(" ", "_")
    if slug in species_by_scientific:
        return species_by_scientific[slug]
    if ident in species_by_common:
        return species_by_common[ident]
    raise KeyError(f"Species not found with identifier '{identifier}'. Available IDs: {list(species_by_id.keys())[:5]}...")

def get_species_by_category(category: str) -> List[PlantSpecies]:
    cat_key = category.strip().lower()
    resolved_cat = CATEGORY_ALIASES.get(cat_key, cat_key)
    results = [s for s in catalog.species if s.category_id == resolved_cat]
    if not results:
        valid_cats = [c.category_id for c in catalog.categories]
        raise KeyError(f"Category '{category}' not found. Available: {valid_cats} or aliases: {list(CATEGORY_ALIASES.keys())}")
    return results

def list_categories() -> List[str]:
    return [c.category_id for c in catalog.categories]

def list_species_ids() -> List[str]:
    return [s.species_id for s in catalog.species]

# Verification assertions
s1 = get_species("veg_tree_oak_01")
assert s1.common_name == "English Oak"
assert s1.id == "veg_tree_oak_01"
assert s1.category == "broadleaf_deciduous_trees"
assert s1.morphology.branching_habit == s1.morphology.branching_pattern
assert s1.meshy_spec.prompt == s1.meshy_spec.positive_prompt

# Test scientific name lookup
s1_sci = get_species("quercus_robur")
assert s1_sci.species_id == "veg_tree_oak_01"

# Test common name lookup
s1_com = get_species("English Oak")
assert s1_com.species_id == "veg_tree_oak_01"

# Test category lookup with canonical and alias
cats_canonical = get_species_by_category("broadleaf_deciduous_trees")
assert len(cats_canonical) == 5
cats_alias = get_species_by_category("broadleaf_trees")
assert len(cats_alias) == 5
assert cats_canonical == cats_alias

# Test all categories
for cat in list_categories():
    assert len(get_species_by_category(cat)) == 5

# Test all aliases
for alias in CATEGORY_ALIASES:
    assert len(get_species_by_category(alias)) == 5

assert len(list_species_ids()) == 35

print("All prototype tests PASSED successfully!")
