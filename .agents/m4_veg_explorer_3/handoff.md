# M4 Vegetation Explorer 3: Handoff Report

## Executive Summary
This handoff report delivers the exhaustive architectural investigation, technical specification, and implementation designs for:
1. **Master Pipeline CLI Runner (`teamwork_projects/vegetation_library/pipeline.py`)**: A production-grade CLI runner coordinating catalog resolution, Meshy AI / procedural fallback generation, pivot grounding, metric normalization, dual-format GLB/OBJ packaging, automated QA inspection, Blender 4.5.4 LTS headless preview rendering, incremental global manifest aggregation (`output/manifest.json`), and formatted Markdown summary table generation.
2. **QA Test Suite (`teamwork_projects/vegetation_library/tests/test_validator.py`)**: A comprehensive 12-scenario unit and integration test suite asserting static mesh, geometric, topological, coordinate, scale, and PBR material invariants.

Both modules have been prototyped and validated directly in the target environment:
- `proposed_pipeline.py` successfully executed single-species procedural generation, normalization, validation, manifest aggregation, and summary reporting in 0.18s.
- `proposed_test_validator.py` was executed with `pytest` against the 20 inspection checks of Explorer 1's validator, achieving **12/12 PASSED in 1.65 seconds** (100% pass rate).

---

## 1. Observation

### 1.1 Existing Codebase Contracts & Signatures
1. **Catalog Module (`teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`)**:
   - Lines 42-74: `DimensionsSpec` enforces positive metric dimensions: `height_m: float`, `height_range_m: Tuple[float, float]`, `canopy_spread_m: float`, `trunk_stem_diameter_m: float`.
   - Lines 131-166: `PlantSpecies` schema with `species_id`, `common_name`, `scientific_name`, `category_id`, `short_category` property mapping to the 7 canonical output folders (`broadleaf_trees`, `conifers`, `tropical`, `shrubs`, `groundcover`, `succulents`, `vines`).
   - Lines 341-368: `get_species(identifier: str) -> PlantSpecies`: case-insensitive lookup supporting species IDs, scientific names, and common names.
   - Lines 370-388: `get_species_by_category(category: str) -> List[PlantSpecies]`: resolves canonical and alias category names.
   - Lines 402-406: `list_species() -> List[PlantSpecies]`: returns all 35 species.
2. **Generator Module (`teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`)**:
   - Lines 55-82: `unpack_glb_header_and_json(glb_path: Union[str, Path]) -> Tuple[Dict[str, Any], bytes]`: extracts 12-byte header, JSON chunk 0, and binary buffer chunk 1.
   - Lines 117-156: `RawAsset` model: `species_id: str`, `glb_path: Path`, `mesh: Optional[MeshGeometry]`, `textures: Dict[str, Image.Image]`, `source: Literal["meshy", "procedural", "cached"]`.
   - Lines 1460-1522: `generate_plant(species, mode="auto", output_dir=None, seed=None, force_regenerate=False) -> RawAsset`: procedural fallback takes ~0.10s per asset.
3. **Post-Processor Module (`teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py`)**:
   - Lines 95-153: `ExportedAsset` model: `species_id: str`, `glb_path: Path`, `obj_path: Path`, `mtl_path: Path`, `texture_paths: Dict[str, Path]`, `manifest_path: Path`, `dimensions: AssetDimensions`, `vertex_count: int`, `face_count: int`, `ground_pivot_z: float`, `base_centroid: Tuple[float, float]`.
   - Lines 430-436: `export_production_glb(mesh: MeshGeometry, filepath: Union[str, Path], textures: Dict[str, Image.Image], species_id: str = "botanical_asset", double_sided: bool = True) -> Path`.
     * **CRITICAL OBSERVATION**: The argument order is `(mesh, filepath, textures, ...)` - `filepath` is argument 2, `textures` is argument 3.
   - Lines 1025-1034: `process_and_export(raw_asset: RawAsset, species: Union[PlantSpecies, str], output_dir: Optional[Union[str, Path]] = None, config: Optional[PostProcessorConfig] = None) -> ExportedAsset`.
4. **Existing Test Suite Baseline**:
   - Running `pytest teamwork_projects/vegetation_library/tests -q` yielded: `222 passed in 9.21s`.

### 1.2 M4 Peer Explorer Findings
1. **Explorer 1 (`proposed_validator.py` & `handoff.md`)**:
   - Delivered a pure Python/NumPy validator with zero external dependencies (no trimesh/pygltflib required).
   - Functions: `validate_asset(asset: Union[ExportedAsset, Path], catalog: Optional[VegetationCatalog] = None) -> ValidationReport`, `validate_directory(output_dir: Path, catalog: Optional[VegetationCatalog] = None) -> Dict[str, ValidationReport]`.
   - Evaluates 20 distinct checks:
     * `zero_nan_inf_coordinates`
     * `vertex_count_budget` ([3,000, 45,000])
     * `normals_finite_and_unit` (||n|| == 1.0 +/- 0.05)
     * `non_degenerate_faces` (no duplicate indices, area > 1e-8)
     * `ground_contact_base_aligned` (Z_min or Y_min == 0.000m +/- 0.005m)
     * `base_contact_centroid_centered` (bottom 5% slice centered at (0, 0) +/- 0.05m)
     * `metric_scale_bounds` (height within +/- 10% of catalog target)
     * `static_mesh_no_skins`, `static_mesh_no_animations`, `static_mesh_no_joint_weights`, `static_mesh_no_node_skins`
     * `obj_no_bones`, `n_bones_strictly_zero`
     * `textures_channels_present`, `textures_readable_and_sized` (>= 256x256)
     * `texture_albedo_plausible` (mean > 0.05, std > 0.02)
     * `texture_normal_plausible` (mean nz in [0.5, 1.0], magnitude ~= 1.0)
     * `texture_roughness_plausible` (mean in [0.20, 0.95], std > 0.01)
     * `texture_metallic_dielectric` (max <= 0.05, mean <= 0.02)
     * `glb_container_valid`
2. **Explorer 2 (`test_renderer_module.py` & Blender 4.5.4 LTS)**:
   - System has Blender 4.5.4 LTS at `C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`.
   - Contract: `render_asset_preview(glb_path: Union[str, Path], output_image: Optional[Union[str, Path]] = None, config: Optional[RenderConfig] = None) -> Path`.
   - Produces `thumbnail.png` via 4-angle turntable contact sheet (Hero, Front, Side, Crown) with EEVEE Next / Cycles, plus pure-Python software projection fallback when Blender is absent.

### 1.3 Windows Console Encoding Trap
- On Windows systems, default PowerShell console encoding is `cp1252`. Printing Unicode characters like checkmark `\u2705` raises `UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'`.
- Verified solution: Calling `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` and `sys.stderr.reconfigure(encoding="utf-8", errors="replace")` in `pipeline.py:main()` guarantees clean Unicode table formatting across Windows and POSIX shells.

---

## 2. Logic Chain

### 2.1 Master Pipeline Architecture (`pipeline.py`)
The pipeline runner is designed around an end-to-end chaining model:

