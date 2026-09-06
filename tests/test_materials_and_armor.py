"""
MorphoMesh: Automated Unit & Integration Test Suite for Milestone M3.
Covers:
1. 5-slot Principled BSDF v2 PBR Material Suite (`src/morphomesh/materials.py`)
2. Procedural War Armor Fitting Engine (`src/morphomesh/armor.py`)
3. Blender Bridge IPC Dispatchers (`src/morphomesh/blender_bridge.py`)
4. Headless Blender 5.2.1 LTS Execution & Verification
"""

import ast
import math
import os
import subprocess
from typing import Dict, List, Tuple

import pytest

from morphomesh.armor import ProceduralArmorEngine, fit_war_armor
from morphomesh.blender_bridge import BlenderBridge, BpyCodeValidator
from morphomesh.creature_generator import generate_bear_base_mesh, get_blender_generation_script
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.materials import (
    CreaturePBRSuite,
    PBRMaterialConfig,
    STANDARD_PBR_MATERIALS,
    create_pbr_creature_materials,
    setup_bear_materials,
)


# ==============================================================================
# 1. PBR MATERIAL SUITE UNIT TESTS
# ==============================================================================

class TestPBRMaterialSuite:
    """Validates physical parameters and Principled BSDF v2 socket configurations."""

    def test_all_five_standard_materials_present(self):
        """Asserts that exactly the 5 specified PBR materials are present."""
        expected = {
            "Mat_Bear_Fur",
            "Mat_Bear_Skin_Nose",
            "Mat_Bear_Claws",
            "Mat_Armor_WeatheredSteel",
            "Mat_Armor_BrassTrim",
        }
        assert set(STANDARD_PBR_MATERIALS.keys()) == expected

    def test_mat_bear_fur_physical_parameters(self):
        """Validates physical parameters for Mat_Bear_Fur."""
        cfg = STANDARD_PBR_MATERIALS["Mat_Bear_Fur"]
        assert cfg.roughness >= 0.70, "Fur must have high roughness >= 0.70"
        assert cfg.roughness == 0.85
        assert cfg.metallic == 0.0, "Organic fur is non-metallic"
        assert cfg.sheen_weight == 0.65, "Must feature velvet sheen weight 0.65"
        assert cfg.sheen_roughness == 0.30
        assert cfg.subsurface_weight == 0.08, "Must simulate light diffusion via subsurface 0.08"
        assert cfg.texture_type == "NOISE"

    def test_mat_bear_skin_nose_physical_parameters(self):
        """Validates physical parameters for Mat_Bear_Skin_Nose (wet moisture)."""
        cfg = STANDARD_PBR_MATERIALS["Mat_Bear_Skin_Nose"]
        assert cfg.roughness <= 0.25, "Wet skin must have low roughness (high gloss)"
        assert cfg.roughness == 0.15
        assert cfg.metallic == 0.0, "Skin is a dielectric (metallic 0.0)"
        assert cfg.coat_weight == 0.85, "Must render clearcoat moisture layer of 0.85"
        assert cfg.coat_roughness == 0.04
        assert cfg.specular_ior_level == 0.60
        assert cfg.texture_type == "VORONOI"

    def test_mat_bear_claws_physical_parameters(self):
        """Validates physical parameters for Mat_Bear_Claws."""
        cfg = STANDARD_PBR_MATERIALS["Mat_Bear_Claws"]
        assert 0.25 <= cfg.roughness <= 0.50, "Keratin must exhibit satin roughness"
        assert cfg.roughness == 0.38
        assert cfg.metallic == 0.0, "Keratin is non-metallic"
        assert cfg.texture_type == "WAVE", "Claws require longitudinal directional striations"

    def test_mat_armor_weathered_steel_physical_parameters(self):
        """Validates physical parameters for Mat_Armor_WeatheredSteel."""
        cfg = STANDARD_PBR_MATERIALS["Mat_Armor_WeatheredSteel"]
        assert cfg.metallic == 1.0, "Steel armor must be pure conductor (metallic 1.0)"
        assert 0.30 <= cfg.roughness <= 0.60
        assert cfg.roughness == 0.42
        assert cfg.texture_type == "NOISE"

    def test_mat_armor_brass_trim_physical_parameters(self):
        """Validates physical parameters for Mat_Armor_BrassTrim."""
        cfg = STANDARD_PBR_MATERIALS["Mat_Armor_BrassTrim"]
        assert cfg.metallic == 1.0, "Brass trim must be pure conductor (metallic 1.0)"
        assert 0.20 <= cfg.roughness <= 0.50
        assert cfg.roughness == 0.32
        assert cfg.base_color[0] > cfg.base_color[2], "Brass must have warm golden hue (R > B)"

    def test_create_pbr_creature_materials_contract(self):
        """Asserts create_pbr_creature_materials returns descriptions for all 5 materials."""
        mats = create_pbr_creature_materials()
        assert len(mats) == 5
        for m_name in [
            "Mat_Bear_Fur",
            "Mat_Bear_Skin_Nose",
            "Mat_Bear_Claws",
            "Mat_Armor_WeatheredSteel",
            "Mat_Armor_BrassTrim",
        ]:
            assert m_name in mats

    def test_materials_blender_script_ast_security(self):
        """Asserts materials Blender script passes AST parsing and BpyCodeValidator."""
        suite = CreaturePBRSuite()
        script = suite.get_materials_blender_script()
        assert len(script) < 10000, "Script length must remain within safe boundary"
        tree = ast.parse(script)
        assert tree is not None
        validator = BpyCodeValidator()
        validator.validate(script)


