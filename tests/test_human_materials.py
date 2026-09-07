"""
Unit & Integration Tests for MorphoMesh Digital Human PBR Material Suite.

Validates Milestone 3 Task 1 requirements:
1. Complete PBR shader builder for Blender 4.5+ using Principled BSDF v2 node trees.
2. PBR Skin Shader (Mat_Human_Skin_SSS):
   - Random Walk Subsurface Scattering (subsurface_weight 0.28, radius (1.0, 0.2, 0.1), IOR 1.45, roughness 0.35)
   - Micro-roughness specular bump
   - Porcelain fair tone base color
3. Dual-Chamber Refractive Eye Shader:
   - Outer Cornea (Mat_Human_Eye_Outer_Cornea): Transmission 1.0, Roughness 0.02, IOR 1.376, transparent glass
   - Inner Iris & Pupil (Mat_Human_Eye_Inner_Iris): Dark charcoal/brown iris with radial fiber gradient, limbal ring, pupil dilation driver
   - Sclera (Mat_Human_Eye_Sclera): Subtle red vein tint with SSS (subsurface_weight 0.20, radius (0.8, 0.3, 0.1))
4. Realistic Hair Shader (Mat_Human_Hair):
   - Principled Hair BSDF (melanin 0.85, roughness 0.25, radial roughness 0.45, coat sheen 0.45)
5. Wardrobe Materials:
   - Mat_Dress_WhiteSilk: Off-white (0.95, 0.95, 0.95), sheen 0.6, roughness 0.4
   - Mat_Dress_WaistBelt: Dark sash belt (0.15, 0.15, 0.15), roughness 0.5
   - Mat_Sandal_Leather: Dark leather (0.1, 0.08, 0.07), roughness 0.45
6. Standalone script generation (AST valid) and material slot assignment.
"""

from __future__ import annotations

import ast
import json
import math
from unittest.mock import MagicMock
import pytest

from morphomesh.human_materials import (
    HumanMaterialConfig,
    HumanPBRSuite,
    STANDARD_HUMAN_MATERIALS,
    _build_inner_iris_node_tree,
    get_material_setup_script,
    setup_human_materials,
)
from morphomesh.models import HumanMaterialResult