```
[Target Resolution]
  --species <id>  |  --category <name>  |  --all
        |
        v
[Lifecycle Loop per Species]
  1. generate_plant(species, mode=mode, seed=seed)
        |
        v
  2. process_and_export(raw_asset, species, output_dir=species_dir)
        |
        v
  3. validate_asset(exported_asset)  [Bypassed if --skip-validate or --render-only]
        |
        v
  4. render_asset_preview(glb_path, output_image=thumb_path)  [Bypassed if --skip-render or --validate-only]
        |
        v
[Aggregate Manifest Update]
  Update output/manifest.json (Incremental merge of new & existing assets)
        |
        v
[Summary Reporting]
  Print Markdown Summary Table (--summary) / Output JSON (--json)
```

#### CLI Argument Specification
| Argument | Type | Default | Purpose |
|:---|:---:|:---:|:---|
| `--species`, `-s` | `str` | `None` | Run pipeline for single species ID, scientific name, or common name |
| `--category`, `-c` | `str` | `None` | Run pipeline for all species in a biome category |
| `--all`, `-a` | `flag` | `False` | Run pipeline across all 35 catalog species |
| `--mode`, `-m` | `choice` | `"auto"` | Generation mode: `"auto"`, `"meshy"`, or `"procedural"` |
| `--seed` | `int` | `None` | Deterministic random seed for procedural generator |
| `--output-dir`, `-o` | `Path` | `Path("output")` | Destination folder for library deliverables |
| `--force`, `-f` | `flag` | `False` | Force asset re-generation, ignoring disk cache |
| `--skip-render` | `flag` | `False` | Skip Blender thumbnail preview rendering |
| `--skip-validate` | `flag` | `False` | Skip QA validation checks |
| `--validate-only` | `flag` | `False` | Validate existing output assets without re-generating geometry |
| `--render-only` | `flag` | `False` | Render preview thumbnails for existing output assets |
| `--summary` | `flag` | `False` | Print formatted Markdown summary table of all library assets |
| `--json` | `flag` | `False` | Output execution results and manifest as JSON to stdout |
| `--verbose`, `-v` | `flag` | `False` | Enable DEBUG level logging |

#### Global Manifest Aggregation Schema (`output/manifest.json`)
The manifest records:
- Metadata: `schema_version`, `project`, `generated_at`, `total_catalog_species`, `indexed_species_count`, `passed_validation_count`, `failed_validation_count`.
- Category breakdown: `categories_summary` tracking total, indexed, and passing assets per biome.
- Asset entries: mapped by `species_id`, containing botanical taxonomy, metric dimensions, bounding box, vertex/face counts, ground pivot Z, base contact centroid, relative file paths (`glb`, `obj`, `mtl`, `textures`, `thumbnail`, `asset_manifest`), validation report (`is_valid`, `checks`, `metrics`, `errors`, `warnings`), and timestamp.
- **Incremental Merge Guarantee**: New pipeline runs update or add their target species without erasing previously generated species records.

#### Formatted Summary Table
The table formats columns:
`Category | Species ID | Common Name | Scientific Name | Height (m) | Canopy (m) | Vertices | Faces | Source | Verdict | Thumbnail`
Followed by a Biome Categories Breakdown summarizing generation and validation progress.

---

### 2.2 QA Test Suite Design (`tests/test_validator.py`)
To ensure rapid, deterministic CI testing without network or GPU dependencies, tests use:
1. Genuine procedural plant assets via `generate_plant(..., mode="procedural")` for positive integration tests.
2. Lightweight pure-Python synthetic mesh generators (`MeshGeometry` + `export_production_glb`) to produce exact boundary-condition failures in milliseconds.
3. Binary GLB modification helpers (`repack_glb_json`) that parse and mutate the glTF JSON chunk to inject rigging or strip texture channels.

#### Test Matrix Mapping (12 Test Scenarios)
1. **`test_valid_asset_passes_all_checks`**:
   - Action: Generates genuine procedural `veg_tree_oak_01` (English Oak), exports via `process_and_export`.
   - Assertions: `report.is_valid is True`, `len(report.errors) == 0`, `report.checks["vertex_count_budget"] is True`, `report.checks["ground_contact_base_aligned"] is True`, `report.checks["n_bones_strictly_zero"] is True`. Validating directory also passes.
2. **`test_vertex_count_under_budget_fails`**:
   - Action: Mocks mesh with exactly 1,500 vertices (< 3,000 threshold).
   - Assertions: `report.is_valid is False`, `report.checks["vertex_count_budget"] is False`, error mentions "under budget" or "minimum".
3. **`test_vertex_count_over_budget_fails`**:
   - Action: Mocks mesh with 50,000 vertices (> 45,000 threshold).
   - Assertions: `report.is_valid is False`, `report.checks["vertex_count_budget"] is False`, error mentions "over budget" or "maximum".
4. **`test_ungrounded_pivot_fails`**:
   - Action: Mocks mesh shifted by Z_offset = +1.0m (Z_min = 1.0m > 0.005m).
   - Assertions: `report.is_valid is False`, `report.checks["ground_contact_base_aligned"] is False`, error mentions "ground" or "pivot".
5. **`test_uncentered_centroid_fails`**:
   - Action: Mocks mesh shifted horizontally by X_offset = +0.5m (centroid offset = 0.5m > 0.05m).
   - Assertions: `report.is_valid is False`, `report.checks["base_contact_centroid_centered"] is False`, error mentions "centroid" or "center".
6. **`test_nan_inf_coordinates_fails`**:
   - Action: Injects `float("nan")` into vertex coordinates.
   - Assertions: `report.is_valid is False`, `report.checks["zero_nan_inf_coordinates"] is False`, error mentions "nan" or "inf".
7. **`test_armature_or_skinning_fails`**:
   - Action: Repacks GLB with `"skins": [{"joints": [0, 1]}]` and primitive attribute `"JOINTS_0": 0`.
   - Assertions: `report.is_valid is False`, `report.checks["static_mesh_no_skins"] is False` or `report.checks["n_bones_strictly_zero"] is False`, error mentions "skin", "armature", or "joint".
8. **`test_solid_black_texture_fails`**:
   - Action: Replaces albedo map with solid black `(0, 0, 0)` image (mean = 0.0 <= 0.05).
   - Assertions: `report.is_valid is False`, `report.checks["texture_albedo_plausible"] is False`, error mentions "black" or "dark".
9. **`test_missing_texture_channel_fails`**:
   - Action: Omits `normal.png` from `textures/` and strips `normalTexture` from GLB material.
   - Assertions: `report.is_valid is False`, `report.checks["textures_channels_present"] is False`, error mentions "normal" or "missing".
10. **`test_non_dielectric_metallic_fails`**:
    - Action: Sets metallic texture to 255 (metal = 1.0 > 0.05).
    - Assertions: `report.is_valid is False`, `report.checks["texture_metallic_dielectric"] is False`, error mentions "metallic" or "dielectric".
11. **`test_corrupt_glb_fails`**:
    - Action: Passes truncated 30-byte invalid container `b"glTF\x02\x00\x00\x00truncated..."`.
    - Assertions: `report.is_valid is False`, `report.checks["glb_container_valid"] is False`, error caught gracefully without crash.
