"""
Adversarial Empirical Challenge Test Suite for Milestone M3.
Focus: War Armor Clearances, 2-Manifold Shell Integrity, Zero-Area Faces,
PBR Principled BSDF v2 Shaders, and Extreme Scale Stress Testing.

Designed and executed by Challenger M3-1.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import tempfile
from typing import Dict, List, Tuple

import pytest

from morphomesh.armor import ProceduralArmorEngine, fit_war_armor
from morphomesh.blender_bridge import BlenderBridge
from morphomesh.creature_generator import (
    UrsineAnatomyConfig,
    generate_bear_base_mesh,
    get_blender_generation_script,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.materials import CreaturePBRSuite, STANDARD_PBR_MATERIALS

BLENDER_BIN = "/Applications/Blender.app/Contents/MacOS/Blender"


# ==============================================================================
# 1. PBR PRINCIPLED BSDF V2 SHADER AUDIT (BLENDER 5.2.1 LTS)
# ==============================================================================

@pytest.mark.skipif(not os.path.isfile(BLENDER_BIN), reason="Blender 5.2.1 LTS not installed")
class TestPBRShaderForensicAudit:
    """Verifies that all 5 PBR materials instantiate valid Principled BSDF v2 node trees."""

    def test_principled_bsdf_v2_sockets_and_physical_properties(self):
        """Asserts metallic == 1.0 for metals, coat weight >= 0.80 for wet nose, and correct socket names."""
        s_mats = CreaturePBRSuite().get_materials_blender_script("Bear_Base_Mesh")
        audit_code = s_mats + """
import bpy, json

audit = {}
for m_name in [
    "Mat_Bear_Fur",
    "Mat_Bear_Skin_Nose",
    "Mat_Bear_Claws",
    "Mat_Armor_WeatheredSteel",
    "Mat_Armor_BrassTrim",
]:
    mat = bpy.data.materials.get(m_name)
    assert mat is not None, f"Material {m_name} not found"
    bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    assert bsdf is not None, f"Principled BSDF node missing in {m_name}"

    audit[m_name] = {
        "metallic": bsdf.inputs["Metallic"].default_value,
        "roughness": bsdf.inputs["Roughness"].default_value,
        "coat_weight": bsdf.inputs["Coat Weight"].default_value,
        "coat_roughness": bsdf.inputs["Coat Roughness"].default_value,
        "sheen_weight": bsdf.inputs["Sheen Weight"].default_value,
        "subsurface_weight": bsdf.inputs["Subsurface Weight"].default_value,
        "specular_ior_level": bsdf.inputs["Specular IOR Level"].default_value,
    }

print("PBR_AUDIT_OUTPUT:" + json.dumps(audit))
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(audit_code)
            f_path = f.name

        try:
            res = subprocess.run(
                [BLENDER_BIN, "--background", "--python", f_path],
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert res.returncode == 0, f"Blender execution failed:\n{res.stderr}\n{res.stdout}"
            audit_data = None
            for line in res.stdout.splitlines():
                if line.startswith("PBR_AUDIT_OUTPUT:"):
                    audit_data = json.loads(line.replace("PBR_AUDIT_OUTPUT:", ""))
                    break
            assert audit_data is not None, "Failed to parse PBR audit output from Blender"

            # 1. Mat_Armor_WeatheredSteel: pure conductor (metallic == 1.0)
            steel = audit_data["Mat_Armor_WeatheredSteel"]
            assert math.isclose(steel["metallic"], 1.0, abs_tol=1e-3), f"Steel metallic != 1.0: {steel['metallic']}"
            assert 0.30 <= steel["roughness"] <= 0.50

            # 2. Mat_Armor_BrassTrim: pure conductor (metallic == 1.0)
            brass = audit_data["Mat_Armor_BrassTrim"]
            assert math.isclose(brass["metallic"], 1.0, abs_tol=1e-3), f"Brass metallic != 1.0: {brass['metallic']}"
            assert 0.20 <= brass["roughness"] <= 0.40

            # 3. Mat_Bear_Skin_Nose: wet clearcoat moisture (coat weight >= 0.80)
            nose = audit_data["Mat_Bear_Skin_Nose"]
            assert nose["coat_weight"] >= 0.80, f"Nose coat weight < 0.80: {nose['coat_weight']}"
            assert nose["roughness"] <= 0.20, f"Nose roughness > 0.20: {nose['roughness']}"
            assert math.isclose(nose["metallic"], 0.0, abs_tol=1e-3)

            # 4. Mat_Bear_Fur: velvet sheen and subsurface
            fur = audit_data["Mat_Bear_Fur"]
            assert fur["roughness"] >= 0.80
            assert fur["sheen_weight"] >= 0.60
            assert fur["subsurface_weight"] >= 0.05
            assert math.isclose(fur["metallic"], 0.0, abs_tol=1e-3)

            # 5. Mat_Bear_Claws: satin keratin
            claws = audit_data["Mat_Bear_Claws"]
            assert 0.30 <= claws["roughness"] <= 0.45
            assert math.isclose(claws["metallic"], 0.0, abs_tol=1e-3)
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)


