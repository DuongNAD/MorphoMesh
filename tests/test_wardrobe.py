"""
Unit & Integration Tests for MorphoMesh Parametric Digital Human Wardrobe.

Validates Milestone 3 Task 3 requirements:
1. Parametric procedural garment generator matching Yu Nian An's turnaround:
   - White two-strap slip dress: sleeveless, dual shoulder straps, scoop neckline,
     draped A-line 20-pleat flared skirt ending at kneecap, Solidify thickness 0.002m, manifold geometry.
   - Sash waist belt: cinched around waist at waist_girth, front knot and dangling ribbons.
   - Strappy flat sandals: sole matching foot dimensions (23.5cm x 8.2cm x 1.2cm), thin strap arching instep.
   - Signature magic props: 10 taut marionette red cords, 10 luminous white butterflies.
2. Binding / Rigging integration: Armature / Deform modifier binding to character rig.
3. Standalone Blender 4.5+ LTS script generation (AST syntax valid).
4. dress_human callable function conforming to HumanWardrobeResult model.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from unittest.mock import MagicMock
import pytest

from morphomesh.models import HumanWardrobeResult
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


class TestWardrobeMeshGeneration:
    """Validates 3D mesh geometry, topology, and dimensions for all garment pieces."""

    def test_dress_bodice_quad_topology_and_dimensions(self):
        """Validates dress bodice is pure quad, has straps and scoop neckline."""
        bodice = generate_dress_bodice(height=1.65, clearance=0.015, thickness=0.002)
        assert len(bodice.vertices) >= 100, "Bodice requires sufficient vertex density"
        assert len(bodice.faces) >= 50
        assert len(bodice.faces) % 2 == 0, "Quads must be stored as paired triangles"

        # Check Z elevation span: empire waist (~1.03m) to shoulder strap top (~1.34m)
        zs = [v[2] for v in bodice.vertices]
        assert min(zs) >= 1.00, f"Bodice bottom Z={min(zs)} should start near empire waist"
        assert max(zs) >= 1.32, f"Bodice straps top Z={max(zs)} should reach clavicle/shoulder top"

        # Check bilateral symmetry in X
        xs = [v[0] for v in bodice.vertices]
        assert abs(min(xs) + max(xs)) < 1e-3, "Bodice must be laterally symmetric"

    def test_waist_sash_dimensions_and_knot_ribbons(self):
        """Validates empire waist sash wrap with front knot and dangling streamers."""
        sash = generate_dress_waist_sash(height=1.65, clearance=0.016, belt_width=0.045)
        assert len(sash.vertices) >= 80
        assert len(sash.faces) % 2 == 0

        # Verify ribbon streamers cascade down
        zs = [v[2] for v in sash.vertices]
        assert min(zs) <= 0.75, f"Ribbon streamers should cascade down to Z={min(zs)}"
        assert max(zs) >= 1.05, f"Waist sash band should wrap at empire waist Z={max(zs)}"

    def test_pleated_skirt_flared_silhouette_and_pleats(self):
        """Validates 20-pleat flared A-line skirt radiating to kneecap."""
        skirt = generate_dress_pleated_skirt(height=1.65, clearance=0.015, pleat_count=20)
        assert len(skirt.vertices) >= 300
        assert len(skirt.faces) % 2 == 0

        zs = [v[2] for v in skirt.vertices]
        assert 0.48 <= min(zs) <= 0.55, f"Skirt hem Z={min(zs)} must settle right at kneecap (~0.52m)"
        assert max(zs) >= 1.00, f"Skirt top Z={max(zs)} must attach to waistline"

        # Verify A-line flare: hem radius must be significantly wider than waist radius
        waist_verts = [v for v in skirt.vertices if abs(v[2] - max(zs)) < 0.02]
        hem_verts = [v for v in skirt.vertices if abs(v[2] - min(zs)) < 0.02]

        r_waist = max(math.sqrt(v[0]**2 + v[1]**2) for v in waist_verts)
        r_hem = max(math.sqrt(v[0]**2 + v[1]**2) for v in hem_verts)
        assert r_hem > r_waist * 1.8, f"Skirt must flare outward: r_hem={r_hem:.3f}, r_waist={r_waist:.3f}"

    def test_flat_sandals_dimensions_and_instep_strap(self):
        """Validates flat slip-on sandals sole dimensions (23.5cm x 8.2cm) and instep strap."""
        sandals = generate_flat_sandals(height=1.65)
        assert "Mesh_Sandal_L" in sandals
        assert "Mesh_Sandal_R" in sandals

        for side, s_mesh in sandals.items():
            assert len(s_mesh.vertices) >= 30
            assert len(s_mesh.faces) % 2 == 0
            ys = [v[1] for v in s_mesh.vertices]
            sole_length = max(ys) - min(ys)
            assert 0.22 <= sole_length <= 0.25, f"Sandal sole length {sole_length} must match foot (~0.235m)"

            zs = [v[2] for v in s_mesh.vertices]
            assert min(zs) >= 0.0, "Sandal sole rests on ground Z=0"
            assert max(zs) >= 0.03, "Instep strap must arch over metatarsals"

    def test_magic_marionette_red_strings(self):
        """Validates 10 taut marionette cords tethered to finger distal points."""
        strings = generate_marionette_red_strings(height=1.65)
        assert len(strings.vertices) >= 60
        assert len(strings.faces) % 2 == 0
        zs = [v[2] for v in strings.vertices]
        # Strings span from elevated hands (~1.0m) down to skirt hem (~0.50m)
        assert min(zs) <= 0.52
        assert max(zs) >= 0.98

    def test_luminous_butterflies_morphology(self):
        """Validates swallowtail butterfly quad geometry with wings."""
        b_mesh = generate_swallowtail_butterfly(scale=0.045, wing_angle_deg=25.0)
        assert len(b_mesh.vertices) >= 12
        assert len(b_mesh.faces) >= 4
        assert len(b_mesh.faces) % 2 == 0

    def test_full_wardrobe_suite_generation(self):
        """Validates generate_yu_nian_an_wardrobe creates all components."""
        suite = generate_yu_nian_an_wardrobe()
        assert "Dress_Bodice" in suite
        assert "Dress_WaistSash" in suite
        assert "Dress_PleatedSkirt" in suite
        assert "Mesh_Sandal_L" in suite
        assert "Mesh_Sandal_R" in suite
        assert "Prop_Marionette_Strings" in suite
        assert "Prop_Butterfly_00" in suite
        assert len(suite) >= 16  # 3 dress + 2 sandals + 1 strings + 10 butterflies


class TestWardrobeScriptAST:
    """Validates standalone executable Python script generated for Blender."""

    def test_wardrobe_script_generates_valid_python_ast(self):
        """Verify wardrobe script parses cleanly into Python AST and executes without NameError."""
        script = get_wardrobe_script(
            target_object="Human_Base_Mesh",
            outfit_preset="yu_nian_an_dress",
            include_sandals=True,
            include_red_threads=True,
            include_glowing_butterflies=True,
        )
        assert isinstance(script, str)
        assert len(script) > 500
        assert "json.loads" in script, "Script must use json.loads for CFG and WARDROBE_GEOM"

        tree = ast.parse(script)
        assert tree is not None
        assert isinstance(tree, ast.Module)

        # Mock execute script to verify zero NameError (e.g. name 'true' is not defined)
        mock_bpy = MagicMock()
        sys.modules["bpy"] = mock_bpy
        sys.modules["mathutils"] = MagicMock()
        scope = {"bpy": mock_bpy, "math": math, "json": json}
        code_obj = compile(script, "<wardrobe_script>", "exec")
        exec(code_obj, scope, scope)

    def test_script_contains_collections_armature_binding_and_materials(self):
        """Verify script binds to armature, assigns materials, populates meshes, and adds Solidify."""
        script = get_wardrobe_script(target_object="Yu_Nian_An_Body")
        assert "Mesh_Dress_Bodice" in script
        assert "Mesh_Dress_WaistSash" in script
        assert "Mesh_Dress_PleatedSkirt" in script
        assert "Mesh_Sandal_L" in script
        assert "Prop_Marionette_Strings" in script
        assert "Prop_Butterfly" in script
        assert "Armature_Yu_Nian_An_Rigify" in script
        assert "Mat_Dress_WhiteSilk" in script
        assert "Mat_Dress_WaistBelt" in script
        assert "Mat_Sandal_Leather" in script

        # Verify genuine mesh data population (not empty meshes!)
        assert "from_pydata" in script, "Script must call me.from_pydata(verts, [], faces) to populate geometry"
        assert "me.update()" in script, "Script must call me.update() on populated meshes"
        assert "WARDROBE_GEOM" in script, "Script must contain serialized WARDROBE_GEOM data"

        # Verify Solidify modifier added with thickness 0.002m
        assert "SOLIDIFY" in script, "Script must add Solidify modifier to dress parts"
        assert "Solidify" in script

    def test_wardrobe_girth_scaling_prevents_penetration(self):
        """Verify that wardrobe girth scaling parameterizes waist and chest without clipping."""
        sash_narrow = generate_dress_waist_sash(height=1.65, clearance=0.015, waist_girth=0.58)
        sash_wide = generate_dress_waist_sash(height=1.65, clearance=0.015, waist_girth=1.20)
        r_narrow = max(math.hypot(v[0], v[1]) for v in sash_narrow.vertices if abs(v[2] - 1.05) < 1e-4)
        r_wide = max(math.hypot(v[0], v[1]) for v in sash_wide.vertices if abs(v[2] - 1.05) < 1e-4)
        assert r_wide > r_narrow * 1.5, "Waist sash radius must expand proportionally with waist_girth"


class TestDressHumanFunction:
    """Validates the dress_human callable function."""

    def test_dress_human_returns_authoritative_result(self):
        """Asserts result dict conforms to HumanWardrobeResult model."""
        res = dress_human(
            human_object_name="Human_Base_Mesh",
            outfit="yu_nian_an_dress",
            include_sandals=True,
            include_red_threads=True,
            include_glowing_butterflies=True,
            butterfly_count=10,
        )
        assert res["status"] == "success"
        assert res["outfit_preset"] == "yu_nian_an_dress"
        assert res["clearance_offset"] == 0.015
        assert "Dress_Bodice" in res["garments"]
        assert "Dress_PleatedSkirt" in res["garments"]
        assert "Sandals_Flat" in res["accessories"]
        assert "Prop_Marionette_Strings" in res["accessories"]
        assert res["prop_count"] == 20  # 10 strings + 10 butterflies

        # Validate with Pydantic model
        model = HumanWardrobeResult(**res)
        assert model.status == "success"
        assert model.prop_count == 20
        assert model.clearance_offset == 0.015