class TestHumanMaterialConfigs:
    """Validates physical parameters of all digital human PBR materials."""

    def test_required_materials_present(self):
        """Asserts that all required PBR materials are defined."""
        required = [
            "Mat_Human_Skin_SSS",
            "Mat_Human_Eye_Outer_Cornea",
            "Mat_Human_Eye_Inner_Iris",
            "Mat_Human_Eye_Sclera",
            "Mat_Human_Hair",
            "Mat_Dress_WhiteSilk",
            "Mat_Dress_WaistBelt",
            "Mat_Sandal_Leather",
            "Mat_Marionette_RedString",
            "Mat_Magic_Butterfly",
        ]
        for name in required:
            assert name in STANDARD_HUMAN_MATERIALS, f"Missing required material: {name}"

    def test_skin_sss_physical_parameters(self):
        """Validates Mat_Human_Skin_SSS physical parameters matching specification."""
        cfg = STANDARD_HUMAN_MATERIALS["Mat_Human_Skin_SSS"]
        assert cfg.subsurface_weight == 0.28, "Skin SSS weight must be exactly 0.28"
        assert cfg.subsurface_radius == (1.0, 0.2, 0.1), "Skin SSS radius must be (1.0, 0.2, 0.1)"
        assert cfg.subsurface_radius[0] > cfg.subsurface_radius[1] > cfg.subsurface_radius[2]
        assert cfg.ior == 1.45, "Skin IOR must be 1.45"
        assert cfg.roughness == 0.35, "Base skin roughness must be 0.35"
        assert cfg.subsurface_method == "RANDOM_WALK"
        assert cfg.bump_strength > 0.0, "Skin must have micro-roughness specular bump"
        assert cfg.bump_scale >= 300.0, "Skin bump must have fine micro-texture scale"
        assert cfg.metallic == 0.0, "Human skin is non-metallic"

    def test_cornea_refraction_parameters(self):
        """Validates Mat_Human_Eye_Outer_Cornea refractive glass parameters."""
        cfg = STANDARD_HUMAN_MATERIALS["Mat_Human_Eye_Outer_Cornea"]
        assert cfg.transmission_weight == 1.0, "Cornea must have full transmission 1.0"
        assert cfg.roughness <= 0.03, "Cornea must be optical mirror finish <= 0.03"
        assert abs(cfg.ior - 1.376) < 1e-4, "Cornea IOR must match human anatomical cornea IOR 1.376"
        assert cfg.metallic == 0.0

    def test_inner_iris_and_pupil_parameters(self):
        """Validates Mat_Human_Eye_Inner_Iris dark stroma and radial fiber parameters."""
        cfg = STANDARD_HUMAN_MATERIALS["Mat_Human_Eye_Inner_Iris"]
        assert cfg.texture_type == "RADIAL", "Iris requires radial texture type for stroma fibers"
        assert cfg.subsurface_weight == 0.18, "Iris stroma requires subsurface weight 0.18"
        assert 0.20 <= cfg.pupil_dilation <= 0.50, "Pupil dilation must be in anatomical range"
        # Iris base color should be dark charcoal/slate
        assert max(cfg.base_color[:3]) <= 0.25, "Yu Nian An iris must be dark charcoal"

    def test_sclera_parameters(self):
        """Validates Mat_Human_Eye_Sclera moist surface and SSS."""
        cfg = STANDARD_HUMAN_MATERIALS["Mat_Human_Eye_Sclera"]
        assert cfg.roughness <= 0.10, "Moist sclera must have low roughness <= 0.10"
        assert cfg.subsurface_weight == 0.20, "Sclera must have SSS 0.20"
        assert cfg.subsurface_radius == (0.8, 0.3, 0.1)

    def test_hair_shader_parameters(self):
        """Validates Mat_Human_Hair Principled Hair BSDF parameters."""
        cfg = STANDARD_HUMAN_MATERIALS["Mat_Human_Hair"]
        assert cfg.is_hair is True
        assert cfg.melanin == 0.85, "Melanin concentration must be 0.85 for natural black hair"
        assert cfg.roughness == 0.25, "Hair roughness must be 0.25"
        assert cfg.radial_roughness == 0.45, "Radial roughness must be 0.45"
        assert cfg.coat_weight >= 0.40, "Hair must feature angel-ring coat sheen"

    def test_wardrobe_materials_parameters(self):
        """Validates white silk dress, waist belt, and sandal leather parameters."""
        # White silk dress
        dress_cfg = STANDARD_HUMAN_MATERIALS["Mat_Dress_WhiteSilk"]
        assert dress_cfg.base_color[:3] == (0.95, 0.95, 0.95), "Dress must be off-white (0.95, 0.95, 0.95)"
        assert dress_cfg.sheen_weight == 0.60, "Dress must feature sheen weight 0.6"
        assert dress_cfg.roughness == 0.40, "Dress roughness must be 0.4"
        assert dress_cfg.subsurface_weight > 0.0, "Silk dress must feature subtle light translucency"

        # Waist belt
        belt_cfg = STANDARD_HUMAN_MATERIALS["Mat_Dress_WaistBelt"]
        assert belt_cfg.base_color[:3] == (0.15, 0.15, 0.15), "Waist belt must be dark sash (0.15, 0.15, 0.15)"
        assert belt_cfg.roughness == 0.50, "Belt roughness must be 0.5"

        # Sandal leather
        sandal_cfg = STANDARD_HUMAN_MATERIALS["Mat_Sandal_Leather"]
        assert sandal_cfg.base_color[:3] == (0.10, 0.08, 0.07), "Sandal leather must be dark leather (0.1, 0.08, 0.07)"
        assert sandal_cfg.roughness == 0.45, "Sandal leather roughness must be 0.45"


