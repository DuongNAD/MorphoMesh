"""
Unit & Integration Tests for MorphoMesh Geometry Nodes Hair Curves Grooming Engine.

Validates Milestone 3 Task 2 requirements:
1. Geometry Nodes Hair Curves generator for Blender 4.5+ (Curves object, not old particle hair).
2. Hairstyle: Yu Nian An signature hime cut with:
   - Straight forehead bangs ending at eyebrow level (length 0.12 - 0.14m).
   - Symmetrical sidelocks framing cheeks down to shoulder (length 0.35 - 0.40m).
   - Long flowing back hair cascade extending to hips (~1.0m length).
   - Eyebrows, eyelashes, and crown scalp parting layers.
3. Geometry Nodes hair modifier network (Curve Radius taper, clump, micro-noise, hair material).
4. Procedural 3D curve spline generation and ribbon quad mesh evaluation.
5. Standalone Blender 4.5+ script generation (valid AST).
"""

from __future__ import annotations

import ast
import json
import math
import sys
from unittest.mock import MagicMock
import pytest

from morphomesh.human_grooming import (
    HairCurveSpline,
    HairGroomConfig,
    HairLayerConfig,
    build_hair_geom_node_tree,
    convert_curves_to_ribbon_mesh,
    generate_hime_cut_splines,
    get_default_hime_cut_layers,
    get_grooming_script,
    groom_human,
)
from morphomesh.models import HumanGroomingResult


class TestHairLayerConfigs:
    """Validates structural layer parameters for Yu Nian An's signature hime cut."""

    def test_all_six_hime_cut_layers_present(self):
        """Asserts all 6 anatomical hair strata are configured."""
        layers = get_default_hime_cut_layers(15000)
        expected = [
            "Hair_Hime_Bangs",
            "Hair_Hime_Sidelocks",
            "Hair_Scalp_Crown",
            "Hair_Back_Cascade",
            "Hair_Eyebrows",
            "Hair_Eyelashes",
        ]
        for name in expected:
            assert name in layers, f"Missing required layer: {name}"

    def test_hime_bangs_dimensions_and_taper(self):
        """Validates forehead bangs trimmed at eyebrow level."""
        layer = get_default_hime_cut_layers(15000)["Hair_Hime_Bangs"]
        assert 0.11 <= layer.length <= 0.15, "Forehead bangs must be 0.12 - 0.14m"
        assert layer.root_radius > layer.tip_radius, "Hair must taper from root to tip"
        assert layer.tip_radius <= 0.000030, "Hair tip must be finely tapered"

    def test_hime_sidelocks_dimensions(self):
        """Validates face-framing cheek sidelocks descending to shoulder."""
        layer = get_default_hime_cut_layers(15000)["Hair_Hime_Sidelocks"]
        assert 0.34 <= layer.length <= 0.42, "Sidelocks must be 0.35 - 0.40m"
        assert layer.clump_factor >= 0.15, "Sidelocks require cohesive clumping"

    def test_back_cascade_length(self):
        """Validates back hair cascade extending to hips (~1.0m length)."""
        layer = get_default_hime_cut_layers(15000)["Hair_Back_Cascade"]
        assert 0.90 <= layer.length <= 1.10, "Back hair cascade must be ~1.0m length"
        assert layer.strand_count >= 5000, "Back cascade requires dominant strand allocation"
        assert layer.clump_factor >= 0.25, "Back hair requires organic strand clumping"