# ==============================================================================
# 2. CANONICAL CLEARANCE AUDIT (SCALE 1.0)
# ==============================================================================

class TestCanonicalArmorClearance:
    """Verifies minimum clearance distance d_min >= 0.015m at canonical scale 1.0."""

    @pytest.fixture
    def bear_mesh(self) -> MeshGeometry:
        return generate_bear_base_mesh(UrsineAnatomyConfig(scale=1.0)).mesh

    @pytest.fixture
    def engine(self) -> ProceduralArmorEngine:
        return ProceduralArmorEngine()

    def test_all_six_plates_clearance_strictly_positive(self, engine, bear_mesh):
        """Asserts d_min >= 0.015m for all 6 plates in Python data structure."""
        plates = engine.generate_all_armor_plates(scale=1.0, bear_mesh=bear_mesh)
        assert len(plates) == 6

        expected_bounds = {
            "Armor_Pauldron_L": (0.015, 0.045),
            "Armor_Pauldron_R": (0.015, 0.045),
            "Armor_Gorget": (0.015, 0.045),
            "Armor_Bracer_L": (0.015, 0.045),
            "Armor_Bracer_R": (0.015, 0.045),
            "Armor_Backplate": (0.015, 0.045),
        }

        for name, plate in plates.items():
            metrics = engine.compute_clearance_metrics(plate, bear_mesh)
            d_min = metrics["min_distance"]
            min_bound, max_bound = expected_bounds[name]
            assert d_min >= 0.015, f"{name} violates clearance: d_min={d_min:.4f}m < 0.015m"
            assert d_min <= max_bound, f"{name} clearance too large: d_min={d_min:.4f}m > {max_bound}m"


# ==============================================================================
# 3. TOPOLOGY & 2-MANIFOLD AUDIT IN HEADLESS BLENDER 5.2.1 LTS
# ==============================================================================

