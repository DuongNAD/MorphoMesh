"""
Adversarial Stress Test Suite for Milestone 3:
Materials, Hair Curves, Wardrobe & Magic Props.

Empirical verification of:
1. Standalone Blender script AST validity under diverse/adversarial configurations.
2. Manifoldness, non-degeneracy, and zero-area face freedom for all garment & prop meshes.
3. Hair curve splines integrity across heights and density scales (0 NaNs/Infs, taper bounds, positive lengths).
4. Anthropometric boundary tests and clearance offset analysis across heights and waist girths.
"""

from __future__ import annotations

import ast
import math
import pytest
from typing import Dict, List, Tuple

from morphomesh.human_materials import (
    HumanMaterialConfig,
    STANDARD_HUMAN_MATERIALS,
    get_material_setup_script,
    setup_human_materials,
)
from morphomesh.human_grooming import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    convert_curves_to_ribbon_mesh,
    generate_hime_cut_splines,
    get_default_hime_cut_layers,
    get_grooming_script,
    groom_human,
)
from morphomesh.wardrobe import (
    WardrobeConfig,
    dress_human,
    generate_dress_bodice,
    generate_dress_pleated_skirt,
    generate_dress_waist_sash,
    generate_flat_sandals,
    generate_marionette_red_strings,
    generate_swallowtail_butterfly,
    generate_yu_nian_an_wardrobe,
    get_wardrobe_script,
)
from morphomesh.human_generator import HumanAnatomyGenerator
from morphomesh.models import HumanAnatomyConfig
from morphomesh.inference_adapter import MeshGeometry


def _triangle_area_3d(v0: Tuple[float, float, float], v1: Tuple[float, float, float], v2: Tuple[float, float, float]) -> float:
    """Computes 3D Euclidean area of triangle (v0, v1, v2) via cross product."""
    ax = v1[0] - v0[0]
    ay = v1[1] - v0[1]
    az = v1[2] - v0[2]

    bx = v2[0] - v0[0]
    by = v2[1] - v0[1]
    bz = v2[2] - v0[2]

    # Cross product a x b
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx

    return 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)


class TestScriptASTAdversarial:
    """Adversarially tests Python AST validity across combinatorial parameter inputs."""

    @pytest.mark.parametrize("target_obj", ["Human_Base_Mesh", "Yu_Nian_An_Model", "Mesh Object With Spaces", "Obj_42"])
    @pytest.mark.parametrize("engine", ["CYCLES", "BLENDER_EEVEE_NEXT", "BLENDER_WORKBENCH"])
    @pytest.mark.parametrize("preset", ["yu_nian_an", "default"])
    def test_material_script_ast_permutations(self, target_obj: str, engine: str, preset: str):
        """Verify all material setup script variations produce valid Python AST."""
        code = get_material_setup_script(target_object=target_obj, render_engine=engine, material_preset=preset)
        parsed = ast.parse(code)
        assert isinstance(parsed, ast.Module), "Generated script must parse to an ast.Module"

    @pytest.mark.parametrize("target_obj", ["Human_Base_Mesh", "Yu_Nian_An"])
    @pytest.mark.parametrize("strand_count", [0, 10, 1500, 15000, 50000])
    @pytest.mark.parametrize("ribbons", [False, True])
    def test_grooming_script_ast_permutations(self, target_obj: str, strand_count: int, ribbons: bool):
        """Verify all grooming script variations produce valid Python AST."""
        code = get_grooming_script(
            target_object=target_obj,
            strand_count=strand_count,
            generate_ribbons=ribbons,
            include_eyebrows=True,
            include_eyelashes=True,
        )
        parsed = ast.parse(code)
        assert isinstance(parsed, ast.Module)

    @pytest.mark.parametrize("target_obj", ["Human_Base_Mesh", "Yu_Nian_An"])
    @pytest.mark.parametrize("clearance", [-0.01, 0.0, 0.015, 0.05])
    @pytest.mark.parametrize("b_count", [0, 1, 10, 30])
    def test_wardrobe_script_ast_permutations(self, target_obj: str, clearance: float, b_count: int):
        """Verify all wardrobe script variations produce valid Python AST."""
        code = get_wardrobe_script(
            target_object=target_obj,
            clearance_offset=clearance,
            butterfly_count=b_count,
            include_sandals=True,
            include_red_threads=True,
            include_glowing_butterflies=True,
        )
        parsed = ast.parse(code)
        assert isinstance(parsed, ast.Module)


