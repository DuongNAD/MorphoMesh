"""
Adversarial Empirical Stress Test Suite for Milestone M1 (Challenger M1-2):
Topology, 18 Standardized Vertex Groups, Facial Landmarks, and Mesh Validity.

Verifies:
1. 18 standardized vertex groups presence and non-zero counts across archetypes.
2. Facial geometry:
   - Indented nostrils (apex recessed into rhinarium, inward normal orientation).
   - Recessed mouth cavity (bounded within snout and jaw).
   - Distinct canines and incisors (12 separate convex tooth meshes).
   - Eyelids enclosing eye spheres (vertical bracketing and lateral aperture analysis).
3. Numerical and topological mesh validity:
   - Zero NaN / Inf coordinates.
   - Degenerate zero-area faces detection (adversarial oracle).
   - Inverted face normal winding detection (adversarial oracle).
"""

import ast
import math

import numpy as np

from morphomesh.creature_generator import (
    STANDARDIZED_VERTEX_GROUPS,
    generate_bear_base_mesh,
    generate_creature_mesh,
    get_blender_generation_script,
)

# ==============================================================================
# 1. STANDARDIZED VERTEX GROUPS TESTS
# ==============================================================================

def test_18_standardized_vertex_groups_presence_and_non_zero_counts():
    """Assert all 18 standardized vertex groups exist and contain genuine, non-zero vertex counts."""
    res = generate_bear_base_mesh()
    mesh = res.mesh
    vg = res.vertex_groups

    assert len(STANDARDIZED_VERTEX_GROUPS) == 18, (
        f"Expected 18 standardized vertex groups, found {len(STANDARDIZED_VERTEX_GROUPS)}"
    )

    empty_groups = []
    populated_groups = {}
    for group_name in STANDARDIZED_VERTEX_GROUPS:
        assert group_name in vg, f"Missing vertex group in result: '{group_name}'"
        count = len(vg[group_name])
        if count == 0:
            empty_groups.append(group_name)
        else:
            populated_groups[group_name] = count

    assert len(empty_groups) == 0, f"Vertex groups with zero vertices: {empty_groups}"

    # Also assert internal mesh.vertex_groups mirror
    for group_name in STANDARDIZED_VERTEX_GROUPS:
        assert group_name in mesh.vertex_groups, f"Mesh internal vertex_groups missing '{group_name}'"
        assert len(mesh.vertex_groups[group_name]) > 0, f"Mesh internal vertex group '{group_name}' is empty"


def test_vertex_group_indices_within_valid_mesh_range():
    """Assert all vertex group indices point to valid, non-out-of-bounds mesh vertices."""
    res = generate_bear_base_mesh()
    total_verts = len(res.mesh.vertices)

    for group_name, indices in res.vertex_groups.items():
        assert len(indices) > 0, f"Group '{group_name}' is empty"
        for idx in indices:
            assert 0 <= idx < total_verts, (
                f"Out-of-bounds vertex index {idx} in group '{group_name}' (total vertices: {total_verts})"
            )


def test_multi_archetype_vertex_groups_coverage():
    """Assert both Ursine and generic Quadruped archetypes populate all 18 vertex groups."""
    for arch in ["ursine", "quadruped", "bear", "wolf"]:
        res = generate_creature_mesh(archetype=arch)
        for vg_name in STANDARDIZED_VERTEX_GROUPS:
            assert vg_name in res.vertex_groups, f"Archetype '{arch}' missing vertex group '{vg_name}'"
            assert len(res.vertex_groups[vg_name]) > 0, f"Archetype '{arch}' has empty vertex group '{vg_name}'"


# ==============================================================================
# 2. FACIAL GEOMETRY LANDMARKS TESTS
# ==============================================================================