class TestMaterialSetupScript:
    """Validates standalone executable Python script generated for Blender."""

    def test_script_generates_valid_python_ast(self):
        """Verify the material setup script parses cleanly into Python AST without syntax errors."""
        script = get_material_setup_script(
            target_object="Human_Base_Mesh",
            material_preset="yu_nian_an",
            assign_slots=True,
            render_engine="CYCLES",
        )
        assert isinstance(script, str)
        assert len(script) > 500

        # Parse AST to ensure 100% valid Python syntax
        tree = ast.parse(script)
        assert tree is not None
        assert isinstance(tree, ast.Module)

        # Verify json.loads is used and script executes without NameError: name 'false' is not defined
        assert "json.loads" in script, "Script must use json.loads to parse MAT_CONFIGS"
        import sys
        mock_bpy = MagicMock()
        mock_bpy.data.scenes = [MagicMock()]
        mock_bpy.data.scenes[0].render.engine = "CYCLES"
        sys.modules["bpy"] = mock_bpy
        scope = {"bpy": mock_bpy, "math": math, "json": json}
        code_obj = compile(script, "<material_script>", "exec")
        exec(code_obj, scope, scope)

    def test_script_contains_key_shaders_and_slots(self):
        """Verify generated script contains node configurations and slot assignments."""
        script = get_material_setup_script(target_object="Yu_Nian_An_Body")
        assert "Mat_Human_Skin_SSS" in script
        assert "Mat_Human_Eye_Outer_Cornea" in script
        assert "Mat_Human_Eye_Inner_Iris" in script
        assert "Mat_Human_Eye_Sclera" in script
        assert "Mat_Human_Hair" in script
        assert "Mat_Dress_WhiteSilk" in script
        assert "Mat_Dress_WaistBelt" in script
        assert "Mat_Sandal_Leather" in script
        assert "Yu_Nian_An_Body" in script
        assert "ShaderNodeBsdfHairPrincipled" in script
        assert "ShaderNodeBsdfPrincipled" in script
        assert "Is Shadow Ray" in script

    def test_iris_radial_center_offset_in_script_and_helper(self):
        """Verify iris radial mapping centers UV coordinates at (0.5, 0.5) via SUBTRACT vector math node."""
        script = get_material_setup_script(target_object="Yu_Nian_An_Body")
        assert "SUBTRACT" in script, "Iris shader must include SUBTRACT vector math node to center coordinates"
        assert "(0.5, 0.5, 0.0)" in script, "Iris radial stroma center must be (0.5, 0.5)"

        # Direct test for _build_inner_iris_node_tree helper
        mock_nodes = MagicMock()
        mock_links = MagicMock()
        mock_bsdf = MagicMock()
        cfg = {"base_color": (0.141, 0.165, 0.188, 1.0), "pupil_dilation": 0.35}
        _build_inner_iris_node_tree(mock_nodes, mock_links, cfg, mock_bsdf)
        assert mock_nodes.new.called
        assert mock_links.new.called


class TestSetupHumanMaterialsFunction:
    """Validates the setup_human_materials callable function."""

    def test_setup_human_materials_returns_authoritative_result(self):
        """Asserts result dict conforms to HumanMaterialResult model."""
        res = setup_human_materials(
            target_object="Human_Base_Mesh",
            material_preset="yu_nian_an",
            subsurface_scattering=True,
            refractive_eyes=True,
        )
        assert res["status"] == "success"
        assert res["material_preset"] == "yu_nian_an"
        assert res["subsurface_scattering"] is True
        assert res["refractive_eyes"] is True
        assert res["socket_version"] == "Principled BSDF v2"
        assert "Mat_Human_Skin_SSS" in res["materials_created"]
        assert "Mat_Human_Eye_Outer_Cornea" in res["materials_created"]
        assert "Mat_Human_Hair" in res["materials_created"]

        # Validate with Pydantic model
        model = HumanMaterialResult(**res)
        assert model.status == "success"
        assert model.subsurface_scattering is True