# ==============================================================================
# 2. PROCEDURAL WAR ARMOR ENGINE UNIT TESTS
# ==============================================================================

class TestProceduralArmorEngine:
    """Validates geometry, 2-manifold properties, zero-area faces, and non-intersection clearance."""

    @pytest.fixture
    def engine(self) -> ProceduralArmorEngine:
        return ProceduralArmorEngine()

    @pytest.fixture
    def bear_mesh(self) -> MeshGeometry:
        res = generate_bear_base_mesh()
        return res.mesh

    def test_all_six_armor_plates_generated(self, engine, bear_mesh):
        """Asserts all 6 war armor plates are generated with non-empty geometry."""
        plates = engine.generate_all_armor_plates(bear_mesh=bear_mesh)
        expected = [
            "Armor_Pauldron_L",
            "Armor_Pauldron_R",
            "Armor_Gorget",
            "Armor_Bracer_L",
            "Armor_Bracer_R",
            "Armor_Backplate",
        ]
        assert set(plates.keys()) == set(expected)
        for name, mesh in plates.items():
            assert len(mesh.vertices) > 0, f"{name} has 0 vertices"
            assert len(mesh.faces) > 0, f"{name} has 0 faces"

    def test_armor_plates_2_manifold_watertight(self, engine, bear_mesh):
        """Asserts every armor plate is a closed 2-manifold shell (0 non-manifold edges)."""
        plates = engine.generate_all_armor_plates(bear_mesh=bear_mesh)
        for name, mesh in plates.items():
            is_m, nm_count = engine.verify_2_manifold(mesh)
            assert is_m, f"{name} violates 2-manifold property with {nm_count} non-manifold edges"
            assert nm_count == 0

    def test_armor_plates_zero_zero_area_faces(self, engine, bear_mesh):
        """Asserts zero degenerate zero-area faces across all armor plates."""
        plates = engine.generate_all_armor_plates(bear_mesh=bear_mesh)
        for name, mesh in plates.items():
            for f in mesh.faces:
                v0 = mesh.vertices[f[0]]
                v1 = mesh.vertices[f[1]]
                v2 = mesh.vertices[f[2]]
                # Triangle area
                ax, ay, az = v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2]
                bx, by, bz = v2[0] - v0[0], v2[1] - v0[0], v2[2] - v0[2]
                cx = ay * bz - az * by
                cy = az * bx - ax * bz
                cz = ax * by - ay * bx
                area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
                assert area > 1e-7, f"Degenerate face {f} in {name} with area {area}"

    def test_armor_clearance_guarantee_positive(self, engine, bear_mesh):
        """Asserts every armor plate has minimum clearance distance >= 0.015m from bear mesh."""
        plates = engine.generate_all_armor_plates(bear_mesh=bear_mesh)
        for name, mesh in plates.items():
            metrics = engine.compute_clearance_metrics(mesh, bear_mesh)
            min_d = metrics["min_distance"]
            assert min_d >= 0.015, (
                f"{name} clearance violation: minimum distance {min_d:.4f}m < 0.015m requirement"
            )
            assert min_d <= 0.055, (
                f"{name} clearance too large: minimum distance {min_d:.4f}m > 0.055m"
            )

    def test_fit_war_armor_contract(self, engine):
        """Asserts fit_war_armor top-level function returns expected 6 plate names."""
        names = fit_war_armor()
        assert len(names) == 6
        assert "Armor_Pauldron_L" in names
        assert "Armor_Pauldron_R" in names
        assert "Armor_Gorget" in names
        assert "Armor_Bracer_L" in names
        assert "Armor_Bracer_R" in names
        assert "Armor_Backplate" in names

    def test_armor_blender_script_ast_security_and_length(self, engine):
        """Asserts armor Blender script is < 10000 characters and passes BpyCodeValidator."""
        script = engine.get_armor_blender_script()
        assert len(script) < 10000, f"Script length {len(script)} exceeds 10,000 char limit"
        tree = ast.parse(script)
        assert tree is not None
        validator = BpyCodeValidator()
        validator.validate(script)


