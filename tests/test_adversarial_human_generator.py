"""
Adversarial Stress Test Suite for MorphoMesh Human Geometry Generator.
Authored by: challenger_human_m1_1 (Empirical Challenger)

Stress-tests:
1. Boundary parameter ranges: heights [0.5m, 3.0m], head_ratio [4.0, 10.0], waist_girth [0.3m, 1.5m], styles.
2. Parametric responsiveness: whether config parameters actually affect mesh geometry or are silently ignored.
3. True topological quad percentage: empirical quad count vs hardcoded 0.965 claim.
4. Mesh topology integrity: zero-area faces, non-manifold edges, boundary edges (open holes/watertightness).
5. Numerical stability: NaN and Inf detection across vertices, normals, UVs, and shape keys.
6. Landmark consistency and pre-bend angles across boundary configurations.
7. Parity between Python generator (generate_human_base_mesh) and Blender generator script (get_human_generation_script).
"""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from typing import Dict, List, Set, Tuple

import pytest
from pydantic import ValidationError

from morphomesh.human_generator import (
    ARKIT_52_BLENDSHAPES,
    STANDARDIZED_HUMAN_VERTEX_GROUPS,
    HumanAnatomyConfig,
    HumanAnatomyGenerator,
    HumanMeshResult,
    generate_human_base_mesh,
    get_human_generation_script,
)
from morphomesh.inference_adapter import MeshGeometry


# ==============================================================================
# HELPER FUNCTIONS FOR EMPIRICAL GEOMETRY ANALYSIS
# ==============================================================================

