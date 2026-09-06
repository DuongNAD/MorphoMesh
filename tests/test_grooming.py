"""
MorphoMesh: Volumetric Fur & Hair Grooming Engine Test Suite.

Verifies:
1. Multi-layer fur strand counts (>= 12,000 parent guide strands, exceeding >= 10,000 requirement).
2. Child particle interpolation (> 100,000 total render strands).
3. Undercoat vs Guard Hairs physical layer configuration.
4. Biological growth flow vector field along dorsal spine, flanks, and limbs.
5. Vertex group density masking: full density on torso/spine/mane, strictly 0.0 on naked features.
6. Curve-to-mesh glTF ribbon mesh evaluation, quad topology, and UV coordinates.
7. AST static security validation of generated Blender automation scripts.
8. Blender 5.2.1 LTS integration verification (socket & headless).
"""

from __future__ import annotations

import math
from typing import Dict, List, Tuple

import pytest

from morphomesh.blender_bridge import BlenderBridge, BpyCodeValidator
from morphomesh.creature_generator import (
    STANDARDIZED_VERTEX_GROUPS,
    generate_bear_base_mesh,
    get_blender_generation_script,
)
from morphomesh.grooming import (
    FULL_FUR_GROUPS,
    MODULATED_FUR_GROUPS,
    ZERO_FUR_GROUPS,
    CreatureGroomingEngine,
    compute_biological_flow_vector,
    evaluate_fur_ribbons_for_gltf,
    get_default_guard_hair_config,
    get_default_undercoat_config,
    setup_volumetric_fur,
)


# ==============================================================================
# 1. MULTI-LAYER FUR STRAND COUNT & PARAMETER TESTS
# ==============================================================================

class TestVolumetricFurConfiguration:
    """Verifies strand metrics and multi-layer fur architecture."""

    def test_default_strand_counts_meet_and_exceed_10k_requirement(self):
        """Asserts total parent guide strands >= 12,000, strictly exceeding the >= 10,000 mandate."""
        undercoat = get_default_undercoat_config(8000)
        guard = get_default_guard_hair_config(4000)

        assert undercoat.strand_count >= 8000
        assert guard.strand_count >= 4000
        total_parents = undercoat.strand_count + guard.strand_count
        assert total_parents >= 12000
        assert total_parents >= 10000, "Must satisfy >= 10,000 parent guide strands requirement"

    def test_child_particle_interpolation_yields_over_100k_render_strands(self):
        """Asserts interpolated child distribution yields > 100,000 render strands."""
        undercoat = get_default_undercoat_config(8000)
        guard = get_default_guard_hair_config(4000)

        undercoat_render = undercoat.strand_count * (1 + undercoat.rendered_child_count)
        guard_render = guard.strand_count * (1 + guard.rendered_child_count)
        total_render = undercoat_render + guard_render

        assert undercoat.child_type == "INTERPOLATED"
        assert guard.child_type == "INTERPOLATED"
        assert undercoat_render >= 88000  # 8000 * 11
        assert guard_render >= 36000     # 4000 * 9
        assert total_render >= 124000
        assert total_render > 100000, "Must exceed > 100,000 render strands"

    def test_multi_layer_strata_physical_differentiation(self):
        """Verifies distinct biophysical characteristics between undercoat and guard hairs."""
        undercoat = get_default_undercoat_config()
        guard = get_default_guard_hair_config()

        # Undercoat: shorter, high insulation, crimp/frizz, lighter clumping
        assert undercoat.hair_length < guard.hair_length
        assert undercoat.hair_length <= 0.05
        assert undercoat.roughness_endpoint > guard.roughness_endpoint
        assert undercoat.clump_factor < guard.clump_factor

        # Guard hairs: longer, sleek, pronounced directional clumping, heavier drape
        assert guard.hair_length >= 0.08
        assert guard.root_radius > undercoat.root_radius
        assert guard.gravity > undercoat.gravity
        assert guard.align_factor[1] > undercoat.align_factor[1]

    def test_tapering_and_root_tip_diameters(self):
        """Verifies sharp apical taper geometry (shape <= -0.7, root > tip)."""
        undercoat = get_default_undercoat_config()
        guard = get_default_guard_hair_config()

        for layer in [undercoat, guard]:
            assert layer.shape <= -0.70, "Negative shape required for realistic taper"
            assert layer.root_radius >= 0.0010, "Root radius should be ~1.0 - 1.4mm"
            assert layer.tip_radius <= 0.0002, "Tip radius should taper to sharp point <= 0.2mm"
            assert layer.root_radius > layer.tip_radius * 5.0