12. **`test_validate_directory`**:
    - Action: Sets up multi-species directory with 2 valid species (`veg_tree_oak_01`, `veg_conifer_pine_01`) and 1 invalid species (`veg_shrub_boxwood_01` with 1,200 vertices). Calls `validate_directory(root_dir)`.
    - Assertions: `len(reports) >= 3`, oak and pine are `is_valid == True`, boxwood is `is_valid == False`.

---

## 3. Caveats
1. **Meshy AI Mode Dependency**: Running with `--mode meshy` requires the `MESHY_API_KEY` environment variable. The default `--mode auto` seamlessly falls back to the deterministic procedural generator if the key is absent or API fails.
2. **Blender Headless Rendering**: If Blender is not present or exits with an error, the pipeline records a render warning without failing the geometry generation or validation verdicts. Explorer 2 provides a software rasterizer fallback for standalone preview generation.
3. **glTF vs Blender Coordinate Orientation**: Blender uses Z-up, while glTF uses Y-up. The validator dynamically detects the vertical axis by testing |Z_min| <= 0.005m vs |Y_min| <= 0.005m and comparing bounding extents to catalog target height.

---

## 4. Conclusion
Both `teamwork_projects/vegetation_library/pipeline.py` and `teamwork_projects/vegetation_library/tests/test_validator.py` have been designed, tested, and validated.

### 4.1 Worker Implementation Action Plan
The Worker can immediately implement the deliverables using the code templates below:
1. **File 1**: `teamwork_projects/vegetation_library/pipeline.py` (Master CLI runner conforming to Section 4.2).
2. **File 2**: `teamwork_projects/vegetation_library/tests/test_validator.py` (12 QA test cases conforming to Section 4.3).

---

### 4.2 Complete Code Template: `pipeline.py`
Target File: `teamwork_projects/vegetation_library/pipeline.py`

