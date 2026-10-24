"""
MorphoMesh: Critic Geometric Math & Ray-Triangle Primitives.

Pure-Python 3D vector arithmetic, Möller–Trumbore ray-triangle intersection,
Möller triangle-triangle intersection, Eberly point-to-triangle distance,
and Axis-Aligned Bounding Box (AABB) spatial primitives.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

def _cross_product(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot_product(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _sub_vec(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add_vec(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> Tuple[float, float, float]:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale_vec(a: Tuple[float, float, float], s: float) -> Tuple[float, float, float]:
    return (a[0] * s, a[1] * s, a[2] * s)


def _norm_vec(a: Tuple[float, float, float]) -> Tuple[float, float, float]:
    mag = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    if mag < 1e-12:
        return (0.0, 0.0, 1.0)
    return (a[0] / mag, a[1] / mag, a[2] / mag)


def _vec_len(a: Tuple[float, float, float]) -> float:
    return math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])


def point_to_triangle_distance_eberly(
    point: Tuple[float, float, float],
    v0: Tuple[float, float, float],
    v1: Tuple[float, float, float],
    v2: Tuple[float, float, float],
) -> Tuple[Tuple[float, float, float], Tuple[float, float, float], float]:
    """
    David Eberly's exact 3D point-to-triangle closest point algorithm.
    Returns (closest_point, unit_normal, distance).
    """
    e0 = _sub_vec(v1, v0)
    e1 = _sub_vec(v2, v0)
    d = _sub_vec(v0, point)

    a = _dot_product(e0, e0)
    b = _dot_product(e0, e1)
    c = _dot_product(e1, e1)
    d_val = _dot_product(e0, d)
    e_val = _dot_product(e1, d)

    det = a * c - b * b
    s = b * e_val - c * d_val
    t = b * d_val - a * e_val

    if s + t <= det:
        if s < 0.0:
            if t < 0.0:
                # Region 4
                if d_val < 0.0:
                    t = 0.0
                    s = -d_val / a if a > 1e-12 else 0.0
                    s = max(0.0, min(1.0, s))
                else:
                    s = 0.0
                    t = -e_val / c if c > 1e-12 else 0.0
                    t = max(0.0, min(1.0, t))
            else:
                # Region 3
                s = 0.0
                t = -e_val / c if c > 1e-12 else 0.0
                t = max(0.0, min(1.0, t))
        elif t < 0.0:
            # Region 5
            t = 0.0
            s = -d_val / a if a > 1e-12 else 0.0
            s = max(0.0, min(1.0, s))
        else:
            # Region 0 (Interior)
            inv_det = 1.0 / det if abs(det) > 1e-12 else 0.0
            s *= inv_det
            t *= inv_det
    else:
        if s < 0.0:
            # Region 2
            tmp0 = b + d_val
            tmp1 = c + e_val
            if tmp1 > tmp0:
                numer = tmp1 - tmp0
                denom = a - 2.0 * b + c
                s = numer / denom if denom > 1e-12 else 0.0
                s = max(0.0, min(1.0, s))
                t = 1.0 - s
            else:
                s = 0.0
                t = -e_val / c if c > 1e-12 else 0.0
                t = max(0.0, min(1.0, t))
        elif t < 0.0:
            # Region 6
            tmp0 = b + e_val
            tmp1 = a + d_val
            if tmp1 > tmp0:
                numer = tmp1 - tmp0
                denom = a - 2.0 * b + c
                t = numer / denom if denom > 1e-12 else 0.0
                t = max(0.0, min(1.0, t))
                s = 1.0 - t
            else:
                t = 0.0
                s = -d_val / a if a > 1e-12 else 0.0
                s = max(0.0, min(1.0, s))
        else:
            # Region 1
            numer = (c + e_val) - (b + d_val)
            if numer <= 0.0:
                s = 0.0
                t = 1.0
            else:
                denom = a - 2.0 * b + c
                s = numer / denom if denom > 1e-12 else 0.0
                s = max(0.0, min(1.0, s))
                t = 1.0 - s

    closest = _add_vec(v0, _add_vec(_scale_vec(e0, s), _scale_vec(e1, t)))
    norm_raw = _cross_product(e0, e1)
    unit_norm = _norm_vec(norm_raw)
    dist = _vec_len(_sub_vec(point, closest))
    return closest, unit_norm, dist


def ray_triangle_intersection_moller_trumbore(
    origin: Tuple[float, float, float],
    direction: Tuple[float, float, float],
    v0: Tuple[float, float, float],
    v1: Tuple[float, float, float],
    v2: Tuple[float, float, float],
    max_dist: float = 1e9,
) -> Optional[Tuple[Tuple[float, float, float], Tuple[float, float, float], float]]:
    """
    Möller–Trumbore Ray-Triangle Intersection.
    Returns (hit_point, normal, distance) or None.
    """
    e1 = _sub_vec(v1, v0)
    e2 = _sub_vec(v2, v0)
    pvec = _cross_product(direction, e2)
    det = _dot_product(e1, pvec)

    if abs(det) < 1e-10:
        return None

    inv_det = 1.0 / det
    tvec = _sub_vec(origin, v0)
    u = _dot_product(tvec, pvec) * inv_det
    if u < 0.0 or u > 1.0:
        return None

    qvec = _cross_product(tvec, e1)
    v = _dot_product(direction, qvec) * inv_det
    if v < 0.0 or u + v > 1.0:
        return None

    t = _dot_product(e2, qvec) * inv_det
    if t < 1e-8 or t > max_dist:
        return None

    hit_pt = _add_vec(origin, _scale_vec(direction, t))
    norm = _norm_vec(_cross_product(e1, e2))
    return hit_pt, norm, t


def _segments_intersect_2d(
    a: Tuple[float, float],
    b: Tuple[float, float],
    c: Tuple[float, float],
    d: Tuple[float, float],
    eps: float = 1e-8,
) -> bool:
    """Tests if 2D line segment ab intersects 2D line segment cd."""
    def ccw(p1, p2, p3):
        return (p2[0] - p1[0]) * (p3[1] - p1[1]) - (p2[1] - p1[1]) * (p3[0] - p1[0])

    def on_segment(p, q1, q2):
        return (
            min(q1[0], q2[0]) - eps <= p[0] <= max(q1[0], q2[0]) + eps and
            min(q1[1], q2[1]) - eps <= p[1] <= max(q1[1], q2[1]) + eps
        )

    d1 = ccw(a, b, c)
    d2 = ccw(a, b, d)
    d3 = ccw(c, d, a)
    d4 = ccw(c, d, b)

    if ((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps)) and \
       ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps)):
        return True

    if abs(d1) <= eps and on_segment(c, a, b):
        return True
    if abs(d2) <= eps and on_segment(d, a, b):
        return True
    if abs(d3) <= eps and on_segment(a, c, d):
        return True
    if abs(d4) <= eps and on_segment(b, c, d):
        return True

    return False


def _point_in_triangle_2d(
    p: Tuple[float, float],
    v0: Tuple[float, float],
    v1: Tuple[float, float],
    v2: Tuple[float, float],
    eps: float = 1e-8,
) -> bool:
    """Tests if 2D point p is inside or on the boundary of triangle (v0, v1, v2)."""
    def ccw(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    s0 = ccw(v0, v1, p)
    s1 = ccw(v1, v2, p)
    s2 = ccw(v2, v0, p)

    has_neg = (s0 < -eps) or (s1 < -eps) or (s2 < -eps)
    has_pos = (s0 > eps) or (s1 > eps) or (s2 > eps)

    return not (has_neg and has_pos)


def _coplanar_triangle_triangle_intersection_2d(
    t1_v0: Tuple[float, float, float],
    t1_v1: Tuple[float, float, float],
    t1_v2: Tuple[float, float, float],
    t2_v0: Tuple[float, float, float],
    t2_v1: Tuple[float, float, float],
    t2_v2: Tuple[float, float, float],
    normal: Tuple[float, float, float],
) -> bool:
    """
    Evaluates authentic 2D coplanar triangle-triangle intersection.
    Projects 3D coplanar triangles onto the dominant 2D coordinate plane
    (dropping the axis corresponding to the maximum normal component)
    and evaluates:
    1. 2D edge-edge intersection (9 edge pairs).
    2. Point-in-triangle containment (t1 vertices in t2, and t2 vertices in t1).
    """
    norm_sq = normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]
    if norm_sq < 1e-16:
        return False

    abs_x = abs(normal[0])
    abs_y = abs(normal[1])
    abs_z = abs(normal[2])

    if abs_x >= abs_y and abs_x >= abs_z:
        def proj(v): return (v[1], v[2])
    elif abs_y >= abs_x and abs_y >= abs_z:
        def proj(v): return (v[0], v[2])
    else:
        def proj(v): return (v[0], v[1])

    p0, p1, p2 = proj(t1_v0), proj(t1_v1), proj(t1_v2)
    q0, q1, q2 = proj(t2_v0), proj(t2_v1), proj(t2_v2)

    p_edges = ((p0, p1), (p1, p2), (p2, p0))
    q_edges = ((q0, q1), (q1, q2), (q2, q0))

    for ea in p_edges:
        for eb in q_edges:
            if _segments_intersect_2d(ea[0], ea[1], eb[0], eb[1]):
                return True

    for pt in (p0, p1, p2):
        if _point_in_triangle_2d(pt, q0, q1, q2):
            return True
    for pt in (q0, q1, q2):
        if _point_in_triangle_2d(pt, p0, p1, p2):
            return True

    return False


def triangle_triangle_intersection_moller(
    t1_v0: Tuple[float, float, float],
    t1_v1: Tuple[float, float, float],
    t1_v2: Tuple[float, float, float],
    t2_v0: Tuple[float, float, float],
    t2_v1: Tuple[float, float, float],
    t2_v2: Tuple[float, float, float],
) -> bool:
    """
    Tomas Möller 3D triangle-triangle intersection algorithm.
    Returns True if the two triangles intersect, False otherwise.
    """
    n1 = _cross_product(_sub_vec(t1_v1, t1_v0), _sub_vec(t1_v2, t1_v0))
    n1_len = math.sqrt(n1[0] * n1[0] + n1[1] * n1[1] + n1[2] * n1[2])
    if n1_len < 1e-12:
        return False
    d1 = -_dot_product(n1, t1_v0)

    dv0 = (_dot_product(n1, t2_v0) + d1) / n1_len
    dv1 = (_dot_product(n1, t2_v1) + d1) / n1_len
    dv2 = (_dot_product(n1, t2_v2) + d1) / n1_len

    if (dv0 > 1e-7 and dv1 > 1e-7 and dv2 > 1e-7) or (dv0 < -1e-7 and dv1 < -1e-7 and dv2 < -1e-7):
        return False

    n2 = _cross_product(_sub_vec(t2_v1, t2_v0), _sub_vec(t2_v2, t2_v0))
    n2_len = math.sqrt(n2[0] * n2[0] + n2[1] * n2[1] + n2[2] * n2[2])
    if n2_len < 1e-12:
        return False
    d2 = -_dot_product(n2, t2_v0)

    du0 = (_dot_product(n2, t1_v0) + d2) / n2_len
    du1 = (_dot_product(n2, t1_v1) + d2) / n2_len
    du2 = (_dot_product(n2, t1_v2) + d2) / n2_len

    if (du0 > 1e-7 and du1 > 1e-7 and du2 > 1e-7) or (du0 < -1e-7 and du1 < -1e-7 and du2 < -1e-7):
        return False

    d_dir = _cross_product(n1, n2)
    max_d = max(abs(d_dir[0]), abs(d_dir[1]), abs(d_dir[2]))
    if max_d < 1e-8:
        # Triangles are coplanar or nearly parallel
        if abs(dv0) > 1e-6 or abs(dv1) > 1e-6 or abs(dv2) > 1e-6:
            return False
        return _coplanar_triangle_triangle_intersection_2d(
            t1_v0, t1_v1, t1_v2, t2_v0, t2_v1, t2_v2, n1
        )

    # Compute 1D projection intervals along line of intersection
    def _project_triangle(v0, v1, v2, d0, d1, d2):
        pts = []
        for a, b, da, db in [(v0, v1, d0, d1), (v1, v2, d1, d2), (v2, v0, d2, d0)]:
            if (da < -1e-7 and db > 1e-7) or (da > 1e-7 and db < -1e-7):
                alpha = da / (da - db)
                pt = _add_vec(a, _scale_vec(_sub_vec(b, a), alpha))
                pts.append(_dot_product(pt, d_dir))
            elif abs(da) <= 1e-7:
                pts.append(_dot_product(a, d_dir))
        if not pts:
            return None, None
        return min(pts), max(pts)

    t1_min, t1_max = _project_triangle(t1_v0, t1_v1, t1_v2, du0, du1, du2)
    t2_min, t2_max = _project_triangle(t2_v0, t2_v1, t2_v2, dv0, dv1, dv2)

    if t1_min is None or t2_min is None:
        return False

    return not (t1_max < t2_min - 1e-7 or t2_max < t1_min - 1e-7)


@dataclass
class PurePythonAABB:
    min_pt: Tuple[float, float, float]
    max_pt: Tuple[float, float, float]

    def distance_squared(self, p: Tuple[float, float, float]) -> float:
        sq_dist = 0.0
        for i in range(3):
            v = p[i]
            if v < self.min_pt[i]:
                sq_dist += (self.min_pt[i] - v) ** 2
            elif v > self.max_pt[i]:
                sq_dist += (v - self.max_pt[i]) ** 2
        return sq_dist

    def intersects_ray(self, origin: Tuple[float, float, float], direction: Tuple[float, float, float], max_dist: float) -> bool:
        tmin = 0.0
        tmax = max_dist
        for i in range(3):
            if abs(direction[i]) < 1e-12:
                if origin[i] < self.min_pt[i] or origin[i] > self.max_pt[i]:
                    return False
            else:
                inv_d = 1.0 / direction[i]
                t1 = (self.min_pt[i] - origin[i]) * inv_d
                t2 = (self.max_pt[i] - origin[i]) * inv_d
                if t1 > t2:
                    t1, t2 = t2, t1
                tmin = max(tmin, t1)
                tmax = min(tmax, t2)
                if tmin > tmax:
                    return False
        return True

    def intersects_aabb(self, other: PurePythonAABB) -> bool:
        for i in range(3):
            if self.max_pt[i] < other.min_pt[i] or self.min_pt[i] > other.max_pt[i]:
                return False
        return True


__all__ = [
    "_cross_product",
    "_dot_product",
    "_sub_vec",
    "_add_vec",
    "_scale_vec",
    "_norm_vec",
    "_vec_len",
    "point_to_triangle_distance_eberly",
    "ray_triangle_intersection_moller_trumbore",
    "_segments_intersect_2d",
    "_point_in_triangle_2d",
    "_coplanar_triangle_triangle_intersection_2d",
    "triangle_triangle_intersection_moller",
    "PurePythonAABB",
]
