# Project: Vegetation Library

## Architecture
The Vegetation Library is an automated generation pipeline and high-fidelity 3D botanical asset library leveraging Meshy AI Text-to-3D with an offline deterministic procedural botanical fallback. It produces 35 diverse, unrigged plant species across 7 major biomes with complete 4-channel PBR materials and clean topology.

### Module Boundaries & Data Flow
1. **Catalog Module (`vegetation_pipeline/catalog.py`)**:
   - Stores taxonomy specifications for 35 species across 7 categories.
   - Contains botanical morphology, real-world metric dimensions, and tuned Meshy AI prompts with negative blacklists.
2. **Generation Module (`vegetation_pipeline/generator.py`)**:
   - `MeshyGenerator`: Two-stage Text-to-3D (`preview` + `refine`) with polling, rate limiting, and disk caching.
   - `ProceduralBotanicalGenerator`: Offline deterministic 3D procedural generator using `MeshGeometry` and procedural PBR texture synthesis (`numpy` + `PIL.Image`).
3. **Post-Processing & Normalization (`vegetation_pipeline/post_processor.py`)**:
   - Computes bottom 5% contact centroid to ground root pivot at $Z_{\min} = 0.0$ (Blender) / $Y_{\min} = 0.0$ (glTF).
   - Normalizes metric scale according to catalog height/canopy targets.
   - Exports production `.glb` (glTF 2.0 binary with embedded PBR textures) and companion `.obj`/`.mtl`.
4. **Validation & Testing Suite (`vegetation_pipeline/validator.py`, `tests/`)**:
   - Inspects GLB/OBJ files: asserts 0 armatures/bones/weights, 3,000–45,000 vertices, zero NaN/Inf coordinates, valid unit normals, and non-black PBR maps.
5. **Headless Renderer (`vegetation_pipeline/renderer.py`)**:
   - Invokes Blender 4.5.4 LTS in background mode to render multi-angle turntable and thumbnail images (Isometric hero, Front, Side, Top-down).
6. **Master Pipeline Orchestrator (`pipeline.py`)**:
   - CLI interface supporting `--species`, `--category`, `--all`, `--mode` (meshy/procedural/auto), and `--render`.

---

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Botanical Taxonomy Catalog | 35 distinct species across 7 biomes with scientific/common names, family, dimensions | M1 | Survey (Explorer 2) |
| 2 | Botanical Prompt Conditioning | Tuned positive prompt templates + universal negative blacklist eliminating pots/stands/humans | M1 | Survey (Explorer 2) |
| 3 | Meshy AI Generation Client | Two-stage Text-to-3D client (preview + refine/boost) with polling, backoff, and caching | M2 | Survey (Explorer 1) |
| 4 | Offline Procedural Fallback | Deterministic 3D botanical mesh + PBR texture generator for all 7 plant categories | M2 | Survey (Explorer 1, 3) |
| 5 | Pivot Ground Snapping | Contact centroid alignment placing root base at origin ($Z_{\min} = 0$, $Y_{\min} = 0$) | M3 | Survey (Explorer 3) |
| 6 | Metric Scale Normalization | Scaling to real-world botanical dimensions (trees 8-12m, shrubs 1-2m, groundcover 0.2-1m) | M3 | Survey (Explorer 3) |
| 7 | Dual-Format Export | Production GLB (embedded PBR) and companion Wavefront OBJ/MTL packaging | M3 | Survey (Explorer 1, 3) |
| 8 | Categorized Asset Organization | Directory hierarchy by biome category with per-asset and global `manifest.json` | M3 | Survey (Explorer 1, 2) |
| 9 | Static Mesh Integrity Verifier | Asserts zero bones, zero armatures, zero bone weights, zero skinning clusters in GLB/OBJ | M4 | Survey (Explorer 3) |
| 10 | Geometry Quality Verifier | Asserts 3k-45k vertices, zero NaN/Inf, manifold edges, non-degenerate faces, unit normals | M4 | Survey (Explorer 3) |
| 11 | PBR Texture Verifier | Asserts valid Albedo, Normal, Roughness, Metallic channels (non-black, proper ranges) | M4 | Survey (Explorer 3) |
| 12 | Headless Visual Showcase | Blender 4.5.4 LTS multi-angle turntable and thumbnail contact sheet rendering | M4 | Survey (Explorer 1, 3) |
| 13 | End-to-End Test Suite | Comprehensive 4-tier test suite (`test_vegetation_pipeline.py`) passing 100% | M5 | Survey (Explorer 3) |
| 14 | Full 35-Species Generation | Batch generation and verification of all 35 species with complete deliverables | M5 | User Request |

