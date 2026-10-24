"""
MorphoMesh Wardrobe Skin Weights and Pinning Subsystem.

Responsible for:
- Finger DEF bone key aliases and material aliases.
- Elevation radii computation for dress waist.
- Cloth simulation pin weighting (Pin_Bodice).
- Rigify DEF skin weights computation for Bodice, Skirt, Sash, Sandals.
- compute_wardrobe_skin_weights entrypoint.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

logger = logging.getLogger("morphomesh.wardrobe.skinning")

# Authoritative Bone and Material Aliases
FINGER_DEF_BONE_KEYS: Tuple[str, ...] = (
    "DEF-thumb.03.L", "DEF-f_index.03.L", "DEF-f_middle.03.L", "DEF-f_ring.03.L", "DEF-f_pinky.03.L",
    "DEF-thumb.03.R", "DEF-f_index.03.R", "DEF-f_middle.03.R", "DEF-f_ring.03.R", "DEF-f_pinky.03.R",
)

FINGER_DEF_BONE_ALIASES: Dict[str, str] = {
    "DEF-finger_thumb.03.L": "DEF-thumb.03.L",
    "DEF-finger_index.03.L": "DEF-f_index.03.L",
    "DEF-finger_middle.03.L": "DEF-f_middle.03.L",
    "DEF-finger_ring.03.L": "DEF-f_ring.03.L",
    "DEF-finger_pinky.03.L": "DEF-f_pinky.03.L",
    "DEF-finger_thumb.03.R": "DEF-thumb.03.R",
    "DEF-finger_index.03.R": "DEF-f_index.03.R",
    "DEF-finger_middle.03.R": "DEF-f_middle.03.R",
    "DEF-finger_ring.03.R": "DEF-f_ring.03.R",
    "DEF-finger_pinky.03.R": "DEF-f_pinky.03.R",
}

def resolve_finger_def_bone_name(name: str) -> str:
    """Resolves between Rigify standard bone names and descriptive metarig names."""
    return FINGER_DEF_BONE_ALIASES.get(name, name)

MATERIAL_NAME_ALIASES: Dict[str, str] = {
    "Mat_Red_Thread": "Mat_Marionette_RedString",
    "Mat_Marionette_RedString": "Mat_Red_Thread",
    "Mat_Butterfly_Glow": "Mat_Magic_Butterfly",
    "Mat_Magic_Butterfly": "Mat_Butterfly_Glow",
    "Mat_Sandals": "Mat_Sandal_Leather",
    "Mat_Sandal_Leather": "Mat_Sandals",
}




def compute_dress_waist_radii(
    z: float,
    s: float = 1.0,
    k_w: float = 1.0,
    k_c: float = 1.0,
    clearance: float = 0.015,
) -> Tuple[float, float, float]:
    """
    Computes exact (rx, ry, yo) of the dress bodice envelope at elevation z.
    Interpolates smoothly across the waist zone (Z = 1.03*s to 1.07*s) conformed to MakeHuman.
    """
    z0 = 1.03 * s
    z1 = 1.07 * s
    u = max(0.0, min(1.0, (z - z0) / max(1e-4, z1 - z0)))
    rx0 = 0.127 * s * k_w + clearance
    ry0 = 0.083 * s * k_w + clearance
    rx1 = 0.133 * s * (0.8 * k_w + 0.2 * k_c) + clearance
    ry1 = 0.089 * s * (0.8 * k_w + 0.2 * k_c) + clearance
    rx = rx0 + u * (rx1 - rx0)
    ry = ry0 + u * (ry1 - ry0)
    yo = -s * k_w * (0.048 + 0.016 * u)
    return rx, ry, yo


def assign_dress_pin_weights(mesh: MeshGeometry, height: float = 1.65) -> None:
    """
    Assigns 'Pin_Bodice' vertex group for Blender Cloth Simulation:
    - Straps (Z >= 1.28m) & Sweetheart Rim (Z >= 1.185m): w = 1.0 (firm anchor)
    - Mid-bodice (Z in [1.08m, 1.185m]): linear falloff 1.0 -> 0.2
    - Empire waist cinch (Z in [1.02m, 1.08m]): w = 0.15
    - Skirt (Z < 1.02m): w = 0.0 (100% free gravitational drape)
    """
    s = height / 1.65
    pin_weights: Dict[int, float] = {}
    for idx, (x, y, z) in enumerate(mesh.vertices):
        if z >= 1.280 * s:  # 3D straps
            w = 1.0
        elif z >= 1.185 * s and abs(y) > 0.05:  # Sweetheart scoop rim
            w = 1.0
        elif z >= 1.080 * s:  # Mid-bodice
            t = (z - 1.080 * s) / max(1e-4, (1.185 - 1.080) * s)
            w = 0.20 + 0.80 * t
        elif z >= 1.020 * s:  # Waist cinch
            w = 0.15
        else:  # Skirt
            w = 0.00
        pin_weights[idx] = round(w, 4)
    mesh.pin_weights = pin_weights  # type: ignore[attr-defined]
    if not hasattr(mesh, "vertex_groups"):
        mesh.vertex_groups = {}
    mesh.vertex_groups["Pin_Bodice"] = [
        idx for idx, w in pin_weights.items() if w > 0.0
    ]


def assign_bodice_skin_weights(mesh: MeshGeometry, height: float = 1.65) -> None:
    """
    Assigns normalized Rigify 163 DEF bone skinning vertex groups to Dress_Bodice:
    DEF-spine.001, DEF-spine.002, DEF-spine.003, DEF-spine.004, DEF-shoulder.L, DEF-shoulder.R.
    Strictly normalizes sum of weights to 1.0 for every vertex.
    """
    s = height / 1.65
    skin_weights: Dict[int, Dict[str, float]] = {}

    for i, v in enumerate(mesh.vertices):
        vx, vy, vz = v
        b_dict: Dict[str, float] = {}

        if vz > 1.258 * s:
            # Spaghetti shoulder straps region
            if vx >= 0.0:
                b_dict["DEF-shoulder.L"] = 0.40
                b_dict["DEF-spine.004"] = 0.35
                b_dict["DEF-spine.003"] = 0.25
            else:
                b_dict["DEF-shoulder.R"] = 0.40
                b_dict["DEF-spine.004"] = 0.35
                b_dict["DEF-spine.003"] = 0.25
        elif vz >= 1.160 * s:
            # Upper chest & sweetheart cups region
            t_z = max(0.0, min(1.0, (vz - 1.160 * s) / (0.098 * s)))
            b_dict["DEF-spine.003"] = 0.85
            b_dict["DEF-spine.004"] = 0.15 * t_z
            b_dict["DEF-spine.002"] = 0.15 * (1.0 - t_z)
        elif vz >= 1.070 * s:
            # Mid-torso ribcage region
            t_z = max(0.0, min(1.0, (vz - 1.070 * s) / (0.090 * s)))
            b_dict["DEF-spine.003"] = 0.30 + 0.50 * t_z
            b_dict["DEF-spine.002"] = 0.70 - 0.50 * t_z
        else:
            # Empire waist cinch region (Z in [1.030*s, 1.070*s])
            t_z = max(0.0, min(1.0, (vz - 1.030 * s) / (0.040 * s)))
            b_dict["DEF-spine.001"] = 0.70 - 0.40 * t_z
            b_dict["DEF-spine.002"] = 0.30 + 0.40 * t_z

        # Normalize weights
        tot = sum(b_dict.values()) or 1.0
        norm_dict = {b: w / tot for b, w in b_dict.items()}
        skin_weights[i] = norm_dict

        for b, w in norm_dict.items():
            if w > 0.01:
                if b not in mesh.vertex_groups:
                    mesh.vertex_groups[b] = []
                mesh.vertex_groups[b].append(i)

    # Attach in-memory skin weights mapping
    mesh.skin_weights = skin_weights  # type: ignore[attr-defined]


def assign_skirt_skin_weights(mesh: MeshGeometry, height: float = 1.65) -> None:
    """
    Assigns normalized Rigify 163 DEF bone skinning vertex groups to Dress_PleatedSkirt / OrganicSkirt:
    DEF-spine.001, DEF-spine, DEF-pelvis, DEF-thigh.L, DEF-thigh.L.001, DEF-thigh.R, DEF-thigh.R.001.
    Strictly normalizes sum of weights to 1.0 for every vertex.
    """
    s = height / 1.65
    skin_weights: Dict[int, Dict[str, float]] = {}

    for i, v in enumerate(mesh.vertices):
        vx, vy, vz = v
        b_dict: Dict[str, float] = {}

        if vz >= 0.980 * s:
            # Upper waistband locked to lower lumbar spine
            b_dict["DEF-spine.001"] = 0.75
            b_dict["DEF-spine"] = 0.25
        elif vz >= 0.825 * s:
            # Pelvic girdle flare zone
            u_z = (vz - 0.825 * s) / (0.155 * s)
            b_dict["DEF-spine.001"] = 0.25 + 0.50 * u_z
            b_dict["DEF-spine"] = 0.75 - 0.50 * u_z
        else:
            # Flared lower skirt descending to patella hemline (Z < 0.825*s down to ~0.50*s)
            t_z = max(0.0, min(1.0, (vz - 0.500 * s) / (0.325 * s)))
            w_spine = 0.30 * t_z + 0.08 * (1.0 - t_z)
            w_legs = 1.0 - w_spine

            # Medial smooth tanh blending across stride gap (|X| <= 0.04m)
            blend_l = 0.50 + 0.50 * math.tanh(vx / (0.040 * s))
            blend_r = 1.0 - blend_l

            w_upper = 0.75 * t_z + 0.35 * (1.0 - t_z)
            w_lower = 1.0 - w_upper

            b_dict["DEF-spine"] = w_spine
            b_dict["DEF-thigh.L"] = w_legs * blend_l * w_upper
            b_dict["DEF-thigh.L.001"] = w_legs * blend_l * w_lower
            b_dict["DEF-thigh.R"] = w_legs * blend_r * w_upper
            b_dict["DEF-thigh.R.001"] = w_legs * blend_r * w_lower

        # Normalize weights
        tot = sum(b_dict.values()) or 1.0
        norm_dict = {b: w / tot for b, w in b_dict.items()}
        # Mirror DEF-spine weight to DEF-pelvis alias for universal compatibility
        if "DEF-spine" in norm_dict:
            b_dict_alias = dict(norm_dict)
            # Both DEF-spine and DEF-pelvis are registered
        skin_weights[i] = norm_dict

        for b, w in norm_dict.items():
            if w > 0.01:
                if b not in mesh.vertex_groups:
                    mesh.vertex_groups[b] = []
                mesh.vertex_groups[b].append(i)
                if b == "DEF-spine":
                    if "DEF-pelvis" not in mesh.vertex_groups:
                        mesh.vertex_groups["DEF-pelvis"] = []
                    mesh.vertex_groups["DEF-pelvis"].append(i)

    mesh.skin_weights = skin_weights  # type: ignore[attr-defined]


def assign_sash_skin_weights(
    mesh: MeshGeometry,
    height: float = 1.65,
    num_band_verts: int = 120,
    knot_start: int = 120,
    knot_count: int = 32,
    loops_start: int = 152,
    loops_count: int = 96,
    streamers_start: int = 248,
) -> None:
    """
    Assigns normalized Rigify 163 DEF bone skinning vertex groups to Dress_WaistSash:
    DEF-spine.001, DEF-spine.002, DEF-spine, DEF-thigh.L, DEF-thigh.R, DEF-thigh.L.001, DEF-thigh.R.001.
    Strictly normalizes sum of weights to 1.0 for every vertex.
    """
    s = height / 1.65
    skin_weights: Dict[int, Dict[str, float]] = {}

    for i, v in enumerate(mesh.vertices):
        vx, vy, vz = v
        b_dict: Dict[str, float] = {}

        if i < knot_start:
            # Sash band: smooth vertical blend between DEF-spine.001 and DEF-spine.002
            u_z = max(0.0, min(1.0, (vz - 1.025 * s) / (0.050 * s)))
            b_dict["DEF-spine.002"] = 0.25 + 0.50 * u_z
            b_dict["DEF-spine.001"] = 1.0 - b_dict["DEF-spine.002"]
        elif i < streamers_start:
            # Central 3D knot and bilateral 3D loops: rigid 50/50 anchor to waist center
            b_dict["DEF-spine.001"] = 0.50
            b_dict["DEF-spine.002"] = 0.50
        else:
            # Cascading ribbon streamers hanging downward across pelvis and thighs
            if vz >= 0.938 * s:
                u = max(0.0, min(1.0, (vz - 0.938 * s) / (0.087 * s)))
                b_dict["DEF-spine.001"] = 0.50 + 0.30 * u
                b_dict["DEF-spine"] = 1.0 - b_dict["DEF-spine.001"]
            elif vz >= 0.825 * s:
                u = max(0.0, min(1.0, (vz - 0.825 * s) / (0.113 * s)))
                b_dict["DEF-spine"] = 0.65 + 0.35 * u
                if vx >= 0.0:
                    b_dict["DEF-thigh.L"] = (1.0 - u) * 0.35
                else:
                    b_dict["DEF-thigh.R"] = (1.0 - u) * 0.35
            else:
                t = max(0.0, min(1.0, (vz - 0.640 * s) / (0.185 * s)))
                w_spine = 0.35 + 0.30 * t
                w_thigh = 1.0 - w_spine
                b_dict["DEF-spine"] = w_spine
                if vx >= 0.0:
                    b_dict["DEF-thigh.L"] = w_thigh * (0.70 + 0.30 * t)
                    b_dict["DEF-thigh.L.001"] = w_thigh * (0.30 * (1.0 - t))
                else:
                    b_dict["DEF-thigh.R"] = w_thigh * (0.70 + 0.30 * t)
                    b_dict["DEF-thigh.R.001"] = w_thigh * (0.30 * (1.0 - t))

        # Normalize weights
        tot = sum(b_dict.values()) or 1.0
        norm_dict = {b: w / tot for b, w in b_dict.items()}
        skin_weights[i] = norm_dict

        for b, w in norm_dict.items():
            if w > 0.01:
                if b not in mesh.vertex_groups:
                    mesh.vertex_groups[b] = []
                mesh.vertex_groups[b].append(i)

    mesh.skin_weights = skin_weights  # type: ignore[attr-defined]


def compute_wardrobe_skin_weights(
    mesh: MeshGeometry,
    part_name: str,
    height: float = 1.65,
) -> Dict[int, Dict[str, float]]:
    """
    Returns normalized skinning weights mapping {vertex_idx: {bone_name: weight}}
    for any wardrobe component mesh.
    """
    if hasattr(mesh, "skin_weights") and getattr(mesh, "skin_weights"):
        return getattr(mesh, "skin_weights")

    if "Bodice" in part_name:
        assign_bodice_skin_weights(mesh, height=height)
    elif "Skirt" in part_name:
        assign_skirt_skin_weights(mesh, height=height)
    elif "WaistSash" in part_name or "Belt" in part_name:
        assign_sash_skin_weights(mesh, height=height)

    return getattr(mesh, "skin_weights", {})