```python
"""
MorphoMesh Vegetation Library - Master Pipeline CLI Runner
Target File: teamwork_projects/vegetation_library/pipeline.py

Coordinates the end-to-end vegetation asset generation lifecycle:
1. Catalog Resolution: Identifies target species (--species, --category, --all).
2. Asset Generation: Meshy AI Text-to-3D with offline Procedural Fallback (--mode, --seed).
3. Post-Processing & Normalization: Root ground snapping, base centering, metric scaling, GLB/OBJ packaging.
4. QA Inspection & Validation: Automated structural, geometric, and PBR checks (validate_asset).
5. Headless Visual Showcase: Blender 4.5.4 LTS multi-angle preview rendering (render_asset_preview).
6. Manifest Aggregation: Updates/creates output/manifest.json indexing all assets and metrics.
7. Summary Reporting: Emits clean Markdown summary tables (--summary).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Ensure project directories are on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR if (SCRIPT_DIR / "vegetation_pipeline").is_dir() else (SCRIPT_DIR.parent.parent / "teamwork_projects" / "vegetation_library")
REPO_ROOT = PROJECT_DIR.parent.parent

for p in (str(PROJECT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / ".agents" / "m4_veg_explorer_1")):
    if p not in sys.path:
        sys.path.insert(0, p)

from vegetation_pipeline.catalog import (
    PlantSpecies,
    VegetationCatalog,
    get_catalog,
    get_species,
    get_species_by_category,
    list_categories,
    list_species,
    list_species_ids,
    CATEGORY_ALIASES,
)
from vegetation_pipeline.generator import (
    RawAsset,
    generate_plant,
    unpack_glb_header_and_json,
)
from vegetation_pipeline.post_processor import (
    AssetDimensions,
    ExportedAsset,
    PostProcessorConfig,
    process_and_export,
)

# Gracefully import validator (M4)
try:
    from vegetation_pipeline.validator import (
        ValidationReport,
        validate_asset,
        validate_directory,
    )
except ImportError:
    try:
        from proposed_validator import (
            ValidationReport,
            validate_asset,
            validate_directory,
        )
    except ImportError:
        validate_asset = None
        validate_directory = None
        ValidationReport = None

# Gracefully import renderer (M4)
try:
    from vegetation_pipeline.renderer import (
        render_asset_preview,
        render_contact_sheet,
    )
except ImportError:
    try:
        from proposed_renderer import (
            render_asset_preview,
            render_contact_sheet,
        )
    except ImportError:
        render_asset_preview = None
        render_contact_sheet = None

logger = logging.getLogger("vegetation_pipeline.pipeline")


# ==============================================================================
# CLI ARGUMENT PARSING
# ==============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Constructs the comprehensive CLI parser for the vegetation library pipeline."""
    parser = argparse.ArgumentParser(
        prog="pipeline.py",
        description="MorphoMesh Master Vegetation Library Pipeline CLI Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a single species with deterministic procedural generator:
  python pipeline.py --species veg_tree_oak_01 --mode procedural

  # Generate all species in a biome category:
  python pipeline.py --category conifers --mode procedural

  # Generate all 35 catalog species:
  python pipeline.py --all --mode procedural

  # Validate existing output assets without re-generating:
  python pipeline.py --validate-only --output-dir output/

  # Render preview thumbnails for existing output assets:
  python pipeline.py --render-only --output-dir output/

  # Print formatted Markdown summary table of all library assets:
  python pipeline.py --summary --output-dir output/
        """,
    )

    # 1. Target Selection
    target_grp = parser.add_argument_group(
        "Target Selection (specify --species, --category, --all, or use step flags)"
    )
    target_grp.add_argument(
        "--species", "-s",
        type=str,
        default=None,
        help="Canonical species ID (e.g. 'veg_tree_oak_01'), scientific name, or common name.",
    )
    target_grp.add_argument(
        "--category", "-c",
        type=str,
        default=None,
        help="Run pipeline for all species in a biome category (e.g. 'broadleaf_trees', 'conifers', 'tropical', etc.).",
    )
    target_grp.add_argument(
        "--all", "-a",
        action="store_true",
        default=False,
        help="Run pipeline across all 35 catalog species in the library.",
    )

    # 2. Generation Engine Configuration
    gen_grp = parser.add_argument_group("Generation & Normalization Configuration")
    gen_grp.add_argument(
        "--mode", "-m",
        choices=["auto", "meshy", "procedural"],
        default="auto",
        help="Generation mode: 'auto' (Meshy with procedural fallback), 'meshy' (strict AI), or 'procedural' (offline deterministic). Default: auto.",
    )
    gen_grp.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Deterministic integer seed for procedural generation.",
    )
    gen_grp.add_argument(
        "--output-dir", "-o",
        type=Path,
        default=Path("output"),
        help="Root output destination directory for library deliverables. Default: 'output/'.",
    )
    gen_grp.add_argument(
        "--force", "-f",
        action="store_true",
        default=False,
        help="Force asset re-generation, ignoring existing cached assets.",
    )

    # 3. Pipeline Step Execution Flags
    step_grp = parser.add_argument_group("Pipeline Step Execution Controls")
    step_grp.add_argument(
        "--skip-render",
        action="store_true",
        default=False,
        help="Skip Blender preview thumbnail rendering.",
    )
    step_grp.add_argument(
        "--skip-validate",
        action="store_true",
        default=False,
        help="Skip automated QA validation checks.",
    )
    step_grp.add_argument(
        "--validate-only",
        action="store_true",
        default=False,
        help="Validate existing assets on disk without re-generation or export.",
    )
    step_grp.add_argument(
        "--render-only",
        action="store_true",
        default=False,
        help="Render preview thumbnails for existing output assets without re-generation.",
    )
    step_grp.add_argument(
        "--summary",
        action="store_true",
        default=False,
        help="Print formatted Markdown summary table of all library assets and exit.",
    )

    # 4. Reporting & Diagnostics
    diag_grp = parser.add_argument_group("Reporting & Diagnostics")
    diag_grp.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Enable verbose DEBUG console logging.",
    )
    diag_grp.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output manifest and execution results as machine-readable JSON to stdout.",
    )

    return parser


# ==============================================================================
# TARGET SPECIES RESOLUTION
# ==============================================================================

def resolve_target_species(args: argparse.Namespace) -> List[PlantSpecies]:
    """Resolves the list of PlantSpecies targets based on CLI arguments."""
    catalog = get_catalog()

    if args.species:
        sp = get_species(args.species)
        return [sp]
    elif args.category:
        return get_species_by_category(args.category)
    elif args.all:
        return list(catalog.species)
    elif args.validate_only or args.render_only or args.summary:
        # Default to all catalog species when scanning existing outputs
        return list(catalog.species)
    else:
        raise ValueError(
            "No target specified. Please provide --species <id>, --category <name>, --all, "
            "or a step flag like --summary / --validate-only / --render-only."
        )


# ==============================================================================
# SPECIES PIPELINE EXECUTION LIFECYCLE
# ==============================================================================

def execute_species_pipeline(
    species: PlantSpecies,
    output_dir: Path,
    mode: str = "auto",
    seed: Optional[int] = None,
    force: bool = False,
    skip_validate: bool = False,
    skip_render: bool = False,
    validate_only: bool = False,
    render_only: bool = False,
) -> Dict[str, Any]:
    """
    Executes the full pipeline lifecycle for a single plant species:
    1. generate_plant -> 2. process_and_export -> 3. validate_asset -> 4. render_asset_preview
    """
    category_slug = species.short_category
    species_dir = output_dir / category_slug / species.species_id
    glb_path = species_dir / f"{species.species_id}.glb"
    obj_path = species_dir / f"{species.species_id}.obj"
    mtl_path = species_dir / f"{species.species_id}.mtl"
    tex_dir = species_dir / "textures"
    manifest_path = species_dir / "asset_manifest.json"
    thumb_path = species_dir / "thumbnail.png"

    record: Dict[str, Any] = {
        "species_id": species.species_id,
        "common_name": species.common_name,
        "scientific_name": species.scientific_name,
        "family": species.family,
        "category": category_slug,
        "category_id": species.category_id,
        "biome": species.biome,
        "dimensions": None,
        "geometry": None,
        "files": {
            "glb": str(glb_path.relative_to(output_dir)).replace("\\", "/"),
            "obj": str(obj_path.relative_to(output_dir)).replace("\\", "/"),
            "mtl": str(mtl_path.relative_to(output_dir)).replace("\\", "/"),
            "textures": {
                "albedo": str((tex_dir / "albedo.png").relative_to(output_dir)).replace("\\", "/"),
                "normal": str((tex_dir / "normal.png").relative_to(output_dir)).replace("\\", "/"),
                "roughness": str((tex_dir / "roughness.png").relative_to(output_dir)).replace("\\", "/"),
                "metallic": str((tex_dir / "metallic.png").relative_to(output_dir)).replace("\\", "/"),
            },
            "thumbnail": str(thumb_path.relative_to(output_dir)).replace("\\", "/") if thumb_path.exists() else None,
            "asset_manifest": str(manifest_path.relative_to(output_dir)).replace("\\", "/"),
        },
        "validation": {
            "is_valid": None,
            "verdict": "SKIPPED",
            "checks": {},
            "metrics": {},
            "errors": [],
            "warnings": [],
        },
        "source": mode,
        "status": "pending",
        "execution_time_s": 0.0,
    }

    t0 = time.time()

    # --------------------------------------------------------------------------
    # BRANCH A: Validate Only
    # --------------------------------------------------------------------------
    if validate_only:
        if not glb_path.exists():
            record["status"] = "missing"
            record["validation"] = {
                "is_valid": False,
                "verdict": "MISSING",
                "checks": {"file_exists": False},
                "metrics": {},
                "errors": [f"GLB asset not found on disk: {glb_path}"],
                "warnings": [],
            }
            record["execution_time_s"] = round(time.time() - t0, 3)
            return record

        if validate_asset is not None:
            report = validate_asset(species_dir, catalog=get_catalog())
            record["validation"] = {
                "is_valid": report.is_valid,
                "verdict": "PASSED" if report.is_valid else "FAILED",
                "checks": report.checks,
                "metrics": report.metrics,
                "errors": report.errors,
                "warnings": report.warnings,
            }
        else:
            record["validation"]["verdict"] = "VALIDATOR_UNAVAILABLE"

        # Read dimensions/polycounts from asset_manifest.json if available
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    m_data = json.load(f)
                    record["dimensions"] = m_data.get("dimensions")
                    record["geometry"] = {
                        "vertex_count": m_data.get("vertex_count", 0),
                        "face_count": m_data.get("face_count", 0),
                    }
            except Exception as e:
                logger.debug("Failed reading manifest for %s: %s", species.species_id, e)

        record["status"] = "validated"
        record["execution_time_s"] = round(time.time() - t0, 3)
        return record

    # --------------------------------------------------------------------------
    # BRANCH B: Render Only
    # --------------------------------------------------------------------------
    if render_only:
        if not glb_path.exists():
            record["status"] = "missing"
            record["execution_time_s"] = round(time.time() - t0, 3)
            return record

        if render_asset_preview is not None:
            try:
                rendered_thumb = render_asset_preview(glb_path, output_image=thumb_path)
                record["files"]["thumbnail"] = str(rendered_thumb.relative_to(output_dir)).replace("\\", "/")
                record["status"] = "rendered"
            except Exception as e:
                logger.warning("Render failed for %s: %s", species.species_id, e)
                record["status"] = "render_failed"
        else:
            logger.info("renderer module unavailable; skipping render.")
            record["status"] = "renderer_unavailable"

        record["execution_time_s"] = round(time.time() - t0, 3)
        return record

    # --------------------------------------------------------------------------
    # BRANCH C: Full Generation Pipeline (Generate -> Export -> Validate -> Render)
    # --------------------------------------------------------------------------
    # 1. Generation
    raw_asset = generate_plant(
        species=species,
        mode=mode,
        output_dir=species_dir,
        seed=seed,
        force_regenerate=force,
    )
    record["source"] = raw_asset.source

    # 2. Post-Processing & Normalization
    exported_asset = process_and_export(
        raw_asset=raw_asset,
        species=species,
        output_dir=species_dir,
    )
    record["dimensions"] = exported_asset.dimensions.model_dump()
    record["geometry"] = {
        "vertex_count": exported_asset.vertex_count,
        "face_count": exported_asset.face_count,
        "ground_pivot_z": exported_asset.ground_pivot_z,
        "base_contact_centroid": list(exported_asset.base_centroid),
    }

    # 3. Validation
    if not skip_validate and validate_asset is not None:
        report = validate_asset(exported_asset, catalog=get_catalog())
        record["validation"] = {
            "is_valid": report.is_valid,
            "verdict": "PASSED" if report.is_valid else "FAILED",
            "checks": report.checks,
            "metrics": report.metrics,
            "errors": report.errors,
            "warnings": report.warnings,
        }
    elif skip_validate:
        record["validation"]["verdict"] = "SKIPPED"
    else:
        record["validation"]["verdict"] = "VALIDATOR_UNAVAILABLE"

    # 4. Rendering
    if not skip_render and render_asset_preview is not None:
        try:
            rendered_thumb = render_asset_preview(exported_asset.glb_path, output_image=thumb_path)
            record["files"]["thumbnail"] = str(rendered_thumb.relative_to(output_dir)).replace("\\", "/")
        except Exception as e:
            logger.warning("Render preview warning for %s: %s", species.species_id, e)
            record["validation"]["warnings"].append(f"Render preview note: {e}")
    elif skip_render:
        pass
    else:
        logger.debug("render_asset_preview unavailable; thumbnail skipped.")

    record["status"] = "completed"
    record["execution_time_s"] = round(time.time() - t0, 3)
    return record


# ==============================================================================
# MANIFEST AGGREGATION & STORAGE
# ==============================================================================

def aggregate_manifest(output_dir: Path, species_records: List[Dict[str, Any]]) -> Path:
    """
    Aggregates species pipeline records into a unified output/manifest.json.
    Merges incrementally with existing manifest records to preserve catalog history.
    """
    manifest_path = output_dir / "manifest.json"
    existing_assets: Dict[str, Any] = {}

    if manifest_path.is_file():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_assets = data.get("assets", {})
        except Exception as e:
            logger.warning("Could not read existing manifest %s: %s", manifest_path, e)

    now_iso = datetime.now(timezone.utc).isoformat()
    for rec in species_records:
        rec_copy = dict(rec)
        rec_copy["last_updated"] = now_iso
        existing_assets[rec["species_id"]] = rec_copy

    catalog = get_catalog()
    total_catalog = len(catalog)
    indexed_count = len(existing_assets)
    passed_count = sum(1 for a in existing_assets.values() if a.get("validation", {}).get("is_valid") is True)
    failed_count = sum(1 for a in existing_assets.values() if a.get("validation", {}).get("is_valid") is False)

    categories_summary: Dict[str, Dict[str, int]] = {}
    for cat in catalog.categories:
        short_cat = cat.short_category
        cat_species = [s.species_id for s in catalog.species if s.short_category == short_cat]
        cat_tot = len(cat_species)
        cat_gen = sum(1 for sid in cat_species if sid in existing_assets)
        cat_val = sum(1 for sid in cat_species if existing_assets.get(sid, {}).get("validation", {}).get("is_valid") is True)
        categories_summary[short_cat] = {
            "total_catalog": cat_tot,
            "indexed_count": cat_gen,
            "passed_validation": cat_val,
        }

    manifest_payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": "1.0.0",
        "project": "MorphoMesh Vegetation Library",
        "generated_at": now_iso,
        "total_catalog_species": total_catalog,
        "indexed_species_count": indexed_count,
        "passed_validation_count": passed_count,
        "failed_validation_count": failed_count,
        "categories_summary": categories_summary,
        "assets": existing_assets,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_payload, f, indent=2)

    return manifest_path


# ==============================================================================
# MARKDOWN SUMMARY TABLE GENERATION
# ==============================================================================

def format_summary_table(manifest_data: Dict[str, Any]) -> str:
    """Generates a formatted Markdown summary table of all library assets."""
    total = manifest_data.get("total_catalog_species", 35)
    indexed = manifest_data.get("indexed_species_count", 0)
    passed = manifest_data.get("passed_validation_count", 0)
    failed = manifest_data.get("failed_validation_count", 0)
    pass_pct = (passed / indexed * 100.0) if indexed > 0 else 0.0

    lines = [
        "# MorphoMesh Vegetation Library — Asset Catalog Summary",
        "",
        f"**Catalog Completeness**: {indexed} / {total} species indexed ({indexed/total*100:.1f}%) | "
        f"**Validation Pass Rate**: {passed} / {indexed} ({pass_pct:.1f}%) | "
        f"**Failures**: {failed}",
        f"**Generated**: {manifest_data.get('generated_at', 'N/A')}",
        "",
        "| Category | Species ID | Common Name | Scientific Name | Height (m) | Canopy (m) | Vertices | Faces | Source | Verdict | Thumbnail |",
        "|:---|:---|:---|:---|---:|---:|---:|---:|:---:|:---:|:---:|",
    ]

    assets = manifest_data.get("assets", {})
    sorted_assets = sorted(assets.values(), key=lambda a: (a.get("category", ""), a.get("species_id", "")))

    for a in sorted_assets:
        cat = a.get("category", "-")
        s_id = a.get("species_id", "-")
        c_name = a.get("common_name", "-")
        sci_name = f"*{a.get('scientific_name', '-') }*"
        dims = a.get("dimensions") or {}
        height = f"{dims.get('height_m', 0.0):.2f}" if "height_m" in dims else "-"
        canopy = f"{dims.get('canopy_spread_m', 0.0):.2f}" if "canopy_spread_m" in dims else "-"
        geom = a.get("geometry") or {}
        verts = f"{geom.get('vertex_count', 0):,}" if "vertex_count" in geom else "-"
        faces = f"{geom.get('face_count', 0):,}" if "face_count" in geom else "-"
        src = a.get("source", "-")
        val = a.get("validation", {})
        if val.get("is_valid") is True:
            verdict = "✅ PASS"
        elif val.get("is_valid") is False:
            verdict = "❌ FAIL"
        else:
            verdict = f"⚪ {val.get('verdict', 'SKIP')}"

        thumb = a.get("files", {}).get("thumbnail")
        thumb_link = f"[View]({thumb})" if thumb else "-"

        lines.append(
            f"| {cat} | `{s_id}` | {c_name} | {sci_name} | {height} | {canopy} | {verts} | {faces} | {src} | {verdict} | {thumb_link} |"
        )

    lines.append("")
    lines.append("### Biome Categories Breakdown")
    for cat_slug, stats in manifest_data.get("categories_summary", {}).items():
        c_tot = stats.get("total_catalog", 5)
        c_idx = stats.get("indexed_count", 0)
        c_pass = stats.get("passed_validation", 0)
        lines.append(
            f"- **{cat_slug.replace('_', ' ').title()}** (`{cat_slug}`): "
            f"{c_idx}/{c_tot} generated, {c_pass}/{c_idx if c_idx > 0 else 1} valid"
        )

    return "\n".join(lines)


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    """Main CLI execution harness."""
    parser = create_parser()
    args = parser.parse_args(argv)

    # Configure Windows console UTF-8 encoding
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    out_dir = Path(args.output_dir)

    # 1. Fast Summary Mode (no execution required)
    if args.summary and not (args.species or args.category or args.all):
        manifest_p = out_dir / "manifest.json"
        if not manifest_p.is_file():
            print(f"[ERROR] Manifest not found at: {manifest_p}. Generate assets first.", file=sys.stderr)
            return 1
        with open(manifest_p, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        summary_md = format_summary_table(m_data)
        print(summary_md)
        return 0

    # 2. Resolve targets
    try:
        targets = resolve_target_species(args)
    except Exception as e:
        print(f"[ERROR] Target resolution failed: {e}", file=sys.stderr)
        return 2

    logger.info(
        "Executing pipeline for %d species | Mode: %s | Output: %s | Validate: %s | Render: %s",
        len(targets),
        args.mode,
        out_dir,
        not args.skip_validate and not args.render_only,
        not args.skip_render and not args.validate_only,
    )

    results: List[Dict[str, Any]] = []
    failures = 0

    for idx, species in enumerate(targets, 1):
        logger.info("[%d/%d] Processing %s (%s)...", idx, len(targets), species.species_id, species.common_name)
        try:
            res = execute_species_pipeline(
                species=species,
                output_dir=out_dir,
                mode=args.mode,
                seed=args.seed,
                force=args.force,
                skip_validate=args.skip_validate,
                skip_render=args.skip_render,
                validate_only=args.validate_only,
                render_only=args.render_only,
            )
            results.append(res)
            is_valid = res.get("validation", {}).get("is_valid")
            if is_valid is False:
                failures += 1
                logger.warning("Validation FAILED for %s: %s", species.species_id, res.get("validation", {}).get("errors"))
            else:
                logger.info("Successfully processed %s (verdict: %s, %.2fs)", species.species_id, res.get("validation", {}).get("verdict"), res.get("execution_time_s", 0.0))
        except Exception as e:
            failures += 1
            logger.error("Exception processing %s: %s", species.species_id, e, exc_info=args.verbose)
            results.append({
                "species_id": species.species_id,
                "category": species.short_category,
                "status": "error",
                "validation": {"is_valid": False, "verdict": "ERROR", "errors": [str(e)]},
                "source": args.mode,
                "execution_time_s": 0.0,
            })

    # 3. Aggregate Manifest
    manifest_p = aggregate_manifest(out_dir, results)
    logger.info("Global library manifest updated: %s", manifest_p)

    # 4. Summary Output
    if args.summary or not args.json:
        with open(manifest_p, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        summary_md = format_summary_table(m_data)
        if args.summary:
            print("\n" + summary_md)

    if args.json:
        with open(manifest_p, "r", encoding="utf-8") as f:
            m_data = json.load(f)
        print(json.dumps(m_data, indent=2))

    return 1 if failures > 0 else 0


if __name__ == "__main__":
    sys.exit(main())

```

