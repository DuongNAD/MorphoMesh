# Milestone 1 (M1) Test Design & Unit Test Suite Specification Report

**Project**: MorphoMesh Vegetation Library  
**Milestone**: M1 (Botanical Taxonomy & Catalog Specification)  
**Agent**: Explorer 3 (`.agents/m1_explorer_3`)  
**Date**: 2026-09-10  
**Target Module Under Test**: `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`  
**Target Test Suite**: `teamwork_projects/vegetation_library/tests/test_catalog.py`  
**Target Test Config**: `teamwork_projects/vegetation_library/tests/conftest.py`  
**Deliverables in Explorer Directory**:
- `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\prototype_test_catalog.py` (Validated prototype test harness, 335 tests passing in 0.31s)
- `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_test_catalog.py` (Drop-in production test suite for M1 Worker)
- `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_conftest.py` (Drop-in pytest configuration for M1 Worker)

---

## 1. Observation

### 1.1 Authoritative Requirements & Target Specifications
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

### 1.2 Survey Catalog & Peer Explorer Analysis
1. **Catalog Dataset** (`.agents/explorer_survey_veg_2/taxonomy_catalog.json`):
   - Total species count: **35** (exceeds requirement of $\ge 30$).
   - Total categories count: **7** (exceeds requirement of $\ge 6$).
   - Uniform distribution: Exactly **5 species per category**.
   - Categories present:
     - `broadleaf_deciduous_trees`
     - `conifers_evergreens`
     - `tropical_foliage_palms`
     - `flowering_shrubs_ornamentals`
     - `ferns_grasses_groundcover`
     - `succulents_cacti`
     - `climbing_vines_epiphytes`
2. **Explorer 1 Architecture** (`.agents/m1_explorer_1/proposed_catalog.py`):
   - Pydantic v2 schemas: `DimensionsSpec`, `MorphologySpec`, `MeshyPromptSpec`, `VerificationCriteria`, `PlantSpecies`, `BotanicalCategory`, `VegetationLibraryCatalog`.
   - Programmatic API: `get_catalog()`, `get_species(identifier)`, `get_species_by_category(category)`, `list_categories()`, `list_species_ids()`, `list_species()`.
   - Bidirectional contract compatibility properties:
     - `PlantSpecies.id -> species_id`
     - `PlantSpecies.category -> category_id`
     - `PlantSpecies.scientific_slug -> scientific_name.lower().replace(" ", "_")`
     - `MorphologySpec.branching_habit -> branching_pattern`
     - `MorphologySpec.bark_texture -> trunk_bark_texture`
     - `MeshyPromptSpec.prompt -> positive_prompt`
3. **Explorer 2 Audit Findings** (`.agents/m1_explorer_2/audit_catalog.py`):
   - 100% of species positive prompts contain standalone/ground-rooted anchor tokens (`"standalone"` or `"single"` with `"ground"`, `"rooted"`, or `"growing"`).
   - 100% of species contain the negative blacklist tokens: `"pot, planter, flowerpot, terracotta, container, vase, pedestal, base stand, ground soil box, square block, platform, roots in pot, indoor room, wall, background, floor, furniture, table, saucer, human, hands, person, animal, insect, artificial plastic, low quality, deformed, floating leaves, disconnected branches, blurry, cartoon, toy, miniature, wireframe, baked lighting shadow"`.
   - All metric dimensions have $H > 0$, $W > 0$, $D > 0$.

### 1.3 Empirical Test Execution & Botanical Boundary Discovery
Execution of initial test prototype revealed two critical botanical boundary edge cases in `prototype_test_catalog.py`:
```
FAILED test_botanical_proportions_and_sanity[veg_ground_moss_01]:
AssertionError: Trunk diameter 0.45 exceeds canopy spread 0.45 in veg_ground_moss_01 (assert 0.45 < 0.45)

FAILED test_botanical_proportions_and_sanity[veg_ground_grass_01]:
AssertionError: Trunk diameter 0.5 exceeds height 0.45 in veg_ground_grass_01 (assert 0.5 < 0.45)
```
- For cushion moss (`Leucobryum glaucum`), the growth habit is a hemispherical mat dome where base diameter equals canopy spread ($D = W = 0.45\text{m}$). Therefore, $D \le W$ holds, but strict $D < W$ is violated.
- For tussock grasses (`Hakonechloa macra`), the basal clump diameter ($D = 0.5\text{m}$) exceeds the arching foliage height ($H = 0.45\text{m}$).
- Re-tuning the boundary assertion: $D \le W$ for all plants, and $D < H$ for upright woody species (`broadleaf_deciduous_trees`, `conifers_evergreens`, `flowering_shrubs_ornamentals`).
- Upon incorporating this adjustment, the prototype test suite executed:
```powershell
uv run pytest .agents/m1_explorer_3/prototype_test_catalog.py -v
```
Output:
```
============================= 335 passed in 0.31s =============================
```
100% of 335 assertion points passed with zero failures.