---

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Botanical Taxonomy & Catalog Specification | `vegetation_pipeline/catalog.py`, `tests/test_catalog.py`, taxonomy schemas | none | DONE |
| M2 | Generation Engine & Fallback Harness | `vegetation_pipeline/generator.py`, `tests/test_generator.py` | M1 | DONE |
| M3 | Asset Post-Processing & Multi-Format Export | `vegetation_pipeline/post_processor.py`, `tests/test_normalization.py` | M1, M2 | DONE |
| M4 | Inspection Suite & Preview Visuals | `vegetation_pipeline/validator.py`, `vegetation_pipeline/renderer.py`, `pipeline.py` | M1, M2, M3 | DONE |
| M5 | Full Library Generation & Final Verification | Generate all 35 species, execute E2E test suite, render visuals, forensic audit | M1, M2, M3, M4 | DONE |

---

## Interface Contracts

### M1 ↔ M2: Catalog Contract
- `get_catalog() -> VegetationCatalog`: Returns all 35 species indexed by `species_id`.
- `PlantSpecies`:
  - `id: str` (e.g. `"quercus_robur"`)
  - `common_name: str` (e.g. `"English Oak"`)
  - `category: str` (one of: `"broadleaf_trees"`, `"conifers"`, `"tropical"`, `"shrubs"`, `"groundcover"`, `"succulents"`, `"vines"`)
  - `dimensions: DimensionsSpec` (`height_m: float`, `canopy_spread_m: float`, `trunk_stem_diameter_m: float`)
  - `morphology: MorphologySpec` (`branching_habit: str`, `foliage_density: str`, `leaf_type: str`, `bark_texture: str`)
  - `meshy_spec: MeshyPromptSpec` (`prompt: str`, `negative_prompt: str`, `art_style: str`, `target_polycount: int`)

### M2 ↔ M3: Generator Output Contract
- `generate_plant(species: PlantSpecies, mode: str = "auto", output_dir: Path) -> RawAsset`:
  - Returns `RawAsset` containing:
    - `mesh: MeshGeometry` (or path to raw downloaded `.glb`)
    - `textures: Dict[str, Image.Image]` (albedo, normal, roughness, metallic)
    - `source: str` (`"meshy"` or `"procedural"`)
    - `metadata: Dict[str, Any]`

### M3 ↔ M4: Processed Asset Contract
- `process_and_export(raw_asset: RawAsset, species: PlantSpecies, output_dir: Path) -> ExportedAsset`:
  - Outputs:
    - `<species_id>.glb` (glTF 2.0 binary with embedded PBR textures, $Y_{\min} \approx 0$)
    - `<species_id>.obj` + `<species_id>.mtl` (Wavefront OBJ with materials)
    - `textures/` (`albedo.png`, `normal.png`, `roughness.png`, `metallic.png`)
    - `asset_manifest.json` (metadata, bounding box, vertex/face count)
  - Returns `ExportedAsset(glb_path, obj_path, texture_paths, manifest_path)`

### M4 ↔ M5: Validator & Renderer Contract
- `validate_asset(exported_asset: ExportedAsset) -> ValidationReport`:
  - `is_valid: bool`
  - `zero_armatures: bool`
  - `grounded_pivot: bool` ($Z_{\min} \approx 0$ or $Y_{\min} \approx 0$)
  - `vertex_count: int` ($3,000 \le V \le 45,000$)
  - `textures_valid: bool`
  - `errors: List[str]`
- `render_asset_preview(glb_path: Path, output_image: Path) -> Path`:
  - Generates multi-angle or isometric preview render.

---

## Code Layout
```
teamwork_projects/vegetation_library/
├── ORIGINAL_REQUEST.md
├── TEST_INFRA.md
├── TEST_READY.md
├── pipeline.py                      # Master pipeline orchestration CLI
├── vegetation_pipeline/             # Main Python module
│   ├── __init__.py
│   ├── catalog.py                   # 35 species catalog (taxonomy, prompts, metrics)
│   ├── generator.py                 # Meshy AI client + Procedural Botanical Fallback
│   ├── post_processor.py            # Grounding, scaling, quad/tri validation, GLB/OBJ packaging
│   ├── validator.py                 # Structural QA (manifold, 0 bones, 3k-45k verts, textures)
│   └── renderer.py                  # Blender 4.5 headless turntable / thumbnail renderer
├── tests/
│   ├── __init__.py
│   ├── test_catalog.py              # Taxonomy & prompt verification
│   ├── test_generator.py            # Meshy AI & procedural fallback tests
│   ├── test_normalization.py        # Pivot grounding & scale checks
│   └── test_vegetation_pipeline.py  # End-to-end integration & QA assertions
└── output/                          # Categorized assets with manifests
    ├── broadleaf_trees/
    ├── conifers/
    ├── tropical/
    ├── shrubs/
    ├── groundcover/
    ├── succulents/
    ├── vines/
    └── manifest.json
```
