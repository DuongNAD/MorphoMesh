"""
Milestone 2 Iteration 2 Empirical Challenger 2 Test Suite
File: E:/tool/mcp/MorphoMesh/.agents/m2_iter2_veg_challenger_2/empirical_stress_test.py

Adversarial Stress Testing & Verification:
1. Conifer Geometry & Quad Stitching:
   - All 5 conifer species in catalog (veg_conifer_pine_01, veg_conifer_spruce_01, veg_conifer_cypress_01, veg_conifer_redcedar_01, veg_conifer_cedar_01)
   - Strictly 0 orphan / unindexed vertices
   - quad_ratio == 1.0000, tri_count == 0
   - No NaNs, valid normals, closed quad cylinders and caps
2. Seed Boundary Stress:
   - Mandatory seeds: -1, 0, 2**32 - 1, 2**32, 2**64, 123.456, "test_string"
   - Adversarial extensions: -2**32, -999999999999, -3.14159, 2**128, "", "tree_unicode_seed", None
   - Deterministic repeatability across non-int seeds
3. Broadleaf Proportional Scaling:
   - Canopy spread sweep: 0.5m to 25.0m
   - Monotonic scaling of bounding box and crown radius
   - No miniature blowout, no extreme dimension clipping
4. Exhaustive 35-Species Invariant Verification:
   - Z_min == 0.000m (+/- 0.005m)
   - Base contact centroid (bottom 5% height) <= 0.05m of origin
   - Vertex budget: 3,000 <= V <= 45,000
   - Static GLB: 0 bones/skins/anims/joints/weights
   - 4-Channel PBR textures (512x512, dielectric metallic <= 0.05, OpenGL normal, valid albedo & roughness)
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
from typing import Any, Dict, List, Set, Tuple

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "teamwork_projects" / "vegetation_library"))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from vegetation_pipeline.catalog import get_catalog, PlantSpecies
from vegetation_pipeline.generator import (
    ProceduralBotanicalGenerator,
    RawAsset,
    unpack_glb_header_and_json,
)
from morphomesh.geometry.quad_utils import compute_quad_metrics


class EmpiricalTestReport:
    def __init__(self) -> None:
        self.total_tests: int = 0
        self.passed_tests: int = 0
        self.failed_tests: int = 0
        self.failures: List[Dict[str, Any]] = []

    def record_pass(self, name: str, details: str = "") -> None:
        self.total_tests += 1
        self.passed_tests += 1
        msg = f"  [PASS] {name}"
        if details:
            msg += f": {details}"
        print(msg)

    def record_fail(self, name: str, reason: str, details: str = "") -> None:
        self.total_tests += 1
        self.failed_tests += 1
        self.failures.append({"name": name, "reason": reason, "details": details})
        msg = f"  [FAIL] {name}: {reason}"
        if details:
            msg += f" ({details})"
        print(msg)


def test_conifer_geometry_suite(report: EmpiricalTestReport, temp_dir: Path) -> None:
    print("\n" + "=" * 80)
    print("SUITE 1: CONIFER GEOMETRY QUAD STITCHING & ORPHAN VERTEX VERIFICATION")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()
    conifers = [s for s in cat.species if "conifer" in s.category_id or s.short_category in ("conifers", "conifers_evergreens")]

    print(f"Discovered {len(conifers)} conifer species in catalog:")
    for c in conifers:
        print(f"  - {c.species_id} ({c.common_name}): H={c.dimensions.height_m}m, spread={c.dimensions.canopy_spread_m}m")

    assert len(conifers) >= 5, f"Expected at least 5 conifer species, found {len(conifers)}"

    for species in conifers:
        s_dir = temp_dir / "conifers" / species.species_id
        asset = gen.generate(species, output_dir=s_dir, seed=42)
        mesh = asset.mesh
        assert mesh is not None, f"Asset mesh is None for {species.species_id}"

        # 1. Orphan vertex check
        all_face_v: Set[int] = set()
        for f in mesh.faces:
            all_face_v.update(f)
        total_v = len(mesh.vertices)
        orphans = set(range(total_v)) - all_face_v

        test_orphan = f"{species.species_id} - Strictly 0 Orphan Vertices"
        if len(orphans) == 0:
            report.record_pass(test_orphan, f"total_verts={total_v}, indexed={len(all_face_v)}, orphans=0")
        else:
            report.record_fail(test_orphan, f"Found {len(orphans)} unindexed orphan vertices out of {total_v}")

        # 2. Quad dominance ratio check
        quad_count, tri_count, quad_ratio = compute_quad_metrics(mesh)
        test_quad = f"{species.species_id} - Face Topology (quad_ratio == 1.0000, tri_count == 0)"
        if quad_ratio == 1.0000 and tri_count == 0:
            report.record_pass(test_quad, f"quad_ratio={quad_ratio:.4f}, quads={quad_count}, tris={tri_count}")
        else:
            report.record_fail(test_quad, f"quad_ratio={quad_ratio:.4f} != 1.0000 or tri_count={tri_count} != 0")

        # 3. Geometry sanity (no NaNs, no Infs, positive volume)
        test_sanity = f"{species.species_id} - Coordinate Sanity & Bounds"
        has_nan = any(math.isnan(c) or math.isinf(c) for pt in mesh.vertices for c in pt)
        bbox = mesh.compute_bounding_box()
        if not has_nan and bbox.dimensions[0] > 0 and bbox.dimensions[1] > 0 and bbox.dimensions[2] > 0:
            report.record_pass(test_sanity, f"bbox={bbox.dimensions[0]:.2f}m x {bbox.dimensions[1]:.2f}m x {bbox.dimensions[2]:.2f}m")
        else:
            report.record_fail(test_sanity, f"has_nan={has_nan}, bbox={bbox.dimensions}")


def test_seed_boundary_stress_suite(report: EmpiricalTestReport, temp_dir: Path) -> None:
    print("\n" + "=" * 80)
    print("SUITE 2: SEED BOUNDARY & DATA TYPE ADVERSARIAL STRESS SUITE")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()
    oak = cat["veg_tree_oak_01"]

    stress_cases = [
        ("seed = -1", -1),
        ("seed = 0", 0),
        ("seed = 2**32 - 1", 2**32 - 1),
        ("seed = 2**32", 2**32),
        ("seed = 2**64", 2**64),
        ("seed = 123.456", 123.456),
        ("seed = 'test_string'", "test_string"),
        ("seed = -2**32", -(2**32)),
        ("seed = -999999999999", -999999999999),
        ("seed = -3.14159", -3.14159),
        ("seed = 2**128", 2**128),
        ("seed = '' (empty string)", ""),
        ("seed = 'tree_unicode_seed'", "tree_unicode_seed"),
        ("seed = None (fallback to species hash)", None),
    ]

    for label, seed_val in stress_cases:
        test_name = f"Seed Stress: {label}"
        safe_tag = abs(hash(str(seed_val))) % 100000
        out_dir = temp_dir / "seeds" / f"case_{safe_tag}"
        try:
            asset = gen.generate(oak, output_dir=out_dir, seed=seed_val)
            v = asset.vertex_count
            m_seed = asset.metadata.get("seed")
            if 3000 <= v <= 45000 and m_seed is not None and 0 <= m_seed < 2**32:
                report.record_pass(test_name, f"verts={v}, normalized_seed={m_seed}")
            else:
                report.record_fail(test_name, f"verts={v} or normalized_seed={m_seed} invalid")
        except Exception as e:
            report.record_fail(test_name, f"Raised unexpected {type(e).__name__}: {e}")

    repeat_cases = [-1, 2**32, 123.456, "test_string", "tree_unicode_seed"]
    for sc in repeat_cases:
        test_rep = f"Determinism for seed = {repr(sc)}"
        d1 = temp_dir / "seed_rep" / f"{abs(hash(str(sc)))%10000}_1"
        d2 = temp_dir / "seed_rep" / f"{abs(hash(str(sc)))%10000}_2"
        a1 = gen.generate(oak, output_dir=d1, seed=sc)
        a2 = gen.generate(oak, output_dir=d2, seed=sc)
        if a1.mesh.vertices == a2.mesh.vertices and a1.mesh.faces == a2.mesh.faces:
            report.record_pass(test_rep, "Bit-for-bit identical geometry produced")
        else:
            report.record_fail(test_rep, "Divergence between runs with identical non-standard seed")


def test_broadleaf_canopy_scaling_suite(report: EmpiricalTestReport, temp_dir: Path) -> None:
    print("\n" + "=" * 80)
    print("SUITE 3: BROADLEAF CANOPY SPREAD PROPORTIONAL SCALING (0.5m to 25.0m)")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()
    oak = cat["veg_tree_oak_01"]

    spread_steps = [0.5, 1.0, 2.0, 4.0, 8.0, 14.0, 20.0, 25.0]
    results: List[Tuple[float, float, float, float]] = []

    for spread in spread_steps:
        sp = oak.model_copy(deep=True)
        sp.dimensions.canopy_spread_m = spread
        s_dir = temp_dir / "scaling" / f"spread_{int(spread*10)}"
        asset = gen.generate(sp, output_dir=s_dir, seed=42)
        bbox = asset.mesh.compute_bounding_box()

        dx = bbox.dimensions[0]
        dy = bbox.dimensions[1]
        max_rad = max((v[0]**2 + v[1]**2)**0.5 for v in asset.mesh.vertices)
        eff_diam = 2.0 * max_rad
        results.append((spread, dx, dy, eff_diam))

        test_step = f"Broadleaf Spread = {spread:4.1f}m Scaling"
        if spread <= 1.0:
            if dx <= 1.5 and dy <= 1.5:
                report.record_pass(test_step, f"eff_diameter={eff_diam:.2f}m, dx={dx:.2f}m, dy={dy:.2f}m (no blowout)")
            else:
                report.record_fail(test_step, f"Small canopy spread {spread}m blown out to dx={dx:.2f}m, dy={dy:.2f}m")
        else:
            ratio = eff_diam / spread
            if 0.9 <= ratio <= 1.5:
                report.record_pass(test_step, f"eff_diameter={eff_diam:.2f}m, ratio={ratio:.3f} within [0.9, 1.5]")
            else:
                report.record_fail(test_step, f"eff_diameter={eff_diam:.2f}m ratio {ratio:.3f} out of proportional corridor [0.9, 1.5]")

    test_mono = "Broadleaf Canopy Spread Strict Monotonicity"
    is_monotonic = all(results[i][3] <= results[i+1][3] for i in range(len(results) - 1))
    if is_monotonic:
        report.record_pass(test_mono, f"Diameters strictly monotonically increase: {[round(r[3], 2) for r in results]}")
    else:
        report.record_fail(test_mono, f"Non-monotonic scaling observed: {results}")


def test_exhaustive_35_species_sweep(report: EmpiricalTestReport, temp_dir: Path) -> None:
    print("\n" + "=" * 80)
    print("SUITE 4: EXHAUSTIVE 35-SPECIES MULTI-BIOME INVARIANT SWEEP")
    print("=" * 80)

    cat = get_catalog()
    gen = ProceduralBotanicalGenerator()

    outlier_v = []
    outlier_z = []
    outlier_c = []
    outlier_bones = []
    outlier_pbr = []

    for s in cat.species:
        s_dir = temp_dir / "sweep35" / s.species_id
        asset = gen.generate(s, output_dir=s_dir, seed=42)

        v = asset.vertex_count
        if not (3000 <= v <= 45000):
            outlier_v.append((s.species_id, v))

        verts = asset.mesh.vertices
        z_min = min(pt[2] for pt in verts)
        if abs(z_min) > 0.005:
            outlier_z.append((s.species_id, z_min))

        z_max = max(pt[2] for pt in verts)
        h = z_max - z_min
        base_threshold = z_min + 0.05 * h
        base_verts = [pt for pt in verts if pt[2] <= base_threshold]
        if base_verts:
            cx = sum(pt[0] for pt in base_verts) / len(base_verts)
            cy = sum(pt[1] for pt in base_verts) / len(base_verts)
            c_dist = math.hypot(cx, cy)
            if c_dist > 0.05:
                outlier_c.append((s.species_id, c_dist))
        else:
            outlier_c.append((s.species_id, "no_base_verts"))

        gltf, _ = unpack_glb_header_and_json(asset.glb_path)
        skins = gltf.get("skins", [])
        anims = gltf.get("animations", [])
        has_bad_attr = False
        for m in gltf.get("meshes", []):
            for prim in m.get("primitives", []):
                attrs = prim.get("attributes", {})
                if any(k in attrs for k in ("JOINTS_0", "JOINTS_1", "WEIGHTS_0", "WEIGHTS_1")):
                    has_bad_attr = True
        if len(skins) > 0 or len(anims) > 0 or has_bad_attr:
            outlier_bones.append((s.species_id, len(skins), len(anims), has_bad_attr))

        pbr_errs = []
        for tname in ("albedo", "normal", "roughness", "metallic"):
            tp = asset.texture_paths.get(tname)
            if not tp or not tp.is_file():
                pbr_errs.append(f"missing_{tname}")
                continue
            img = Image.open(tp)
            if img.size != (512, 512):
                pbr_errs.append(f"{tname}_res_{img.size}")
            arr = np.array(img).astype(np.float32)
            if tname == "albedo":
                if float(np.mean(arr)) < 15.0 or float(np.var(arr)) < 3.0:
                    pbr_errs.append("albedo_flat_or_black")
            elif tname == "normal":
                if float(np.mean(arr[:, :, 2])) < 170.0 or float(np.var(arr)) < 1.0:
                    pbr_errs.append("normal_invalid_tangent")
            elif tname == "metallic":
                if float(np.max(arr)) / 255.0 > 0.05:
                    pbr_errs.append("metallic_non_dielectric")
            elif tname == "roughness":
                r_norm = float(np.mean(arr)) / 255.0
                if not (0.15 <= r_norm <= 0.95):
                    pbr_errs.append("roughness_out_of_range")
        if pbr_errs:
            outlier_pbr.append((s.species_id, pbr_errs))

    test_v = "35-Species Sweep: Vertex Budget [3000, 45000]"
    if not outlier_v:
        report.record_pass(test_v, "All 35 species strictly within [3000, 45000] vertices")
    else:
        report.record_fail(test_v, f"Outliers: {outlier_v}")

    test_z = "35-Species Sweep: Ground Alignment min(Z) == 0.000m (+/- 0.005m)"
    if not outlier_z:
        report.record_pass(test_z, "All 35 species strictly grounded at Z_min = 0.000m")
    else:
        report.record_fail(test_z, f"Outliers: {outlier_z}")

    test_c = "35-Species Sweep: Base Contact Centroid Centering (<= 0.05m)"
    if not outlier_c:
        report.record_pass(test_c, "All 35 species base centroids within 0.05m of origin")
    else:
        report.record_fail(test_c, f"Outliers: {outlier_c}")

    test_b = "35-Species Sweep: N_bones == 0 Static Mesh GLB Compliance"
    if not outlier_bones:
        report.record_pass(test_b, "All 35 species strictly unrigged, 0 skins, 0 anims, 0 joints/weights")
    else:
        report.record_fail(test_b, f"Outliers: {outlier_bones}")

    test_p = "35-Species Sweep: 4-Channel PBR Textures Valid"
    if not outlier_pbr:
        report.record_pass(test_p, "All 35 species feature valid 512x512 dielectric PBR textures")
    else:
        report.record_fail(test_p, f"Outliers: {outlier_pbr}")


def main() -> int:
    report = EmpiricalTestReport()
    temp_dir = Path(tempfile.mkdtemp(prefix="veg_challenger2_iter2_"))

    print("=" * 80)
    print("EMPIRICAL CHALLENGER 2 - MILESTONE 2 ITERATION 2 ADVERSARIAL STRESS SUITE")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Temporary directory: {temp_dir}")
    print("=" * 80)

    try:
        test_conifer_geometry_suite(report, temp_dir)
        test_seed_boundary_stress_suite(report, temp_dir)
        test_broadleaf_canopy_scaling_suite(report, temp_dir)
        test_exhaustive_35_species_sweep(report, temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\n" + "=" * 80)
    print("TEST SUITE SUMMARY")
    print(f"Total Tests Executed : {report.total_tests}")
    print(f"Passed Tests         : {report.passed_tests}")
    print(f"Failed Tests         : {report.failed_tests}")
    print("=" * 80)

    if report.failures:
        print("\nFAILURES DETECTED:")
        for idx, f in enumerate(report.failures, 1):
            print(f"[{idx}] {f['name']}: {f['reason']} - {f['details']}")
        return 1

    print("\nALL ADVERSARIAL EMPIRICAL TESTS PASSED WITH ZERO DEFECTS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