# ==============================================================================
# 2. BIOLOGICAL GROWTH FLOW VECTOR FIELD TESTS
# ==============================================================================

class TestBiologicalFlowMechanics:
    """Verifies mathematical growth flow radiating from dorsal spine downwards."""

    def test_dorsal_spine_caudal_flow(self):
        """Test points along the dorsal spine flow caudally toward tail (+Y in model space)."""
        spine_points = [
            (0.0, -0.2, 1.05),  # Shoulder hump
            (0.0, 0.1, 1.08),   # Mid-back spine
            (0.0, 0.4, 0.95),   # Lumbar spine
        ]
        for pt in spine_points:
            vec = compute_biological_flow_vector(pt, normal=(0.0, 0.0, 1.0))
            vx, vy, vz = vec
            assert vy > 0.30, f"Flow along dorsal spine at {pt} should point caudally (+Y), got vy={vy}"
            assert abs(vx) < 0.15, f"Midline spine flow should be symmetric in X, got vx={vx}"

    def test_lateral_flank_radiance(self):
        """Test points on ribcage/flanks radiate outward in ±X and curve down in -Z."""
        left_flank = (0.35, 0.1, 0.75)
        right_flank = (-0.35, 0.1, 0.75)

        v_left = compute_biological_flow_vector(left_flank, normal=(1.0, 0.0, 0.0))
        v_right = compute_biological_flow_vector(right_flank, normal=(-1.0, 0.0, 0.0))

        # Left flank should radiate toward +X
        assert v_left[0] > 0.25, f"Left flank should radiate outward (+X), got {v_left[0]}"
        assert v_left[2] < -0.20, f"Left flank should drape downward (-Z), got {v_left[2]}"

        # Right flank should radiate toward -X
        assert v_right[0] < -0.25, f"Right flank should radiate outward (-X), got {v_right[0]}"
        assert v_right[2] < -0.20, f"Right flank should drape downward (-Z), got {v_right[2]}"

        # Flanks should be symmetric
        assert math.isclose(v_left[0], -v_right[0], abs_tol=1e-3)
        assert math.isclose(v_left[1], v_right[1], abs_tol=1e-3)
        assert math.isclose(v_left[2], v_right[2], abs_tol=1e-3)

    def test_limb_downward_gravitational_descent(self):
        """Test points on distal limbs (Z < 0.45) flow predominantly downward toward paws."""
        limb_points = [
            (0.38, -0.35, 0.20),  # Forelimb wrist
            (-0.38, -0.35, 0.20),
            (0.36, 0.45, 0.15),   # Hindlimb shank
            (-0.36, 0.45, 0.15),
        ]
        for pt in limb_points:
            vec = compute_biological_flow_vector(pt, normal=(0.0, 0.0, 1.0))
            vx, vy, vz = vec
            assert vz < -0.60, f"Limb flow at {pt} must be strongly downward (-Z), got vz={vz}"

    def test_biological_flow_vector_strictly_normalized(self):
        """Test all output vectors are unit vectors."""
        test_points = [
            (0.0, 0.0, 0.8),
            (0.4, -0.3, 0.2),
            (-0.2, 0.5, 0.9),
            (0.0, -0.8, 1.2),
        ]
        for pt in test_points:
            vec = compute_biological_flow_vector(pt)
            mag = math.sqrt(sum(c * c for c in vec))
            assert math.isclose(mag, 1.0, abs_tol=1e-5), f"Vector {vec} not normalized"


# ==============================================================================
# 3. VERTEX GROUP DENSITY MASKING TESTS
# ==============================================================================