class TestMeshTopologyAndManifoldness:
    """Validates manifoldness, non-degeneracy, and zero-area face freedom for all wardrobe & prop meshes."""

    @pytest.fixture(scope="class")
    def full_wardrobe(self) -> Dict[str, MeshGeometry]:
        cfg = WardrobeConfig(character_height=1.65, clearance_offset=0.015, butterfly_count=10)
        return generate_yu_nian_an_wardrobe(cfg)

    def test_all_wardrobe_components_present_and_non_empty(self, full_wardrobe: Dict[str, MeshGeometry]):
        """Verify all expected garments, footwear, strings, and butterflies exist and have non-empty geometry."""
        expected_keys = [
            "Dress_Bodice",
            "Dress_WaistSash",
            "Dress_PleatedSkirt",
            "Mesh_Sandal_L",
            "Mesh_Sandal_R",
            "Prop_Marionette_Strings",
        ] + [f"Prop_Butterfly_{i:02d}" for i in range(10)]

        for key in expected_keys:
            assert key in full_wardrobe, f"Missing component: {key}"
            mesh = full_wardrobe[key]
            assert len(mesh.vertices) > 0, f"{key} has 0 vertices"
            assert len(mesh.faces) > 0, f"{key} has 0 faces"

    def test_zero_degenerate_faces(self, full_wardrobe: Dict[str, MeshGeometry]):
        """Ensure no face contains duplicate vertex indices (e.g. i0 == i1)."""
        for name, mesh in full_wardrobe.items():
            for f_idx, (i0, i1, i2) in enumerate(mesh.faces):
                assert i0 != i1 and i1 != i2 and i0 != i2, (
                    f"Degenerate face {f_idx} in {name} with vertices ({i0}, {i1}, {i2})"
                )

    def test_zero_area_faces_freedom(self, full_wardrobe: Dict[str, MeshGeometry]):
        """Assert all triangular facets across all garments and props have strictly positive area (> 1e-9 m^2)."""
        zero_area_count = 0
        min_areas: Dict[str, float] = {}

        for name, mesh in full_wardrobe.items():
            min_area = float("inf")
            for f_idx, (i0, i1, i2) in enumerate(mesh.faces):
                v0 = mesh.vertices[i0]
                v1 = mesh.vertices[i1]
                v2 = mesh.vertices[i2]
                area = _triangle_area_3d(v0, v1, v2)
                if area < min_area:
                    min_area = area
                if area < 1e-9:
                    zero_area_count += 1
            min_areas[name] = min_area
            assert min_area >= 1e-9, f"{name} contains near-zero area face: min_area={min_area}"

        assert zero_area_count == 0, f"Found {zero_area_count} zero-area faces in wardrobe meshes"

    def test_edge_manifoldness(self, full_wardrobe: Dict[str, MeshGeometry]):
        """
        Verify that for every garment and prop, no edge is shared by > 2 triangular facets.
        For open 2-manifold surfaces, each edge must have either 1 adjacent face (boundary)
        or 2 adjacent faces (manifold interior). Edge count >= 3 indicates non-manifold T-junctions.
        """
        for name, mesh in full_wardrobe.items():
            edge_face_count: Dict[Tuple[int, int], int] = {}
            for i0, i1, i2 in mesh.faces:
                edges = [
                    (min(i0, i1), max(i0, i1)),
                    (min(i1, i2), max(i1, i2)),
                    (min(i2, i0), max(i2, i0)),
                ]
                for e in edges:
                    edge_face_count[e] = edge_face_count.get(e, 0) + 1

            non_manifold_edges = {e: cnt for e, cnt in edge_face_count.items() if cnt > 2}
            assert len(non_manifold_edges) == 0, (
                f"{name} has {len(non_manifold_edges)} non-manifold edges with > 2 adjacent faces: {non_manifold_edges}"
            )

    def test_finite_normals_and_uvs(self, full_wardrobe: Dict[str, MeshGeometry]):
        """Verify normal vectors and UV coordinates have 0 NaNs or Infs."""
        for name, mesh in full_wardrobe.items():
            for idx, norm in enumerate(mesh.normals):
                for val in norm:
                    assert not math.isnan(val) and not math.isinf(val), f"NaN/Inf normal at {idx} in {name}"
            for idx, uv in enumerate(mesh.uvs):
                for val in uv:
                    assert not math.isnan(val) and not math.isinf(val), f"NaN/Inf UV at {idx} in {name}"