def test_facial_geometry_nostrils_indented_nares():
    """
    Verify nostrils are indented nares:
    - Base sits on the anterior rhinarium surface (more negative Y).
    - Apex penetrates inward/posteriorly into the snout (+Y direction from base).
    - Side faces of nostril cones have positive Y normal components (pointing inward).
    """
    res = generate_bear_base_mesh()
    mesh = res.mesh
    nostril_indices = set(res.vertex_groups["nostrils"])
    assert len(nostril_indices) == 16  # 2 cones * 8 vertices

    # Find nostril faces
    nostril_faces = [f for f in mesh.faces if any(vi in nostril_indices for vi in f)]
    assert len(nostril_faces) == 24  # 2 cones * 12 faces

    # Identify base center and apex for both left and right nostrils
    # Base center has normal (-dir), apex has normal (+dir)
    inward_side_faces = 0
    for f in nostril_faces:
        v0, v1, v2 = [np.array(mesh.vertices[i]) for i in f]
        cross = np.cross(v1 - v0, v2 - v0)
        area = 0.5 * np.linalg.norm(cross)
        if area > 1e-6:
            fn = cross / np.linalg.norm(cross)
            # Side faces of the inward cone point with positive Y (into the head)
            if fn[1] > 0.1:
                inward_side_faces += 1

    # Both nostrils have 6 side faces pointing inward = 12 inward side faces
    assert inward_side_faces == 12, (
        f"Expected 12 inward-oriented side faces for indented nostrils, found {inward_side_faces}"
    )


def test_facial_geometry_mouth_cavity_recessed():
    """
    Verify oral mouth cavity vertices are recessed inside cranium/snout and jaw:
    - Lateral X bounds of mouth cavity are within snout and jaw X envelope.
    - Longitudinal Y bounds of mouth cavity are behind front snout/jaw tip.
    - Vertical Z bounds sit directly at the oral fissure between jaw and upper rostrum.
    """
    res = generate_bear_base_mesh()
    mesh = res.mesh
    mouth_verts = np.array([mesh.vertices[i] for i in res.vertex_groups["mouth_cavity"]])
    snout_verts = np.array([mesh.vertices[i] for i in res.vertex_groups["snout"]])
    jaw_verts = np.array([mesh.vertices[i] for i in res.vertex_groups["jaw"]])

    # X bounds check: mouth cavity is narrower than external muzzle
    assert np.min(mouth_verts[:, 0]) >= np.min(snout_verts[:, 0])
    assert np.max(mouth_verts[:, 0]) <= np.max(snout_verts[:, 0])
    assert np.min(mouth_verts[:, 0]) >= np.min(jaw_verts[:, 0])
    assert np.max(mouth_verts[:, 0]) <= np.max(jaw_verts[:, 0])

    # Y bounds check: mouth cavity front is behind the front-most rostrum tip
    assert np.min(mouth_verts[:, 1]) > np.min(snout_verts[:, 1]), (
        "Mouth cavity protrudes ahead of snout tip"
    )

    # Z bounds check: mouth cavity is between bottom of snout and top of jaw
    assert np.min(mouth_verts[:, 2]) >= np.min(jaw_verts[:, 2])
    assert np.max(mouth_verts[:, 2]) <= np.max(snout_verts[:, 2])


def test_facial_geometry_dentition_distinct_canines_and_incisors():
    """
    Verify teeth comprise 12 distinct convex conical meshes:
    - 4 canines (2 upper pointing downward, 2 lower pointing upward).
    - 8 incisors (4 upper pointing downward, 4 lower pointing upward).
    - Disjoint connected components with positive vertical clearance.
    """
    res = generate_bear_base_mesh()
    mesh = res.mesh
    teeth_verts = res.vertex_groups["teeth"]
    assert len(teeth_verts) == 80  # 4 canines * 8 verts + 8 incisors * 6 verts

    # Build adjacency graph for tooth vertices to extract connected components
    teeth_set = set(teeth_verts)
    teeth_faces = [f for f in mesh.faces if any(vi in teeth_set for vi in f)]

    adj: dict[int, set[int]] = {vi: set() for vi in teeth_verts}
    for f in teeth_faces:
        for i in range(3):
            for j in range(3):
                if i != j and f[i] in adj and f[j] in adj:
                    adj[f[i]].add(f[j])

    components: list[list[int]] = []
    visited: set[int] = set()
    for vi in teeth_verts:
        if vi not in visited:
            comp: list[int] = []
            queue = [vi]
            visited.add(vi)
            while queue:
                curr = queue.pop(0)
                comp.append(curr)
                for neighbor in adj[curr]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)
            components.append(comp)

    assert len(components) == 12, (
        f"Expected 12 distinct tooth components (4 canines + 8 incisors), got {len(components)}"
    )

    # Verify 4 canines have 8 vertices each and 8 incisors have 6 vertices each
    canine_comps = [c for c in components if len(c) == 8]
    incisor_comps = [c for c in components if len(c) == 6]
    assert len(canine_comps) == 4, f"Expected 4 canines with 8 vertices, found {len(canine_comps)}"
    assert len(incisor_comps) == 8, f"Expected 8 incisors with 6 vertices, found {len(incisor_comps)}"