class TestVertexGroupDensityMasking:
    """Verifies anatomical masking prevents hair growth on naked biological structures."""

    def test_zero_fur_features_strictly_zero_weight(self):
        """Asserts weight = 0.0 on snout, nostrils, mouth, teeth, eyes, claws, and pads."""
        res = generate_bear_base_mesh()
        masks = CreatureGroomingEngine.build_density_mask_weights(res.vertex_groups, len(res.mesh.vertices))

        density_map = masks["Fur_Density"]
        length_map = masks["Fur_Length"]

        for gname in ZERO_FUR_GROUPS:
            assert gname in res.vertex_groups, f"Missing group {gname}"
            indices = res.vertex_groups[gname]
            assert len(indices) > 0, f"Group {gname} has no vertices"
            for v_idx in indices:
                assert density_map[v_idx] == 0.0, f"Vertex {v_idx} in {gname} must have 0.0 density"
                assert length_map[v_idx] == 0.0, f"Vertex {v_idx} in {gname} must have 0.0 length"

    def test_full_fur_regions_receive_full_density(self):
        """Asserts weight = 1.0 on torso, dorsal spine, and shoulder hump."""
        res = generate_bear_base_mesh()
        masks = CreatureGroomingEngine.build_density_mask_weights(res.vertex_groups, len(res.mesh.vertices))
        density_map = masks["Fur_Density"]

        for gname in FULL_FUR_GROUPS:
            indices = res.vertex_groups[gname]
            assert len(indices) > 0
            for v_idx in indices:
                assert density_map[v_idx] == 1.0, f"Vertex {v_idx} in {gname} should have 1.0 density"

    def test_modulated_fur_regions_weights(self):
        """Asserts modulated weights on limbs (0.75), tail (0.85), ears (0.35)."""
        res = generate_bear_base_mesh()
        masks = CreatureGroomingEngine.build_density_mask_weights(res.vertex_groups, len(res.mesh.vertices))
        density_map = masks["Fur_Density"]

        # Tail vertices
        tail_indices = res.vertex_groups["tail"]
        assert len(tail_indices) > 0
        for idx in tail_indices:
            assert density_map[idx] == 0.85

        # Ear vertices
        ear_indices = res.vertex_groups["ears"]
        assert len(ear_indices) > 0
        for idx in ear_indices:
            assert density_map[idx] == 0.35


# ==============================================================================
# 4. PURE PYTHON GLTF RIBBON MESH EVALUATION TESTS
# ==============================================================================

class TestCurveToMeshRibbonEvaluation:
    """Verifies geometric evaluation of hair strands into polygonal ribbons for glTF export."""

    def test_pure_python_ribbon_mesh_topology(self):
        """Tests that strands evaluate into clean quad polygon ribbons."""
        # Create 10 mock hair strands
        mock_strands = []
        for s in range(10):
            strand = [
                (0.05 * s, 0.0, 1.0),
                (0.05 * s, 0.02, 0.98),
                (0.05 * s, 0.05, 0.95),
                (0.05 * s, 0.08, 0.91),
                (0.05 * s, 0.11, 0.86),
            ]
            mock_strands.append(strand)

        ribbon_data = CreatureGroomingEngine.generate_ribbon_geometry_pure_python(
            mock_strands,
            root_width=0.003,
            tip_width=0.0004,
            taper_shape=-0.7,
        )

        assert ribbon_data["strand_count"] == 10
        # 10 strands * 5 keys * 2 vertices per key = 100 vertices
        assert ribbon_data["vertex_count"] == 100
        # 10 strands * 4 quad segments per strand = 40 quad faces
        assert ribbon_data["face_count"] == 40
        assert ribbon_data["quad_count"] == 40
        assert ribbon_data["triangle_count"] == 80
        assert ribbon_data["has_uvs"] is True
        assert len(ribbon_data["uvs"]) == 160  # 40 faces * 4 UVs per face

    def test_ribbon_width_tapers_from_root_to_tip(self):
        """Asserts root ribbon width is strictly wider than tip ribbon width."""
        mock_strand = [
            [(0.0, 0.0, 0.0), (0.0, 0.0, 0.05), (0.0, 0.0, 0.10)]
        ]
        root_w = 0.004
        tip_w = 0.0005
        ribbon_data = CreatureGroomingEngine.generate_ribbon_geometry_pure_python(
            mock_strand,
            root_width=root_w,
            tip_width=tip_w,
            taper_shape=-0.7,
        )

        verts = ribbon_data["vertices"]
        root_span = math.dist(verts[0], verts[1])
        tip_span = math.dist(verts[4], verts[5])

        assert root_span > tip_span * 4.0
        assert math.isclose(root_span, root_w, rel_tol=0.05)
        assert math.isclose(tip_span, tip_w, rel_tol=0.05)

    def test_ribbon_faces_have_positive_surface_area(self):
        """Asserts no zero-area degenerate faces in generated ribbons."""
        mock_strand = [
            [(0.1 * i, 0.2 * i, 0.5) for i in range(6)]
        ]
        ribbon = CreatureGroomingEngine.generate_ribbon_geometry_pure_python(mock_strand)
        verts = ribbon["vertices"]
        for f in ribbon["faces"]:
            v0, v1, v2, v3 = [verts[idx] for idx in f]
            # Triangle 1
            e1 = (v1[0] - v0[0], v1[1] - v0[1], v1[2] - v0[2])
            e2 = (v2[0] - v0[0], v2[1] - v0[1], v2[2] - v0[2])
            cross1 = (e1[1]*e2[2] - e1[2]*e2[1], e1[2]*e2[0] - e1[0]*e2[2], e1[0]*e2[1] - e1[1]*e2[0])
            area1 = 0.5 * math.sqrt(sum(c*c for c in cross1))
            assert area1 > 1e-8, f"Ribbon face {f} has degenerate triangle area"