class TestHairCurveSplinesAdversarial:
    """Stress tests hair curve splines generation across extreme heights and densities."""

    @pytest.mark.parametrize("h", [1.20, 1.40, 1.65, 2.00, 2.20])
    @pytest.mark.parametrize("density", [0.02, 0.10, 0.50])
    def test_spline_points_length_nans_and_taper(self, h: float, density: float):
        """Verify hair curve splines have point count >= 2, positive length, 0 NaNs/Infs, and proper taper."""
        splines_by_layer = generate_hime_cut_splines(height=h, sample_density_scale=density)
        assert len(splines_by_layer) == 6, f"Expected 6 layers, got {len(splines_by_layer)}"

        for layer_name, splines in splines_by_layer.items():
            assert len(splines) > 0, f"Layer {layer_name} generated 0 splines"
            for s_idx, spline in enumerate(splines):
                # Point count > 0 (at least 2 for segment)
                assert len(spline.points) >= 2, f"{layer_name} spline {s_idx} has < 2 points"
                # Length > 0
                assert spline.length > 0.0, f"{layer_name} spline {s_idx} has non-positive length {spline.length}"

                # 0 NaNs / Infs in coordinates
                for p_idx, pt in enumerate(spline.points):
                    for c_idx, c in enumerate(pt):
                        assert not math.isnan(c) and not math.isinf(c), (
                            f"NaN/Inf in {layer_name} spline {s_idx} pt {p_idx} coord {c_idx}"
                        )

                # 0 NaNs / Infs in radii
                assert len(spline.radii) == len(spline.points), (
                    f"Radii count ({len(spline.radii)}) != points count ({len(spline.points)}) in {layer_name}"
                )
                for r_idx, r in enumerate(spline.radii):
                    assert not math.isnan(r) and not math.isinf(r), f"NaN/Inf radius in {layer_name} spline {s_idx}"
                    assert r > 0.0, f"Radius <= 0 ({r}) in {layer_name} spline {s_idx}"

                # Root-to-tip taper radius bounds
                root_r = spline.radii[0]
                tip_r = spline.radii[-1]
                assert root_r >= tip_r, (
                    f"Root radius ({root_r}) must be >= tip radius ({tip_r}) for {layer_name}"
                )
                assert 0.00008 <= root_r <= 0.00030, f"Root radius {root_r} out of biological bounds"
                assert 0.00001 <= tip_r <= 0.00005, f"Tip radius {tip_r} out of biological bounds"

    def test_ribbon_mesh_vertical_tangent_singularity_documented(self):
        """
        Adversarial Defect Reproduction:
        In convert_curves_to_ribbon_mesh, when a hair spline segment falls purely
        vertically (dx=0, dy=0), the 2D side normal sx = -dy/dlen vanishes, collapsing
        cur_left and cur_right onto the exact same coordinate.
        This produces degenerate zero-area triangular facets in Hair_Hime_Bangs.
        """
        splines_by_layer = generate_hime_cut_splines(height=1.65, sample_density_scale=0.05)
        bangs_splines = splines_by_layer["Hair_Hime_Bangs"]
        ribbon_mesh = convert_curves_to_ribbon_mesh(bangs_splines, ribbon_width=0.002)

        zero_area_faces = []
        for f_idx, (i0, i1, i2) in enumerate(ribbon_mesh.faces):
            area = _triangle_area_3d(ribbon_mesh.vertices[i0], ribbon_mesh.vertices[i1], ribbon_mesh.vertices[i2])
            if area < 1e-10:
                zero_area_faces.append(f_idx)

        # Verify that the vertical tangent fallback along X-axis eliminates all degenerate zero-area faces in bangs
        assert len(zero_area_faces) == 0, (
            f"Expected 0 degenerate zero-area faces in Hair_Hime_Bangs, got {len(zero_area_faces)}"
        )