def compute_face_areas(mesh: MeshGeometry) -> List[float]:
    """Calculates individual face areas for all triangular faces."""
    verts = mesh.vertices
    areas = []
    for face in mesh.faces:
        p0 = verts[face[0]]
        p1 = verts[face[1]]
        p2 = verts[face[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        cx = v1[1] * v2[2] - v1[2] * v2[1]
        cy = v1[2] * v2[0] - v1[0] * v2[2]
        cz = v1[0] * v2[1] - v1[1] * v2[0]
        area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
        areas.append(area)
    return areas


def analyze_manifoldness(mesh: MeshGeometry) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
    """
    Analyzes mesh edges.
    Returns: (non_manifold_edges, boundary_edges)
    - non_manifold_edges: edges shared by > 2 faces.
    - boundary_edges: edges shared by exactly 1 face (open hole boundaries / unstitched seams).
    """
    edge_counts: Dict[Tuple[int, int], int] = {}
    for face in mesh.faces:
        n = len(face)
        for j in range(n):
            v_a = face[j]
            v_b = face[(j + 1) % n]
            edge = (min(v_a, v_b), max(v_a, v_b))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    non_manifold = [e for e, count in edge_counts.items() if count > 2]
    boundary = [e for e, count in edge_counts.items() if count == 1]
    return non_manifold, boundary


def calculate_actual_quad_metrics(mesh: MeshGeometry) -> Dict[str, float]:
    """
    Calculates actual quad metrics by analyzing pairs of consecutive triangles
    sharing an edge and common vertex winding from add_quad(i0, i1, i2, i3).
    """
    faces = mesh.faces
    total_tris = len(faces)

    quad_count = 0
    tri_count = 0
    i = 0
    while i < total_tris:
        if i + 1 < total_tris:
            f1 = faces[i]
            f2 = faces[i + 1]
            if f1[0] == f2[0] and f1[2] == f2[1]:
                quad_count += 1
                i += 2
                continue
        tri_count += 1
        i += 1

    total_polys = quad_count + tri_count
    quad_ratio = quad_count / total_polys if total_polys > 0 else 0.0

    return {
        "total_triangles": total_tris,
        "reconstructed_quads": quad_count,
        "isolated_triangles": tri_count,
        "total_polygons": total_polys,
        "actual_quad_ratio": quad_ratio,
    }


def compute_pre_bend_angle(a: Tuple[float, float, float], b: Tuple[float, float, float], c: Tuple[float, float, float]) -> float:
    """Computes interior angle at joint b between segments ba and bc in degrees."""
    v_ba = (a[0] - b[0], a[1] - b[1], a[2] - b[2])
    v_bc = (c[0] - b[0], c[1] - b[1], c[2] - b[2])
    dot = v_ba[0] * v_bc[0] + v_ba[1] * v_bc[1] + v_ba[2] * v_bc[2]
    len_ba = math.sqrt(v_ba[0] ** 2 + v_ba[1] ** 2 + v_ba[2] ** 2)
    len_bc = math.sqrt(v_bc[0] ** 2 + v_bc[1] ** 2 + v_bc[2] ** 2)
    if len_ba < 1e-8 or len_bc < 1e-8:
        return 0.0
    cos_ang = max(-1.0, min(1.0, dot / (len_ba * len_bc)))
    return math.degrees(math.acos(cos_ang))


# ==============================================================================
# 1. BOUNDARY PARAMETERS & PYDANTIC VALIDATION CHALLENGE
# ==============================================================================

class TestBoundaryParametersAndValidation:
    """Adversarially tests boundary parameters specified in assignment."""

    def test_height_boundary_pydantic_enforcement(self):
        """
        Assignment specifies testing heights [0.5m, 3.0m].
        Empirical check: HumanAnatomyConfig schema specifies ge=1.0, le=2.5.
        Thus heights 0.5m and 3.0m raise ValidationError.
        """
        # Height 0.5m should raise ValidationError
        with pytest.raises(ValidationError) as exc_05:
            HumanAnatomyConfig(height=0.5)
        assert "greater than or equal to 1" in str(exc_05.value)

        # Height 3.0m should raise ValidationError
        with pytest.raises(ValidationError) as exc_30:
            HumanAnatomyConfig(height=3.0)
        assert "less than or equal to 2.5" in str(exc_30.value)

        # Valid boundaries 1.0m and 2.5m should succeed
        cfg_min = HumanAnatomyConfig(height=1.0)
        assert cfg_min.height == 1.0
        cfg_max = HumanAnatomyConfig(height=2.5)
        assert cfg_max.height == 2.5

    def test_head_ratio_boundary_pydantic_enforcement(self):
        """
        Assignment specifies head_ratio [4.0, 10.0].
        HumanAnatomyConfig specifies ge=5.0, le=10.0.
        head_ratio=4.0 raises ValidationError.
        head_ratio=10.0 is accepted.
        """
        with pytest.raises(ValidationError) as exc_4:
            HumanAnatomyConfig(head_ratio=4.0)
        assert "greater than or equal to 5" in str(exc_4.value)

        cfg_10 = HumanAnatomyConfig(head_ratio=10.0)
        assert cfg_10.head_ratio == 10.0

    def test_waist_girth_boundary_pydantic_enforcement(self):
        """
        Assignment specifies waist_girth [0.3m, 1.5m].
        HumanAnatomyConfig specifies ge=0.4, le=1.2.
        waist_girth 0.3m and 1.5m raise ValidationError.
        """
        with pytest.raises(ValidationError) as exc_03:
            HumanAnatomyConfig(waist_girth=0.3)
        assert "greater than or equal to 0.4" in str(exc_03.value)

        with pytest.raises(ValidationError) as exc_15:
            HumanAnatomyConfig(waist_girth=1.5)
        assert "less than or equal to 1.2" in str(exc_15.value)


# ==============================================================================
# 2. PARAMETRIC RESPONSIVENESS (SILENT PARAMETER IGNORING BUG)
# ==============================================================================

class TestParametricResponsiveness:
    """
    Adversarially verifies that HumanAnatomyGenerator responds to config fields
    with real geometric changes rather than ignoring them or hardcoding values.
    """

    def test_head_ratio_is_applied_correctly(self):
        """
        Verify that when head_ratio is changed from 5.0 to 10.0 in HumanAnatomyConfig,
        the generator updates head dimensions proportionally and returns matching ratios.
        """
        cfg_5 = HumanAnatomyConfig(head_ratio=5.0)
        cfg_10 = HumanAnatomyConfig(head_ratio=10.0)

        res_5 = generate_human_base_mesh(cfg_5)
        res_10 = generate_human_base_mesh(cfg_10)

        assert res_5.head_ratio == 5.0
        assert res_10.head_ratio == 10.0

        # Empirical head dimension (crown Z - chin Z) changes with head_ratio
        head_h_5 = res_5.landmarks["head_top"][2] - res_5.landmarks["chin"][2]
        head_h_10 = res_10.landmarks["head_top"][2] - res_10.landmarks["chin"][2]
        assert head_h_5 > head_h_10, "Head height for ratio 5.0 must be taller than for ratio 10.0"
        assert abs(head_h_5 - head_h_10) > 0.05, "Head height must respond significantly to head_ratio!"

    def test_waist_girth_modifies_geometry(self):
        """
        Verify that when waist_girth is varied from 0.40m to 1.20m, the generated
        mesh vertices in the waist ring respond with genuine radial expansion.
        """
        cfg_slim = HumanAnatomyConfig(waist_girth=0.40)
        cfg_wide = HumanAnatomyConfig(waist_girth=1.20)

        res_slim = generate_human_base_mesh(cfg_slim)
        res_wide = generate_human_base_mesh(cfg_wide)

        waist_verts_slim = [res_slim.mesh.vertices[idx] for idx in res_slim.vertex_groups["waist"]]
        waist_verts_wide = [res_wide.mesh.vertices[idx] for idx in res_wide.vertex_groups["waist"]]

        diffs = [
            math.sqrt((s[0] - w[0]) ** 2 + (s[1] - w[1]) ** 2 + (s[2] - w[2]) ** 2)
            for s, w in zip(waist_verts_slim, waist_verts_wide)
        ]
        max_diff = max(diffs)
        assert max_diff > 0.05, f"Waist girth had insufficient effect on vertices (max_diff={max_diff})!"

    def test_chest_and_hip_girth_modify_geometry(self):
        """
        Verify that chest_girth, hip_girth, shoulder_width, leg_length, arm_span
        produce genuine geometric modifications across the generated mesh.
        """
        cfg_1 = HumanAnatomyConfig(chest_girth=0.5, hip_girth=0.5, shoulder_width=0.2, style="stylized")
        cfg_2 = HumanAnatomyConfig(chest_girth=1.5, hip_girth=1.5, shoulder_width=0.8, style="realistic")

        res_1 = generate_human_base_mesh(cfg_1)
        res_2 = generate_human_base_mesh(cfg_2)

        v1 = res_1.mesh.vertices
        v2 = res_2.mesh.vertices
        assert len(v1) == len(v2)
        diff = max(math.sqrt((a[0] - b[0])**2 + (a[1] - b[1])**2 + (a[2] - b[2])**2) for a, b in zip(v1, v2))
        assert diff > 0.05, f"Mesh vertices must respond to chest/hip/shoulder configs (diff={diff})!"


# ==============================================================================
# 3. TOPOLOGICAL QUAD PERCENTAGE: HARDCODED 0.965 VS EMPIRICAL REALITY
# ==============================================================================

class TestQuadPercentageEmpiricalReality:
    """
    Adversarially tests quad dominance and verifies authentic dynamic >=95% quad ratio.
    """

    def test_empirical_quad_percentage_meets_95_percent(self):
        """
        Empirical measurement of quad dominance dynamically computed.
        """
        res = generate_human_base_mesh()
        metrics = calculate_actual_quad_metrics(res.mesh)

        actual_quad_ratio = metrics["actual_quad_ratio"]
        claimed_quad_ratio = res.quad_ratio

        assert claimed_quad_ratio >= 0.95
        assert actual_quad_ratio >= 0.95, (
            f"Actual quad ratio {actual_quad_ratio:.2%} must meet >= 95.0% threshold"
        )
        assert claimed_quad_ratio == actual_quad_ratio

    def test_isolated_triangle_count_in_digits(self):
        """
        Verify pure quad topologies across digits, oral cavity, crown cap, and feet.
        """
        res = generate_human_base_mesh()
        metrics = calculate_actual_quad_metrics(res.mesh)

        assert metrics["isolated_triangles"] == 0
        assert metrics["reconstructed_quads"] > 0
        assert metrics["actual_quad_ratio"] == 1.0


# ==============================================================================
# 4. ZERO-AREA FACES, NON-MANIFOLD EDGES, AND OPEN BOUNDARY HOLES
# ==============================================================================

class TestTopologyManifoldnessAndWatertightness:
    """
    Stress-tests degenerate faces, non-manifold edges, and open boundary edges.
    """

    @pytest.mark.parametrize("h", [0.5, 1.0, 1.65, 2.5, 3.0])
    def test_zero_area_faces_across_heights(self, h: float):
        """Verify that no zero-area faces exist across extreme scale heights."""
        cfg = HumanAnatomyConfig.model_construct(height=h)
        gen = HumanAnatomyGenerator(cfg)
        res = gen.generate()

        areas = compute_face_areas(res.mesh)
        assert len(areas) > 0
        min_area = min(areas)
        assert min_area > 0.0, f"Found zero-area face with area {min_area} at height {h}"
        assert not any(math.isnan(a) for a in areas)

    @pytest.mark.parametrize("h", [0.5, 1.0, 1.65, 2.5, 3.0])
    def test_non_manifold_edges_are_zero(self, h: float):
        """Verify 0 non-manifold edges (edges with > 2 incident faces)."""
        cfg = HumanAnatomyConfig.model_construct(height=h)
        gen = HumanAnatomyGenerator(cfg)
        res = gen.generate()

        non_manifold, _ = analyze_manifoldness(res.mesh)
        assert len(non_manifold) == 0, f"Found {len(non_manifold)} non-manifold edges at height {h}"

    def test_mesh_is_watertight_closed_manifold(self):
        """
        Verify that the generator produces a closed 2-manifold surface with 0 boundary edges.
        """
        res = generate_human_base_mesh()
        _, boundary_edges = analyze_manifoldness(res.mesh)

        assert len(boundary_edges) == 0, (
            f"Expected 0 open boundary edges on watertight mesh, found {len(boundary_edges)}"
        )


# ==============================================================================
# 5. NUMERICAL STABILITY: NANS, INFS, BOUNDING BOXES
# ==============================================================================

class TestNumericalStability:
    """Stress-tests coordinates, normals, UVs, and shape keys for NaNs/Infs."""

    @pytest.mark.parametrize("h", [0.5, 1.0, 1.65, 2.5, 3.0])
    def test_no_nans_or_infs_in_mesh_attributes(self, h: float):
        """Verify 0 NaNs or Infs in vertices, normals, and UVs."""
        cfg = HumanAnatomyConfig.model_construct(height=h)
        gen = HumanAnatomyGenerator(cfg)
        res = gen.generate()

        mesh = res.mesh
        for i, v in enumerate(mesh.vertices):
            assert not any(math.isnan(c) or math.isinf(c) for c in v), f"NaN/Inf in vertex {i}: {v}"

        for i, n in enumerate(mesh.normals):
            assert not any(math.isnan(c) or math.isinf(c) for c in n), f"NaN/Inf in normal {i}: {n}"

        for i, uv in enumerate(mesh.uvs):
            assert not any(math.isnan(c) or math.isinf(c) for c in uv), f"NaN/Inf in UV {i}: {uv}"

    def test_shape_key_deltas_numerical_stability(self):
        """Verify no NaNs or Infs across all 52 ARKit FACS blendshapes."""
        res = generate_human_base_mesh()
        for sk_name, deltas in res.shape_key_deltas.items():
            for v_idx, delta in deltas.items():
                assert not any(math.isnan(c) or math.isinf(c) for c in delta), (
                    f"NaN/Inf in shape key '{sk_name}' delta for vertex {v_idx}: {delta}"
                )


# ==============================================================================
# 6. LANDMARK CONSISTENCY & JOINT PRE-BEND ANGLES
# ==============================================================================

class TestLandmarkConsistencyAndPreBends:
    """Stress-tests landmark positions and pre-bend angles across boundary configurations."""

    @pytest.mark.parametrize("h", [0.5, 1.0, 1.65, 2.5, 3.0])
    def test_pre_bend_angles_remain_consistent(self, h: float):
        """
        Verify elbow and knee pre-bend angles.
        Elbow angle (shoulder -> elbow -> wrist): interior angle < 180 degrees.
        Knee angle (hip -> knee -> ankle): interior angle < 180 degrees.
        """
        cfg = HumanAnatomyConfig.model_construct(height=h)
        gen = HumanAnatomyGenerator(cfg)
        res = gen.generate()
        lm = res.landmarks

        # Left Elbow
        ang_elbow_L = compute_pre_bend_angle(lm["shoulder_L"], lm["elbow_L"], lm["wrist_L"])
        # Right Elbow
        ang_elbow_R = compute_pre_bend_angle(lm["shoulder_R"], lm["elbow_R"], lm["wrist_R"])
        assert 140.0 < ang_elbow_L < 179.0, f"Elbow L angle abnormal: {ang_elbow_L:.2f} deg"
        assert 140.0 < ang_elbow_R < 179.0, f"Elbow R angle abnormal: {ang_elbow_R:.2f} deg"
        assert abs(ang_elbow_L - ang_elbow_R) < 1e-4

        # Left Knee
        ang_knee_L = compute_pre_bend_angle(lm["hip_L"], lm["knee_L"], lm["ankle_L"])
        # Right Knee
        ang_knee_R = compute_pre_bend_angle(lm["hip_R"], lm["knee_R"], lm["ankle_R"])
        assert 160.0 < ang_knee_L < 179.5, f"Knee L angle abnormal: {ang_knee_L:.2f} deg"
        assert 160.0 < ang_knee_R < 179.5, f"Knee R angle abnormal: {ang_knee_R:.2f} deg"
        assert abs(ang_knee_L - ang_knee_R) < 1e-4


# ==============================================================================
# 7. PYTHON GENERATOR VS BLENDER SCRIPT PARITY (CRITICAL BUG)
# ==============================================================================

class TestBlenderScriptGenerationParity:
    """
    Verifies 100% parity between Python generator and Blender generation script.
    """

    def test_blender_script_includes_limbs_and_digits(self):
        """Verify that get_human_generation_script generates limbs, hands, fingers, and feet."""
        script = get_human_generation_script("Test_Mesh", HumanAnatomyConfig())

        # The script creates vertex groups for limbs and fingers
        assert '"arm_upper_L"' in script
        assert '"leg_upper_L"' in script
        assert '"fingers_L"' in script

        assert "body_slices = [" in script
        assert "leg_slices" in script, "leg_slices must be in Blender generation script"
        assert "arm_slices" in script, "arm_slices must be in Blender generation script"
        assert "finger_configs" in script, "finger_configs must be in Blender generation script"
        assert "tarsus_verts" in script or "tarsus_indices" in script, "tarsus must be in Blender generation script"

    def test_blender_headless_audit_confirms_full_body_and_zero_empty_groups(self):
        """
        Executes get_human_generation_script() inside Blender 4.5.4 LTS headless:
        Verifies that Blender mesh generates the complete body (>1500 vertices)
        and 0 vertex groups are empty.
        """
        blender_exe = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
        if not os.path.exists(blender_exe):
            pytest.skip("Blender 4.5 executable not found on host.")

        audit_snippet = """
import bpy
obj = bpy.data.objects.get('Human_Base_Mesh')
assert obj is not None, 'Object Human_Base_Mesh not found'
vert_count = len(obj.data.vertices)
poly_count = len(obj.data.polygons)

empty_groups = []
for vg in obj.vertex_groups:
    cnt = sum(1 for v in obj.data.vertices if any(g.group == vg.index for g in v.groups))
    if cnt == 0:
        empty_groups.append(vg.name)

print(f"AUDIT_RESULT: verts={vert_count}, polys={poly_count}, empty_count={len(empty_groups)}")
print(f"EMPTY_GROUPS: {empty_groups}")
"""
        script = get_human_generation_script("Human_Base_Mesh", HumanAnatomyConfig()) + audit_snippet

        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as f:
            f.write(script)
            tmp_path = f.name

        try:
            proc = subprocess.run(
                [blender_exe, "--background", "--factory-startup", "--python", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            stdout = proc.stdout
            assert "empty_count=0" in stdout, f"Expected 0 empty groups, output:\n{stdout}"
            import re
            m = re.search(r"verts=(\d+)", stdout)
            assert m and int(m.group(1)) > 1500, f"Expected > 1500 vertices, got: {stdout}"
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
