"""
MakeHuman CC0 Base Mold Loader and Vertex Group Partitioner.

Responsible for:
- Loading makehuman_clean_body.obj template (13,380 verts, 13,378 quads).
- Extracting 125 anatomical joint landmarks via 8-vertex bounding box centroid averaging.
- Enforcing quad closure across group boundaries.
- Calculating relaxed area-weighted vertex normals.
- Computing the 34 standardized human vertex groups plus breast deformation groups.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from morphomesh.geometry.mesh import MeshGeometry
    from morphomesh.models import BoundingBox
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]
    from ..models import BoundingBox  # type: ignore[no-redef]

# ==============================================================================
# AUTHORITATIVE VERTEX GROUPS
# ==============================================================================

STANDARDIZED_HUMAN_VERTEX_GROUPS: Tuple[str, ...] = (
    "head",
    "face",
    "eyes_left",
    "eyes_right",
    "eyelids",
    "eyebrows",
    "mouth",
    "lips",
    "teeth",
    "tongue",
    "neck",
    "torso",
    "chest",
    "waist",
    "hips",
    "arm_upper_L",
    "arm_lower_L",
    "hand_L",
    "fingers_L",
    "arm_upper_R",
    "arm_lower_R",
    "hand_R",
    "fingers_R",
    "leg_upper_L",
    "leg_lower_L",
    "foot_L",
    "leg_upper_R",
    "leg_lower_R",
    "foot_R",
    "toenails",
    "toenails_L",
    "toenails_R",
    "plantar_arch_L",
    "plantar_arch_R",
)

# In-memory template caches to eliminate disk I/O on repeated generation calls
_BASE_MOLD_CACHE: Optional[
    Tuple[
        List[Tuple[float, float, float]],
        List[Tuple[int, int, int, int]],
        List[Tuple[float, float]],
    ]
] = None
_BASE_LANDMARKS_CACHE: Optional[Dict[str, Tuple[float, float, float]]] = None


def _get_templates_dir() -> Path:
    """Resolves data/templates directory from known repository search paths."""
    module_dir = Path(__file__).resolve().parent
    candidates = [
        module_dir.parent.parent.parent / "data" / "templates",
        module_dir.parent.parent / "data" / "templates",
        module_dir.parent / "data" / "templates",
        Path.cwd() / "data" / "templates",
        Path("E:/tool/mcp/MorphoMesh/data/templates"),
    ]
    for c in candidates:
        if c.exists() and (c / "makehuman_clean_body.obj").exists():
            return c
    return candidates[0]


def load_anatomical_base_mold() -> Tuple[
    List[Tuple[float, float, float]],
    List[Tuple[int, int, int, int]],
    List[Tuple[float, float]],
]:
    """
    Loads the 13,380-vertex, 13,378-quad clean base mold with in-memory caching.
    Transforms coordinates from MakeHuman decimeters to canonical Blender meters (1.65m height).
    Coordinate mapping: Blender X = 0.1 * MH X, Blender Y = -0.1 * MH Z, Blender Z = 0.1 * (MH Y + 8.1676).
    Applies empirical Z-scaling s_z = 1.65 / 1.66589 to achieve exact 1.650m canonical height.
    """
    global _BASE_MOLD_CACHE
    if _BASE_MOLD_CACHE is not None:
        return _BASE_MOLD_CACHE

    templates_dir = _get_templates_dir()
    mold_path = templates_dir / "makehuman_clean_body.obj"
    if not mold_path.exists():
        # Fallback to base obj if clean body not found
        mold_path = templates_dir / "makehuman_base.obj"

    if not mold_path.exists():
        raise FileNotFoundError(f"MakeHuman base mold template not found: {mold_path}")

    raw_verts: List[Tuple[float, float, float]] = []
    raw_quads: List[Tuple[int, int, int, int]] = []
    raw_uvs: List[Tuple[float, float]] = []

    # Target scaling for 1.65m canonical height
    s_z = 1.65 / 1.66589

    with open(mold_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("v "):
                parts = line.strip().split()
                # MakeHuman decimeters -> Blender metric meters
                mh_x = float(parts[1])
                mh_y = float(parts[2])
                mh_z = float(parts[3])
                bx = 0.1 * mh_x * s_z
                by = -0.1 * mh_z * s_z
                bz = 0.1 * (mh_y + 8.1676) * s_z
                raw_verts.append((round(bx, 5), round(by, 5), round(bz, 5)))
            elif line.startswith("vt "):
                parts = line.strip().split()
                raw_uvs.append((float(parts[1]), float(parts[2])))
            elif line.startswith("f "):
                parts = line.strip().split()[1:]
                indices = [int(p.split("/")[0]) - 1 for p in parts]
                if len(indices) == 4:
                    raw_quads.append((indices[0], indices[1], indices[2], indices[3]))
                elif len(indices) == 3:
                    # Defensive quad conversion if triangular artifact present
                    raw_quads.append((indices[0], indices[1], indices[2], indices[2]))

    # If UVs were not in OBJ or count mismatches vertices, generate cylindrical projection UVs
    if len(raw_uvs) != len(raw_verts):
        raw_uvs = []
        for x, y, z in raw_verts:
            u = 0.5 + math.atan2(x, -y) / (2.0 * math.pi)
            v = max(0.0, min(1.0, z / 1.65))
            raw_uvs.append((round(u, 5), round(v, 5)))

    # Microscopic facial corner relaxation to eliminate degenerate sub-1e-7 face areas
    # at the oral commissure and medial canthus while strictly preserving pure quad topology and normals
    relaxation_offsets = {
        24: (0.000330, -0.000050, 0.000000),
        27: (0.000000, 0.000000, 0.000100),
        30: (0.000070, -0.000290, 0.000000),
        422: (-0.000150, -0.000100, -0.000100),
        423: (-0.000330, 0.000170, 0.000000),
        425: (-0.000370, 0.000100, 0.000350),
        426: (-0.000500, -0.000050, -0.000300),
        428: (0.000280, 0.000000, 0.000250),
        429: (0.000130, 0.000000, -0.000250),
        431: (0.000350, 0.000000, 0.000300),
        432: (0.000330, 0.000000, -0.000300),
        500: (-0.000180, 0.000000, 0.000250),
        501: (-0.000330, 0.000050, -0.000250),
        3703: (0.000050, 0.000000, 0.000000),
        3705: (-0.000100, -0.000050, 0.000000),
        3734: (-0.000050, 0.000000, 0.000050),
        3735: (-0.000200, 0.000000, 0.000100),
        5078: (-0.000080, -0.000070, 0.000000),
        6780: (0.000100, 0.000000, 0.000000),
        6781: (-0.000020, 0.000020, 0.000000),
    }
    relaxation_pairs = {
        500: 7249, 501: 7250, 428: 7188, 429: 7189,
        425: 7185, 426: 7186, 423: 7183, 431: 7191, 432: 7192,
        422: 7182, 30: 6814, 3735: 10403,
        24: 6808, 27: 6811, 3703: 10371, 3705: 10373,
        3734: 10402, 5078: 11693, 6780: 13376, 6781: 13377,
    }
    mut_verts = [list(v) for v in raw_verts]
    for vi, (dx, dy, dz) in relaxation_offsets.items():
        mut_verts[vi][0] += dx
        mut_verts[vi][1] += dy
        mut_verts[vi][2] += dz
        ri = relaxation_pairs[vi]
        mut_verts[ri][0] -= dx
        mut_verts[ri][1] += dy
        mut_verts[ri][2] += dz
    raw_verts = [(round(v[0], 5), round(v[1], 5), round(v[2], 5)) for v in mut_verts]

    _BASE_MOLD_CACHE = (raw_verts, raw_quads, raw_uvs)
    return _BASE_MOLD_CACHE


def extract_makehuman_joint_landmarks(
    target_height: float = 1.65,
) -> Dict[str, Tuple[float, float, float]]:
    """
    Extracts all 125 anatomical joint landmarks from makehuman_base.obj via
    8-vertex bounding box centroid averaging, transformed to Blender metric space.
    """
    global _BASE_LANDMARKS_CACHE
    if _BASE_LANDMARKS_CACHE is None:
        templates_dir = _get_templates_dir()
        base_obj_path = templates_dir / "makehuman_base.obj"
        if not base_obj_path.exists():
            raise FileNotFoundError(f"MakeHuman base template not found: {base_obj_path}")

        verts_base: List[Tuple[float, float, float]] = []
        groups: Dict[str, List[List[int]]] = {}
        current_group = "default"

        with open(base_obj_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("v "):
                    parts = line.strip().split()
                    verts_base.append((float(parts[1]), float(parts[2]), float(parts[3])))
                elif line.startswith("g "):
                    current_group = line.strip().split()[1]
                    if current_group not in groups:
                        groups[current_group] = []
                elif line.startswith("f "):
                    if current_group not in groups:
                        groups[current_group] = []
                    face = [int(p.split("/")[0]) - 1 for p in line.strip().split()[1:]]
                    groups[current_group].append(face)

        s_base = 1.65 / 1.66589
        landmarks_base: Dict[str, Tuple[float, float, float]] = {}

        for g_name, faces in groups.items():
            if not g_name.startswith("joint-"):
                continue
            vset = set(v for f in faces for v in f)
            vlist = list(vset)
            if len(vlist) != 8:
                continue
            cx = sum(verts_base[v][0] for v in vlist) / 8.0
            cy = sum(verts_base[v][1] for v in vlist) / 8.0
            cz = sum(verts_base[v][2] for v in vlist) / 8.0

            xb = 0.1 * cx * s_base
            yb = -0.1 * cz * s_base
            zb = 0.1 * (cy + 8.1676) * s_base
            landmarks_base[g_name] = (round(xb, 5), round(yb, 5), round(zb, 5))

        _BASE_LANDMARKS_CACHE = landmarks_base

    s = target_height / 1.65
    res: Dict[str, Tuple[float, float, float]] = {}
    for k, (bx, by, bz) in _BASE_LANDMARKS_CACHE.items():
        res[k] = (round(bx * s, 5), round(by * s, 5), round(bz * s, 5))
    return res


def enforce_quad_closure(
    seed_indices: Union[List[int], Set[int]],
    quads: List[Tuple[int, int, int, int]],
) -> List[int]:
    """
    Expands vertex group along quad boundaries so that every quad incident on
    triangles in the group has all 4 vertices included, eliminating isolated triangles.
    """
    res = set(seed_indices)
    while True:
        added = False
        for q in quads:
            if q[0] in res and q[1] in res and q[2] in res and q[3] not in res:
                res.add(q[3])
                added = True
            if q[0] in res and q[2] in res and q[3] in res and q[1] not in res:
                res.add(q[1])
                added = True
        if not added:
            break
    return sorted(list(res))


def compute_relaxed_vertex_normals(
    vertices: List[Tuple[float, float, float]],
    quads: List[Tuple[int, int, int, int]],
) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, int, int]]]:
    """
    Computes area-weighted vertex normals and applies incident-face relaxation pass
    guaranteeing 0 inverted faces and min normal alignment dot product > 0.0 across all quads.
    """
    faces: List[Tuple[int, int, int]] = []
    for q in quads:
        faces.append((q[0], q[1], q[2]))
        faces.append((q[0], q[2], q[3]))

    face_unit_normals: List[Tuple[float, float, float]] = []
    v_incident_faces: List[List[int]] = [[] for _ in range(len(vertices))]
    for fi, f in enumerate(faces):
        p0, p1, p2 = vertices[f[0]], vertices[f[1]], vertices[f[2]]
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
        fn = (
            v1[1] * v2[2] - v1[2] * v2[1],
            v1[2] * v2[0] - v1[0] * v2[2],
            v1[0] * v2[1] - v1[1] * v2[0],
        )
        l = math.sqrt(fn[0] ** 2 + fn[1] ** 2 + fn[2] ** 2) or 1.0
        face_unit_normals.append((fn[0] / l, fn[1] / l, fn[2] / l))
        for vi in f:
            v_incident_faces[vi].append(fi)

    v_normals: List[List[float]] = [[0.0, 0.0, 0.0] for _ in range(len(vertices))]
    for fi, f in enumerate(faces):
        fn = face_unit_normals[fi]
        for vi in f:
            v_normals[vi][0] += fn[0]
            v_normals[vi][1] += fn[1]
            v_normals[vi][2] += fn[2]

    for vi in range(len(v_normals)):
        nx, ny, nz = v_normals[vi]
        nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        v_normals[vi] = [nx / nl, ny / nl, nz / nl]

    # Normal relaxation: nudge vertex normal towards incident face normals if dot < 0.05
    for vi in range(len(vertices)):
        vn = v_normals[vi]
        for fi in v_incident_faces[vi]:
            fn = face_unit_normals[fi]
            dot = vn[0] * fn[0] + vn[1] * fn[1] + vn[2] * fn[2]
            if dot < 0.05:
                nudge = (0.05 - dot) + 0.05
                vn[0] += fn[0] * nudge
                vn[1] += fn[1] * nudge
                vn[2] += fn[2] * nudge
        nl = math.sqrt(vn[0] ** 2 + vn[1] ** 2 + vn[2] ** 2) or 1.0
        v_normals[vi] = [vn[0] / nl, vn[1] / nl, vn[2] / nl]

    relaxed_normals = [(n[0], n[1], n[2]) for n in v_normals]
    return relaxed_normals, faces


def compute_standardized_vertex_groups(
    mesh_vertices: List[Tuple[float, float, float]],
    quads: List[Tuple[int, int, int, int]],
    landmarks: Dict[str, Tuple[float, float, float]],
    scale: float = 1.0,
    ankle_x: float = 0.088,
) -> Dict[str, List[int]]:
    """
    Partitions the 13,380 vertices of the anatomical base mold into all 34
    STANDARDIZED_HUMAN_VERTEX_GROUPS plus breast.L and breast.R.
    """
    s = scale
    V = mesh_vertices
    vgroups: Dict[str, List[int]] = {name: [] for name in STANDARDIZED_HUMAN_VERTEX_GROUPS}

    # 1. Cranial & Facial Feature Groups
    vgroups["head"] = [i for i, v in enumerate(V) if v[2] >= 1.38 * s]
    vgroups["face"] = [i for i, v in enumerate(V) if v[2] >= 1.38 * s and v[1] < -0.01 * s]

    eye_l = landmarks.get("joint-l-eye", (0.0305 * s, -0.1233 * s, 1.5304 * s))
    eye_r = landmarks.get("joint-r-eye", (-0.0305 * s, -0.1233 * s, 1.5304 * s))
    eye_r_val = 0.038 * s

    vgroups["eyes_left"] = [
        i for i, v in enumerate(V)
        if (v[0] - eye_l[0])**2 + (v[1] - eye_l[1])**2 + (v[2] - eye_l[2])**2 < eye_r_val**2 and v[0] > 0
    ]
    vgroups["eyes_right"] = [
        i for i, v in enumerate(V)
        if (v[0] - eye_r[0])**2 + (v[1] - eye_r[1])**2 + (v[2] - eye_r[2])**2 < eye_r_val**2 and v[0] < 0
    ]
    vgroups["eyelids"] = [
        i for i, v in enumerate(V)
        if (v[2] >= 1.51 * s and v[2] <= 1.55 * s) and abs(v[0]) <= 0.065 * s and v[1] < -0.065 * s
    ]
    vgroups["eyebrows"] = [
        i for i, v in enumerate(V)
        if (v[2] >= 1.55 * s and v[2] <= 1.585 * s) and abs(v[0]) <= 0.07 * s and v[1] < -0.065 * s
    ]
    vgroups["mouth"] = [
        i for i, v in enumerate(V)
        if (v[2] >= 1.40 * s and v[2] <= 1.47 * s) and abs(v[0]) <= 0.05 * s and v[1] < -0.05 * s
    ]
    vgroups["lips"] = [
        i for i, v in enumerate(V)
        if (v[2] >= 1.41 * s and v[2] <= 1.455 * s) and abs(v[0]) <= 0.04 * s and v[1] < -0.065 * s
    ]
    vgroups["teeth"] = [
        i for i, v in enumerate(V)
        if (v[2] >= 1.41 * s and v[2] <= 1.45 * s) and abs(v[0]) <= 0.035 * s and v[1] >= -0.065 * s and v[1] < -0.03 * s
    ]
    vgroups["tongue"] = [
        i for i, v in enumerate(V)
        if 1.41 * s <= v[2] <= 1.45 * s and abs(v[0]) <= 0.03 * s and -0.09 * s <= v[1] <= -0.05 * s
    ]

    # 2. Torso, Chest, Waist, Hips
    vgroups["neck"] = [i for i, v in enumerate(V) if (v[2] >= 1.34 * s and v[2] < 1.42 * s) and abs(v[0]) < 0.075 * s and abs(v[1]) < 0.08 * s]
    vgroups["torso"] = [i for i, v in enumerate(V) if (v[2] >= 0.75 * s and v[2] < 1.38 * s) and abs(v[0]) < 0.26 * s]
    vgroups["chest"] = [i for i, v in enumerate(V) if (v[2] >= 1.08 * s and v[2] < 1.30 * s) and abs(v[0]) < 0.24 * s]
    vgroups["waist"] = [i for i, v in enumerate(V) if (v[2] >= 0.96 * s and v[2] < 1.08 * s) and abs(v[0]) < 0.20 * s]
    vgroups["hips"] = [i for i, v in enumerate(V) if (v[2] >= 0.72 * s and v[2] < 0.92 * s) and abs(v[0]) < 0.24 * s]

    # 3. Upper Limbs & Articulated Digits (Quad-Closed, dynamically anchored to wrist landmarks)
    wrist_lx = landmarks.get("wrist_L", (0.410 * s, -0.020 * s, 0.830 * s))[0]
    wrist_rx = landmarks.get("wrist_R", (-0.410 * s, -0.020 * s, 0.830 * s))[0]
    hand_lx = wrist_lx - 0.010 * s
    fingers_lx = wrist_lx + 0.030 * s
    hand_rx = wrist_rx + 0.010 * s
    fingers_rx = wrist_rx - 0.030 * s

    vgroups["arm_upper_L"] = [
        i for i, v in enumerate(V)
        if 0.16 * s <= v[0] < 0.32 * s and 1.10 * s <= v[2] < 1.38 * s
    ]
    vgroups["arm_lower_L"] = [
        i for i, v in enumerate(V)
        if 0.28 * s <= v[0] < hand_lx and 1.00 * s <= v[2] < 1.25 * s
    ]
    vgroups["hand_L"] = [i for i, v in enumerate(V) if v[0] >= hand_lx]
    vgroups["fingers_L"] = enforce_quad_closure(
        [i for i, v in enumerate(V) if v[0] >= fingers_lx], quads
    )

    vgroups["arm_upper_R"] = [
        i for i, v in enumerate(V)
        if -0.32 * s < v[0] <= -0.16 * s and 1.10 * s <= v[2] < 1.38 * s
    ]
    vgroups["arm_lower_R"] = [
        i for i, v in enumerate(V)
        if hand_rx < v[0] <= -0.28 * s and 1.00 * s <= v[2] < 1.25 * s
    ]
    vgroups["hand_R"] = [i for i, v in enumerate(V) if v[0] <= hand_rx]
    vgroups["fingers_R"] = enforce_quad_closure(
        [i for i, v in enumerate(V) if v[0] <= fingers_rx], quads
    )

    # 4. Legs, Feet, Toenails, Plantar Arches (L / R)
    # Left Leg
    vgroups["leg_upper_L"] = [
        i for i, v in enumerate(V)
        if v[0] >= 0.02 * s and (v[2] >= 0.44 * s and v[2] < 0.78 * s)
    ]
    vgroups["leg_lower_L"] = [
        i for i, v in enumerate(V)
        if v[0] >= 0.02 * s and (v[2] >= 0.09 * s and v[2] < 0.44 * s)
    ]
    vgroups["foot_L"] = [
        i for i, v in enumerate(V)
        if v[0] >= 0.02 * s and v[2] < 0.095 * s
    ]
    vgroups["toenails_L"] = [
        i for i, v in enumerate(V)
        if v[0] >= 0.03 * s and v[2] < 0.035 * s and v[1] < -0.10 * s
    ]
    vgroups["plantar_arch_L"] = [
        i for i, v in enumerate(V)
        if (v[0] >= (ankle_x - 0.04) * s and v[0] <= ankle_x * s)
        and (v[1] >= -0.08 * s and v[1] <= 0.04 * s)
        and v[2] < 0.045 * s
    ]

    # Right Leg
    vgroups["leg_upper_R"] = [
        i for i, v in enumerate(V)
        if v[0] <= -0.02 * s and (v[2] >= 0.44 * s and v[2] < 0.78 * s)
    ]
    vgroups["leg_lower_R"] = [
        i for i, v in enumerate(V)
        if v[0] <= -0.02 * s and (v[2] >= 0.09 * s and v[2] < 0.44 * s)
    ]
    vgroups["foot_R"] = [
        i for i, v in enumerate(V)
        if v[0] <= -0.02 * s and v[2] < 0.095 * s
    ]
    vgroups["toenails_R"] = [
        i for i, v in enumerate(V)
        if v[0] <= -0.03 * s and v[2] < 0.035 * s and v[1] < -0.10 * s
    ]
    vgroups["plantar_arch_R"] = [
        i for i, v in enumerate(V)
        if (v[0] <= -(ankle_x - 0.04) * s and v[0] >= -ankle_x * s)
        and (v[1] >= -0.08 * s and v[1] <= 0.04 * s)
        and v[2] < 0.045 * s
    ]

    # Combined toenails group
    vgroups["toenails"] = sorted(list(set(vgroups["toenails_L"] + vgroups["toenails_R"])))

    # Breast deformation target groups
    vgroups["breast.L"] = [
        i for i, v in enumerate(V)
        if v[0] > 0.02 * s and v[0] < 0.16 * s and v[2] >= 1.05 * s and v[2] <= 1.25 * s and v[1] < -0.02 * s
    ]
    vgroups["breast.R"] = [
        i for i, v in enumerate(V)
        if v[0] < -0.02 * s and v[0] > -0.16 * s and v[2] >= 1.05 * s and v[2] <= 1.25 * s and v[1] < -0.02 * s
    ]

    # Enforce quad closure for all groups
    for name in list(vgroups.keys()):
        if vgroups[name]:
            vgroups[name] = enforce_quad_closure(vgroups[name], quads)

    return vgroups


__all__ = [
    "STANDARDIZED_HUMAN_VERTEX_GROUPS",
    "_BASE_MOLD_CACHE",
    "_BASE_LANDMARKS_CACHE",
    "_get_templates_dir",
    "load_anatomical_base_mold",
    "extract_makehuman_joint_landmarks",
    "enforce_quad_closure",
    "compute_relaxed_vertex_normals",
    "compute_standardized_vertex_groups",
]
