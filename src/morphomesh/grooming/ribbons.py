"""
MorphoMesh Hair Curves-to-Ribbon Mesh Extrusion Evaluator.

Responsible for:
- convert_curves_to_ribbon_mesh: Evaluates 3D hair splines into polygonal quad ribbon meshes.
- UV coordinate generation, outward-facing normal calculation, and Rigify DEF-head binding.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:
    from morphomesh.inference_adapter import MeshGeometry
except (ImportError, ModuleNotFoundError):
    from ..geometry.mesh import MeshGeometry  # type: ignore[no-redef]

from .hime_cut import HairCurveSpline

logger = logging.getLogger("morphomesh.grooming.ribbons")

def convert_curves_to_ribbon_mesh(
    splines: Sequence[HairCurveSpline],
    ribbon_width: float = 0.002,
) -> MeshGeometry:
    """
    Converts a collection of 3D hair splines into a quad ribbon mesh for real-time export.
    Every consecutive point pair forms a pure quad facet (0 tris) with monotonic UV coordinates,
    outward-facing normal vectors, and DEF-head vertex group weighting.
    """
    mesh = MeshGeometry()
    half_w = ribbon_width * 0.5

    for spline in splines:
        pts = spline.points
        if len(pts) < 2:
            continue

        prev_left = None
        prev_right = None

        for p_idx in range(len(pts)):
            pt = pts[p_idx]
            # Tangent vector
            if p_idx < len(pts) - 1:
                next_pt = pts[p_idx + 1]
                dx = next_pt[0] - pt[0]
                dy = next_pt[1] - pt[1]
                dz = next_pt[2] - pt[2]
            else:
                prev_p = pts[p_idx - 1]
                dx = pt[0] - prev_p[0]
                dy = pt[1] - prev_p[1]
                dz = pt[2] - prev_p[2]

            xy_sq = dx * dx + dy * dy
            if xy_sq < 1e-12:
                # Pure vertical tangent fallback
                sx = half_w
                sy = 0.0
                sz = 0.0
                bx, by, bz = 1.0, 0.0, 0.0
            else:
                xy_len = math.sqrt(xy_sq)
                bx = -dy / xy_len
                by = dx / xy_len
                bz = 0.0
                sx = bx * half_w
                sy = by * half_w
                sz = 0.0

            # Calculate outward-facing normal
            t_len = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
            tx, ty, tz = dx / t_len, dy / t_len, dz / t_len
            nx = by * tz - bz * ty
            ny = bz * tx - bx * tz
            nz = bx * ty - by * tx
            n_len = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            nx, ny, nz = nx / n_len, ny / n_len, nz / n_len

            # Ensure normal points outward away from cranial center (0, 0, 1.55)
            head_vec = (pt[0], pt[1], pt[2] - 1.55)
            if (nx * head_vec[0] + ny * head_vec[1] + nz * head_vec[2]) < 0:
                nx, ny, nz = -nx, -ny, -nz

            norm = (round(nx, 4), round(ny, 4), round(nz, 4))
            v_coord = p_idx / max(1, len(pts) - 1)

            cur_left = mesh.add_vertex((round(pt[0] + sx, 5), round(pt[1] + sy, 5), round(pt[2] + sz, 5)), norm, (0.0, v_coord))
            cur_right = mesh.add_vertex((round(pt[0] - sx, 5), round(pt[1] - sy, 5), round(pt[2] - sz, 5)), norm, (1.0, v_coord))

            if prev_left is not None and prev_right is not None:
                mesh.add_quad(prev_left, prev_right, cur_right, cur_left)

            prev_left = cur_left
            prev_right = cur_right

    # Assign normalized Rigify DEF-head skin weights
    if len(mesh.vertices) > 0:
        mesh.vertex_groups["DEF-head"] = list(range(len(mesh.vertices)))
        mesh.skin_weights = {i: {"DEF-head": 1.0} for i in range(len(mesh.vertices))}

    return mesh

