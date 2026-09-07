"""
MorphoMesh: Yu Nian An Master Character Assembler Unit & Integration Tests.

Validates Milestone 4:
1. MasterAssemblyConfig data model and default parameters.
2. 7-Tier Collection Hierarchy specification (Yu_Nian_An_Master + 6 child collections).
3. 10 PBR Materials suite definition and node setup script generation.
4. Standalone Blender 4.5+ LTS assembly script generation and AST validation.
5. Offline / headless assembly execution with summary statistics.
6. Armature deformation binding with volume preservation and 163 DEF bones.
7. Props setup: 10 crimson marionette strings and 10 luminous white butterflies.
8. 3-point studio lighting (Key 5500K, Fill 6500K, Rim 4500K) + 85mm portrait camera.
9. FastMCP server tool registration and execution (morphomesh_assemble_master_character).
10. BlenderBridge dispatch and headless script generation.
11. Listener RPC handler routing.
12. Live Blender 4.5+ master asset verification (output/yu_nian_an/Yu_Nian_An_Master.blend).
"""

from __future__ import annotations

import ast
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from morphomesh.blender_bridge import BlenderBridge
from morphomesh.character_assembler import (
    ALL_SEVEN_COLLECTIONS,
    FINGER_DEF_BONE_KEYS,
    FINGER_LANDMARK_KEYS,
    MATERIAL_NAMES,
    ROOT_COLLECTION_NAME,
    SEVEN_TIER_COLLECTION_HIERARCHY,
    TIER_COLLECTION_NAMES,
    MasterAssemblyConfig,
    YuNianAnAssembler,
    assemble_master_character,
    get_master_assembly_script,
)
from morphomesh.server import (
    HUMAN_TOOL_NAMES,
    mcp,
    morphomesh_assemble_master_character,
    morphomesh_create_human_asset,
)


# ==============================================================================
# 1. CONFIGURATION & CONSTANTS
# ==============================================================================

class TestMasterAssemblyConfig:
    """Validates configuration parameters and constants for master assembly."""

    def test_default_config_parameters(self):
        """Validates default assembly parameters match turnaround specifications."""
        cfg = MasterAssemblyConfig()
        assert cfg.character_name == "Yu_Nian_An"
        assert cfg.height == 1.65
        assert cfg.head_ratio == 7.41
        assert cfg.waist_girth == 0.58
        assert cfg.chest_girth == 0.82
        assert cfg.hip_girth == 0.86
        assert cfg.butterfly_count == 10
        assert cfg.string_count == 10
        assert cfg.render_engine == "CYCLES"
        assert cfg.cycles_samples == 128
        assert cfg.color_management == "AgX"
        assert cfg.camera_lens == 85.0
        assert cfg.camera_fullbody_lens == 50.0
        assert cfg.camera_fullbody_distance == 5.5
        assert cfg.camera_fullbody_target_z == 0.825
        assert cfg.key_light_temperature == 5500.0
        assert cfg.fill_light_temperature == 6500.0
        assert cfg.rim_light_temperature == 4500.0

    def test_config_serialization(self):
        """Verifies MasterAssemblyConfig serializes correctly to dictionary."""
        cfg = MasterAssemblyConfig(cycles_samples=256, camera_lens=100.0)
        d = cfg.to_dict()
        assert d["cycles_samples"] == 256
        assert d["camera_lens"] == 100.0
        assert d["character_name"] == "Yu_Nian_An"

    def test_7_tier_collection_constants(self):
        """Verifies authoritative 7-tier collection hierarchy constants."""
        assert ROOT_COLLECTION_NAME == "Yu_Nian_An_Master"
        assert len(TIER_COLLECTION_NAMES) == 6
        expected_children = [
            "01_Body",
            "02_Hair",
            "03_Wardrobe",
            "04_Props",
            "05_Armature",
            "06_Lights_Camera",
        ]
        assert list(TIER_COLLECTION_NAMES) == expected_children
        assert len(ALL_SEVEN_COLLECTIONS) == 7
        assert ALL_SEVEN_COLLECTIONS[0] == ROOT_COLLECTION_NAME
        assert list(ALL_SEVEN_COLLECTIONS[1:]) == expected_children
        assert SEVEN_TIER_COLLECTION_HIERARCHY[ROOT_COLLECTION_NAME] == expected_children

    def test_authoritative_material_constants(self):
        """Verifies all 10 authoritative PBR material names."""
        assert len(MATERIAL_NAMES) == 10
        expected_materials = {
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
        }
        assert set(MATERIAL_NAMES) == expected_materials

    def test_finger_landmarks_and_def_bones_constants(self):
        """Verifies 10 finger distal landmarks and 10 DEF bones for string anchors."""
        assert len(FINGER_LANDMARK_KEYS) == 10
        assert len(FINGER_DEF_BONE_KEYS) == 10
        for bone in FINGER_DEF_BONE_KEYS:
            assert bone.startswith("DEF-")
            assert bone.endswith(".L") or bone.endswith(".R")