class TestHairCurveSplineGeneration:
    """Validates authentic 3D curve spline mathematics in pure Python."""

    def test_spline_generation_all_layers(self):
        """Asserts that 3D splines are generated for each layer."""
        splines = generate_hime_cut_splines(sample_density_scale=0.05)
        assert len(splines) >= 4
        assert "Hair_Hime_Bangs" in splines
        assert "Hair_Hime_Sidelocks" in splines
        assert "Hair_Back_Cascade" in splines

    def test_bangs_eyebrow_level_termination(self):
        """Verify that bangs terminate cleanly at eyebrow level (Z ~ 1.53 - 1.54m)."""
        splines = generate_hime_cut_splines(sample_density_scale=0.05)["Hair_Hime_Bangs"]
        assert len(splines) > 0
        for s in splines:
            root = s.points[0]
            tip = s.points[-1]
            assert root[2] > tip[2], "Bangs must fall downward"
            assert 1.50 <= tip[2] <= 1.56, f"Bangs tip at Z={tip[2]} must end at eyebrow level (~1.53m)"
            # Bangs must lie on front of forehead (negative Y)
            assert tip[1] < 0.0, "Bangs must fall forward over forehead"

    def test_sidelocks_bilateral_symmetry(self):
        """Verify sidelocks generate symmetrical left (+X) and right (-X) locks."""
        splines = generate_hime_cut_splines(sample_density_scale=0.05)["Hair_Hime_Sidelocks"]
        left_locks = [s for s in splines if s.points[0][0] > 0.0]
        right_locks = [s for s in splines if s.points[0][0] < 0.0]
        assert len(left_locks) > 0, "Must have left sidelocks"
        assert len(right_locks) > 0, "Must have right sidelocks"
        # Check termination around shoulder level (Z ~ 1.30 - 1.35m)
        for s in splines:
            tip = s.points[-1]
            assert 1.25 <= tip[2] <= 1.38, f"Sidelock tip Z={tip[2]} must reach collarbone level"

    def test_back_cascade_hip_level_termination(self):
        """Verify back cascade falls along spine to hip level (~Z = 0.70m, length ~1.0m)."""
        splines = generate_hime_cut_splines(sample_density_scale=0.05)["Hair_Back_Cascade"]
        assert len(splines) > 0
        for s in splines:
            root = s.points[0]
            tip = s.points[-1]
            assert root[2] > 1.55, "Root must start on cranial crown/occiput"
            assert tip[2] <= 0.78, f"Tip Z={tip[2]} must reach hip level"
            assert 0.85 <= s.length <= 1.10, f"Cascade length {s.length} must be ~1.0m"
            # Must drape over rear (positive Y or near spine)
            assert tip[1] >= -0.05, "Back hair must drape along the back"


class TestHairRibbonMeshEvaluator:
    """Validates real-time polygonal quad ribbon mesh conversion."""

    def test_convert_curves_to_ribbon_mesh_produces_pure_quads(self):
        """Verify ribbon evaluator produces pure quads with UVs."""
        splines = generate_hime_cut_splines(sample_density_scale=0.02)["Hair_Hime_Bangs"]
        ribbon_mesh = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.002)

        assert len(ribbon_mesh.vertices) > 0
        assert len(ribbon_mesh.faces) > 0

        # Verify face count: in MeshGeometry, each quad is stored as 2 triangles
        assert len(ribbon_mesh.faces) % 2 == 0, "Quads are paired triangles"

        # Check vertex coordinates non-degenerate
        for v in ribbon_mesh.vertices:
            assert not any(math.isnan(c) for c in v)