---

## 2. Logic Chain

### Step 1: Formulating 8 Distinct Testing Dimensions
- **Observation Reference**: Section 1.1 requires verifying taxonomy, botanical naming, metric dimensions, Meshy prompts, negative blacklists, and querying functions.
- **Deduction**:
  To guarantee full coverage without gaps, the test suite must be organized into 8 targeted test classes:
  1. `TestCatalogCompletenessAndScale`: Total species ($\ge 30, == 35$), total categories ($\ge 6, == 7$), uniform distribution (5/category), identifier uniqueness.
  2. `TestTaxonomyAndBotanicalNomenclature`: Regex validation of `species_id` (`^veg_[a-z0-9_]+$`), non-empty strings, binomial nomenclature (Genus capitalized, specific epithet lowercase), family ending in `-aceae`, valid biomes.
  3. `TestBotanicalMetricDimensions`: Strictly positive values ($H > 0, W > 0, D > 0$), valid range ordering ($0 < \min \le \max$), height containment ($\min \le H \le \max$), and botanical proportion sanity ($D \le W$ globally, $D < H$ for erect woody species).
  4. `TestMeshyPromptConditioningAndBlacklists`: Prompt length $\ge 50$, contains common name/genus, contains standalone anchor (`"standalone"` or `"single"`), contains botanical/PBR keywords, contains all 20 mandatory blacklist tokens, and correct Meshy API hyperparameters (`meshy-4`, `realistic`, `quad`, 10k–45k polycount, `enable_pbr=True`, `boost=True`).
  5. `TestAssetVerificationCriteria`: Vertex boundaries ($3000 \le V \le 45000$), `enforce_zero_armature=True`, `enforce_root_pivot=True`, and 4 mandatory PBR channels.
  6. `TestQueryingHelperFunctions`: `get_species` (by ID, scientific slug, common name case-insensitively, KeyError on nonexistent), `get_species_by_category` (by canonical ID and aliases, KeyError on invalid category), `list_categories` (7 categories), `list_species_ids` (35 IDs), `list_species` (35 instances).
  7. `TestInterfaceContractsAndAliases`: Parameterized verification that all 35 species expose the M1 ↔ M2 contract attributes (`.id`, `.category`, `.prompt`, `.branching_habit`, `.bark_texture`, `.scientific_slug`).
  8. `TestPydanticSerializationAndValidation`: Model round-tripping (`model_dump()`, `model_validate()`, `model_dump_json()`), rejection of invalid height ranges ($\min > \max$), negative dimensions, and malformed IDs.

### Step 2: Parametrization Strategy for Exhaustive Verification
- **Observation Reference**: A single catalog test asserting `assert len(catalog.species) == 35` does not detect if species #27 has an invalid prompt or negative height.
- **Deduction**:
  Tests for taxonomy, dimensions, prompts, and verification criteria must be parameterized across all 35 species using `@pytest.mark.parametrize` or parameterized test loops over `all_species`.
  This transforms the suite into 335 granular checkpoints, ensuring that if any single species in the catalog has a defect, the exact failing species ID is isolated instantly in pytest output.

### Step 3: Test Infrastructure & Path Resolution (`conftest.py`)
- **Observation Reference**: In the root repository, `pyproject.toml` defines `pythonpath = ["src"]`. Running `uv run pytest teamwork_projects/vegetation_library/tests -v` from the repository root fails to find `vegetation_pipeline` unless the test directory explicitly adds `teamwork_projects/vegetation_library` to `sys.path`.
- **Deduction**:
  A dedicated `conftest.py` must be placed in `teamwork_projects/vegetation_library/tests/conftest.py`:
  ```python
  PROJECT_DIR = Path(__file__).resolve().parent.parent
  REPO_ROOT = PROJECT_DIR.parent.parent
  if str(PROJECT_DIR) not in sys.path:
      sys.path.insert(0, str(PROJECT_DIR))
  if str(REPO_ROOT) not in sys.path:
      sys.path.insert(0, str(REPO_ROOT))
  ```
  This guarantees that tests run reliably whether executed from repo root (`uv run pytest teamwork_projects/vegetation_library/tests`) or from within the project directory.

---

## 3. Caveats

