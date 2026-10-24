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
