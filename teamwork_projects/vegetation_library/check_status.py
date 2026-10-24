"""
Normalize and post-process all genuine Meshy models and re-render with Headless Blender 4.5.
File: teamwork_projects/vegetation_library/normalize_all_meshy.py
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "src"))

from vegetation_pipeline.catalog import get_catalog, get_species
from vegetation_pipeline.generator import RawAsset
from vegetation_pipeline.post_processor import AssetPostProcessor, PostProcessorConfig, process_and_export
from vegetation_pipeline.validator import validate_asset
from vegetation_pipeline.renderer import RenderConfig, render_asset_preview

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("normalize_all_meshy")

OUTPUT_DIR = SCRIPT_DIR / "output"
catalog = get_catalog()

def normalize_single_species(sp_id: str):
    sp = get_species(sp_id)
    sp_dir = OUTPUT_DIR / sp.short_category / sp.species_id
    raw_glb = sp_dir / "raw_meshy_model.glb"
    if not raw_glb.is_file():
        logger.warning(f"No raw_meshy_model.glb found for {sp_id}")
        return False

    manifest_p = sp_dir / "asset_manifest.json"
    prov_meta = {}
    if manifest_p.is_file():
        try:
            m_data = json.loads(manifest_p.read_text("utf-8"))
            prov_meta = m_data.get("provenance", {})
            if not prov_meta:
                prov_meta = {
                    "source": "meshy",
                    "task_id": m_data.get("metadata", {}).get("task_id")
                }
        except Exception as e:
            logger.debug(f"Manifest read note for {sp_id}: {e}")

    tex_dir = sp_dir / "textures"
    tex_paths = {}
    for ch in ("albedo", "normal", "roughness", "metallic"):
        tp = tex_dir / f"{ch}.png"
        if tp.is_file():
            tex_paths[ch] = tp

    raw_asset = RawAsset(
        species_id=sp.species_id,
        glb_path=raw_glb,
        texture_paths=tex_paths,
        source=prov_meta.get("source", "meshy"),
        metadata={
            "task_id": prov_meta.get("task_id"),
            "preview_task_id": prov_meta.get("preview_task_id"),
            "provenance": prov_meta,
        }
    )

    t0 = time.time()
    logger.info(f"--- Normalizing {sp.species_id} ({sp.common_name}) ---")
    exported = process_and_export(raw_asset, sp, output_dir=sp_dir)
    dt = time.time() - t0
    logger.info(f"Normalized {sp.species_id} in {dt:.2f}s: {exported.vertex_count} verts, {exported.face_count} faces, Z_min={exported.ground_pivot_z:.4f}m, base={exported.base_centroid}")

    rep = validate_asset(exported.glb_path, catalog=catalog)
    logger.info(f"Validation {sp.species_id}: {'PASSED' if rep.is_valid else 'FAILED'} ({rep.passed_checks_count}/{rep.total_checks_count})")
    if rep.errors:
        logger.error(f"Validation errors for {sp.species_id}: {rep.errors}")

    # Re-render with Blender 4.5
    logger.info(f"Rendering 4-angle turntables & thumbnail for {sp.species_id} with Headless Blender 4.5...")
    r_cfg = RenderConfig(
        engine="BLENDER_EEVEE_NEXT",
        use_blender=True,
        res_x=512,
        res_y=512,
        enable_contact_sheet=True,
        contact_sheet_resolution=1024,
    )
    render_res = render_asset_preview(
        asset=exported,
        output_dir=sp_dir,
        config=r_cfg,
        use_blender=True,
    )
    logger.info(f"Rendered views for {sp.species_id}: {list(render_res.keys())}")
    return rep.is_valid

def main():
    raw_glbs = sorted(OUTPUT_DIR.glob("*/*/raw_meshy_model.glb"))
    logger.info(f"Found {len(raw_glbs)} raw Meshy models to normalize.")

    results = {}
    for r_p in raw_glbs:
        sp_id = r_p.parent.name
        # Skip Oak if already passing 21/21 unless requested
        if sp_id == "veg_tree_oak_01":
            rep = validate_asset(r_p.parent / f"{sp_id}.glb", catalog=catalog)
            if rep.is_valid and rep.passed_checks_count == 21:
                logger.info(f"Skipping Oak (already valid and normalized).")
                results[sp_id] = True
                continue

        ok = normalize_single_species(sp_id)
        results[sp_id] = ok

    passed = sum(1 for v in results.values() if v)
    logger.info(f"=== Summary: {passed}/{len(results)} Meshy models normalized and validated ===")

if __name__ == "__main__":
    main()