1. **Basal Caliper vs Canopy Spread in Cushion Flora**:
   - For prostrate mats and cushion mosses (e.g. *Leucobryum glaucum*), base diameter equals canopy spread ($D = W = 0.45\text{m}$). The test assertion must use `d <= w + 1e-6` rather than `d < w`.
2. **Basal Caliper vs Height in Tussock Grasses**:
   - For spreading tussock grasses (e.g. *Hakonechloa macra*), basal clump diameter ($0.5\text{m}$) exceeds foliage height ($0.45\text{m}$). The rule $D < H$ must only be asserted on erect woody plants (trees, conifers, and upright flowering shrubs).
3. **Pydantic Validation Performance**:
   - Running full Pydantic v2 validation and 335 assertions takes 0.31 seconds in memory. This is well within fast unit test thresholds (< 1.0s), meaning no mocking or stubbing is necessary.

---

## 4. Conclusion & Implementation Blueprint for M1 Worker

The testing strategy and unit test suite for Milestone 1 are completely designed, validated, and packaged into drop-in files.

### 4.1 Worker File Deliverables
The M1 Worker must write the following two test files:
1. `teamwork_projects/vegetation_library/tests/conftest.py`:
   - Source code provided in `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_conftest.py`.
2. `teamwork_projects/vegetation_library/tests/test_catalog.py`:
   - Source code provided in `E:\tool\mcp\MorphoMesh\.agents\m1_explorer_3\proposed_test_catalog.py`.

### 4.2 Summary of Test Suite Capabilities
| Test Class | Scope | Invariants Verified |
|---|---|---|
| `TestCatalogCompletenessAndScale` | Catalog scale & structure | $\ge 30$ species (35 exact), $\ge 6$ categories (7 exact), 5 species/category, 0 duplicate IDs. |
| `TestTaxonomyAndBotanicalNomenclature` | Botanical naming & classification | Regex `^veg_[a-z0-9_]+$`, non-empty strings, Binomial names (Capitalized Genus, lowercase epithet), families in `-aceae`. |
| `TestBotanicalMetricDimensions` | Physical scale & proportions | $H > 0, W > 0, D > 0$, $\min \le H \le \max$, $D \le W$ globally, $D < H$ for erect woody species, height in $[0.05\text{m}, 45.0\text{m}]$. |
| `TestMeshyPromptConditioningAndBlacklists` | Meshy AI prompt conditioning | Length $\ge 50$, contains common name/genus, standalone/ground anchors, all 20 mandatory blacklist tokens present, Meshy-4 quad params. |
| `TestAssetVerificationCriteria` | Structural asset QA contracts | $3000 \le V \le 45000$, zero armatures enforced, root pivot enforced, 4 PBR channels (`baseColor`, `normal`, `roughness`, `metallic`). |
| `TestQueryingHelperFunctions` | Programmatic query API | `get_species` (by ID, slug, common name, case-insensitivity, KeyError on missing), `get_species_by_category` (canonical + 8 aliases), `list_categories`, `list_species_ids`. |
| `TestInterfaceContractsAndAliases` | M1 ↔ M2 cross-module contract | Validates compatibility properties `.id`, `.category`, `.prompt`, `.branching_habit`, `.bark_texture`, `.scientific_slug` on all 35 species. |
| `TestPydanticSerializationAndValidation` | Serialization & edge rejection | Full dictionary and JSON round-tripping, rejection of inverted height ranges ($\min > \max$), negative values, and malformed IDs. |

---

## 5. Verification Method

### 5.1 Independent Verification Command
After the M1 Worker implements `catalog.py`, `conftest.py`, and `test_catalog.py`, the test suite must be executed using:

```powershell
# Run the entire M1 catalog test suite
uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v
```

**Expected Result**:
```
============================= 335 passed in 0.31s =============================
Exit Code: 0
Failures: 0
Errors: 0
```

### 5.2 Targeted Class and Parametric Executions
```powershell
# Test catalog scale and completeness only
uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -k "Scale" -v

# Test dimensions and botanical bounds only
uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -k "Dimensions" -v

# Test Meshy prompt conditioning and blacklists only
uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -k "Prompt" -v

# Test query helpers and alias lookups only
uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -k "Helper" -v
```

### 5.3 Invalidation Conditions
The verification fails and requires worker intervention if:
1. Total species count $< 30$ or $\ne 35$.
2. Any category has $\ne 5$ species.
3. Any species fails the binomial nomenclature test or family `-aceae` check.
4. Any metric dimension is $\le 0$ or violates height range bounds.
5. Any species is missing any of the 20 mandatory negative blacklist tokens.
6. Lookups by category aliases (e.g. `broadleaf_trees`, `conifers`, `shrubs`) raise KeyError.
7. Any test exits with code $\ne 0$.