class TestAnthropometricBoundariesAndClearance:
    """Stress tests boundary configurations and investigates clearance / penetration behavior."""

    @pytest.mark.parametrize("h", [1.20, 1.40, 1.65, 1.80, 2.00, 2.20])
    def test_canonical_height_clearance_maintained(self, h: float):
        """
        Under canonical female proportions scaled across heights (1.2m to 2.2m),
        verify that dress waist sash vertices maintain positive clearance
        offset (> 10mm) relative to the generated body waist vertices at all 24 angular sectors.
        """
        s = h / 1.65
        body_gen = HumanAnatomyGenerator(HumanAnatomyConfig(height=h))
        res = body_gen.generate("Test_Body")
        waist_indices = res.vertex_groups["waist"]
        # Extract waist slice at 1.05 * s
        body_ring = [res.mesh.vertices[i] for i in waist_indices if abs(res.mesh.vertices[i][2] - 1.05 * s) < 1e-4]
        assert len(body_ring) == 24, f"Expected 24 waist vertices in ring, got {len(body_ring)}"

        sash = generate_dress_waist_sash(height=h, clearance=0.015)
        sash_ring = [v for v in sash.vertices if abs(v[2] - 1.05 * s) < 1e-4]
        assert len(sash_ring) == 24, f"Expected 24 sash vertices in center ring, got {len(sash_ring)}"

        # Compare matching angular sectors (both are generated with theta = 2*pi*i/24)
        min_radial_clearance = float("inf")
        for i in range(24):
            bv = body_ring[i]
            sv = sash_ring[i]
            rb = math.sqrt(bv[0]**2 + bv[1]**2)
            rs = math.sqrt(sv[0]**2 + sv[1]**2)
            gap = rs - rb
            if gap < min_radial_clearance:
                min_radial_clearance = gap

        assert min_radial_clearance > 0.0, f"Penetration detected at height {h}m: gap={min_radial_clearance:.4f}m"
        assert min_radial_clearance >= 0.010, (
            f"Clearance at height {h}m is {min_radial_clearance:.4f}m, expected >= 0.010m"
        )

    def test_extreme_waist_girth_penetration_analysis(self):
        """
        Adversarial Boundary Analysis:
        Tests what happens when waist_girth is varied from 0.40m to 1.20m on a 1.65m character.
        Empirically proves that wardrobe generators model Yu Nian An's canonical 0.58m proportions,
        leading to penetration when waist_girth exceeds 0.65m.
        """
        h = 1.65
        s = 1.0
        clearance = 0.015
        sash = generate_dress_waist_sash(height=h, clearance=clearance)
        sash_ring = [v for v in sash.vertices if abs(v[2] - 1.05 * s) < 1e-4]

        results = {}
        for w in [0.40, 0.50, 0.58, 0.65, 0.75, 0.85, 1.00, 1.20]:
            body_gen = HumanAnatomyGenerator(HumanAnatomyConfig(height=h, waist_girth=w))
            res = body_gen.generate("Test_Body")
            waist_indices = res.vertex_groups["waist"]
            body_ring = [res.mesh.vertices[i] for i in waist_indices if abs(res.mesh.vertices[i][2] - 1.05 * s) < 1e-4]

            min_gap = float("inf")
            for i in range(len(body_ring)):
                bv = body_ring[i]
                sv = sash_ring[i]
                rb = math.sqrt(bv[0]**2 + bv[1]**2)
                rs = math.sqrt(sv[0]**2 + sv[1]**2)
                gap = rs - rb
                if gap < min_gap:
                    min_gap = gap

            results[w] = {
                "min_gap_mm": round(min_gap * 1000, 2),
                "penetrates": min_gap < 0.0,
            }

        # Verification of non-penetration under canonical and slender waists
        assert results[0.40]["penetrates"] is False, "0.40m waist must not penetrate"
        assert results[0.58]["penetrates"] is False, "Canonical 0.58m waist must not penetrate"
        assert results[0.58]["min_gap_mm"] == 12.00, "Canonical clearance is exactly +12.00mm"
        assert results[0.65]["penetrates"] is False, "0.65m waist must clear"

        # Empirical proof of penetration for oversized waist girths (un-parameterized wardrobe bug)
        assert results[0.75]["penetrates"] is True, "0.75m waist penetrates by -18.08mm"
        assert results[0.75]["min_gap_mm"] == -18.08
        assert results[1.00]["penetrates"] is True, "1.00m waist penetrates by -69.62mm"
        assert results[1.20]["penetrates"] is True, "1.20m waist penetrates by -111.61mm"