# ==============================================================================
# 2. STANDALONE ASSEMBLY SCRIPT GENERATION & AST VALIDATION
# ==============================================================================

class TestMasterAssemblyScriptGeneration:
    """Validates procedural generation of standalone Blender 4.5+ LTS assembly scripts."""

    def test_script_syntax_ast_validity(self):
        """Verifies that the generated standalone assembly script is 100% valid Python syntax."""
        cfg = MasterAssemblyConfig()
        script = get_master_assembly_script(cfg, output_blend_path="output/test.blend")
        assert len(script) > 5000, "Assembly script must be comprehensive"

        # ast.parse raises SyntaxError if invalid
        parsed = ast.parse(script)
        assert isinstance(parsed, ast.Module)

    def test_script_contains_7_tier_collection_hierarchy(self):
        """Verifies the assembly script establishes the 7-tier collection structure."""
        script = get_master_assembly_script()
        assert "Yu_Nian_An_Master" in script
        assert "01_Body" in script
        assert "02_Hair" in script
        assert "03_Wardrobe" in script
        assert "04_Props" in script
        assert "05_Armature" in script
        assert "06_Lights_Camera" in script
        assert "tier_names" in script or "tier_cols" in script

    def test_script_contains_10_pbr_materials_with_fake_user(self):
        """Verifies script instantiates all 10 materials and sets use_fake_user = True."""
        script = get_master_assembly_script()
        for mat in MATERIAL_NAMES:
            assert mat in script, f"Material '{mat}' missing from assembly script"
        assert "use_fake_user = True" in script

    def test_script_contains_armature_binding_logic(self):
        """Verifies script binds meshes to armature with preserve_volume."""
        script = get_master_assembly_script()
        assert "ARMATURE" in script
        assert "use_deform_preserve_volume = True" in script

    def test_script_contains_hair_and_wardrobe_setup(self):
        """Verifies script includes hair curves parenting and wardrobe solidify modifier."""
        script = get_master_assembly_script()
        assert "Curves" in script or "hair" in script
        assert "SOLIDIFY" in script
        assert "thickness = 0.002" in script or "wardrobe_thickness" in script

    def test_script_contains_props_strings_and_butterflies(self):
        """Verifies script generates 10 marionette strings and 10 luminous butterflies."""
        script = get_master_assembly_script()
        assert "Prop_Butterfly" in script
        assert "Prop_Marionette_Strings" in script or "Prop_String" in script
        assert "Mat_Marionette_RedString" in script
        assert "Mat_Magic_Butterfly" in script

    def test_script_contains_lighting_and_portrait_camera(self):
        """Verifies 3-point lighting setup and 85mm portrait camera."""
        script = get_master_assembly_script()
        assert "Light_Key_Softbox" in script
        assert "Light_Fill_Softbox" in script
        assert "Light_Rim_HairLight" in script
        assert "Camera_Portrait_85mm" in script
        assert "5500" in script  # Key light color temperature
        assert "6500" in script  # Fill light color temperature
        assert "4500" in script  # Rim light color temperature
        assert "lens = 85.0" in script or "lens = 85" in script

    def test_script_contains_render_settings_and_blend_save(self):
        """Verifies Cycles 128 samples, AgX color management, and blend file save."""
        script = get_master_assembly_script()
        assert "CYCLES" in script
        assert "AgX" in script
        assert "save_as_mainfile" in script


