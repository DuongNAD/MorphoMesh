"""
Vegetation Library Pipeline Package.
Provides access to botanical taxonomy catalog, procedural generators,
post-processing normalization, and multi-format exporters.
"""
from .catalog import (
    DimensionsSpec,
    MorphologySpec,
    MeshyPromptSpec,
    VerificationCriteria,
    PlantSpecies,
    BotanicalCategory,
    VegetationLibraryCatalog,
    VegetationCatalog,
    load_catalog,
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

from .generator import (
    RawAsset,
    MeshyGenerator,
    MeshyGeneratorConfig,
    ProceduralBotanicalGenerator,
    ProceduralGeneratorConfig,
    generate_plant,
)

from .post_processor import (
    AssetDimensions,
    ExportedAsset,
    PostProcessorConfig,
    AssetPostProcessor,
    process_and_export,
)

from .validator import (
    ValidationReport,
    validate_asset,
    validate_directory,
)

from .renderer import (
    RenderConfig,
    render_asset_preview,
    render_contact_sheet,
)

__all__ = [
    "DimensionsSpec",
    "MorphologySpec",
    "MeshyPromptSpec",
    "VerificationCriteria",
    "PlantSpecies",
    "BotanicalCategory",
    "VegetationLibraryCatalog",
    "VegetationCatalog",
    "load_catalog",
    "get_catalog",
    "get_species",
    "get_species_by_category",
    "list_categories",
    "list_species_ids",
    "list_species",
    "CATEGORY_ALIASES",
    "REVERSE_CATEGORY_ALIASES",
    "UNIVERSAL_NEGATIVE_BLACKLIST",
    "RawAsset",
    "MeshyGenerator",
    "MeshyGeneratorConfig",
    "ProceduralBotanicalGenerator",
    "ProceduralGeneratorConfig",
    "generate_plant",
    "AssetDimensions",
    "ExportedAsset",
    "PostProcessorConfig",
    "AssetPostProcessor",
    "process_and_export",
    "ValidationReport",
    "validate_asset",
    "validate_directory",
    "RenderConfig",
    "render_asset_preview",
    "render_contact_sheet",
]