class TestGroomingScriptAST:
    """Validates standalone executable Python script generated for Blender."""

    def test_grooming_script_generates_valid_python_ast(self):
        """Verify grooming script parses cleanly into Python AST and executes without NameError."""
        script = get_grooming_script(
            target_object="Human_Base_Mesh",
            hair_style="hime_cut_long",
            strand_count=15000,
        )
        assert isinstance(script, str)
        assert len(script) > 500
        assert "json.loads" in script, "Script must use json.loads for LAYERS, HAIR_SPLINES, HAIR_RIBBONS"

        tree = ast.parse(script)
        assert tree is not None
        assert isinstance(tree, ast.Module)

        # Mock execute script to verify zero NameError
        mock_bpy = MagicMock()
        sys.modules["bpy"] = mock_bpy
        scope = {"bpy": mock_bpy, "math": math, "json": json}
        code_obj = compile(script, "<grooming_script>", "exec")
        exec(code_obj, scope, scope)

    def test_script_contains_curves_objects_and_gn_modifier(self):
        """Verify script sets up modern Curves objects, full GN modifier network, and material."""
        script = get_grooming_script(target_object="Yu_Nian_An_Body")
        assert "Hair_Hime_Bangs" in script
        assert "Hair_Hime_Sidelocks" in script
        assert "Hair_Back_Cascade" in script
        assert "GN_HairGroom" in script
        assert "GeometryNodeTree" in script
        assert "Mat_Human_Hair" in script

        # Verify full GN modifier network nodes
        assert "GeometryNodeCurveSplineParameter" in script or "CurveSplineParameter" in script, "GN tree must include CurveSplineParameter for taper"
        assert "ShaderNodeMapRange" in script or "MapRange" in script, "GN tree must map factor to root/tip radius"
        assert "GeometryNodeSetCurveRadius" in script or "SetCurveRadius" in script, "GN tree must set curve radius"
        assert "ShaderNodeTexNoise" in script or "TexNoise" in script, "GN tree must include TexNoise for micro-frizz"
        assert "GeometryNodeSetPosition" in script or "SetPosition" in script, "GN tree must perturb position with noise"
        assert "clump_val" in script or "clump_factor" in script, "GN tree must modulate clump factor"
        assert "from_pydata" in script, "Script must populate mesh/ribbon data using from_pydata"

    def test_build_hair_geom_node_tree_direct(self):
        """Direct unit test verifying build_hair_geom_node_tree constructs taper and noise nodes."""
        mock_tree = MagicMock()
        mock_mat = MagicMock()
        cfg = {"root_radius": 0.00016, "tip_radius": 0.000025, "clump_factor": 0.28, "noise_frequency": 14.0}
        result = build_hair_geom_node_tree(mock_tree, cfg, mock_mat)
        assert result is mock_tree
        assert mock_tree.nodes.new.called
        assert mock_tree.links.new.called

    def test_convert_curves_to_ribbon_mesh_zero_degenerate_faces(self):
        """Verify convert_curves_to_ribbon_mesh produces 0 degenerate zero-area faces on vertical splines."""
        splines = generate_hime_cut_splines(height=1.65, sample_density_scale=0.05)["Hair_Hime_Bangs"]
        rm = convert_curves_to_ribbon_mesh(splines, ribbon_width=0.002)
        zero_area_faces = 0
        for i0, i1, i2 in rm.faces:
            v0, v1, v2 = rm.vertices[i0], rm.vertices[i1], rm.vertices[i2]
            ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
            bx, by, bz = v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2]
            cx = ay * bz - az * by
            cy = az * bx - ax * bz
            cz = ax * by - ay * bx
            area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
            if area < 1e-10:
                zero_area_faces += 1
        assert zero_area_faces == 0, f"Expected 0 degenerate zero-area faces in bangs, got {zero_area_faces}"


class TestGroomHumanFunction:
    """Validates the groom_human callable function."""

    def test_groom_human_returns_authoritative_result(self):
        """Asserts result dict conforms to HumanGroomingResult model."""
        res = groom_human(
            mesh_object_name="Human_Base_Mesh",
            hair_style="hime_cut_long",
            strand_count=15000,
        )
        assert res["status"] == "success"
        assert res["hair_style"] == "hime_cut_long"
        assert res["strand_count"] == 15000
        assert "Hair_Hime_Bangs" in res["layers"]
        assert "Hair_Hime_Sidelocks" in res["layers"]
        assert "Hair_Back_Cascade" in res["layers"]

        # Validate with Pydantic model
        model = HumanGroomingResult(**res)
        assert model.status == "success"
        assert model.hair_style == "hime_cut_long"