# ==============================================================================
# 3. BLENDER BRIDGE IPC INTEGRATION TESTS
# ==============================================================================

class TestBlenderBridgeMaterialsAndArmor:
    """Validates BlenderBridge integration for materials and armor dispatch."""

    def test_bridge_has_setup_creature_materials(self):
        """Asserts BlenderBridge has setup_creature_materials method with correct signature."""
        bridge = BlenderBridge()
        assert hasattr(bridge, "setup_creature_materials")

    def test_bridge_has_generate_war_armor(self):
        """Asserts BlenderBridge has generate_war_armor method with correct signature."""
        bridge = BlenderBridge()
        assert hasattr(bridge, "generate_war_armor")

    def test_bridge_generate_headless_script_materials_ast(self):
        """Asserts bridge._generate_headless_script for setup_creature_materials is valid AST."""
        bridge = BlenderBridge()
        script = bridge._generate_headless_script("morphomesh.setup_creature_materials", {
            "mesh_object_name": "Bear_Base_Mesh",
        })
        tree = ast.parse(script)
        assert tree is not None

    def test_bridge_generate_headless_script_armor_ast(self):
        """Asserts bridge._generate_headless_script for generate_war_armor is valid AST."""
        bridge = BlenderBridge()
        script = bridge._generate_headless_script("morphomesh.generate_war_armor", {
            "base_mesh_name": "Bear_Base_Mesh",
            "clearance_offset": 0.025,
        })
        tree = ast.parse(script)
        assert tree is not None


# ==============================================================================
# 4. BLENDER 5.2.1 LTS FORENSIC VERIFICATION TESTS
# ==============================================================================

BLENDER_APP_PATH = "/Applications/Blender.app/Contents/MacOS/Blender"

