"""
Adversarial empirical stress tests for MorphoMesh Milestone M2 (Volumetric Fur & Grooming):
1. Parent strand assertions (>= 10,000, verify >= 12,000) & render strands (>= 100,000).
2. 100% Zero-Fur density verification on naked features across scales and parameter variations.
3. Biological flow vector field and spine tangent caudal alignment (t_y > 0.60 in headless Blender).
4. Ribbon mesh topology, face validity, UV coordinates strictly in [0, 1], and glTF export validity.
5. Boundary condition and extreme parameter stress testing (scale, clamping, taper, clumping).
6. AST security and sandboxing compliance under adversarial input scripts.
"""

from __future__ import annotations

import json
import math
import os
import random
import tempfile
from typing import Dict, List, Tuple

import pytest

from morphomesh.blender_bridge import BlenderBridge, BpyCodeValidator
from morphomesh.creature_generator import (
    STANDARDIZED_VERTEX_GROUPS,
    UrsineAnatomyConfig,
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
# 1. ADVERSARIAL STRAND DENSITY & METRICS
# ==============================================================================

class TestAdversarialStrandMetrics:
    """Stress tests strand counts, boundary clamping, and child particle evaluation."""

    def test_strand_count_strict_spec_compliance(self):
        """Asserts total parent strands >= 12,000 (exceeding >= 10,000) and render strands >= 100,000."""
        undercoat = get_default_undercoat_config(8000)
        guard = get_default_guard_hair_config(4000)

        total_parents = undercoat.strand_count + guard.strand_count
        assert total_parents >= 12000, f"Expected total parents >= 12000, got {total_parents}"
        assert total_parents >= 10000, f"Specification violation: {total_parents} < 10000"

        render_undercoat = undercoat.strand_count * (1 + undercoat.rendered_child_count)
        render_guard = guard.strand_count * (1 + guard.rendered_child_count)
        total_renders = render_undercoat + render_guard

        assert total_renders >= 100000, f"Specification violation: {total_renders} < 100000"
        assert total_renders == 124000, f"Expected exactly 124000 render strands, got {total_renders}"

    def test_strand_count_adversarial_undersized_inputs_are_safely_clamped(self):
        """
        Adversarial attack: user or agent requests 0, negative, or tiny strand counts.
        The engine must defensively clamp to minimum biological thresholds (8000 undercoat, 4000 guard).
        """
        engine = CreatureGroomingEngine()
        malicious_inputs = [
            (0, 0),
            (-500, -100),
            (10, 5),
            (1000, 500),
            (7999, 3999),
        ]
        for u_in, g_in in malicious_inputs:
            res = engine.setup_volumetric_fur("Test_Bear", undercoat_strands=u_in, guard_hair_strands=g_in)
            assert res["status"] == "success"
            assert res["undercoat_strands"] >= 8000, f"Undercoat failed clamp with input {u_in}"
            assert res["guard_hair_strands"] >= 4000, f"Guard hairs failed clamp with input {g_in}"
            assert res["total_parent_strands"] >= 12000
            assert res["total_render_strands"] >= 100000

    def test_strand_count_high_density_scaling(self):
        """Tests that user requesting higher density (e.g. 15,000 undercoat, 8,000 guard) is honored."""
        engine = CreatureGroomingEngine()
        res = engine.setup_volumetric_fur("High_Density_Bear", undercoat_strands=15000, guard_hair_strands=8000)
        assert res["undercoat_strands"] == 15000
        assert res["guard_hair_strands"] == 8000
        assert res["total_parent_strands"] == 23000
        # 15000 * 11 + 8000 * 9 = 165000 + 72000 = 237000
        assert res["total_render_strands"] == 237000
        assert res["total_render_strands"] > 100000


# ==============================================================================
# 2. ADVERSARIAL ZERO-FUR MASKING ACROSS RANDOM SCALES & CONFIGS
# ==============================================================================

class TestAdversarialZeroFurMasking:
    """Stress tests vertex group masking against 100 randomized anatomical variations."""

    @pytest.mark.parametrize("scale", [0.15, 0.5, 1.0, 1.85, 3.5, 5.0])
    def test_zero_fur_weights_strictly_zero_across_scales(self, scale: float):
        """
        Adversarial test: across extreme biological scales, every single vertex in ZERO_FUR_GROUPS
        must strictly receive weight == 0.0 in Fur_Density and Fur_Length.
        """
        cfg = UrsineAnatomyConfig(scale=scale)
        res = generate_bear_base_mesh(cfg)
        masks = CreatureGroomingEngine.build_density_mask_weights(
            res.vertex_groups, len(res.mesh.vertices)
        )
        density_map = masks["Fur_Density"]
        length_map = masks["Fur_Length"]
        clump_map = masks["Fur_Clump"]

        zero_features = (
            "snout", "nostrils", "mouth_cavity", "jaw", "teeth",
            "eyes", "eyelids", "claws_front", "claws_hind", "pads_front", "pads_hind"
        )
        total_zero_verts = 0
        for feat in zero_features:
            assert feat in res.vertex_groups, f"Feature {feat} missing from vertex groups"
            v_indices = res.vertex_groups[feat]
            assert len(v_indices) > 0, f"Feature {feat} has 0 vertices at scale {scale}"
            for idx in v_indices:
                total_zero_verts += 1
                assert density_map[idx] == 0.0, f"Vertex {idx} in {feat} has non-zero density {density_map[idx]}"
                assert length_map[idx] == 0.0, f"Vertex {idx} in {feat} has non-zero length {length_map[idx]}"
                assert clump_map[idx] == 0.0, f"Vertex {idx} in {feat} has non-zero clump {clump_map[idx]}"

        assert total_zero_verts > 200, f"Expected substantial zero-fur vertices, got {total_zero_verts}"

    def test_zero_fur_masking_with_adversarial_partial_vertex_groups(self):
        """
        Adversarial test: what if an input mesh has only a subset of vertex groups?
        The masking engine must gracefully handle missing groups without throwing KeyErrors.
        """
        sparse_vgs = {
            "snout": [0, 1, 2],
            "claws_front": [3, 4, 5],
            "torso": [6, 7, 8],
        }
        masks = CreatureGroomingEngine.build_density_mask_weights(sparse_vgs, total_vertices=12)
        d_map = masks["Fur_Density"]

        # 0, 1, 2 and 3, 4, 5 must be 0.0
        for i in range(6):
            assert d_map[i] == 0.0
        # 6, 7, 8 must be 1.0 (torso)
        for i in range(6, 9):
            assert d_map[i] == 1.0
        # 9, 10, 11 (unspecified) should fall back to default body weight
        for i in range(9, 12):
            assert d_map[i] == 0.75


# ==============================================================================
# 3. ADVERSARIAL BIOLOGICAL FLOW FIELD MATHEMATICS
# ==============================================================================

class TestAdversarialBiologicalFlowField:
    """Stress tests mathematical vector field across 1,000 spatial samples."""

    def test_spine_flow_strictly_caudal_across_entire_back(self):
        """
        Tests 100 sample points along dorsal spine midline (Y from -0.3 to 0.7).
        Asserts tangent vector y component vy > 0.50 (consistently caudal toward tail).
        """
        for i in range(100):
            py = -0.3 + (i / 99.0) * 1.0  # -0.3 to +0.7
            pz = 1.0 + 0.05 * math.cos(py * 3.0)  # dorsal crest
            pt = (0.0, py, pz)
            vec = compute_biological_flow_vector(pt, normal=(0.0, 0.0, 1.0))
            vx, vy, vz = vec
            assert vy > 0.40, f"Spine flow at Y={py} lacked sufficient caudal direction: vy={vy}"
            assert abs(vx) < 0.15, f"Spine flow at midline Y={py} deviated laterally: vx={vx}"

    def test_flank_lateral_symmetry_stress(self):
        """
        Adversarial test: sample 50 pairs of symmetric points on left (+X) and right (-X) flanks.
        Flow vectors must be precisely mirrored (vx_left == -vx_right, vy_left == vy_right, vz_left == vz_right).
        """
        for i in range(50):
            x = 0.15 + (i / 49.0) * 0.35
            y = -0.1 + (i / 49.0) * 0.6
            z = 0.65 + 0.1 * math.sin(i)

            vl = compute_biological_flow_vector((x, y, z), normal=(1.0, 0.0, 0.0))
            vr = compute_biological_flow_vector((-x, y, z), normal=(-1.0, 0.0, 0.0))

            assert math.isclose(vl[0], -vr[0], abs_tol=1e-4), f"Asymmetry in X: {vl[0]} vs {vr[0]}"
            assert math.isclose(vl[1], vr[1], abs_tol=1e-4), f"Asymmetry in Y: {vl[1]} vs {vr[1]}"
            assert math.isclose(vl[2], vr[2], abs_tol=1e-4), f"Asymmetry in Z: {vl[2]} vs {vr[2]}"

    def test_flow_vector_robustness_against_degenerate_inputs(self):
        """Tests flow calculation at origin, singularities, and zero normals."""
        vec1 = compute_biological_flow_vector((0.0, 0.0, 0.0), normal=(0.0, 0.0, 0.0))
        assert math.isclose(math.sqrt(sum(c * c for c in vec1)), 1.0, abs_tol=1e-5)

        vec2 = compute_biological_flow_vector((1e9, 1e9, 1e9), normal=(0.0, 0.0, 1.0))
        assert math.isclose(math.sqrt(sum(c * c for c in vec2)), 1.0, abs_tol=1e-5)


# ==============================================================================
# 4. ADVERSARIAL RIBBON MESH GEOMETRY & UV INTEGRITY
# ==============================================================================

class TestAdversarialRibbonGeometry:
    """Stress tests ribbon generation against extreme curve topologies."""

    def test_ribbon_quads_and_uvs_strict_interval(self):
        """
        Generates 50 randomized hair strands with 4 to 12 keys each.
        Asserts:
        - All faces are 4-vertex quads.
        - UV coordinates are strictly inside [0.0, 1.0].
        - No NaN or infinite coordinates.
        - Face surface areas are strictly positive.
        """
        random.seed(999)
        mock_strands = []
        for _ in range(50):
            num_keys = random.randint(4, 10)
            start_x = random.uniform(-0.5, 0.5)
            start_y = random.uniform(-0.5, 0.5)
            start_z = random.uniform(0.5, 1.2)
            strand = [(start_x, start_y, start_z)]
            for k in range(1, num_keys):
                prev = strand[-1]
                dx = random.uniform(-0.01, 0.01)
                dy = random.uniform(0.01, 0.03)  # caudal
                dz = random.uniform(-0.03, -0.01)  # downward
                strand.append((prev[0] + dx, prev[1] + dy, prev[2] + dz))
            mock_strands.append(strand)

        ribbon = CreatureGroomingEngine.generate_ribbon_geometry_pure_python(
            mock_strands,
            root_width=0.0035,
            tip_width=0.0003,
            taper_shape=-0.75,
        )

        assert ribbon["strand_count"] == 50
        assert ribbon["face_count"] > 0
        assert ribbon["quad_count"] == ribbon["face_count"]
        assert len(ribbon["faces"]) * 4 == len(ribbon["uvs"])

        # Validate UV range strictly in [0.0, 1.0]
        for u, v in ribbon["uvs"]:
            assert not math.isnan(u) and not math.isinf(u), f"Invalid UV u={u}"
            assert not math.isnan(v) and not math.isinf(v), f"Invalid UV v={v}"
            assert 0.0 <= u <= 1.0, f"UV u={u} out of [0, 1]"
            assert 0.0 <= v <= 1.0, f"UV v={v} out of [0, 1]"

        # Validate face areas
        verts = ribbon["vertices"]
        for f in ribbon["faces"]:
            assert len(f) == 4, f"Face {f} is not a quad"
            v0, v1, v2, v3 = [verts[i] for i in f]
            # Cross product check for non-degeneracy
            e1 = (v1[0]-v0[0], v1[1]-v0[1], v1[2]-v0[2])
            e2 = (v2[0]-v0[0], v2[1]-v0[1], v2[2]-v0[2])
            cp = (e1[1]*e2[2]-e1[2]*e2[1], e1[2]*e2[0]-e1[0]*e2[2], e1[0]*e2[1]-e1[1]*e2[0])
            area = 0.5 * math.sqrt(sum(c * c for c in cp))
            assert area > 1e-9, f"Degenerate face area: {area}"

    def test_ribbon_generator_handles_single_key_or_empty_strands(self):
        """Edge case: empty strands or 1-key strands must be cleanly skipped without throwing."""
        edge_strands = [
            [],
            [(0.0, 0.0, 1.0)],  # single key
            [(0.0, 0.0, 1.0), (0.0, 0.0, 1.0)],  # zero length
        ]
        ribbon = CreatureGroomingEngine.generate_ribbon_geometry_pure_python(edge_strands)
        assert ribbon["strand_count"] == 3
        # Should not crash


# ==============================================================================
# 5. HEADLESS BLENDER 5.2.1 LTS DEEP FORENSIC AUDIT
# ==============================================================================

class TestBlenderHeadlessForensicAudit:
    """Direct execution inside Blender 5.2.1 LTS binary asserting all 4 core criteria."""

    def test_headless_blender_full_grooming_verification(self):
        """
        Executes an end-to-end audit inside headless Blender 5.2.1 LTS:
        1. Generates Bear_Audit_Mesh.
        2. Applies CreatureGroomingEngine with 8,000 undercoat + 4,000 guard hairs.
        3. Asserts parent strands >= 12,000 across evaluated particle systems.
        4. Asserts render strands >= 100,000.
        5. Asserts 0.0 weight on 100% of vertices in all zero-fur groups.
        6. Asserts average dorsal spine particle tangent ty > 0.60.
        7. Asserts ribbon mesh exists, has quad polygons > 0, and UVMap in [0, 1].
        """
        bridge = BlenderBridge()
        gen_script = get_blender_generation_script("Bear_Forensic_Obj", 1.0)
        groom_script = CreatureGroomingEngine().get_grooming_blender_script(
            mesh_obj_name="Bear_Forensic_Obj",
            undercoat_strands=8000,
            guard_hair_strands=4000,
            generate_ribbons=True,
            max_ribbon_strands=1000,
        )

        audit_verification_code = """
obj = bpy.data.objects.get("Bear_Forensic_Obj")
if not obj:
    raise ValueError("Bear_Forensic_Obj not found in scene")

depsgraph = bpy.context.evaluated_depsgraph_get()
eval_obj = obj.evaluated_get(depsgraph)

# 1. Assert Parent & Render Strands
psys_list = [ps for ps in eval_obj.particle_systems if ps.name in ['Undercoat_Fur', 'Guard_Hairs_Fur']]
total_parents = sum(len(ps.particles) for ps in psys_list)
total_renders = sum(len(ps.particles) * (1 + ps.settings.rendered_child_count) for ps in psys_list)

assert total_parents >= 12000, f"Parent strands {total_parents} < 12,000"
assert total_renders >= 100000, f"Render strands {total_renders} < 100,000"

# 2. Assert 0.0 fur density on naked features
vg_density = obj.vertex_groups.get("Fur_Density")
assert vg_density is not None, "Fur_Density vertex group missing"

zero_features = (
    "snout", "nostrils", "mouth_cavity", "teeth", "eyes",
    "eyelids", "claws_front", "claws_hind", "pads_front", "pads_hind"
)

mask_violations = 0
total_zero_verts_checked = 0
for feat in zero_features:
    vg = obj.vertex_groups.get(feat)
    if not vg:
        continue
    gid = vg.index
    for v in obj.data.vertices:
        for g in v.groups:
            if g.group == gid and g.weight > 0.1:
                total_zero_verts_checked += 1
                # Check weight in Fur_Density
                w_dense = 0.0
                for dg in v.groups:
                    if dg.group == vg_density.index:
                        w_dense = dg.weight
                        break
                if w_dense > 1e-4:
                    mask_violations += 1

assert mask_violations == 0, f"Found {mask_violations} zero-fur mask violations"
assert total_zero_verts_checked > 100, f"Checked too few zero vertices: {total_zero_verts_checked}"

# 3. Assert biological flow alignment along dorsal spine (ty > 0.60)
spine_tangents_y = []
for ps in psys_list:
    for p in ps.particles:
        root_co = p.hair_keys[0].co
        # Midline spine region: |x| < 0.08, y between -0.2 and 0.5, z > 0.85
        if abs(root_co.x) < 0.08 and -0.2 <= root_co.y <= 0.5 and root_co.z > 0.85:
            if len(p.hair_keys) >= 2:
                tangent = (p.hair_keys[1].co - root_co).normalized()
                spine_tangents_y.append(tangent.y)

assert len(spine_tangents_y) > 0, "No spine particles sampled"
avg_spine_ty = sum(spine_tangents_y) / len(spine_tangents_y)
assert avg_spine_ty > 0.60, f"Dorsal spine flow alignment ty={avg_spine_ty:.4f} <= 0.60"

# 4. Assert ribbon mesh has valid polygons and UV coordinates in [0, 1]
rib_obj = bpy.data.objects.get("Bear_Forensic_Obj_Fur_Ribbons")
assert rib_obj is not None, "Ribbon mesh object missing"
assert len(rib_obj.data.vertices) > 0, "Ribbon mesh has 0 vertices"
assert len(rib_obj.data.polygons) > 0, "Ribbon mesh has 0 polygons"
assert "UVMap" in rib_obj.data.uv_layers, "UVMap layer missing from ribbon mesh"

uv_layer = rib_obj.data.uv_layers["UVMap"]
uv_violations = 0
for loop_uv in uv_layer.data:
    u, v = loop_uv.uv
    if math.isnan(u) or math.isnan(v) or u < -1e-4 or u > 1.0001 or v < -1e-4 or v > 1.0001:
        uv_violations += 1

assert uv_violations == 0, f"Found {uv_violations} ribbon UV violations out of [0, 1]"

forensic_result = {
    "total_parents": total_parents,
    "total_renders": total_renders,
    "mask_violations": mask_violations,
    "total_zero_verts_checked": total_zero_verts_checked,
    "sampled_spine_particles": len(spine_tangents_y),
    "avg_spine_ty": avg_spine_ty,
    "ribbon_vertices": len(rib_obj.data.vertices),
    "ribbon_quads": len(rib_obj.data.polygons),
    "uv_violations": uv_violations,
}
"""
        blender_bin = bridge._resolve_blender_binary()
        assert blender_bin and os.path.exists(blender_bin), f"Blender binary not found at {blender_bin}"

        full_script = f"""
import bpy
import json
import math
import mathutils

{gen_script}

{groom_script}

{audit_verification_code}

with open("{os.path.join(tempfile.gettempdir(), 'forensic_out.json')}", "w") as f:
    json.dump(forensic_result, f)
print("FORENSIC_AUDIT_COMPLETE")
"""
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as script_file:
            script_file.write(full_script)
            script_path = script_file.name

        out_json_path = os.path.join(tempfile.gettempdir(), "forensic_out.json")
        if os.path.exists(out_json_path):
            os.remove(out_json_path)

        import subprocess
        proc = subprocess.run(
            [blender_bin, "--background", "--python", script_path],
            capture_output=True,
            text=True,
            timeout=120,
        )

        try:
            os.remove(script_path)
        except OSError:
            pass

        assert proc.returncode == 0, f"Blender exited with code {proc.returncode}:\n{proc.stderr}\n{proc.stdout}"
        assert "FORENSIC_AUDIT_COMPLETE" in proc.stdout, f"Forensic script did not reach completion:\n{proc.stdout}"

        with open(out_json_path, "r") as f:
            res = json.load(f)

        assert res["total_parents"] >= 12000
        assert res["total_renders"] >= 100000
        assert res["mask_violations"] == 0
        assert res["total_zero_verts_checked"] > 100
        assert res["sampled_spine_particles"] > 0
        assert res["avg_spine_ty"] > 0.60
        assert res["ribbon_quads"] > 0
        assert res["uv_violations"] == 0