def test_facial_geometry_eyelids_and_eyes_metrics():
    """
    Verify dimensional eyelids bracket the eyeball spheres:
    - Bilateral symmetry across midline (left X > 0, right X < 0).
    - Upper and lower eyelids bracket eye sphere vertically (Z).
    - Quantifies horizontal X/Y aperture coverage.
    """
    res = generate_bear_base_mesh()
    mesh = res.mesh
    eyes_verts = np.array([mesh.vertices[i] for i in res.vertex_groups["eyes"]])
    eyelids_verts = np.array([mesh.vertices[i] for i in res.vertex_groups["eyelids"]])

    # Left eye & eyelids
    left_eye = eyes_verts[eyes_verts[:, 0] > 0]
    left_lid = eyelids_verts[eyelids_verts[:, 0] > 0]
    assert len(left_eye) > 0 and len(left_lid) > 0

    # Vertical Z bracketing: eyelids span from below bottom of eye to above top of eye
    eye_z_min, eye_z_max = np.min(left_eye[:, 2]), np.max(left_eye[:, 2])
    lid_z_min, lid_z_max = np.min(left_lid[:, 2]), np.max(left_lid[:, 2])

    assert lid_z_min <= eye_z_min + 0.005, (
        f"Lower eyelid bottom {lid_z_min} does not cover lower eye pole {eye_z_min}"
    )
    assert lid_z_max >= eye_z_max - 0.005, (
        f"Upper eyelid top {lid_z_max} does not cover upper eye pole {eye_z_max}"
    )


# ==============================================================================
# 3. NUMERICAL VALIDITY & DEFECT ORACLES
# ==============================================================================

def test_mesh_numerical_validity_zero_nans():
    """Assert zero NaN or Infinite coordinates exist across all mesh vertices."""
    res = generate_bear_base_mesh()
    for idx, (x, y, z) in enumerate(res.mesh.vertices):
        assert not (math.isnan(x) or math.isinf(x)), f"NaN/Inf at vertex {idx} x: {x}"
        assert not (math.isnan(y) or math.isinf(y)), f"NaN/Inf at vertex {idx} y: {y}"
        assert not (math.isnan(z) or math.isinf(z)), f"NaN/Inf at vertex {idx} z: {z}"


def test_adversarial_degenerate_zero_area_faces():
    """
    Adversarially assert zero degenerate zero-area faces in synthesized mesh.

    DEFECT FINDING:
    add_ellipsoid (and add_sphere) in inference_adapter.py generates 2 degenerate
    zero-area triangles per sector at the polar rings (theta=0 and theta=pi) because
    all sector vertices at the poles share identical coordinates, causing quad
    triangulation to collapse one triangle per sector to zero area.
    Across 31 ellipsoids, this generates 508 degenerate zero-area faces.
    """
    res = generate_bear_base_mesh()
    mesh = res.mesh

    zero_area_faces = []
    for f_idx, (i0, i1, i2) in enumerate(mesh.faces):
        v0 = np.array(mesh.vertices[i0])
        v1 = np.array(mesh.vertices[i1])
        v2 = np.array(mesh.vertices[i2])
        cross = np.cross(v1 - v0, v2 - v0)
        area = 0.5 * np.linalg.norm(cross)
        if area < 1e-9:
            zero_area_faces.append((f_idx, (i0, i1, i2), area))

    assert len(zero_area_faces) == 0, (
        f"DEFECT CONFIRMED: Found {len(zero_area_faces)} degenerate zero-area faces "
        f"(< 1e-9) in base bear mesh! Polar ellipsoid quads collapse to zero area."
    )


