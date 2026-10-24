"""
Anthropometric Morphology and Parametric Proportion Engine.

Responsible for:
- Standard proportion presets (stylized heroine, realistic female, chibi, etc.).
- Robust configuration resolver handling positional and keyword arguments.
- Quad dominance calculation and quad mesh primitives (caps, ellipsoids).
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from morphomesh.geometry.mesh import MeshGeometry
    from morphomesh.models import HumanAnatomyConfig
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]
    from ..models import HumanAnatomyConfig  # type: ignore[no-redef]


def compute_quad_metrics(mesh: MeshGeometry) -> Tuple[int, int, float]:
    """
    Dynamically computes the actual quad dominance ratio from mesh faces.
    In MeshGeometry, quads added via add_quad(i0, i1, i2, i3) are stored as two
    consecutive triangles (i0, i1, i2) and (i0, i2, i3).
    Returns: (quad_count, tri_count, quad_ratio).
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
    quad_ratio = round(quad_count / total_polys, 4) if total_polys > 0 else 0.0
    return quad_count, tri_count, quad_ratio


def add_quad_cap(mesh: MeshGeometry, ring_indices: List[int], flip_normal: bool = False) -> None:
    """
    Caps an even-sided circular ring of N vertices with pure quad strips.
    Bridges pairs (i, i+1) with (N-2-i, N-1-i) for i = 0 to (N-4)//2.
    Produces exactly (N-2)//2 quads and 0 triangles.
    """
    n = len(ring_indices)
    assert n % 2 == 0 and n >= 4, "Ring must have an even number of vertices >= 4"
    num_quads = (n - 2) // 2
    for k in range(num_quads):
        i0 = ring_indices[k]
        i1 = ring_indices[k + 1]
        i2 = ring_indices[n - 2 - k]
        i3 = ring_indices[n - 1 - k]
        if flip_normal:
            mesh.add_quad(i0, i3, i2, i1)
        else:
            mesh.add_quad(i0, i1, i2, i3)


def add_quad_ellipsoid(
    mesh: MeshGeometry,
    center: Tuple[float, float, float],
    radii: Tuple[float, float, float],
    rings: int = 4,
    sectors: int = 8,
) -> List[int]:
    """
    Creates an axis-oriented 3D ellipsoid with 100% pure quads (0 triangles)
    and 0 open boundary edges using quad-capped latitude rings.
    Returns list of added vertex indices.
    """
    cx, cy, cz = center
    rx, ry, rz = radii
    sectors = max(4, sectors if sectors % 2 == 0 else sectors + 1)
    rings = max(2, rings)
    ring_indices: List[List[int]] = []
    added_indices: List[int] = []

    for r in range(rings):
        phi = -math.pi / 2.0 + math.pi * (r + 0.5) / rings
        cos_phi = math.cos(phi)
        sin_phi = math.sin(phi)

        current_ring: List[int] = []
        for s in range(sectors):
            theta = 2.0 * math.pi * s / sectors
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            px = cx + rx * cos_phi * cos_t
            py = cy + ry * cos_phi * sin_t
            pz = cz + rz * sin_phi

            nx = (cos_phi * cos_t) / rx if rx > 1e-6 else 0.0
            ny = (cos_phi * sin_t) / ry if ry > 1e-6 else 0.0
            nz = sin_phi / rz if rz > 1e-6 else 0.0
            nlen = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            norm = (nx / nlen, ny / nlen, nz / nlen)

            u = s / sectors
            v = (r + 0.5) / rings
            idx = mesh.add_vertex((px, py, pz), norm, (u, v))
            current_ring.append(idx)
            added_indices.append(idx)
        ring_indices.append(current_ring)

    for r in range(rings - 1):
        for s in range(sectors):
            ns = (s + 1) % sectors
            mesh.add_quad(
                ring_indices[r][s],
                ring_indices[r][ns],
                ring_indices[r + 1][ns],
                ring_indices[r + 1][s],
            )

    add_quad_cap(mesh, ring_indices[0], flip_normal=True)
    add_quad_cap(mesh, ring_indices[-1], flip_normal=False)

    return added_indices