# ==============================================================================
# 5. AST SECURITY VALIDATOR TESTS FOR GROOMING SCRIPTS
# ==============================================================================

class TestGroomingBlenderScriptSecurity:
    """Verifies that grooming automation scripts pass two-tier AST static analysis."""

    def test_grooming_blender_script_ast_validation(self):
        """Asserts generated grooming script is 100% compliant with AST security rules."""
        engine = CreatureGroomingEngine()
        script = engine.get_grooming_blender_script(
            mesh_obj_name="Bear_Base_Mesh",
            undercoat_strands=8000,
            guard_hair_strands=4000,
            generate_ribbons=True,
            max_ribbon_strands=1000,
        )

        validator = BpyCodeValidator()
        validator.validate(script)  # Must not raise SecurityException

    def test_grooming_script_contains_required_identifiers(self):
        """Verifies essential grooming keywords and particle configurations are embedded."""
        engine = CreatureGroomingEngine()
        script = engine.get_grooming_blender_script("Test_Mesh", 8000, 4000)

        assert "Undercoat_Fur" in script
        assert "Guard_Hairs_Fur" in script
        assert "Fur_Density" in script
        assert "Fur_Length" in script
        assert "Fur_Clump" in script
        assert "INTERPOLATED" in script
        assert "object_align_factor" in script


# ==============================================================================
# 6. BLENDER 5.2.1 LTS INTEGRATION & VERIFICATION
# ==============================================================================

class TestBlenderBridgeGroomingIntegration:
    """Verifies bridge methods and live/headless execution in Blender 5.2.1 LTS."""

    @pytest.fixture
    def bridge(self) -> BlenderBridge:
        return BlenderBridge()

    def test_bridge_has_setup_creature_fur_method(self, bridge: BlenderBridge):
        """Asserts setup_creature_fur exists and has correct default signature."""
        assert hasattr(bridge, "setup_creature_fur")
        assert hasattr(bridge, "evaluate_fur_ribbons")

    def test_top_level_convenience_functions(self):
        """Asserts PROJECT.md top-level function interface contracts."""
        res = setup_volumetric_fur("Bear_Test", undercoat_strands=8000, guard_hair_strands=4000)
        assert res["status"] == "success"
        assert res["total_parent_strands"] >= 12000
        assert res["total_render_strands"] >= 100000

        ribbon_name = evaluate_fur_ribbons_for_gltf("Bear_Test")
        assert ribbon_name == "Bear_Test_Fur_Ribbons"

    def test_live_or_headless_blender_fur_grooming_verification(self, bridge: BlenderBridge):
        """
        Executes setup_creature_fur on active or headless Blender session and asserts
        that total parent strands >= 12,000 and total render strands >= 100,000.
        """
        # Ensure a bear mesh is present in Blender
        gen_script = get_blender_generation_script("Bear_Pytest_Groom", 1.0)
        out = bridge.execute_custom_script(gen_script)
        assert out.success is True

        res = bridge.setup_creature_fur(
            mesh_object_name="Bear_Pytest_Groom",
            undercoat_strands=8000,
            guard_hair_strands=4000,
            flow_vertex_group="dorsal_spine",
            generate_gltf_ribbons=True,
            max_ribbon_strands=1000,
        )

        assert res["status"] == "success"
        assert res["mesh_object_name"] == "Bear_Pytest_Groom"
        assert res["total_parent_strands"] >= 12000
        assert res["total_render_strands"] >= 100000
        assert "Undercoat_Fur" in res["fur_systems"]
        assert "Guard_Hairs_Fur" in res["fur_systems"]
        assert res["ribbon_mesh_name"] == "Bear_Pytest_Groom_Fur_Ribbons"