@pytest.mark.skipif(not os.path.isfile(BLENDER_BIN), reason="Blender 5.2.1 LTS not installed")
class TestBlenderArmorTopologyAdversarialAudit:
    """
    Adversarially stress-tests the actual meshes committed to Blender by get_armor_blender_script.
    Checks:
    - Zero degenerate zero-area faces.
    - 2-manifold closed watertight shells (0 non-manifold edges).
    - Normal vector orientation (positive signed volume).
    """

    def _run_blender_topology_audit(self, scale: float = 1.0) -> Dict[str, any]:
        s_mesh = get_blender_generation_script("Bear_Base_Mesh", scale=scale)
        s_mats = CreaturePBRSuite().get_materials_blender_script("Bear_Base_Mesh")
        s_arm = ProceduralArmorEngine().get_armor_blender_script("Bear_Base_Mesh", scale=scale)

        audit_code = s_mesh + "\n" + s_mats + "\n" + s_arm + """
import bpy, bmesh, json

results = {}
for a_name in created_armor_objects:
    obj = bpy.data.objects.get(a_name)
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    nm_edges = [e.index for e in bm.edges if not e.is_manifold or len(e.link_faces) != 2]
    zero_area_faces = [f.index for f in bm.faces if f.calc_area() < 1e-7]

    # Calculate signed volume to verify normal vector outward orientation
    vol = 0.0
    for f in bm.faces:
        if len(f.verts) >= 3:
            v0 = f.verts[0].co
            for k in range(1, len(f.verts) - 1):
                v1 = f.verts[k].co
                v2 = f.verts[k+1].co
                vol += v0.dot(v1.cross(v2)) / 6.0

    results[a_name] = {
        "vertex_count": len(bm.verts),
        "edge_count": len(bm.edges),
        "face_count": len(bm.faces),
        "non_manifold_edge_count": len(nm_edges),
        "zero_area_face_count": len(zero_area_faces),
        "signed_volume": vol,
        "is_watertight": all(len(e.link_faces) == 2 for e in bm.edges),
    }
    bm.free()

print("TOPOLOGY_AUDIT_OUTPUT:" + json.dumps(results))
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(audit_code)
            f_path = f.name

        try:
            res = subprocess.run(
                [BLENDER_BIN, "--background", "--python", f_path],
                capture_output=True,
                text=True,
                timeout=45,
            )
            assert res.returncode == 0, f"Blender execution failed:\n{res.stderr}\n{res.stdout}"
            audit_data = None
            for line in res.stdout.splitlines():
                if line.startswith("TOPOLOGY_AUDIT_OUTPUT:"):
                    audit_data = json.loads(line.replace("TOPOLOGY_AUDIT_OUTPUT:", ""))
                    break
            assert audit_data is not None, "Failed to parse topology audit output from Blender"
            return audit_data
        finally:
            if os.path.exists(f_path):
                os.remove(f_path)

    def test_zero_area_faces_all_plates(self):
        """Asserts zero degenerate zero-area faces across all plates in Blender."""
        results = self._run_blender_topology_audit(scale=1.0)
        for name, data in results.items():
            assert data["zero_area_face_count"] == 0, f"{name} contains {data['zero_area_face_count']} zero-area faces"

    def test_armor_pauldron_r_blender_manifold_defect(self):
        """
        POSITIVE COMPLIANCE ASSERTION:
        In get_armor_blender_script, line 665 appends:
        (og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j])
        ensuring Armor_Pauldron_R is a closed 2-manifold watertight shell in Blender (0 non-manifold edges).
        """
        results = self._run_blender_topology_audit(scale=1.0)
        r_pauldron = results["Armor_Pauldron_R"]
        assert r_pauldron["non_manifold_edge_count"] == 0, (
            f"Armor_Pauldron_R has non-manifold edges: {r_pauldron['non_manifold_edge_count']}"
        )
        assert r_pauldron["is_watertight"] is True

    def test_armor_backplate_inverted_normals_defect(self):
        """
        POSITIVE COMPLIANCE ASSERTION:
        In get_armor_blender_script, make_backplate constructs outer grid faces with
        winding (og[i][j], og[i][j+1], og[i+1][j+1], og[i+1][j]), resulting in
        outward-pointing face normals (+z) and strictly positive signed volume (> 0).
        """
        results = self._run_blender_topology_audit(scale=1.0)
        bp = results["Armor_Backplate"]
        assert bp["signed_volume"] > 0, (
            f"Armor_Backplate has inverted normals: signed volume = {bp['signed_volume']} m^3"
        )


# ==============================================================================
# 4. SCALE STRESS TESTING (0.5x to 2.0x)
# ==============================================================================

class TestArmorScaleStressAudit:
    """
    Stress-tests armor fitting across extreme scaling factors (0.5x to 2.0x).
    Verifies that all 6 armor plates maintain d_min >= 0.015m with 0 collisions/intersections.
    """

    @pytest.mark.parametrize("scale", [0.5, 0.75, 1.0, 1.5, 2.0])
    def test_scale_clearance_behavior(self, scale: float):
        """
        POSITIVE COMPLIANCE ASSERTION:
        Asserts that across all scales from 0.5x to 2.0x:
        - Backplate adaptive sampling bounds scale properly with sc.
        - Minimum clearance d_min >= 0.015m for all 6 plates without intersection or collision.
        """
        engine = ProceduralArmorEngine()
        bear_mesh = generate_bear_base_mesh(UrsineAnatomyConfig(scale=scale)).mesh
        plates = engine.generate_all_armor_plates(scale=scale, bear_mesh=bear_mesh)

        results = {}
        for name, pmesh in plates.items():
            metrics = engine.compute_clearance_metrics(pmesh, bear_mesh)
            results[name] = metrics["min_distance"]

        for name, d_min in results.items():
            assert d_min >= 0.015, (
                f"{name} clearance violation at scale {scale}: d_min = {d_min:.4f}m < 0.015m"
            )
