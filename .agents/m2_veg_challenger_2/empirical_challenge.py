"""
Milestone 2 Botanical Generation Engine - Empirical Challenger 2 Test Suite
File: E:/tool/mcp/MorphoMesh/.agents/m2_veg_challenger_2/empirical_challenge.py

Adversarial Stress Testing & Empirical Verification:
1. Multi-Category Verification (14+ species across all 7 botanical categories, plus exhaustive 35-species sweep).
2. Strict Invariants:
   - Vertex count: 3,000 <= N_verts <= 45,000.
   - Ground alignment: min(v[2]) == 0.000m (+/- 0.005m).
   - Base contact centroid: bottom 5% height centered within (+/- 0.05m) of origin.
   - Static mesh invariants: GLB binary parsing, skins empty/omitted, anims empty/omitted, zero JOINTS_0/WEIGHTS_0.
   - 4-Channel PBR textures: 512x512 PNG, non-flat, non-black Albedo, OpenGL normal, dielectric metallic <= 0.05.
3. Seed Determinism: Identical seeds produce bit-identical geometry, differing seeds diverge.
4. Boundary Conditions: Zero seed, negative seed, large seeds, extreme scale dimensions.
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import time
from typing import Any, Dict, List, Tuple

import numpy as np
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "teamwork_projects" / "vegetation_library"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vegetation_pipeline.catalog import get_catalog, get_species, list_categories, PlantSpecies
from vegetation_pipeline.generator import (
    ProceduralBotanicalGenerator,
    ProceduralGeneratorConfig,
    RawAsset,
    generate_plant,
    unpack_glb_header_and_json,
)


class EmpiricalVerificationReport:
    def __init__(self) -> None:
        self.total_tests: int = 0
        self.passed_tests: int = 0
        self.failed_tests: int = 0
        self.findings: List[Dict[str, Any]] = []
        self.records: List[Dict[str, Any]] = []

    def record_pass(self, test_name: str, details: str = "") -> None:
        self.total_tests += 1
        self.passed_tests += 1
        print(f"  [PASS] {test_name}" + (f": {details}" if details else ""))

    def record_fail(self, test_name: str, reason: str, details: str = "") -> None:
        self.total_tests += 1
        self.failed_tests += 1
        finding = {
            "test_name": test_name,
            "reason": reason,
            "details": details,
        }
        self.findings.append(finding)
        print(f"  [FAIL] {test_name}: {reason}" + (f" ({details})" if details else ""))


def run_multi_category_species_verification(report: EmpiricalVerificationReport, temp_dir: Path) -> None:
    """
    Test all 7 botanical categories with at least 2 distinct species per category (total 14+ species).
    Asserts:
    1. 3,000 <= N_verts <= 45,000
    2. min(v[2]) == 0.000m (+/- 0.005m)
    3. base contact centroid (bottom 5% height) centered within (+/- 0.05m) of origin
    4. static mesh invariants: skins == []/omitted, anims == []/omitted, zero JOINTS_0/WEIGHTS_0
    5. PBR textures: 512x512, non-flat, non-black Albedo, OpenGL normal, dielectric metallic <= 0.05
    """
    print("\n" + "=" * 80)
    print("TEST SUITE 1: 7-BIOME MULTI-SPECIES EMPIRICAL INVARIANT VERIFICATION")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()

    # Select 2 distinct species per category (14 distinct species total)
    selected_species: List[PlantSpecies] = []
    for c in cat.categories:
        species_in_cat = [s for s in cat.species if s.category_id == c.category_id]
        assert len(species_in_cat) >= 2, f"Category {c.category_id} has fewer than 2 species"
        selected_species.extend(species_in_cat[:2])

    print(f"Testing {len(selected_species)} distinct species across all {len(cat.categories)} categories...")

    for species in selected_species:
        species_dir = temp_dir / species.species_id
        t0 = time.perf_counter()
        asset = gen.generate(species, output_dir=species_dir, seed=42)
        elapsed = time.perf_counter() - t0

        # --- 1. Vertex count check ---
        v_count = asset.vertex_count
        test_v = f"{species.species_id} - Vertex Budget"
        if 3000 <= v_count <= 45000:
            report.record_pass(test_v, f"{v_count} verts in budget [3000, 45000]")
        else:
            report.record_fail(test_v, f"Vertex count {v_count} out of budget [3000, 45000]")

        # --- 2. Ground alignment check ---
        verts = asset.mesh.vertices
        z_min = min(v[2] for v in verts)
        z_max = max(v[2] for v in verts)
        h_mesh = z_max - z_min

        test_ground = f"{species.species_id} - Ground Alignment"
        if abs(z_min) <= 0.005:
            report.record_pass(test_ground, f"min(z) = {z_min:.6f}m (within +/- 0.005m)")
        else:
            report.record_fail(test_ground, f"min(z) = {z_min:.6f}m violates ground plane alignment tolerance")

        # --- 3. Contact centroid centering check (bottom 5% height) ---
        test_centroid = f"{species.species_id} - Base Contact Centroid Centering"
        base_threshold = z_min + 0.05 * h_mesh
        base_verts = [v for v in verts if v[2] <= base_threshold]
        if base_verts:
            cx = sum(v[0] for v in base_verts) / len(base_verts)
            cy = sum(v[1] for v in base_verts) / len(base_verts)
            dist_from_origin = math.hypot(cx, cy)
            if dist_from_origin <= 0.05:
                report.record_pass(test_centroid, f"centroid offset = {dist_from_origin:.6f}m (cx={cx:.6f}, cy={cy:.6f}) <= 0.05m")
            else:
                report.record_fail(test_centroid, f"centroid offset {dist_from_origin:.6f}m exceeds 0.05m")
        else:
            report.record_fail(test_centroid, "No base vertices found in bottom 5% height")

        # --- 4. Static mesh invariants in GLB ---
        test_glb = f"{species.species_id} - Static Mesh Binary GLB Compliance"
        glb_path = asset.glb_path
        if not glb_path.is_file() or glb_path.stat().st_size == 0:
            report.record_fail(test_glb, f"GLB file missing or 0 bytes: {glb_path}")
        else:
            try:
                gltf, _ = unpack_glb_header_and_json(glb_path)
                skins = gltf.get("skins", [])
                animations = gltf.get("animations", [])
                has_skin = len(skins) > 0
                has_anim = len(animations) > 0

                has_joint_weight = False
                bad_attrs = []
                for m in gltf.get("meshes", []):
                    for prim in m.get("primitives", []):
                        attrs = prim.get("attributes", {})
                        for bad in ("JOINTS_0", "JOINTS_1", "WEIGHTS_0", "WEIGHTS_1"):
                            if bad in attrs:
                                has_joint_weight = True
                                bad_attrs.append(bad)

                if not has_skin and not has_anim and not has_joint_weight:
                    report.record_pass(test_glb, "skins=[], anims=[], zero JOINTS/WEIGHTS accessors")
                else:
                    report.record_fail(test_glb, f"Non-static GLB! skins={skins}, anims={animations}, bad_attrs={bad_attrs}")
            except Exception as e:
                report.record_fail(test_glb, f"Failed parsing GLB container: {e}")

        # --- 5. PBR Texture suite verification ---
        test_pbr = f"{species.species_id} - PBR Textures Suite"
        pbr_failures = []
        for tname in ("albedo", "normal", "roughness", "metallic"):
            tpath = asset.texture_paths.get(tname)
            if not tpath or not tpath.is_file():
                pbr_failures.append(f"Missing {tname} file on disk")
                continue

            img = Image.open(tpath)
            if img.size != (512, 512):
                pbr_failures.append(f"{tname} dimension {img.size} != (512, 512)")

            arr = np.array(img).astype(np.float32)
            var_val = float(np.var(arr))
            mean_val = float(np.mean(arr))

            if tname == "albedo":
                if mean_val < 15.0:
                    pbr_failures.append(f"albedo mean {mean_val:.2f} < 15.0 (too dark/black)")
                if var_val < 3.0:
                    pbr_failures.append(f"albedo variance {var_val:.2f} < 3.0 (flat)")
            elif tname == "normal":
                # Tangent space normal map: Blue channel (+Z outward) dominant, mean >= 170.0
                blue_mean = float(np.mean(arr[:, :, 2]))
                if blue_mean < 170.0:
                    pbr_failures.append(f"normal blue channel mean {blue_mean:.2f} < 170.0")
                if var_val < 1.0:
                    pbr_failures.append(f"normal variance {var_val:.2f} < 1.0 (flat)")
            elif tname == "roughness":
                norm_mean = mean_val / 255.0
                if not (0.15 <= norm_mean <= 0.95):
                    pbr_failures.append(f"roughness norm mean {norm_mean:.2f} outside [0.15, 0.95]")
            elif tname == "metallic":
                max_norm = float(np.max(arr)) / 255.0
                if max_norm > 0.05:
                    pbr_failures.append(f"metallic max {max_norm:.2f} > 0.05 (non-dielectric)")

        if not pbr_failures:
            report.record_pass(test_pbr, "512x512, non-flat, non-black Albedo, OpenGL normal, dielectric metallic <= 0.05")
        else:
            report.record_fail(test_pbr, "; ".join(pbr_failures))

        report.records.append({
            "species_id": species.species_id,
            "category": species.category_id,
            "vertex_count": v_count,
            "face_count": asset.face_count,
            "z_min": z_min,
            "h_mesh": h_mesh,
            "elapsed_s": elapsed,
        })


def run_exhaustive_35_species_sweep(report: EmpiricalVerificationReport, temp_dir: Path) -> None:
    """Runs a complete sweep across all 35 species in the catalog to ensure zero outliers."""
    print("\n" + "=" * 80)
    print("TEST SUITE 2: EXHAUSTIVE 35-SPECIES SWEEP (ALL BIOMES)")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()

    outlier_verts = []
    outlier_zmin = []
    outlier_centroid = []

    for s in cat.species:
        s_dir = temp_dir / "sweep" / s.species_id
        asset = gen.generate(s, output_dir=s_dir, seed=42)
        v = asset.vertex_count
        if not (3000 <= v <= 45000):
            outlier_verts.append((s.species_id, v))

        verts = asset.mesh.vertices
        z_min = min(pt[2] for pt in verts)
        if abs(z_min) > 0.005:
            outlier_zmin.append((s.species_id, z_min))

        z_max = max(pt[2] for pt in verts)
        h = z_max - z_min
        base_verts = [pt for pt in verts if pt[2] <= z_min + 0.05 * h]
        if base_verts:
            cx = sum(pt[0] for pt in base_verts) / len(base_verts)
            cy = sum(pt[1] for pt in base_verts) / len(base_verts)
            if math.hypot(cx, cy) > 0.05:
                outlier_centroid.append((s.species_id, math.hypot(cx, cy)))

    test_verts = "Exhaustive 35-Species Sweep - Vertex Count Budget"
    if not outlier_verts:
        report.record_pass(test_verts, "All 35 species strictly within [3000, 45000] vertices")
    else:
        report.record_fail(test_verts, f"Outliers found: {outlier_verts}")

    test_zmin = "Exhaustive 35-Species Sweep - Ground Pivot Invariant"
    if not outlier_zmin:
        report.record_pass(test_zmin, "All 35 species strictly aligned at min(z) == 0.000m (+/- 0.005m)")
    else:
        report.record_fail(test_zmin, f"Outliers found: {outlier_zmin}")

    test_cent = "Exhaustive 35-Species Sweep - Centroid Origin Invariant"
    if not outlier_centroid:
        report.record_pass(test_cent, "All 35 species base contact centroids within 0.05m of origin")
    else:
        report.record_fail(test_cent, f"Outliers found: {outlier_centroid}")


def run_seed_determinism_tests(report: EmpiricalVerificationReport, temp_dir: Path) -> None:
    """
    Tests seed determinism:
    1. Identical seed produces identical vertices and faces.
    2. Different seed produces diverging geometry.
    3. Species default seed produces consistent geometry.
    """
    print("\n" + "=" * 80)
    print("TEST SUITE 3: SEED DETERMINISM & DIVERSITY VERIFICATION")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()

    # Test across one representative species per biome (7 species)
    test_species_ids = [
        "veg_tree_oak_01",
        "veg_conifer_pine_01",
        "veg_tropical_palm_01",
        "veg_shrub_rose_01",
        "veg_ground_fern_01",
        "veg_succulent_saguaro_01",
        "veg_vine_ivy_01",
    ]

    for sid in test_species_ids:
        species = cat[sid]
        s_dir = temp_dir / "seeds" / sid

        # Pass 1: seed=12345
        a1 = gen.generate(species, output_dir=s_dir / "s1", seed=12345)
        # Pass 2: seed=12345
        a2 = gen.generate(species, output_dir=s_dir / "s2", seed=12345)
        # Pass 3: seed=98765
        a3 = gen.generate(species, output_dir=s_dir / "s3", seed=98765)

        test_repeat = f"{sid} - Deterministic Repeatability (Seed 12345)"
        verts_match = (a1.mesh.vertices == a2.mesh.vertices)
        faces_match = (a1.mesh.faces == a2.mesh.faces)
        if verts_match and faces_match:
            report.record_pass(test_repeat, "Bit-for-bit identical vertices and faces")
        else:
            report.record_fail(test_repeat, f"Divergence on same seed! verts_match={verts_match}, faces_match={faces_match}")

        test_diversity = f"{sid} - Morphological Diversity (Seed 12345 vs 98765)"
        verts_differ = (a1.mesh.vertices != a3.mesh.vertices)
        if verts_differ:
            report.record_pass(test_diversity, "Geometry successfully diverges across different seeds")
        else:
            report.record_fail(test_diversity, "Geometry unexpectedly identical across different seeds")


def run_boundary_conditions_stress_tests(report: EmpiricalVerificationReport, temp_dir: Path) -> None:
    """
    Stress-tests boundary conditions:
    1. Zero seed (seed = 0)
    2. Large seeds (seed = 2**31 - 1, seed = 2**32 - 1, seed = 2**32, seed = 10**10)
    3. Negative seeds (seed = -1, seed = -42)
    4. Extreme scale dimensions (bonsai/moss scale: 0.05m, hyperion scale: 150m)
    """
    print("\n" + "=" * 80)
    print("TEST SUITE 4: ADVERSARIAL BOUNDARY CONDITIONS STRESS TESTS")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()
    species = cat["veg_tree_oak_01"]

    # --- 1. Zero Seed ---
    test_zero = "Boundary: Zero Seed (seed=0)"
    try:
        a_zero = gen.generate(species, output_dir=temp_dir / "b_zero", seed=0)
        assert 3000 <= a_zero.vertex_count <= 45000
        assert min(v[2] for v in a_zero.mesh.vertices) == 0.0
        report.record_pass(test_zero, f"Generated {a_zero.vertex_count} verts with Z_min=0.0")
    except Exception as e:
        report.record_fail(test_zero, f"Unexpected error on seed=0: {e}")

    # --- 2. Large Seed within uint32: 2**31 - 1 ---
    test_large_uint31 = "Boundary: Large Seed uint31 max (seed=2**31 - 1)"
    try:
        a_uint31 = gen.generate(species, output_dir=temp_dir / "b_uint31", seed=2**31 - 1)
        assert 3000 <= a_uint31.vertex_count <= 45000
        report.record_pass(test_large_uint31, f"Generated {a_uint31.vertex_count} verts")
    except Exception as e:
        report.record_fail(test_large_uint31, f"Failed on seed=2**31 - 1: {e}")

    # --- 3. Large Seed uint32 max: 2**32 - 1 ---
    test_large_uint32 = "Boundary: Large Seed uint32 max (seed=2**32 - 1)"
    try:
        a_uint32 = gen.generate(species, output_dir=temp_dir / "b_uint32", seed=2**32 - 1)
        assert 3000 <= a_uint32.vertex_count <= 45000
        report.record_pass(test_large_uint32, f"Generated {a_uint32.vertex_count} verts")
    except Exception as e:
        report.record_fail(test_large_uint32, f"Failed on seed=2**32 - 1: {e}")

    # --- 4. Negative Seed: seed = -1 ---
    test_neg_seed = "Boundary: Negative Seed (seed=-1)"
    try:
        gen.generate(species, output_dir=temp_dir / "b_neg", seed=-1)
        report.record_pass(test_neg_seed, "Handled negative seed without crashing")
    except ValueError as e:
        report.record_fail(
            test_neg_seed,
            "Numpy RandomState rejection on negative seed without normalization",
            f"ValueError: {e}"
        )
    except Exception as e:
        report.record_fail(test_neg_seed, f"Unexpected exception: {type(e).__name__}: {e}")

    # --- 5. Exceeding uint32: seed = 2**32 ---
    test_overflow_seed = "Boundary: Seed exceeding uint32 (seed=2**32)"
    try:
        gen.generate(species, output_dir=temp_dir / "b_overflow", seed=2**32)
        report.record_pass(test_overflow_seed, "Handled seed >= 2**32 without crashing")
    except ValueError as e:
        report.record_fail(
            test_overflow_seed,
            "Numpy RandomState rejection on seed >= 2**32 without modulo masking",
            f"ValueError: {e}"
        )
    except Exception as e:
        report.record_fail(test_overflow_seed, f"Unexpected exception: {type(e).__name__}: {e}")

    # --- 6. Extreme Scale Dimensions ---
    for cat_name in ("broadleaf_deciduous_trees", "conifers_evergreens", "tropical_foliage_palms",
                     "flowering_shrubs_ornamentals", "ferns_grasses_groundcover", "succulents_cacti", "climbing_vines_epiphytes"):
        sp = [s for s in cat.species if s.category_id == cat_name][0]

        # Tiny scale: H=0.05m
        test_tiny = f"Boundary: Tiny Scale (H=0.05m) - {sp.species_id}"
        tiny_sp = sp.model_copy(deep=True)
        tiny_sp.dimensions.height_m = 0.05
        tiny_sp.dimensions.height_range_m = (0.01, 0.10)
        tiny_sp.dimensions.canopy_spread_m = 0.04
        tiny_sp.dimensions.trunk_stem_diameter_m = 0.005

        try:
            a_tiny = gen.generate(tiny_sp, output_dir=temp_dir / f"tiny_{sp.species_id}", seed=42)
            has_nan = any(math.isnan(c) for pt in a_tiny.mesh.vertices for c in pt)
            z_min = min(pt[2] for pt in a_tiny.mesh.vertices)
            if not has_nan and abs(z_min) <= 0.005 and 3000 <= a_tiny.vertex_count <= 45000:
                report.record_pass(test_tiny, f"verts={a_tiny.vertex_count}, z_min={z_min:.6f}m, zero NaNs")
            else:
                report.record_fail(test_tiny, f"Invariant violation: verts={a_tiny.vertex_count}, z_min={z_min}, has_nan={has_nan}")
        except Exception as e:
            report.record_fail(test_tiny, f"Crash on tiny scale: {e}")

        # Huge scale: H=150.0m
        test_huge = f"Boundary: Huge Scale (H=150.0m) - {sp.species_id}"
        huge_sp = sp.model_copy(deep=True)
        huge_sp.dimensions.height_m = 150.0
        huge_sp.dimensions.height_range_m = (100.0, 200.0)
        huge_sp.dimensions.canopy_spread_m = 80.0
        huge_sp.dimensions.trunk_stem_diameter_m = 5.0

        try:
            a_huge = gen.generate(huge_sp, output_dir=temp_dir / f"huge_{sp.species_id}", seed=42)
            has_nan = any(math.isnan(c) for pt in a_huge.mesh.vertices for c in pt)
            z_min = min(pt[2] for pt in a_huge.mesh.vertices)
            if not has_nan and abs(z_min) <= 0.005 and 3000 <= a_huge.vertex_count <= 45000:
                report.record_pass(test_huge, f"verts={a_huge.vertex_count}, z_min={z_min:.6f}m, zero NaNs")
            else:
                report.record_fail(test_huge, f"Invariant violation: verts={a_huge.vertex_count}, z_min={z_min}, has_nan={has_nan}")
        except Exception as e:
            report.record_fail(test_huge, f"Crash on huge scale: {e}")


def main() -> int:
    report = EmpiricalVerificationReport()
    temp_dir = Path(tempfile.mkdtemp(prefix="veg_challenger2_"))

    print("=" * 80)
    print("STARTING EMPIRICAL CHALLENGER 2 ADVERSARIAL VERIFICATION HARNESS")
    print(f"Working Directory: {Path(__file__).resolve().parent}")
    print(f"Temp Output Directory: {temp_dir}")
    print("=" * 80)

    try:
        run_multi_category_species_verification(report, temp_dir)
        run_exhaustive_35_species_sweep(report, temp_dir)
        run_seed_determinism_tests(report, temp_dir)
        run_boundary_conditions_stress_tests(report, temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 80)
    print("EMPIRICAL CHALLENGER 2 SUMMARY")
    print(f"Total Tests Executed : {report.total_tests}")
    print(f"Passed Tests         : {report.passed_tests}")
    print(f"Failed Tests         : {report.failed_tests}")
    print("=" * 80)

    if report.findings:
        print("\nADVERSARIAL CHALLENGES / VULNERABILITIES IDENTIFIED:")
        for idx, f in enumerate(report.findings, 1):
            print(f"[{idx}] {f['test_name']}")
            print(f"    Reason : {f['reason']}")
            if f.get("details"):
                print(f"    Details: {f['details']}")

    # Return exit code equal to number of failures
    return 0 if report.failed_tests == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