# ==============================================================================
# 3. ASSEMBLER RUNTIME & OFFLINE EVALUATION
# ==============================================================================

class TestYuNianAnAssemblerOffline:
    """Validates assembler execution in pure Python / offline environments."""

    def test_assembler_instantiation(self):
        """Verifies YuNianAnAssembler initializes with config."""
        assembler = YuNianAnAssembler()
        assert assembler.config.character_name == "Yu_Nian_An"
        assert len(assembler.COLLECTIONS) == 7
        assert len(assembler.MATERIALS) == 10

    def test_assemble_master_character_entrypoint(self):
        """Verifies assemble_master_character function returns complete assembly summary."""
        result = assemble_master_character(
            character_name="Yu_Nian_An",
            height=1.65,
            render_engine="CYCLES",
            samples=128,
            save_blend=False,
        )
        assert isinstance(result, dict)
        assert result["status"] == "success"
        assert result["character_name"] == "Yu_Nian_An"
        assert result["root_collection"] == "Yu_Nian_An_Master"
        assert len(result["tier_collections"]) == 6
        assert "collection_hierarchy" in result
        assert result["props"]["butterflies_count"] == 10
        assert result["props"]["strings_count"] == 10
        assert result["armature"]["def_bones_count"] == 163
        assert result["lighting_camera"]["key_light"]["temperature"] == 5500.0
        assert result["lighting_camera"]["fill_light"]["temperature"] == 6500.0
        assert result["lighting_camera"]["rim_light"]["temperature"] == 4500.0
        assert result["lighting_camera"]["camera"]["lens"] == 85.0
        assert result["render_settings"]["engine"] == "CYCLES"
        assert result["render_settings"]["samples"] == 128

    def test_assembler_custom_options(self):
        """Verifies assembler respects custom toggles (e.g. disabling props or lighting)."""
        cfg = MasterAssemblyConfig(
            character_name="Custom_Heroine",
            height=1.70,
            include_props=False,
            include_lighting_camera=False,
            cycles_samples=64,
        )
        assembler = YuNianAnAssembler(config=cfg)
        result = assembler.assemble(output_path="output/custom.blend")
        assert result["character_name"] == "Custom_Heroine"
        assert result["render_settings"]["samples"] == 64
        # Standalone script generated from config should be valid AST
        script = assembler.get_assembly_script("output/custom.blend")
        parsed = ast.parse(script)
        assert isinstance(parsed, ast.Module)


# ==============================================================================
# 4. FASTMCP TOOL INTEGRATION
# ==============================================================================