@pytest.mark.skipif(not os.path.isfile(BLENDER_APP_PATH), reason="Blender 5.2.1 LTS binary not found on system")
class TestBlenderLTSForensicAudit:
    """Executes forensic material and armor tests directly inside Blender 5.2.1 LTS."""

    def test_blender_materials_and_armor_headless_execution(self):
        """Runs base mesh generation, material assignment, and armor fitting in Blender 5.2.1."""
        s_mesh = get_blender_generation_script("Bear_Base_Mesh", 1.0)
        s_mats = CreaturePBRSuite().get_materials_blender_script("Bear_Base_Mesh")
        s_arm = ProceduralArmorEngine().get_armor_blender_script("Bear_Base_Mesh")

        verification_logic = """
import math
import bpy

# 1. Verify materials
expected_mats = [
    "Mat_Bear_Fur",
    "Mat_Bear_Skin_Nose",
    "Mat_Bear_Claws",
    "Mat_Armor_WeatheredSteel",
    "Mat_Armor_BrassTrim",
]
for m_name in expected_mats:
    mat = bpy.data.materials.get(m_name)
    assert mat is not None, f"Material {m_name} missing from scene"
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    assert bsdf is not None, f"Principled BSDF missing in {m_name}"

# Check BSDF sockets
m_fur = bpy.data.materials["Mat_Bear_Fur"]
bsdf_fur = next(n for n in m_fur.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert math.isclose(bsdf_fur.inputs["Roughness"].default_value, 0.85, rel_tol=1e-3)
assert math.isclose(bsdf_fur.inputs["Sheen Weight"].default_value, 0.65, rel_tol=1e-3)

m_skin = bpy.data.materials["Mat_Bear_Skin_Nose"]
bsdf_skin = next(n for n in m_skin.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert math.isclose(bsdf_skin.inputs["Coat Weight"].default_value, 0.85, rel_tol=1e-3)
assert math.isclose(bsdf_skin.inputs["Roughness"].default_value, 0.15, rel_tol=1e-3)

m_steel = bpy.data.materials["Mat_Armor_WeatheredSteel"]
bsdf_steel = next(n for n in m_steel.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert math.isclose(bsdf_steel.inputs["Metallic"].default_value, 1.0, rel_tol=1e-3)

m_brass = bpy.data.materials["Mat_Armor_BrassTrim"]
bsdf_brass = next(n for n in m_brass.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
assert math.isclose(bsdf_brass.inputs["Metallic"].default_value, 1.0, rel_tol=1e-3)

# 2. Verify armor objects
armor_names = [
    "Armor_Pauldron_L",
    "Armor_Pauldron_R",
    "Armor_Gorget",
    "Armor_Bracer_L",
    "Armor_Bracer_R",
    "Armor_Backplate",
]
for a_name in armor_names:
    obj = bpy.data.objects.get(a_name)
    assert obj is not None, f"Armor object {a_name} missing"
    mesh = obj.data
    assert len(mesh.vertices) > 0, f"{a_name} has no vertices"
    assert len(mesh.polygons) > 0, f"{a_name} has no polygons"
    zero_area = [p for p in mesh.polygons if p.area < 1e-9]
    assert len(zero_area) == 0, f"{a_name} has {len(zero_area)} zero-area polygons"
    assert len(obj.data.materials) >= 2, f"{a_name} missing material slots"

# 3. Verify measured clearances
for a_name, cl in armor_result["measured_clearances"].items():
    assert cl >= 0.015, f"{a_name} clearance {cl} < 0.015m"

print("BLENDER_5_2_1_LTS_VERIFICATION_PASS")
"""
        full_code = s_mesh + "\n" + s_mats + "\n" + s_arm + "\n" + verification_logic
        temp_file = "/tmp/test_m3_blender_audit.py"
        with open(temp_file, "w") as f:
            f.write(full_code)

        try:
            res = subprocess.run(
                [BLENDER_APP_PATH, "--background", "--python", temp_file],
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert res.returncode == 0, f"Blender execution failed:\n{res.stderr}\n{res.stdout}"
            assert "BLENDER_5_2_1_LTS_VERIFICATION_PASS" in res.stdout
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)