---

### 4.3 Complete Code Template: `tests/test_validator.py`
Target File: `teamwork_projects/vegetation_library/tests/test_validator.py`

```python
﻿"""
MorphoMesh Vegetation Library - Automated QA Validator Test Suite
Target File: teamwork_projects/vegetation_library/tests/test_validator.py

Comprehensive unit and integration test suite covering 12 critical QA scenarios:
1.  test_valid_asset_passes_all_checks
2.  test_vertex_count_under_budget_fails
3.  test_vertex_count_over_budget_fails
4.  test_ungrounded_pivot_fails
5.  test_uncentered_centroid_fails
6.  test_nan_inf_coordinates_fails
7.  test_armature_or_skinning_fails
8.  test_solid_black_texture_fails
9.  test_missing_texture_channel_fails
10. test_non_dielectric_metallic_fails
11. test_corrupt_glb_fails
12. test_validate_directory
"""
from __future__ import annotations

import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
from typing import Any, Dict, Tuple

import numpy as np
from PIL import Image
import pytest

# Ensure sys.path includes project directories and m4_veg_explorer_1
TEST_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TEST_DIR if (TEST_DIR / "vegetation_pipeline").is_dir() else (TEST_DIR.parent.parent / "teamwork_projects" / "vegetation_library")
REPO_ROOT = PROJECT_DIR.parent.parent

for p in (str(PROJECT_DIR), str(REPO_ROOT), str(REPO_ROOT / "src"), str(REPO_ROOT / ".agents" / "m4_veg_explorer_1")):
    if p not in sys.path:
        sys.path.insert(0, p)

from morphomesh.geometry.mesh import MeshGeometry
from vegetation_pipeline.catalog import get_catalog, get_species
from vegetation_pipeline.generator import (
    RawAsset,
    generate_plant,
    unpack_glb_header_and_json,
)
from vegetation_pipeline.post_processor import (
    AssetDimensions,
    ExportedAsset,
    PostProcessorConfig,
    export_production_glb,
    process_and_export,
)

try:
    from vegetation_pipeline.validator import (
        ValidationReport,
        validate_asset,
        validate_directory,
    )
except ImportError:
    from proposed_validator import (
        ValidationReport,
        validate_asset,
        validate_directory,
    )


# ==============================================================================
# TEST FIXTURES & SYNTHETIC ASSET BUILDERS
# ==============================================================================

def make_valid_test_textures() -> Dict[str, Image.Image]:
    """Generates standard compliant 64x64 PBR texture maps."""
    # Albedo: greenish organic field with standard deviation > 0.02
    np.random.seed(42)
    base_col = np.array([80, 140, 50], dtype=np.float32)
    noise = np.random.uniform(-20, 20, (64, 64, 3))
    alb_data = np.clip(base_col + noise, 0, 255).astype(np.uint8)
    albedo = Image.fromarray(alb_data, mode="RGB")

    # Normal: flat tangent-space (128, 128, 255)
    normal = Image.new("RGB", (64, 64), (128, 128, 255))

    # Roughness: organic mean ~0.60, non-zero variance
    r_data = np.clip(np.random.normal(150, 15, (64, 64)), 50, 240).astype(np.uint8)
    roughness = Image.fromarray(r_data, mode="L")

    # Metallic: strictly dielectric (zeros)
    metallic = Image.new("L", (64, 64), 0)

    return {
        "albedo": albedo,
        "normal": normal,
        "roughness": roughness,
        "metallic": metallic,
    }


def make_synthetic_mesh(
    target_vertices: int,
    height: float = 3.0,
    radius: float = 0.5,
    z_offset: float = 0.0,
    x_offset: float = 0.0,
    inject_nan: bool = False,
) -> MeshGeometry:
    """
    Constructs a deterministic synthetic cylindrical/prismatic mesh with an exact or
    approximate vertex count, grounded at Z_min = z_offset.
    """
    mesh = MeshGeometry()
    nx = max(4, int(math.isqrt(target_vertices)))
    ny = max(2, (target_vertices + nx - 1) // nx)

    verts_added = 0
    grid = []

    for iy in range(ny):
        row = []
        fraction_y = iy / max(ny - 1, 1)
        z = z_offset + fraction_y * height
        theta_ring = fraction_y * 2.0 * math.pi

        for ix in range(nx):
            if verts_added >= target_vertices:
                break
            angle = (ix / nx) * 2.0 * math.pi
            x = x_offset + math.cos(angle) * radius
            y = math.sin(angle) * radius

            if inject_nan and verts_added == 0:
                pos = (float("nan"), y, z)
            else:
                pos = (round(x, 5), round(y, 5), round(z, 5))

            norm = (math.cos(angle), math.sin(angle), 0.0)
            uv = (ix / nx, fraction_y)
            mesh.add_vertex(pos, norm, uv)
            row.append(verts_added)
            verts_added += 1

        if row:
            grid.append(row)

    # Triangulate grid rings
    for iy in range(len(grid) - 1):
        r1 = grid[iy]
        r2 = grid[iy + 1]
        common_len = min(len(r1), len(r2))
        for ix in range(common_len):
            nxt = (ix + 1) % common_len
            i0 = r1[ix]
            i1 = r1[nxt]
            i2 = r2[nxt]
            i3 = r2[ix]
            mesh.add_triangle(i0, i1, i2)
            mesh.add_triangle(i0, i2, i3)

    return mesh


def repack_glb_json(
    source_glb: Path,
    dest_glb: Path,
    modifier_fn,
) -> Path:
    """Unpacks GLB, modifies its JSON chunk dictionary, and repacks it."""
    gltf, bin_bytes = unpack_glb_header_and_json(source_glb)
    modifier_fn(gltf)

    json_bytes = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_pad = (4 - (len(json_bytes) % 4)) % 4
    json_bytes += b" " * json_pad

    total_len = 12 + (8 + len(json_bytes)) + (8 + len(bin_bytes))
    hdr = struct.pack("<4sII", b"glTF", 2, total_len)
    c0 = struct.pack("<I4s", len(json_bytes), b"JSON")
    c1 = struct.pack("<I4s", len(bin_bytes), b"BIN\x00")

    dest_glb.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_glb, "wb") as f:
        f.write(hdr + c0 + json_bytes + c1 + bin_bytes)

    return dest_glb


# ==============================================================================
# 12 QA TEST SCENARIOS
# ==============================================================================

def test_valid_asset_passes_all_checks(tmp_path: Path):
    """
    1. test_valid_asset_passes_all_checks:
    Generates a genuine procedural plant asset, post-processes it, and asserts that
    validate_asset returns is_valid == True, 0 errors, and all checks pass.
    """
    species = get_species("veg_tree_oak_01")
    raw = generate_plant(species, mode="procedural", seed=42)
    exported = process_and_export(raw, species, output_dir=tmp_path / "valid_oak")

    report = validate_asset(exported)

    assert report.is_valid is True, f"Valid asset failed validation with errors: {report.errors}"
    assert len(report.errors) == 0
    assert report.species_id == "veg_tree_oak_01"
    assert report.checks.get("vertex_count_budget") is True
    assert report.checks.get("ground_contact_base_aligned") is True
    assert report.checks.get("base_contact_centroid_centered") is True
    assert report.checks.get("zero_nan_inf_coordinates") is True
    assert report.checks.get("n_bones_strictly_zero") is True
    assert report.checks.get("textures_channels_present") is True
    assert report.checks.get("texture_metallic_dielectric") is True

    # Assert validating by path directory also passes
    dir_report = validate_asset(exported.glb_path.parent)
    assert dir_report.is_valid is True


def test_vertex_count_under_budget_fails(tmp_path: Path):
    """
    2. test_vertex_count_under_budget_fails:
    Mocks a mesh with 1,500 vertices (< 3,000 budget), asserts validation fails
    with descriptive error mentioning vertex budget.
    """
    mesh = make_synthetic_mesh(target_vertices=1500, height=12.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "under_budget" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("vertex_count_budget") is False
    assert any("under budget" in err.lower() or "minimum" in err.lower() for err in report.errors)


def test_vertex_count_over_budget_fails(tmp_path: Path):
    """
    3. test_vertex_count_over_budget_fails:
    Mocks a mesh with 50,000 vertices (> 45,000 budget), asserts validation fails.
    """
    mesh = make_synthetic_mesh(target_vertices=50000, height=12.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "over_budget" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("vertex_count_budget") is False
    assert any("over budget" in err.lower() or "maximum" in err.lower() for err in report.errors)


def test_ungrounded_pivot_fails(tmp_path: Path):
    """
    4. test_ungrounded_pivot_fails:
    Shifts mesh vertices up by +1.0m (Z_min = 1.0m > 0.005m tolerance), asserts
    ground contact pivot check fails.
    """
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0, z_offset=1.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "ungrounded" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("ground_contact_base_aligned") is False
    assert any("ground" in err.lower() or "pivot" in err.lower() for err in report.errors)


def test_uncentered_centroid_fails(tmp_path: Path):
    """
    5. test_uncentered_centroid_fails:
    Shifts mesh horizontally by +0.5m (base contact centroid X = 0.5m > 0.05m tolerance),
    asserts base contact centroid centering check fails.
    """
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0, x_offset=0.5)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "uncentered" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("base_contact_centroid_centered") is False
    assert any("centroid" in err.lower() or "center" in err.lower() for err in report.errors)


def test_nan_inf_coordinates_fails(tmp_path: Path):
    """
    6. test_nan_inf_coordinates_fails:
    Injects NaN into vertex coordinates, asserts validation fails with NaN/Inf detection.
    """
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0, inject_nan=True)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, tmp_path / "nan_coords" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    report = validate_asset(glb_p)

    assert report.is_valid is False
    assert report.checks.get("zero_nan_inf_coordinates") is False
    assert any("nan" in err.lower() or "inf" in err.lower() for err in report.errors)


def test_armature_or_skinning_fails(tmp_path: Path):
    """
    7. test_armature_or_skinning_fails:
    Injects joint/weight/skin data into GLB container, asserts zero-armature check fails.
    """
    # 1. Create a valid baseline GLB
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    base_glb = export_production_glb(mesh, tmp_path / "base" / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    # 2. Repack with skeletal skinning and JOINTS_0 attribute
    def inject_rig(gltf: Dict[str, Any]):
        gltf["skins"] = [{"joints": [0, 1], "name": "FakeArmature"}]
        if "meshes" in gltf and gltf["meshes"]:
            for prim in gltf["meshes"][0].get("primitives", []):
                prim["attributes"]["JOINTS_0"] = 0
                prim["attributes"]["WEIGHTS_0"] = 0

    rigged_glb = tmp_path / "rigged" / "veg_tree_oak_01.glb"
    repack_glb_json(base_glb, rigged_glb, inject_rig)

    report = validate_asset(rigged_glb)

    assert report.is_valid is False
    assert (
        report.checks.get("static_mesh_no_skins") is False
        or report.checks.get("n_bones_strictly_zero") is False
        or report.checks.get("static_mesh_no_joint_weights") is False
    )
    assert any("skin" in err.lower() or "armature" in err.lower() or "joint" in err.lower() for err in report.errors)


def test_solid_black_texture_fails(tmp_path: Path):
    """
    8. test_solid_black_texture_fails:
    Replaces albedo map with solid black image (mean = 0.0 <= 0.05), asserts
    albedo physical plausibility check fails.
    """
    out_dir = tmp_path / "black_albedo"
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    # Replace albedo with solid black
    textures["albedo"] = Image.new("RGB", (64, 64), (0, 0, 0))
    glb_p = export_production_glb(mesh, out_dir / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    # Also save discrete texture
    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures["albedo"].save(tex_dir / "albedo.png")

    report = validate_asset(out_dir)

    assert report.is_valid is False
    assert report.checks.get("texture_albedo_plausible") is False
    assert any("black" in err.lower() or "dark" in err.lower() for err in report.errors)


def test_missing_texture_channel_fails(tmp_path: Path):
    """
    9. test_missing_texture_channel_fails:
    Creates an asset directory missing normal.png, asserts PBR channel completeness check fails.
    """
    out_dir = tmp_path / "missing_normal"
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    glb_p = export_production_glb(mesh, out_dir / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    # Save only 3 of 4 channels to textures/
    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures["albedo"].save(tex_dir / "albedo.png")
    textures["roughness"].save(tex_dir / "roughness.png")
    textures["metallic"].save(tex_dir / "metallic.png")
    # normal.png is deliberately omitted

    # Also unpack and strip normal texture from glb to test embedded fallback
    def strip_normal(gltf: Dict[str, Any]):
        for mat in gltf.get("materials", []):
            mat.pop("normalTexture", None)

    stripped_glb = out_dir / "veg_tree_oak_01.glb"
    repack_glb_json(glb_p, stripped_glb, strip_normal)

    report = validate_asset(out_dir)

    assert report.is_valid is False
    assert report.checks.get("textures_channels_present") is False
    assert any("normal" in err.lower() or "missing" in err.lower() for err in report.errors)


def test_non_dielectric_metallic_fails(tmp_path: Path):
    """
    10. test_non_dielectric_metallic_fails:
    Replaces metallic map with 1.0 (pure metal, e.g. pixel value 255), asserts
    dielectric vegetation material rule fails.
    """
    out_dir = tmp_path / "metallic_plant"
    mesh = make_synthetic_mesh(target_vertices=4000, height=12.0)
    textures = make_valid_test_textures()
    # Replace metallic with 255 (metal)
    textures["metallic"] = Image.new("L", (64, 64), 255)
    glb_p = export_production_glb(mesh, out_dir / "veg_tree_oak_01.glb", textures, species_id="veg_tree_oak_01")

    tex_dir = out_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    textures["albedo"].save(tex_dir / "albedo.png")
    textures["normal"].save(tex_dir / "normal.png")
    textures["roughness"].save(tex_dir / "roughness.png")
    textures["metallic"].save(tex_dir / "metallic.png")

    report = validate_asset(out_dir)

    assert report.is_valid is False
    assert report.checks.get("texture_metallic_dielectric") is False
    assert any("metallic" in err.lower() or "dielectric" in err.lower() for err in report.errors)


def test_corrupt_glb_fails(tmp_path: Path):
    """
    11. test_corrupt_glb_fails:
    Passes a truncated and invalid binary file, asserts validation fails gracefully
    without unhandled crashes or exceptions.
    """
    corrupt_p = tmp_path / "corrupt_species" / "corrupt_plant.glb"
    corrupt_p.parent.mkdir(parents=True, exist_ok=True)
    corrupt_p.write_bytes(b"glTF\x02\x00\x00\x00truncated_garbage_data")

    report = validate_asset(corrupt_p)

    assert report.is_valid is False
    assert report.checks.get("glb_container_valid") is False
    assert len(report.errors) > 0
    assert any("corrupted" in err.lower() or "unparseable" in err.lower() or "container" in err.lower() for err in report.errors)


def test_validate_directory(tmp_path: Path):
    """
    12. test_validate_directory:
    Tests batch validation across multiple species directories:
    - 2 valid species (English Oak, Scots Pine)
    - 1 invalid species (under-budget vertex count)
    Asserts validate_directory returns correctly mapped ValidationReport dictionary.
    """
    root_dir = tmp_path / "multi_species_batch"

    # Asset 1: Valid English Oak
    sp1 = get_species("veg_tree_oak_01")
    raw1 = generate_plant(sp1, mode="procedural", seed=42)
    process_and_export(raw1, sp1, output_dir=root_dir / "broadleaf_trees" / "veg_tree_oak_01")

    # Asset 2: Valid Scots Pine
    sp2 = get_species("veg_conifer_pine_01")
    raw2 = generate_plant(sp2, mode="procedural", seed=43)
    process_and_export(raw2, sp2, output_dir=root_dir / "conifers" / "veg_conifer_pine_01")

    # Asset 3: Defective species (under-budget)
    defective_dir = root_dir / "shrubs" / "veg_shrub_boxwood_01"
    defective_dir.mkdir(parents=True, exist_ok=True)
    m_bad = make_synthetic_mesh(target_vertices=1200, height=1.5)
    tex = make_valid_test_textures()
    export_production_glb(m_bad, defective_dir / "veg_shrub_boxwood_01.glb", tex, species_id="veg_shrub_boxwood_01")

    # Execute batch validation
    reports = validate_directory(root_dir)

    assert len(reports) >= 3
    assert "veg_tree_oak_01" in reports
    assert "veg_conifer_pine_01" in reports
    assert "veg_shrub_boxwood_01" in reports

    assert reports["veg_tree_oak_01"].is_valid is True
    assert reports["veg_conifer_pine_01"].is_valid is True
    assert reports["veg_shrub_boxwood_01"].is_valid is False

```

