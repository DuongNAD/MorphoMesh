# Milestone 1 (M1) Investigation & Architectural Specification Report: Botanical Taxonomy & Catalog Specification

**Project**: MorphoMesh Vegetation Library  
**Milestone**: M1 (Botanical Taxonomy & Catalog Specification)  
**Agent**: Explorer 1 (`.agents/m1_explorer_1`)  
**Date**: 2026-09-10  
**Target Module**: `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`  
**Target Tests**: `teamwork_projects/vegetation_library/tests/test_catalog.py`  

---

## 1. Observation

### 1.1 Authoritative Requirements & Target Metrics
From `teamwork_projects/vegetation_library/ORIGINAL_REQUEST.md` (lines 582–633):
> **R1. Comprehensive Botanical Taxonomy & Catalog Specification**  
> "Define an extensive, structured botanical catalog covering at least 30 distinct plant species across >= 6 major categories:  
> 1. Broadleaf & Deciduous Trees (e.g., Oak, Maple, Birch, Willow)  
> 2. Conifers & Evergreens (e.g., Pine, Spruce, Cypress)  
> 3. Tropical Foliage & Palms (e.g., Fan Palm, Monstera, Banana Plant, Fern Tree)  
> 4. Flowering Shrubs & Ornamental Plants (e.g., Rose Bush, Hydrangea, Lavender)  
> 5. Ferns, Grasses & Groundcover (e.g., Boston Fern, Tall Pampas Grass, Forest Moss clump)  
> 6. Succulents & Cacti (e.g., Saguaro Cactus, Aloe Vera, Echeveria)  
> 7. Climbing Vines & Epiphytes (e.g., English Ivy, Wisteria)  
> Each catalog item must specify scientific name, common name, morphological characteristics, and tuned botanical prompts (canopy shape, leaf clustering, trunk texture, floral accents)."

From `E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md` (lines 59–68):
> **M1 ↔ M2: Catalog Contract**  
> - `get_catalog() -> VegetationCatalog`: Returns all 35 species indexed by `species_id`.  
> - `PlantSpecies`:  
>   - `id: str` (e.g. `"quercus_robur"`)  
>   - `common_name: str` (e.g. `"English Oak"`)  
>   - `category: str` (one of: `"broadleaf_trees"`, `"conifers"`, `"tropical"`, `"shrubs"`, `"groundcover"`, `"succulents"`, `"vines"`)  
>   - `dimensions: DimensionsSpec` (`height_m: float`, `canopy_spread_m: float`, `trunk_stem_diameter_m: float`)  
>   - `morphology: MorphologySpec` (`branching_habit: str`, `foliage_density: str`, `leaf_type: str`, `bark_texture: str`)  
>   - `meshy_spec: MeshyPromptSpec` (`prompt: str`, `negative_prompt: str`, `art_style: str`, `target_polycount: int`)

