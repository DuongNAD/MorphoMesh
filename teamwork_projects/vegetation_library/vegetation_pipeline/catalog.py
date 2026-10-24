"""
Vegetation Library - Botanical Taxonomy Catalog Module
Defines Pydantic v2 schemas and programmatic API for 35 plant species across 7 biomes.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterator, List, Literal, Optional, Tuple, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ==============================================================================
# Universal Blacklist & Category Nomenclature Constants
# ==============================================================================

UNIVERSAL_NEGATIVE_BLACKLIST = (
    "pot, planter, flowerpot, flower pot, plant pot, terracotta, container, vase, bowl, "
    "bucket, crate, dish, tray, saucer, pedestal, base stand, stand, ground soil box, "
    "square block, platform, roots in pot, indoor room, wall, background, floor, furniture, "
    "table, human, hands, person, people, man, woman, character, body, face, animal, insect, "
    "artificial plastic, artificial grass, low quality, deformed, floating leaves, "
    "disconnected branches, blurry, cartoon, toy, miniature, wireframe, baked lighting shadow, "
    "skeleton, bones, armature, rig, rigged, rigging, skinning, joints, watermark, text, logo"
)

REVERSE_CATEGORY_ALIASES: Dict[str, str] = {
    "broadleaf_deciduous_trees": "broadleaf_trees",
    "conifers_evergreens": "conifers",
    "tropical_foliage_palms": "tropical",
    "flowering_shrubs_ornamentals": "shrubs",
    "ferns_grasses_groundcover": "groundcover",
    "succulents_cacti": "succulents",
    "climbing_vines_epiphytes": "vines",
}


# ==============================================================================
# Pydantic v2 Schemas
# ==============================================================================

class DimensionsSpec(BaseModel):
    """Physical dimensions and mature growth bounds in metric units."""
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)

    height_m: float = Field(..., gt=0.0, description="Reference mature height in meters")
    height_range_m: Tuple[float, float] = Field(..., description="Min and max mature height range in meters")
    canopy_spread_m: float = Field(..., gt=0.0, description="Crown or canopy spread diameter in meters")
    trunk_stem_diameter_m: float = Field(..., gt=0.0, description="Base trunk or stem diameter in meters")

    @field_validator("height_range_m")
    @classmethod
    def validate_range(cls, v: Tuple[float, float]) -> Tuple[float, float]:
        if len(v) != 2:
            raise ValueError(f"Height range must be a tuple of exactly 2 floats (min, max), got length {len(v)}")
        min_val, max_val = v
        if min_val <= 0.0:
            raise ValueError(f"Min height range bound must be strictly positive (> 0), got {min_val}")
        if max_val <= 0.0:
            raise ValueError(f"Max height range bound must be strictly positive (> 0), got {max_val}")
        if max_val < min_val:
            raise ValueError(f"Min height {min_val} cannot be greater than max height {max_val}")
        return v

    @model_validator(mode="after")
    def validate_height_containment(self) -> "DimensionsSpec":
        min_val, max_val = self.height_range_m
        if not (min_val <= self.height_m <= max_val):
            raise ValueError(
                f"Reference height {self.height_m}m is outside mature height range [{min_val}m, {max_val}m]"
            )
        return self


class MorphologySpec(BaseModel):
    """Botanical morphology and structural characteristics."""
    model_config = ConfigDict(extra="ignore")

    growth_habit: str = Field(..., description="Overall botanical habit (tree, shrub, herb, tussock, rosette, liana, epiphyte)")
    branching_pattern: str = Field(..., description="Branching architecture (deliquescent, excurrent, fastigiate, fountain, twining)")
    trunk_bark_texture: str = Field(..., description="Surface texture and color of trunk, stem, or pseudostem")
    leaf_type: str = Field(..., description="Broadleaf, needle, frond, scale, blade, succulent blade")
    leaf_shape: str = Field(..., description="Botanical leaf shape (lobed, ovate, lanceolate, palmate, bipinnate, etc.)")
    foliage_density: Literal["dense", "medium", "airy", "compact", "open"] = Field("dense")
    floral_reproductive_accents: str = Field(..., description="Flowers, cones, berries, sori, or reproductive structures")

    # Backward compatibility properties for PROJECT.md interface contracts
    @property
    def branching_habit(self) -> str:
        return self.branching_pattern

    @property
    def bark_texture(self) -> str:
        return self.trunk_bark_texture


class MeshyPromptSpec(BaseModel):
    """Meshy AI Text-to-3D prompt conditioning parameters."""
    model_config = ConfigDict(extra="ignore")

    positive_prompt: str = Field(..., min_length=20, description="Conditioned botanical positive prompt")
    negative_prompt: str = Field(..., min_length=20, description="Negative prompt blacklist eliminating pots, stands, humans")
    ai_model: str = Field(default="meshy-6", description="Meshy model tier")
    art_style: str = Field(default="realistic", description="Rendering style")
    topology: Literal["quad", "triangle"] = Field(default="quad", description="Target mesh topology")
    target_polycount: int = Field(default=28000, ge=10000, le=45000, description="Target polygon count")
    enable_pbr: bool = Field(default=True, description="Enable 4-channel PBR texture extraction")
    texture_richness: str = Field(default="high", description="Texture map resolution/richness tier")
    boost: bool = Field(default=True, description="Enable preview + refine boost workflow")

    # Backward compatibility property
    @property
    def prompt(self) -> str:
        return self.positive_prompt


class VerificationCriteria(BaseModel):
    """Quality control thresholds for static unrigged botanical assets."""
    model_config = ConfigDict(extra="ignore")

    min_vertices: int = Field(default=3000, ge=3000, description="Minimum acceptable vertex count")
    max_vertices: int = Field(default=65000, le=65000, description="Maximum acceptable vertex count")
    enforce_zero_armature: bool = Field(default=True, description="Strictly forbid bones or skinning clusters")
    enforce_root_pivot: bool = Field(default=True, description="Require ground pivot at Z_min=0 or Y_min=0")
    required_pbr_maps: List[str] = Field(
        default_factory=lambda: ["baseColor", "normal", "roughness", "metallic"],
        description="Mandatory PBR texture channels"
    )


class PlantSpecies(BaseModel):
    """Canonical specification for a single botanical species."""
    model_config = ConfigDict(extra="ignore")

    species_id: str = Field(..., pattern=r"^veg_[a-z0-9_]+$", description="Unique identifier (e.g. veg_tree_oak_01)")
    common_name: str = Field(..., description="Vernacular common name")
    scientific_name: str = Field(..., description="Binomial scientific nomenclature")
    family: str = Field(..., description="Botanical family")
    category_id: str = Field(..., description="Canonical category ID")
    category_name: str = Field(..., description="Category display title")
    biome: str = Field(..., description="Native ecological biome")
    ecological_niche: str = Field(..., description="Ecological role and habitat")
    dimensions: DimensionsSpec
    morphology: MorphologySpec
    meshy_spec: MeshyPromptSpec
    verification: VerificationCriteria = Field(default_factory=VerificationCriteria)

    # Convenience properties for cross-milestone compatibility
    @property
    def id(self) -> str:
        return self.species_id

    @property
    def category(self) -> str:
        return self.category_id

    @property
    def short_category(self) -> str:
        """Shorthand directory category name matching PROJECT.md layout."""
        return REVERSE_CATEGORY_ALIASES.get(self.category_id, self.category_id)

    @property
    def scientific_slug(self) -> str:
        return self.scientific_name.lower().replace(" ", "_")


class BotanicalCategory(BaseModel):
    """Botanical category metadata."""
    model_config = ConfigDict(extra="ignore")

    category_id: str
    display_name: str
    description: str
    representative_biomes: List[str]
    species_count: int

    @property
    def short_category(self) -> str:
        """Shorthand directory category name matching PROJECT.md layout."""
        return REVERSE_CATEGORY_ALIASES.get(self.category_id, self.category_id)


class VegetationLibraryCatalog(BaseModel):
    """Top-level container holding all 35 species across 7 biomes."""
    model_config = ConfigDict(extra="ignore")

    schema_version: str = "1.0.0"
    project: str = "MorphoMesh Vegetation Library"
    total_species: int
    total_categories: int
    categories: List[BotanicalCategory]
    species: List[PlantSpecies]

    def __len__(self) -> int:
        return len(self.species)

    def __iter__(self) -> Iterator[PlantSpecies]:
        return iter(self.species)

    def _find_species(self, identifier: object) -> Optional[PlantSpecies]:
        """Internal helper to find a species within this catalog instance."""
        if not isinstance(identifier, str):
            return None
        key = identifier.strip().lower()
        if not key:
            return None
        slug = key.replace(" ", "_")

        # 1. Match by species_id (case-insensitive)
        for s in self.species:
            if s.species_id.lower() == key:
                return s
        # 2. Match by scientific name or slug (case-insensitive)
        for s in self.species:
            if s.scientific_slug == slug or s.scientific_name.lower() == key:
                return s
        # 3. Match by common name or slug (case-insensitive)
        for s in self.species:
            if s.common_name.lower() == key or s.common_name.lower().replace(" ", "_") == slug:
                return s
        return None

    def __getitem__(self, identifier: str) -> PlantSpecies:
        sp = self._find_species(identifier)
        if sp is not None:
            return sp
        available = [s.species_id for s in self.species[:5]]
        raise KeyError(
            f"Species '{identifier}' not found in catalog. "
            f"Valid IDs include: {available}... (total {len(self.species)})"
        )

    def __contains__(self, identifier: object) -> bool:
        """
        Membership test: supports species_id, scientific name/slug,
        common name, or PlantSpecies instance.
        """
        if isinstance(identifier, PlantSpecies):
            return any(s.species_id == identifier.species_id for s in self.species)
        if isinstance(identifier, str):
            return self._find_species(identifier) is not None
        return False

    def get(self, identifier: object, default: Any = None) -> Any:
        """Safe lookup returning default if species is not found."""
        if not isinstance(identifier, str):
            return default
        sp = self._find_species(identifier)
        return sp if sp is not None else default

    def keys(self) -> List[str]:
        """Returns a list of all species IDs."""
        return [s.species_id for s in self.species]

    def values(self) -> List[PlantSpecies]:
        """Returns a list of all PlantSpecies instances."""
        return list(self.species)

    def items(self) -> List[Tuple[str, PlantSpecies]]:
        """Returns a list of (species_id, PlantSpecies) pairs."""
        return [(s.species_id, s) for s in self.species]


# ==============================================================================
# Contract Alias (PROJECT.md M1 <-> M2 interface)
# ==============================================================================
VegetationCatalog = VegetationLibraryCatalog


# ==============================================================================
# Category Aliases & Indexing Helpers
# ==============================================================================

CATEGORY_ALIASES: Dict[str, str] = {
    # PROJECT.md contracts & shorthand mappings
    "broadleaf_trees": "broadleaf_deciduous_trees",
    "broadleaf": "broadleaf_deciduous_trees",
    "trees": "broadleaf_deciduous_trees",
    "conifers": "conifers_evergreens",
    "evergreens": "conifers_evergreens",
    "tropical": "tropical_foliage_palms",
    "palms": "tropical_foliage_palms",
    "shrubs": "flowering_shrubs_ornamentals",
    "ornamentals": "flowering_shrubs_ornamentals",
    "groundcover": "ferns_grasses_groundcover",
    "ferns": "ferns_grasses_groundcover",
    "grasses": "ferns_grasses_groundcover",
    "succulents": "succulents_cacti",
    "cacti": "succulents_cacti",
    "vines": "climbing_vines_epiphytes",
    "epiphytes": "climbing_vines_epiphytes",
}

DEFAULT_CATALOG_JSON: Path = Path(__file__).resolve().parent / "taxonomy_catalog.json"

_CACHED_CATALOG: Optional[VegetationLibraryCatalog] = None
_SPECIES_BY_ID: Dict[str, PlantSpecies] = {}
_SPECIES_BY_SCIENTIFIC: Dict[str, PlantSpecies] = {}
_SPECIES_BY_COMMON: Dict[str, PlantSpecies] = {}


def _rebuild_indices(catalog: VegetationLibraryCatalog) -> None:
    global _SPECIES_BY_ID, _SPECIES_BY_SCIENTIFIC, _SPECIES_BY_COMMON
    _SPECIES_BY_ID = {s.species_id.lower(): s for s in catalog.species}
    _SPECIES_BY_SCIENTIFIC = {s.scientific_slug: s for s in catalog.species}
    _SPECIES_BY_COMMON = {s.common_name.lower().replace(" ", "_"): s for s in catalog.species}
    _SPECIES_BY_COMMON.update({s.common_name.lower(): s for s in catalog.species})


def load_catalog(json_path: Optional[Union[str, Path]] = None) -> VegetationLibraryCatalog:
    """
    Loads and validates the botanical catalog from a JSON file.
    Defaults to 'taxonomy_catalog.json' in the same directory as this module.
    """
    target_path = Path(json_path) if json_path else DEFAULT_CATALOG_JSON
    if not target_path.is_file():
        raise FileNotFoundError(
            f"Botanical taxonomy catalog JSON not found at: {target_path}. "
            f"Ensure 'taxonomy_catalog.json' is co-located with catalog.py."
        )

    with open(target_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)

    catalog = VegetationLibraryCatalog.model_validate(raw_data)
    _rebuild_indices(catalog)
    return catalog


def get_catalog(reload: bool = False, json_path: Optional[Union[str, Path]] = None) -> VegetationLibraryCatalog:
    """
    Returns the singleton VegetationLibraryCatalog instance.
    Cached after initial load unless reload=True.
    """
    global _CACHED_CATALOG
    if _CACHED_CATALOG is None or reload:
        _CACHED_CATALOG = load_catalog(json_path)
    return _CACHED_CATALOG


def get_species(identifier: str) -> PlantSpecies:
    """
    Retrieve a species by species_id (e.g. 'veg_tree_oak_01'),
    scientific name (e.g. 'quercus_robur' or 'Quercus robur'),
    or common name (e.g. 'English Oak'). Case-insensitive.
    """
    if not _SPECIES_BY_ID:
        get_catalog()

    key = identifier.strip().lower()
    if key in _SPECIES_BY_ID:
        return _SPECIES_BY_ID[key]

    slug = key.replace(" ", "_")
    if slug in _SPECIES_BY_SCIENTIFIC:
        return _SPECIES_BY_SCIENTIFIC[slug]

    if key in _SPECIES_BY_COMMON:
        return _SPECIES_BY_COMMON[key]
    if slug in _SPECIES_BY_COMMON:
        return _SPECIES_BY_COMMON[slug]

    available = list(_SPECIES_BY_ID.keys())
    raise KeyError(
        f"Species '{identifier}' not found in catalog. "
        f"Valid IDs include: {available[:5]}... (total {len(available)})"
    )


def get_species_by_category(category: str) -> List[PlantSpecies]:
    """
    Retrieve all species belonging to a botanical category.
    Accepts canonical category IDs (e.g. 'broadleaf_deciduous_trees')
    or convenient aliases (e.g. 'broadleaf_trees', 'conifers', 'tropical').
    """
    catalog = get_catalog()
    cat_key = category.strip().lower()
    resolved_cat = CATEGORY_ALIASES.get(cat_key, cat_key)

    results = [s for s in catalog.species if s.category_id == resolved_cat]
    if not results:
        valid_cats = [c.category_id for c in catalog.categories]
        raise KeyError(
            f"Category '{category}' (resolved as '{resolved_cat}') not found or has no species. "
            f"Valid categories: {valid_cats}. Available aliases: {list(CATEGORY_ALIASES.keys())}"
        )
    return results


def list_categories() -> List[str]:
    """Returns a list of all canonical category IDs (7 biomes)."""
    catalog = get_catalog()
    return [c.category_id for c in catalog.categories]


def list_species_ids() -> List[str]:
    """Returns a list of all 35 canonical species IDs."""
    catalog = get_catalog()
    return [s.species_id for s in catalog.species]


def list_species() -> List[PlantSpecies]:
    """Returns a list of all 35 PlantSpecies instances."""
    catalog = get_catalog()
    return list(catalog.species)