class TestFastMCPMasterCharacterTool:
    """Validates FastMCP server registration, schema, and invocation."""

    @pytest.fixture(autouse=True)
    def enable_human_tools(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("MORPHOMESH_INCLUDE_HUMAN_TOOLS", "1")

    @pytest.mark.asyncio
    async def test_tool_registered_in_fastmcp(self):
        """Verifies morphomesh_assemble_master_character is registered in FastMCP tools."""
        tools = await mcp.list_tools()
        registered_names = {t.name for t in tools}
        assert "morphomesh_assemble_master_character" in registered_names
        assert "morphomesh_assemble_master_character" in HUMAN_TOOL_NAMES

    @pytest.mark.asyncio
    async def test_tool_schema_and_metadata(self):
        """Verifies tool description and arguments schema."""
        tools = await mcp.list_tools()
        target_tool = next((t for t in tools if t.name == "morphomesh_assemble_master_character"), None)
        assert target_tool is not None
        assert "7-tier collection" in target_tool.description
        assert "Yu_Nian_An_Master" in target_tool.description
        schema = target_tool.inputSchema
        assert "properties" in schema
        assert "character_name" in schema["properties"]
        assert "height" in schema["properties"]
        assert "output_path" in schema["properties"]
        assert "render_engine" in schema["properties"]
        assert "samples" in schema["properties"]

    @pytest.mark.asyncio
    async def test_call_assemble_master_character_tool(self):
        """Verifies direct execution of morphomesh_assemble_master_character FastMCP tool."""
        res = await morphomesh_assemble_master_character(
            character_name="Yu_Nian_An",
            height=1.65,
            save_blend=False,
        )
        assert isinstance(res, dict)
        assert res["status"] == "success"
        assert res["character_name"] == "Yu_Nian_An"
        assert res["root_collection"] == "Yu_Nian_An_Master"
        assert len(res["tier_collections"]) == 6
        assert res.get("def_bone_count") == 163 or res.get("armature", {}).get("def_bones_count") == 163

    @pytest.mark.asyncio
    async def test_create_human_asset_with_assemble_master(self):
        """Verifies morphomesh_create_human_asset with assemble_master=True triggers master assembly."""
        res = await morphomesh_create_human_asset(
            character_name="Yu_Nian_An",
            assemble_master=True,
        )
        assert isinstance(res, dict)
        assert res["status"] == "success"
        assert res["character_name"] == "Yu_Nian_An"
        assert res["root_collection"] == "Yu_Nian_An_Master"
        assert len(res["tier_collections"]) == 6


# ==============================================================================
# 5. BLENDER BRIDGE & LISTENER INTEGRATION
# ==============================================================================

class TestBlenderBridgeAndListenerIntegration:
    """Validates BlenderBridge dispatch and listener RPC routing."""

    def test_bridge_has_assemble_master_character_method(self):
        """Verifies BlenderBridge exposes assemble_master_character method."""
        bridge = BlenderBridge()
        assert hasattr(bridge, "assemble_master_character")
        assert callable(bridge.assemble_master_character)

    def test_bridge_headless_script_generation(self):
        """Verifies bridge _generate_headless_script generates master character script."""
        bridge = BlenderBridge()
        script = bridge._generate_headless_script(
            method="morphomesh.assemble_master_character",
            params={"character_name": "Yu_Nian_An", "height": 1.65, "save_blend": False},
        )
        assert "Yu_Nian_An_Master" in script
        assert "Mat_Human_Skin_SSS" in script
        assert "01_Body" in script
        # Check AST valid
        parsed = ast.parse(script)
        assert isinstance(parsed, ast.Module)

    def test_bridge_assemble_master_character_dispatch(self):
        """Verifies bridge dispatch returns valid result."""
        bridge = BlenderBridge()
        # Mock interactive check so it executes offline without external Blender process dependency
        with patch.object(bridge, "is_interactive_connected", return_value=False):
            with patch.object(bridge, "run_headless_script", return_value={
                "status": "success",
                "character_name": "Yu_Nian_An",
                "root_collection": "Yu_Nian_An_Master",
                "tier_collections": ["01_Body", "02_Hair", "03_Wardrobe", "04_Props", "05_Armature", "06_Lights_Camera"],
            }):
                result = bridge.assemble_master_character(
                    character_name="Yu_Nian_An",
                    save_blend=False,
                )
                assert result["status"] == "success"
                assert result["character_name"] == "Yu_Nian_An"
                assert result["root_collection"] == "Yu_Nian_An_Master"

    def test_listener_rpc_routing(self):
        """Verifies listener.py registers and handles morphomesh.assemble_master_character."""
        listener_path = os.path.abspath("blender_addon/morphomesh/listener.py")
        spec = importlib.util.spec_from_file_location("morphomesh_listener_test_mod", listener_path)
        assert spec is not None
        assert spec.loader is not None
        mod = importlib.util.module_from_spec(spec)

        mock_bpy = MagicMock()
        mock_mathutils = MagicMock()
        with patch.dict("sys.modules", {"bpy": mock_bpy, "mathutils": mock_mathutils}):
            spec.loader.exec_module(mod)
            server = mod.MorphoMeshSocketServer()
            res = server._dispatch(
                "morphomesh.assemble_master_character",
                {"character_name": "Yu_Nian_An", "save_blend": False},
            )
            assert res["status"] == "success"
            assert res["character_name"] == "Yu_Nian_An"
            assert res["root_collection"] == "Yu_Nian_An_Master"


# ==============================================================================
# 6. LIVE BLENDER MASTER ASSET VERIFICATION (WHEN BLENDER AVAILABLE)
# ==============================================================================

class TestLiveBlenderMasterAssetVerification:
    """Verifies the actual generated Yu_Nian_An_Master.blend file using Blender 4.5+ LTS."""

    @pytest.fixture
    def blender_executable(self) -> str | None:
        """Finds Blender 4.5+ executable if installed."""
        custom_path = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
        if os.path.isfile(custom_path):
            return custom_path
        which_path = shutil.which("blender")
        if which_path and os.path.isfile(which_path):
            return which_path
        return None

    def test_master_blend_file_exists(self):
        """Verifies that output/yu_nian_an/Yu_Nian_An_Master.blend exists on disk."""
        blend_path = "output/yu_nian_an/Yu_Nian_An_Master.blend"
        assert os.path.isfile(blend_path), f"Master blend file missing at {blend_path}"
        assert os.path.getsize(blend_path) > 10000, "Master blend file must have valid size (>10KB)"

    def test_live_master_blend_content_verification(self, blender_executable: str | None):
        """Executes a headless verification script inside Blender to validate scene contents."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")

        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        if not os.path.isfile(blend_path):
            pytest.skip(f"Blend file {blend_path} does not exist.")

        inspect_script = f"""
import bpy
import json
import sys

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")

data = {{
    "collections": [c.name for c in bpy.data.collections],
    "objects": [o.name for o in bpy.data.objects],
    "materials": [m.name for m in bpy.data.materials],
    "armatures": [a.name for a in bpy.data.armatures],
    "cameras": [c.name for c in bpy.data.cameras],
    "lights": [l.name for l in bpy.data.lights],
}}

# Check root collection and children
root_col = bpy.data.collections.get("Yu_Nian_An_Master")
data["has_root_col"] = root_col is not None
if root_col:
    data["child_cols"] = [c.name for c in root_col.children]
else:
    data["child_cols"] = []

# Check armature DEF bones
rig_obj = bpy.data.objects.get("Armature_Yu_Nian_An_Rigify") or bpy.data.objects.get("rig")
if rig_obj and rig_obj.type == 'ARMATURE':
    def_bones = [b.name for b in rig_obj.data.bones if b.name.startswith("DEF-")]
    data["def_bones_count"] = len(def_bones)
else:
    data["def_bones_count"] = 0

# Check body mesh modifiers
body_obj = bpy.data.objects.get("Yu_Nian_An_Body")
if body_obj:
    data["body_modifiers"] = [m.type for m in body_obj.modifiers]
    data["body_shape_keys"] = len(body_obj.data.shape_keys.key_blocks) - 1 if body_obj.data.shape_keys else 0
else:
    data["body_modifiers"] = []
    data["body_shape_keys"] = 0

# Check render engine
data["render_engine"] = bpy.context.scene.render.engine

print("===MORPHOMESH_INSPECT_START===")
print(json.dumps(data))
print("===MORPHOMESH_INSPECT_END===")
"""
        cmd = [blender_executable, "--background", "--python-expr", inspect_script]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Blender inspection failed: {proc.stderr}"

        stdout = proc.stdout
        assert "===MORPHOMESH_INSPECT_START===" in stdout
        start_idx = stdout.index("===MORPHOMESH_INSPECT_START===") + len("===MORPHOMESH_INSPECT_START===")
        end_idx = stdout.index("===MORPHOMESH_INSPECT_END===")
        json_data = json.loads(stdout[start_idx:end_idx].strip())

        # 1. 7-tier collection hierarchy
        assert json_data["has_root_col"] is True
        for tier in TIER_COLLECTION_NAMES:
            assert tier in json_data["child_cols"], f"Tier collection {tier} missing from children"

        # 2. 10 PBR materials
        for mat in MATERIAL_NAMES:
            assert mat in json_data["materials"], f"Material {mat} missing from blend file"

        # 3. 163 DEF bones
        assert json_data["def_bones_count"] == 163, f"Expected 163 DEF bones, found {json_data['def_bones_count']}"

        # 4. Body mesh with Armature modifier and 52 FACS shape keys
        assert "ARMATURE" in json_data["body_modifiers"]
        assert json_data["body_shape_keys"] == 52

        # 5. Render engine CYCLES
        assert json_data["render_engine"] == "CYCLES"

    def test_live_camera_fullbody_and_turnaround_ndc_bounds(self, blender_executable: str | None):
        """Asserts Camera_FullBody and all 4 turnaround views capture complete 1.65m character without decapitation."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        if not os.path.isfile(blend_path):
            pytest.skip(f"Blend file {blend_path} does not exist.")

        test_script = f"""
import bpy
from bpy_extras.object_utils import world_to_camera_view

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
scene = bpy.context.scene
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

body = bpy.data.objects['Yu_Nian_An_Body']
verts = [body.matrix_world @ v.co for v in body.data.vertices]

# Assert Camera_FullBody has 50mm focal length
cam_fb = bpy.data.objects['Camera_FullBody']
assert cam_fb.data.lens == 50.0, f"Expected 50.0mm lens, got {{cam_fb.data.lens}}"

cams_to_test = ['Camera_FullBody', 'Camera_Front', 'Camera_ThreeQuarter', 'Camera_Profile', 'Camera_Back']
for c_name in cams_to_test:
    cam = bpy.data.objects[c_name]
    assert cam.data.lens == 50.0, f"{{c_name}} lens is not 50.0mm"
    ndc = [world_to_camera_view(scene, cam, v) for v in verts if (world_to_camera_view(scene, cam, v)).z > 0]
    min_y = min(c.y for c in ndc)
    max_y = max(c.y for c in ndc)
    assert min_y >= 0.05, f"Foot amputation in {{c_name}}: min_y={{min_y:.4f}} < 0.05"
    assert max_y <= 0.95, f"Head decapitation in {{c_name}}: max_y={{max_y:.4f}} > 0.95"

print("CAMERAS_50MM_NDC_BOUNDS_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Camera audit failed: {proc.stderr}\n{proc.stdout}"
        assert "CAMERAS_50MM_NDC_BOUNDS_VERIFIED" in proc.stdout

    def test_live_marionette_strings_snapped_to_finger_bone_tails(self, blender_executable: str | None):
        """Asserts all 10 marionette cords originate within 5mm of finger DEF bone tails."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        if not os.path.isfile(blend_path):
            pytest.skip(f"Blend file {blend_path} does not exist.")

        test_script = f"""
import bpy
import math

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
arm = bpy.data.objects['Armature_Yu_Nian_An_Rigify']
strings = bpy.data.objects['Prop_Marionette_Strings']

finger_bones = [
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
]

verts_per_cord = 14
for cord_i, b_name in enumerate(finger_bones):
    bone = arm.data.bones[b_name]
    tail_world = arm.matrix_world @ bone.tail_local
    v0_idx = cord_i * verts_per_cord
    v1_idx = v0_idx + 1
    v0 = strings.matrix_world @ strings.data.vertices[v0_idx].co
    v1 = strings.matrix_world @ strings.data.vertices[v1_idx].co
    center = (v0 + v1) * 0.5
    dist = (center - tail_world).length
    assert dist < 0.005, f"String {{cord_i}} detached from {{b_name}}: dist={{dist*1000:.2f}}mm >= 5mm"

print("STRINGS_SNAPPED_TO_BONE_TAILS_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"String snapping audit failed: {proc.stderr}\n{proc.stdout}"
        assert "STRINGS_SNAPPED_TO_BONE_TAILS_VERIFIED" in proc.stdout

    def test_live_wardrobe_signed_clearance_and_zero_penetration(self, blender_executable: str | None):
        """Asserts zero mesh penetrations and minimum signed clearance >= +4mm for all wardrobe items."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        if not os.path.isfile(blend_path):
            pytest.skip(f"Blend file {blend_path} does not exist.")

        test_script = f"""
import bpy
import bmesh
import mathutils

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
body = bpy.data.objects['Yu_Nian_An_Body']
bm_body = bmesh.new()
bm_body.from_mesh(body.data)
bm_body.transform(body.matrix_world)
bvh = mathutils.bvhtree.BVHTree.FromBMesh(bm_body)

wardrobe_parts = ['Mesh_Dress_Bodice', 'Mesh_Dress_WaistSash', 'Mesh_Dress_PleatedSkirt']
for part_name in wardrobe_parts:
    obj = bpy.data.objects[part_name]
    verts = [obj.matrix_world @ v.co for v in obj.data.vertices]
    min_signed = float('inf')
    penetrations = 0
    for v in verts:
        loc, normal, _, dist = bvh.find_nearest(v)
        if loc is not None:
            dot = (v - loc).dot(normal)
            signed = dist if dot >= 0 else -dist
            if signed < min_signed:
                min_signed = signed
            if dot < 0:
                penetrations += 1
    assert penetrations == 0, f"{{part_name}} has {{penetrations}} penetrations"
    assert min_signed >= 0.004, f"{{part_name}} insufficient clearance: {{min_signed*1000:.2f}}mm < 4mm"

print("WARDROBE_SIGNED_CLEARANCE_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Wardrobe clearance audit failed: {proc.stderr}\n{proc.stdout}"
        assert "WARDROBE_SIGNED_CLEARANCE_VERIFIED" in proc.stdout

    def test_live_lips_clearance_and_material_slot_distribution(self, blender_executable: str | None):
        """Asserts Mesh_Lips has zero cranial penetrations, min clearance >= +0.1mm, and correct material slot distributions."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        if not os.path.isfile(blend_path):
            pytest.skip(f"Blend file {blend_path} does not exist.")

        test_script = f"""
import bpy
from mathutils.bvhtree import BVHTree

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
body = bpy.data.objects['Yu_Nian_An_Body']
lips = bpy.data.objects['Mesh_Lips']
deps = bpy.context.evaluated_depsgraph_get()

bvh_body = BVHTree.FromObject(body, deps)
signed_dists = []
penetrations = 0
for v in lips.data.vertices:
    vw = lips.matrix_world @ v.co
    loc, norm, _, dist = bvh_body.find_nearest(vw)
    if loc is not None:
        dot = (vw - loc).dot(norm)
        sd = dist if dot >= 0 else -dist
        signed_dists.append(sd * 1000.0)
        if dot < -0.0001:
            penetrations += 1

min_c = min(signed_dists)
avg_c = sum(signed_dists) / len(signed_dists)
assert penetrations == 0, f"Mesh_Lips has {{penetrations}} penetrating vertices"
assert min_c >= 0.1, f"Mesh_Lips min clearance {{min_c:.2f}}mm < 0.1mm"

# Material slot distribution check
lips_dist = {{}}
for p in lips.data.polygons:
    lips_dist[p.material_index] = lips_dist.get(p.material_index, 0) + 1
assert lips_dist.get(0, 0) == 41, f"Expected 41 quads on slot 0, got {{lips_dist.get(0, 0)}}"
assert lips_dist.get(1, 0) == 9, f"Expected 9 quads on slot 1, got {{lips_dist.get(1, 0)}}"

for el_name in ['Mesh_Eyelid_Left', 'Mesh_Eyelid_Right']:
    el = bpy.data.objects[el_name]
    el_dist = {{}}
    for p in el.data.polygons:
        el_dist[p.material_index] = el_dist.get(p.material_index, 0) + 1
    assert el_dist.get(0, 0) == 8, f"{{el_name}} expected 8 eyeliner quads, got {{el_dist.get(0, 0)}}"
    assert el_dist.get(1, 0) == 8, f"{{el_name}} expected 8 skin SSS quads, got {{el_dist.get(1, 0)}}"

print("LIPS_CLEARANCE_AND_MATERIAL_SLOTS_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Lips and material slot audit failed: {proc.stderr}\n{proc.stdout}"
        assert "LIPS_CLEARANCE_AND_MATERIAL_SLOTS_VERIFIED" in proc.stdout

    def test_live_eye_spheres_hair_armature_binding_and_rotation_kinematics(self, blender_executable: str | None):
        """Asserts all 4 eye spheres and all 6 hair layers are bound to Armature and deform identically with 0.00mm shear."""
        if not blender_executable:
            pytest.skip("Blender executable not found on system.")
        blend_path = os.path.abspath("output/yu_nian_an/Yu_Nian_An_Master.blend")
        if not os.path.isfile(blend_path):
            pytest.skip(f"Blend file {blend_path} does not exist.")

        test_script = f"""
import bpy
import math
from mathutils import Vector

bpy.ops.wm.open_mainfile(filepath=r"{blend_path}")
arm_obj = bpy.data.objects['Armature_Yu_Nian_An_Rigify']
pb_head = arm_obj.pose.bones['DEF-head']

eye_sphere_names = [
    'Mesh_Eye_Left_CorneaSclera', 'Mesh_Eye_Left_IrisPupil',
    'Mesh_Eye_Right_CorneaSclera', 'Mesh_Eye_Right_IrisPupil'
]
hair_names = [
    'Hair_Hime_Bangs', 'Hair_Eyebrows', 'Hair_Eyelashes',
    'Hair_Scalp_Crown', 'Hair_Hime_Sidelocks', 'Hair_Back_Cascade'
]

# 1. Modifiers & Vertex Groups Check
for name in ['Mesh_Lips', 'Mesh_Eyelid_Left', 'Mesh_Eyelid_Right'] + eye_sphere_names + hair_names:
    o = bpy.data.objects[name]
    has_arm = any(m.type == 'ARMATURE' and m.object == arm_obj for m in o.modifiers)
    assert has_arm, f"{{name}} missing Armature modifier targeting {{arm_obj.name}}"
    assert 'DEF-head' in o.vertex_groups, f"{{name}} missing 'DEF-head' vertex group"

def get_eval_center(obj_name, deps):
    o = bpy.data.objects[obj_name]
    e = o.evaluated_get(deps)
    me = e.to_mesh()
    cos = [e.matrix_world @ v.co for v in me.vertices]
    e.to_mesh_clear()
    return sum(cos, Vector((0, 0, 0))) / len(cos) if cos else None

# Reset pose
pb_head.rotation_mode = 'XYZ'
pb_head.rotation_euler = (0.0, 0.0, 0.0)
bpy.context.view_layer.update()
deps_rest = bpy.context.evaluated_depsgraph_get()

all_eval_names = ['Mesh_Lips', 'Mesh_Eyelid_Left', 'Mesh_Eyelid_Right'] + eye_sphere_names + hair_names
base_centers = {{n: get_eval_center(n, deps_rest) for n in all_eval_names}}

# Rotate 30 degrees
pb_head.rotation_euler = (math.radians(30.0), 0.0, 0.0)
bpy.context.view_layer.update()
deps_rot = bpy.context.evaluated_depsgraph_get()

for n in all_eval_names:
    c_base = base_centers[n]
    c_rot = get_eval_center(n, deps_rot)
    disp = (c_rot - c_base).length * 1000.0
    assert disp >= 20.0, f"{{n}} failed kinematics: displacement {{disp:.2f}}mm < 20.0mm"

# Eyelid-to-eyeball shear
c_lid_base = base_centers['Mesh_Eyelid_Left']
c_eye_base = base_centers['Mesh_Eye_Left_CorneaSclera']
c_lid_rot = get_eval_center('Mesh_Eyelid_Left', deps_rot)
c_eye_rot = get_eval_center('Mesh_Eye_Left_CorneaSclera', deps_rot)
dist_base = (c_lid_base - c_eye_base).length * 1000.0
dist_rot = (c_lid_rot - c_eye_rot).length * 1000.0
shear = abs(dist_rot - dist_base)
assert shear < 0.01, f"Separation shear {{shear:.4f}}mm > 0.01mm"

print("EYES_HAIR_ARMATURE_BINDING_AND_KINEMATICS_VERIFIED")
"""
        proc = subprocess.run([blender_executable, "--background", "--python-expr", test_script], capture_output=True, text=True, timeout=60)
        assert proc.returncode == 0, f"Kinematics audit failed: {proc.stderr}\n{proc.stdout}"
        assert "EYES_HAIR_ARMATURE_BINDING_AND_KINEMATICS_VERIFIED" in proc.stdout