### 1.2 Survey Artifact Audit (`taxonomy_catalog.json` & `generate_taxonomy_catalog.py`)
Investigation of survey artifacts at `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\`:
- File `taxonomy_catalog.json` (98,253 bytes) was inspected and parsed.
- Verified exact counts:
  - Total species: **35** (exceeding requirement of >= 30).
  - Total categories: **7** (exceeding requirement of >= 6).
  - Distribution: Exactly **5 species per category**.
- Integrity verification results:
  - Uniqueness: 35/35 `species_id`, 35/35 `common_name`, 35/35 `scientific_name` are 100% unique.
  - Physical dimensions: All `height_m > 0`, `canopy_spread_m > 0`, `trunk_stem_diameter_m > 0`, and `height_range_m[0] <= height_range_m[1]`.
  - Negative prompt blacklist: 100% of species contain the negative blacklist: `"pot, planter, flowerpot, terracotta, container, vase, pedestal, base stand, ground soil box, square block, platform, roots in pot, indoor room, wall, background, floor, furniture, table, saucer, human, hands, person, animal, insect, artificial plastic, low quality, deformed, floating leaves, disconnected branches, blurry, cartoon, toy, miniature, wireframe, baked lighting shadow"`.
  - Quality thresholds: Verification criteria mandate `3000 <= vertex_count <= 45000`, `enforce_zero_armature = True`, `enforce_root_pivot = True`, and all 4 PBR texture channels (`baseColor`, `normal`, `roughness`, `metallic`).

### 1.3 Execution Environment & Runtime Dependencies
- Python environment: Python 3.11.9 running via `uv run` in `E:\tool\mcp\MorphoMesh`.
- Pydantic version: **2.13.5** (`pydantic>=2.0.0`).
- Prototype schema and test execution:
  - Prototype script `proposed_catalog.py` and test suite `proposed_test_catalog.py` were created in `.agents/m1_explorer_1/`.
  - Executed: `uv run pytest .agents/m1_explorer_1/proposed_test_catalog.py -v`.
  - Result: **22 passed in 0.17s** with exit code `0`.

---

## 2. Logic Chain

### Step 1: Reconciling Survey Definitions with PROJECT.md Interface Contracts
- **Observation Reference**: Observation 1.1 specifies `id`, `category`, `prompt`, `branching_habit`, `bark_texture` in `PROJECT.md`, whereas `taxonomy_catalog.json` defines `species_id`, `category_id`, `positive_prompt`, `branching_pattern`, and `trunk_bark_texture`.
- **Deduction**:
  To achieve 100% bidirectional compatibility without data duplication, `catalog.py` must define primary fields matching the rich survey dataset while exposing property getters:
  1. `PlantSpecies.id -> species_id`
  2. `PlantSpecies.category -> category_id`
  3. `PlantSpecies.scientific_slug -> scientific_name.lower().replace(" ", "_")`
  4. `MorphologySpec.branching_habit -> branching_pattern`
  5. `MorphologySpec.bark_texture -> trunk_bark_texture`
  6. `MeshyPromptSpec.prompt -> positive_prompt`
  This guarantees that downstream code adhering to either `PROJECT.md` or `taxonomy_catalog.json` executes without attribute errors.

### Step 2: Category Nomenclature & Aliases
- **Observation Reference**: `PROJECT.md` uses shortened category labels (`"broadleaf_trees"`, `"conifers"`, `"tropical"`, `"shrubs"`, `"groundcover"`, `"succulents"`, `"vines"`), whereas `taxonomy_catalog.json` uses canonical identifiers (`"broadleaf_deciduous_trees"`, `"conifers_evergreens"`, `"tropical_foliage_palms"`, `"flowering_shrubs_ornamentals"`, `"ferns_grasses_groundcover"`, `"succulents_cacti"`, `"climbing_vines_epiphytes"`).
- **Deduction**:
  `get_species_by_category()` must accept both canonical IDs and alias mappings via a normalized `CATEGORY_ALIASES` table. This allows callers to write `get_species_by_category("conifers")` or `get_species_by_category("conifers_evergreens")` interchangeably.

### Step 3: Fast Multi-Index Species Retrieval
- **Observation Reference**: `PROJECT.md` contract mentions `id: str (e.g. "quercus_robur")`, while the catalog assigns primary keys like `"veg_tree_oak_01"`.
- **Deduction**:
  `get_species(identifier: str)` must resolve queries across multiple lookup indices in order of priority:
  1. Exact `species_id` match (`"veg_tree_oak_01"`)
  2. Scientific slug match (`"quercus_robur"`, `"quercus robur"`, `"Quercus robur"`)
  3. Common name match (`"english oak"`, `"English Oak"`, `"english_oak"`)
  All lookups must be case-insensitive and whitespace-tolerant.

### Step 4: Data Storage & Layout Compliance
- **Observation Reference**: Teamwork project rules forbid runtime dependencies on `.agents/` (`.agents/` holds only metadata; placing source, tests, or data there is a violation).
- **Deduction**:
  Production data cannot be read from `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json` at runtime. The M1 Worker must place `taxonomy_catalog.json` directly into `teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json`.
  `catalog.py` will load this file using `Path(__file__).resolve().parent / "taxonomy_catalog.json"`. This makes the library fully self-contained, portable, and operational both in standard CLI and inside Blender's embedded Python.

---

## 3. Caveats

1. **Self-Pruned Lower Branches vs Root Pivot**:
   - For mature trees (e.g. Scots Pine, English Oak), the bottom pivot is defined at ground contact ($Z=0$). In Meshy Text-to-3D, root flaring may occasionally generate tiny fragments below ground level. The M3 Post-Processor milestone will enforce $Z_{\min} = 0.0$, but the catalog correctly specifies `enforce_root_pivot: bool = True` in `VerificationCriteria` to mandate this downstream.
2. **Category Count: 7 Biomes vs 6 Minimum**:
   - The user request specifies ">= 6 major categories". The catalog defines exactly 7 categories (5 species each = 35 total). All 7 categories are fully specified and tested.
3. **Pydantic Model Config**:
   - All schemas use `ConfigDict(extra="ignore")` to permit forward-compatible extension attributes from downstream post-processors without breaking existing validations.

---

## 4. Conclusion & Implementation Plan for M1 Worker

The catalog architecture is completely designed, verified, and ready for immediate implementation by the M1 Worker.

### 4.1 Worker File Boundaries & Write Permissions
The M1 Worker has exclusive write ownership of the following target files:
- `teamwork_projects/vegetation_library/vegetation_pipeline/__init__.py`
- `teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json`
- `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`
- `teamwork_projects/vegetation_library/tests/__init__.py`
- `teamwork_projects/vegetation_library/tests/test_catalog.py`

**Out-of-Scope Files for M1 Worker**:
- `vegetation_pipeline/generator.py` (Assigned to M2)
- `vegetation_pipeline/post_processor.py` (Assigned to M3)
- `vegetation_pipeline/validator.py` (Assigned to M4)
- `vegetation_pipeline/renderer.py` (Assigned to M4)
- `pipeline.py` (Assigned to M4/M5)

### 4.2 Step-by-Step Instructions for M1 Worker

#### Step 1: Copy Canonical Taxonomy Catalog Data
Copy `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_veg_2\taxonomy_catalog.json` to `E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\vegetation_pipeline\taxonomy_catalog.json`.

#### Step 2: Implement `vegetation_pipeline/catalog.py`
Create `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py` using the verified code from `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_1\proposed_catalog.py`.

Key API signatures:
```python
# Pydantic v2 Schemas
class DimensionsSpec(BaseModel): ...
class MorphologySpec(BaseModel): ...
class MeshyPromptSpec(BaseModel): ...
class VerificationCriteria(BaseModel): ...
class PlantSpecies(BaseModel): ...
class BotanicalCategory(BaseModel): ...
class VegetationLibraryCatalog(BaseModel): ...

