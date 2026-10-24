"""
Sync Library: Normalize Remaining Assets, Aggregate Master Manifest & Synchronize Viewer HTML
File: teamwork_projects/vegetation_library/sync_library.py
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
from vegetation_pipeline.post_processor import process_and_export
from vegetation_pipeline.validator import validate_asset
from vegetation_pipeline.renderer import RenderConfig, render_asset_preview

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_library")

OUTPUT_DIR = SCRIPT_DIR / "output"
catalog = get_catalog()

def reprocess_invalid_meshy_assets():
    raw_glbs = sorted(OUTPUT_DIR.glob("*/*/raw_meshy_model.glb"))
    for r_p in raw_glbs:
        sp_id = r_p.parent.name
        prod_glb = r_p.parent / f"{sp_id}.glb"
        is_valid = False
        if prod_glb.is_file():
            rep = validate_asset(prod_glb, catalog=catalog)
            if rep.is_valid and rep.passed_checks_count == rep.total_checks_count:
                is_valid = True
        
        if not is_valid:
            logger.info(f"Re-normalizing invalid Meshy asset: {sp_id}")
            sp = get_species(sp_id)
            sp_dir = r_p.parent
            manifest_p = sp_dir / "asset_manifest.json"
            prov_meta = {}
            if manifest_p.is_file():
                try:
                    m_data = json.loads(manifest_p.read_text("utf-8"))
                    prov_meta = m_data.get("provenance", {})
                    if not prov_meta:
                        prov_meta = {"source": "meshy", "task_id": m_data.get("metadata", {}).get("task_id")}
                except Exception:
                    pass

            tex_dir = sp_dir / "textures"
            tex_paths = {ch: tex_dir / f"{ch}.png" for ch in ("albedo", "normal", "roughness", "metallic") if (tex_dir / f"{ch}.png").is_file()}

            raw_asset = RawAsset(
                species_id=sp.species_id,
                glb_path=r_p,
                texture_paths=tex_paths,
                source=prov_meta.get("source", "meshy"),
                metadata={
                    "task_id": prov_meta.get("task_id"),
                    "preview_task_id": prov_meta.get("preview_task_id"),
                    "provenance": prov_meta,
                }
            )
            exported = process_and_export(raw_asset, sp, output_dir=sp_dir)
            rep2 = validate_asset(exported.glb_path, catalog=catalog)
            logger.info(f"{sp_id} re-validation: {'PASSED' if rep2.is_valid else 'FAILED'} ({rep2.passed_checks_count}/{rep2.total_checks_count})")
            if rep2.errors:
                logger.error(f"Errors for {sp_id}: {rep2.errors}")

            # Re-render
            r_cfg = RenderConfig(
                engine="BLENDER_EEVEE_NEXT",
                use_blender=True,
                res_x=512,
                res_y=512,
                enable_contact_sheet=True,
                contact_sheet_resolution=1024,
            )
            render_asset_preview(asset=exported, output_dir=sp_dir, config=r_cfg, use_blender=True)

def build_master_manifest():
    logger.info("Building unified master output/manifest.json...")
    assets = {}
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    categories_summary = {
        cat.short_category: {"total_catalog": 5, "indexed_count": 0, "passed_validation": 0}
        for cat in catalog.categories
    }

    for sp in catalog.species:
        sp_dir = OUTPUT_DIR / sp.short_category / sp.species_id
        glb_p = sp_dir / f"{sp.species_id}.glb"
        obj_p = sp_dir / f"{sp.species_id}.obj"
        mtl_p = sp_dir / f"{sp.species_id}.mtl"
        thumb_p = sp_dir / "thumbnail.png"
        mani_p = sp_dir / "asset_manifest.json"

        # Read per-species manifest
        m_data = {}
        if mani_p.is_file():
            try:
                m_data = json.loads(mani_p.read_text("utf-8"))
            except Exception:
                pass

        # Validate
        rep = validate_asset(glb_p, catalog=catalog)

        # Provenance
        prov = m_data.get("provenance", {})
        source = prov.get("source", m_data.get("source", "procedural"))
        task_id = prov.get("task_id", m_data.get("metadata", {}).get("task_id"))

        # Dimensions & Geometry from manifest or validator
        dims = m_data.get("geometry", {}).get("dimensions_m") or m_data.get("dimensions", {})
        geom = {
            "vertex_count": m_data.get("geometry", {}).get("vertex_count", rep.metrics.get("vertex_count", 0)),
            "face_count": m_data.get("geometry", {}).get("face_count", rep.metrics.get("triangle_count", 0)),
            "ground_pivot_z": m_data.get("geometry", {}).get("ground_contact_z", 0.0),
            "base_contact_centroid": m_data.get("geometry", {}).get("base_centroid_xy", [0.0, 0.0]),
        }

        # Relative paths
        rel_base = f"{sp.short_category}/{sp.species_id}"
        rec = {
            "species_id": sp.species_id,
            "category": sp.short_category,
            "category_id": sp.category_id,
            "common_name": sp.common_name,
            "scientific_name": sp.scientific_name,
            "family": sp.family,
            "biome": sp.biome,
            "status": "validated" if rep.is_valid else "failed",
            "source": source,
            "dimensions": dims,
            "geometry": geom,
            "provenance": {
                "source": source,
                "task_id": task_id,
                "preview_task_id": prov.get("preview_task_id"),
                "model_type": prov.get("model_type", "meshy-6" if source == "meshy" else "procedural"),
                "refine_status": prov.get("refine_status", "SUCCEEDED" if source == "meshy" else None),
                "remote_urls": prov.get("remote_urls", {}),
            },
            "files": {
                "glb": f"{rel_base}/{sp.species_id}.glb",
                "obj": f"{rel_base}/{sp.species_id}.obj",
                "mtl": f"{rel_base}/{sp.species_id}.mtl",
                "thumbnail": f"{rel_base}/thumbnail.png",
                "asset_manifest": f"{rel_base}/asset_manifest.json",
                "textures": {
                    "albedo": f"{rel_base}/textures/albedo.png",
                    "normal": f"{rel_base}/textures/normal.png",
                    "roughness": f"{rel_base}/textures/roughness.png",
                    "metallic": f"{rel_base}/textures/metallic.png",
                },
            },
            "validation": {
                "is_valid": rep.is_valid,
                "verdict": "PASSED" if rep.is_valid else "FAILED",
                "checks": rep.checks,
                "metrics": rep.metrics,
                "errors": rep.errors,
                "warnings": rep.warnings,
            },
            "last_updated": now_iso,
        }
        assets[sp.species_id] = rec

        c_sum = categories_summary.get(sp.short_category)
        if c_sum:
            c_sum["indexed_count"] += 1
            if rep.is_valid:
                c_sum["passed_validation"] += 1

    passed_count = sum(1 for a in assets.values() if a["validation"]["is_valid"])
    failed_count = sum(1 for a in assets.values() if not a["validation"]["is_valid"])

    manifest_payload = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "schema_version": "1.0.0",
        "project": "MorphoMesh Vegetation Library",
        "generated_at": now_iso,
        "total_catalog_species": len(catalog.species),
        "indexed_species_count": len(assets),
        "passed_validation_count": passed_count,
        "failed_validation_count": failed_count,
        "categories_summary": categories_summary,
        "assets": assets,
    }

    manifest_p = OUTPUT_DIR / "manifest.json"
    manifest_p.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")
    logger.info(f"Master manifest written to {manifest_p}: {passed_count}/{len(assets)} passed validation.")
    return manifest_payload

def synchronize_viewer(manifest_payload: dict):
    logger.info("Synchronizing viewer.html...")
    viewer_file = SCRIPT_DIR / "viewer.html"
    if not viewer_file.is_file():
        logger.error("viewer.html not found!")
        return

    content = viewer_file.read_text("utf-8")

    # Build plants array
    plants_data = []
    for sp in catalog.species:
        rec = manifest_payload["assets"].get(sp.species_id, {})
        geom = rec.get("geometry", {})
        dims = rec.get("dimensions", {})
        h_val = dims.get("height_m") or dims.get("normalized_height_m", sp.dimensions.height_m)
        s_val = dims.get("canopy_spread_m") or dims.get("normalized_canopy_spread_m", sp.dimensions.canopy_spread_m)
        faces_count = geom.get("face_count", 3280)
        verts_count = geom.get("vertex_count", 4064)
        source = rec.get("source", "procedural")

        rel_base = f"output/{sp.short_category}/{sp.species_id}"
        plant_entry = {
            "id": sp.species_id,
            "category": sp.short_category,
            "common_name": sp.common_name,
            "scientific_name": sp.scientific_name,
            "family": sp.family,
            "biome": sp.biome,
            "height": f"{float(h_val):.2f}m",
            "spread": f"{float(s_val):.2f}m",
            "faces": f"{int(faces_count):,}",
            "verts": f"{int(verts_count):,}",
            "thumb": f"{rel_base}/thumbnail.png",
            "turntables": [
                f"{rel_base}/turntable_01.png",
                f"{rel_base}/turntable_02.png",
                f"{rel_base}/turntable_03.png",
                f"{rel_base}/turntable_04.png",
            ],
            "glb": f"{rel_base}/{sp.species_id}.glb",
            "obj": f"{rel_base}/{sp.species_id}.obj",
            "source": source,
        }
        plants_data.append(plant_entry)

    plants_json = json.dumps(plants_data, indent=2)

    # Replace const plants = [...] in viewer.html
    import re
    new_content = re.sub(
        r"const plants = \[[\s\S]*?\n\s*\];",
        f"const plants = {plants_json};",
        content
    )

    # Update card badge to highlight all Meshy AI models
    badge_pattern = r"\$\{p\.id === 'veg_tree_oak_01' \? '([^']*)' : ''\}"
    new_badge = "${p.source === 'meshy' ? '<span class=\"absolute bottom-2 left-2 px-2 py-0.5 rounded-md bg-emerald-600 text-[10px] text-white font-bold shadow\">Meshy AI 3D</span>' : ''}"
    new_content = re.sub(badge_pattern, new_badge, new_content)

    viewer_file.write_text(new_content, encoding="utf-8")
    
    # Also write to output/viewer.html
    out_viewer = OUTPUT_DIR / "viewer.html"
    # In output/viewer.html, paths to output/ need to be relative to output/
    # So replace 'output/' with '' for thumb, turntables, glb, obj
    out_plants = []
    for p in plants_data:
        p_copy = dict(p)
        p_copy["thumb"] = p_copy["thumb"].replace("output/", "")
        p_copy["turntables"] = [t.replace("output/", "") for t in p_copy["turntables"]]
        p_copy["glb"] = p_copy["glb"].replace("output/", "")
        p_copy["obj"] = p_copy["obj"].replace("output/", "")
        out_plants.append(p_copy)
    out_plants_json = json.dumps(out_plants, indent=2)

    out_content = re.sub(
        r"const plants = \[[\s\S]*?\n\s*\];",
        f"const plants = {out_plants_json};",
        content
    )
    out_content = re.sub(badge_pattern, new_badge, out_content)
    # Also fix Hero image path in output/viewer.html if needed
    out_content = out_content.replace('src="output/', 'src="')
    out_viewer.write_text(out_content, encoding="utf-8")
    logger.info("Synchronized viewer.html and output/viewer.html successfully.")

if __name__ == "__main__":
    reprocess_invalid_meshy_assets()
    manifest = build_master_manifest()
    synchronize_viewer(manifest)