PROPORTION_PRESETS: Dict[str, Dict[str, Any]] = {
    "stylized_heroine": {
        "height": 1.65,
        "head_ratio": 7.41,
        "chest_girth": 0.82,
        "waist_girth": 0.58,
        "hip_girth": 0.86,
        "shoulder_width": 0.36,
        "arm_span": 1.62,
        "leg_length": 0.88,
        "gender": "female",
        "style": "stylized_photorealism",
    },
    "realistic_female": {
        "height": 1.68,
        "head_ratio": 7.50,
        "chest_girth": 0.88,
        "waist_girth": 0.66,
        "hip_girth": 0.94,
        "shoulder_width": 0.38,
        "arm_span": 1.65,
        "leg_length": 0.88,
        "gender": "female",
        "style": "realistic",
    },
    "realistic_human": {
        "height": 1.70,
        "head_ratio": 7.50,
        "chest_girth": 0.88,
        "waist_girth": 0.68,
        "hip_girth": 0.94,
        "shoulder_width": 0.38,
        "arm_span": 1.68,
        "leg_length": 0.90,
        "gender": "female",
        "style": "realistic",
    },
    "petite": {
        "height": 1.40,
        "head_ratio": 6.50,
        "chest_girth": 0.76,
        "waist_girth": 0.54,
        "hip_girth": 0.80,
        "shoulder_width": 0.32,
        "arm_span": 1.38,
        "leg_length": 0.75,
        "gender": "female",
        "style": "stylized_photorealism",
    },
    "chibi_petite": {
        "height": 1.30,
        "head_ratio": 5.00,
        "chest_girth": 0.72,
        "waist_girth": 0.52,
        "hip_girth": 0.76,
        "shoulder_width": 0.28,
        "arm_span": 1.25,
        "leg_length": 0.68,
        "gender": "female",
        "style": "stylized_photorealism",
    },
    "heroic_male": {
        "height": 1.85,
        "head_ratio": 8.00,
        "chest_girth": 1.02,
        "waist_girth": 0.80,
        "hip_girth": 0.96,
        "shoulder_width": 0.44,
        "arm_span": 1.85,
        "leg_length": 0.98,
        "gender": "male",
        "style": "realistic",
    },
}

PRESET_ALIASES: Dict[str, str] = {
    "heroine": "stylized_heroine",
    "yu_nian_an": "stylized_heroine",
    "default": "stylized_heroine",
    "semi_realistic": "stylized_heroine",
    "realistic": "realistic_female",
    "realistic_woman": "realistic_female",
    "female_realistic": "realistic_female",
    "chibi": "chibi_petite",
    "asian_petite": "petite",
    "slender_petite": "petite",
    "male": "heroic_male",
    "realistic_male": "heroic_male",
}


def resolve_human_anatomy_config(
    config: Optional[Union[HumanAnatomyConfig, float, int]] = None,
    height: Optional[Union[float, HumanAnatomyConfig]] = None,
    gender: Optional[Union[str, HumanAnatomyConfig]] = None,
    proportion_preset: Optional[str] = None,
    **kwargs: Any,
) -> HumanAnatomyConfig:
    """
    Robustly resolves HumanAnatomyConfig from combinations of preset names,
    explicit parameters, existing config objects, and keyword overrides.
    Guarantees 100% backward compatibility for positional and keyword callers.
    """
    # Defensive handling of shifted positional arguments (e.g. (1.70, config_obj))
    if isinstance(config, (int, float)):
        actual_height = float(config)
        actual_config = height if isinstance(height, HumanAnatomyConfig) else None
        config = actual_config
        height = actual_height

    if isinstance(height, HumanAnatomyConfig):
        if config is None:
            config = height
        height = config.height

    if isinstance(gender, HumanAnatomyConfig):
        if config is None:
            config = gender
        gender = config.gender

    # Extract preset from kwargs if passed under alternative keys
    if proportion_preset is None:
        if "proportion_preset" in kwargs:
            proportion_preset = kwargs.pop("proportion_preset")
        elif "preset" in kwargs:
            proportion_preset = kwargs.pop("preset")

    # Canonicalize preset name
    raw_preset = (proportion_preset or "stylized_heroine").strip().lower().replace("-", "_")
    canonical_preset = PRESET_ALIASES.get(raw_preset, raw_preset)
    base_params = dict(PROPORTION_PRESETS.get(canonical_preset, PROPORTION_PRESETS["stylized_heroine"]))

    # If a pre-constructed HumanAnatomyConfig is passed without field overrides, return it directly
    if config is not None and isinstance(config, HumanAnatomyConfig):
        has_overrides = (
            height is not None or
            gender is not None or
            proportion_preset is not None or
            any(k in HumanAnatomyConfig.model_fields and v is not None for k, v in kwargs.items())
        )
        if not has_overrides:
            return config
        cfg_dict = config.model_dump() if hasattr(config, "model_dump") else dict(config)
        base_params.update({k: v for k, v in cfg_dict.items() if v is not None})

    # Apply explicit height if provided
    if height is not None and isinstance(height, (int, float)):
        base_params["height"] = float(height)

    # Apply explicit gender if provided
    if gender is not None and isinstance(gender, str):
        base_params["gender"] = gender

    # Apply any remaining kwargs that match HumanAnatomyConfig fields
    valid_fields = set(HumanAnatomyConfig.model_fields.keys())
    for k, v in list(kwargs.items()):
        if k in valid_fields and v is not None:
            base_params[k] = v

    return HumanAnatomyConfig.model_construct(**base_params)


__all__ = [
    "compute_quad_metrics",
    "add_quad_cap",
    "add_quad_ellipsoid",
    "PROPORTION_PRESETS",
    "PRESET_ALIASES",
    "resolve_human_anatomy_config",
]