# Programmatic API
def load_catalog(json_path: Optional[Union[str, Path]] = None) -> VegetationLibraryCatalog: ...
def get_catalog(reload: bool = False, json_path: Optional[Union[str, Path]] = None) -> VegetationLibraryCatalog: ...
def get_species(identifier: str) -> PlantSpecies: ...
def get_species_by_category(category: str) -> List[PlantSpecies]: ...
def list_categories() -> List[str]: ...
def list_species_ids() -> List[str]: ...
```

#### Step 3: Implement `vegetation_pipeline/__init__.py`
Expose all public schemas and API functions:
```python
from .catalog import (
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

__all__ = [
    "DimensionsSpec",
    "MorphologySpec",
    "MeshyPromptSpec",
    "VerificationCriteria",
    "PlantSpecies",
    "BotanicalCategory",
    "VegetationLibraryCatalog",
    "get_catalog",
    "get_species",
    "get_species_by_category",
    "list_categories",
    "list_species_ids",
    "CATEGORY_ALIASES",
]
```

#### Step 4: Implement `tests/test_catalog.py`
Create `teamwork_projects/vegetation_library/tests/test_catalog.py` containing the 22 comprehensive test cases validating:
1. Catalog structure, total species (35), total categories (7).
2. Category distribution (exactly 5 species per category).
3. Lookup by `species_id`, scientific name, common name, and case insensitivity.
4. Category filtering and alias resolution (`broadleaf_trees`, `conifers`, `tropical`, `shrubs`, `groundcover`, `succulents`, `vines`).
5. Schema validation for dimensions (min > max height rejection).
6. Morphology properties (`branching_habit`, `bark_texture`).
7. Meshy prompt conditioning and negative keyword blacklist.
8. Verification criteria defaults (`min_vertices >= 3000`, `enforce_zero_armature = True`, 4 PBR maps).
9. Full JSON serialization round-trip.

---

## 5. Verification Method

### 5.1 Pre-Implementation Verification (Executed & Confirmed)
The proposed implementation and test suite were verified in the explorer environment:
```powershell
uv run pytest .agents\m1_explorer_1\proposed_test_catalog.py -v
```
Output:
```
============================= 22 passed in 0.17s ==============================
```

### 5.2 Post-Implementation Independent Verification Commands for Worker
After the Worker completes file writes, the following verification commands must be executed:

1. **Run M1 Catalog Test Suite**:
   ```powershell
   uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v
   ```
   *Expected Result*: All 22 tests pass with 0 failures (`exit code 0`).

2. **Run One-Line Catalog Sanity Assertion**:
   ```powershell
   uv run python -c "from teamwork_projects.vegetation_library.vegetation_pipeline import get_catalog, get_species, get_species_by_category, list_categories; cat = get_catalog(); assert len(cat) == 35; assert len(list_categories()) == 7; assert get_species('quercus_robur').common_name == 'English Oak'; assert len(get_species_by_category('broadleaf_trees')) == 5; print('M1 CATALOG VERIFIED 100% PASS')"
   ```
   *Expected Result*: Prints `M1 CATALOG VERIFIED 100% PASS`.

3. **Invalidation Conditions**:
   - Total species count $\ne 35$ or total categories $\ne 7$.
   - Any species missing negative prompt blacklist or physical dimensions.
   - Any test failure or import regression across `vegetation_pipeline`.
