"""
MorphoMesh: Quad Mesh Topology Metrics & Capping Utilities.
"""
from __future__ import annotations

import math
from typing import Any, List, Tuple


def compute_quad_metrics(mesh: Any) -> Tuple[int, int, float]:
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


def add_quad_cap(mesh: Any, ring_indices: List[int], flip_normal: bool = False) -> None:
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
    mesh: Any,
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


__all__ = [
    "add_quad_cap",
    "add_quad_ellipsoid",
    "compute_quad_metrics",
]