---

## 5. Verification Method

To independently verify all claims, algorithms, and implementations:

### 5.1 Test Suite Verification
Run pytest on the test suite:
```powershell
& "E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe" -m pytest "E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_3\proposed_test_validator.py" -v
```
**Expected Result**:
`12 passed in 1.65s` (100% pass rate).

### 5.2 CLI Runner End-to-End Verification
Run single species generation, validation, and summary reporting:
```powershell
& "E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe" "E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_3\proposed_pipeline.py" --species veg_tree_oak_01 --mode procedural --skip-render --output-dir "tmp_test_e2e" --summary
```
**Expected Result**:
- Exit code 0.
- `output/broadleaf_trees/veg_tree_oak_01/` contains `veg_tree_oak_01.glb`, `.obj`, `.mtl`, `textures/`, `asset_manifest.json`.
- `output/manifest.json` is generated with `passed_validation_count: 1`.
- Clean Markdown table printed to stdout.

Validate existing directory without regeneration:
```powershell
& "E:\tool\mcp\MorphoMesh\.venv\Scripts\python.exe" "E:\tool\mcp\MorphoMesh\.agents\m4_veg_explorer_3\proposed_pipeline.py" --validate-only --output-dir "tmp_test_e2e" --species veg_tree_oak_01
```
**Expected Result**:
- Exit code 0, execution time ~0.03s.

Clean up temporary folder:
```powershell
Remove-Item -Recurse -Force "tmp_test_e2e"
```

### 5.3 Invalidation Conditions
This analysis is invalidated if:
1. `validate_asset` or `ValidationReport` changes schema from Explorer 1's specification.
2. `export_production_glb` signature changes its parameter order.
3. The vertex budget threshold `[3,000, 45,000]` or tolerance values (`0.005m` for ground, `0.05m` for centroid) are modified.