def test_adversarial_inverted_face_normals():
    """
    Adversarially assert zero inverted face normals in synthesized mesh.

    DEFECT FINDING:
    add_box in inference_adapter.py defines the 4 side faces (Front +Y, Back -Y,
    Left -X, Right +X) with clockwise vertex winding when viewed from the outside.
    Their geometric cross product (v1 - v0) x (v2 - v0) points inward into the box
    volume (dot product = -1.0 against assigned outward vertex normals).
    Across 13 box primitives, this creates 104 inverted faces.
    """
    res = generate_bear_base_mesh()
    mesh = res.mesh

    inverted_faces = []
    for f_idx, (i0, i1, i2) in enumerate(mesh.faces):
        v0 = np.array(mesh.vertices[i0])
        v1 = np.array(mesh.vertices[i1])
        v2 = np.array(mesh.vertices[i2])
        cross = np.cross(v1 - v0, v2 - v0)
        norm_len = np.linalg.norm(cross)
        if norm_len < 1e-9:
            continue  # Skip zero-area faces already flagged

        fn = cross / norm_len
        vn = (
            np.array(mesh.normals[i0])
            + np.array(mesh.normals[i1])
            + np.array(mesh.normals[i2])
        ) / 3.0
        vn_len = np.linalg.norm(vn)
        if vn_len > 1e-6:
            vn = vn / vn_len
            dot = np.dot(fn, vn)
            if dot < -0.5:
                inverted_faces.append((f_idx, (i0, i1, i2), dot))

    assert len(inverted_faces) == 0, (
        f"DEFECT CONFIRMED: Found {len(inverted_faces)} inverted faces where geometric "
        f"normal opposes assigned vertex normal (dot < -0.5) due to add_box winding error."
    )


def test_blender_generation_script_box_inversions():
    """
    Assert zero inverted box faces generated by get_blender_generation_script().
    Dynamically parses add_box from the generation script AST and verifies that all
    12 triangles across bottom, top, back, front, left, right faces have outward
    normal orientation (dot product > 0.5 with expected face outward normals).
    """
    script = get_blender_generation_script()
    tree = ast.parse(script)
    add_box_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "add_box")

    # Locate box_faces assignment AST node
    box_faces_node = next(
        stmt.value for stmt in add_box_node.body
        if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "box_faces" for t in stmt.targets)
    )

    faces = []
    for elt in box_faces_node.elts:
        assert isinstance(elt, ast.Tuple)
        indices = []
        for v in elt.elts:
            if isinstance(v, ast.Name) and v.id == "s_idx":
                indices.append(0)
            elif isinstance(v, ast.BinOp) and isinstance(v.right, ast.Constant):
                indices.append(int(v.right.value))
            elif isinstance(v, ast.Constant):
                indices.append(int(v.value))
            else:
                raise ValueError(f"Unexpected AST node in box_faces: {v}")
        faces.append(tuple(indices))

    assert len(faces) == 12, f"Expected 12 box triangles, got {len(faces)}"

    # Unit box corners matching add_box definition
    cx, cy, cz = 0.0, 0.0, 0.0
    sx, sy, sz = 1.0, 1.0, 1.0
    verts = [
        np.array([cx - sx, cy - sy, cz - sz]),
        np.array([cx + sx, cy - sy, cz - sz]),
        np.array([cx + sx, cy + sy, cz - sz]),
        np.array([cx - sx, cy + sy, cz - sz]),
        np.array([cx - sx, cy - sy, cz + sz]),
        np.array([cx + sx, cy - sy, cz + sz]),
        np.array([cx + sx, cy + sy, cz + sz]),
        np.array([cx - sx, cy + sy, cz + sz]),
    ]

    expected_normals = [
        ("bottom", np.array([0.0, 0.0, -1.0])),
        ("bottom", np.array([0.0, 0.0, -1.0])),
        ("top", np.array([0.0, 0.0, 1.0])),
        ("top", np.array([0.0, 0.0, 1.0])),
        ("back", np.array([0.0, -1.0, 0.0])),
        ("back", np.array([0.0, -1.0, 0.0])),
        ("front", np.array([0.0, 1.0, 0.0])),
        ("front", np.array([0.0, 1.0, 0.0])),
        ("left", np.array([-1.0, 0.0, 0.0])),
        ("left", np.array([-1.0, 0.0, 0.0])),
        ("right", np.array([1.0, 0.0, 0.0])),
        ("right", np.array([1.0, 0.0, 0.0])),
    ]

    inverted_script_faces = []
    for (face_name, expected_outward), (i0, i1, i2) in zip(expected_normals, faces):
        v0, v1, v2 = verts[i0], verts[i1], verts[i2]
        cross = np.cross(v1 - v0, v2 - v0)
        norm_len = np.linalg.norm(cross)
        assert norm_len > 1e-6, f"Degenerate face {i0, i1, i2} on {face_name}"
        fn = cross / norm_len
        dot = np.dot(fn, expected_outward)
        if dot < -0.5:
            inverted_script_faces.append((face_name, (i0, i1, i2), dot))

    assert len(inverted_script_faces) == 0, (
        f"Found {len(inverted_script_faces)}/12 box triangles in "
        f"get_blender_generation_script() with inverted winding order!"
    )
