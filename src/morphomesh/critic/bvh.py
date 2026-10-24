"""
MorphoMesh: Pure Python Bounding Volume Hierarchy (BVH) Spatial Index.

Provides PurePythonBVHTree for sub-millisecond ray casting, nearest-neighbor
point-to-surface projection, and triangle-triangle overlap queries without
external C libraries or Blender dependencies.
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

import numpy as np

from .geometry_math import (
    PurePythonAABB,
    _cross_product,
    _dot_product,
    _norm_vec,
    _scale_vec,
    _sub_vec,
    _vec_len,
    point_to_triangle_distance_eberly,
    ray_triangle_intersection_moller_trumbore,
    triangle_triangle_intersection_moller,
)

try:
    import bpy
    import bmesh
    import mathutils
    from mathutils.bvhtree import BVHTree as BlenderBVHTree
    HAS_BLENDER = True
except (ImportError, ModuleNotFoundError):
    bpy = None
    bmesh = None
    mathutils = None
    BlenderBVHTree = None
    HAS_BLENDER = False

class PurePythonBVHNode:
    def __init__(self, bbox: PurePythonAABB, tri_indices: List[int], is_leaf: bool = False):
        self.bbox = bbox
        self.tri_indices = tri_indices
        self.is_leaf = is_leaf
        self.left: Optional[PurePythonBVHNode] = None
        self.right: Optional[PurePythonBVHNode] = None


class PurePythonBVHTree:
    """
    Pure Python spatial bounding volume hierarchy (BVH) tree.
    Provides identical API to Blender's mathutils.bvhtree.BVHTree:
    - FromPolygons(vertices, polygons, all_triangles=True, epsilon=0.0)
    - find_nearest(co, max_dist=1e9) -> (location, normal, index, distance)
    - ray_cast(origin, direction, distance=1e9) -> (location, normal, index, distance)
    - overlap(other_tree) -> List[Tuple[int, int]]
    """

    def __init__(
        self,
        triangles: List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]],
        tri_orig_indices: List[int],
    ):
        self.triangles = triangles
        self.tri_orig_indices = tri_orig_indices
        self.root: Optional[PurePythonBVHNode] = None
        if self.triangles:
            self._build_tree()

    @classmethod
    def FromPolygons(
        cls,
        vertices: Union[List[Any], np.ndarray],
        polygons: Union[List[Any], np.ndarray],
        all_triangles: bool = True,
        epsilon: float = 0.0,
    ) -> PurePythonBVHTree:
        verts_clean: List[Tuple[float, float, float]] = []
        for v in vertices:
            if hasattr(v, "co"):
                co = v.co
                verts_clean.append((float(co[0]), float(co[1]), float(co[2])))
            elif hasattr(v, "__getitem__"):
                verts_clean.append((float(v[0]), float(v[1]), float(v[2])))

        tris: List[Tuple[Tuple[float, float, float], Tuple[float, float, float], Tuple[float, float, float]]] = []
        orig_indices: List[int] = []

        for p_idx, p in enumerate(polygons):
            # Extract vertex indices
            if hasattr(p, "vertices"):
                v_idxs = list(p.vertices)
            elif isinstance(p, (list, tuple, np.ndarray)):
                v_idxs = list(p)
            else:
                continue

            if len(v_idxs) == 3:
                tris.append((verts_clean[v_idxs[0]], verts_clean[v_idxs[1]], verts_clean[v_idxs[2]]))
                orig_indices.append(p_idx)
            elif len(v_idxs) >= 4:
                # Triangulate polygon via fan
                v0 = verts_clean[v_idxs[0]]
                for k in range(1, len(v_idxs) - 1):
                    tris.append((v0, verts_clean[v_idxs[k]], verts_clean[v_idxs[k + 1]]))
                    orig_indices.append(p_idx)

        return cls(tris, orig_indices)

    def _compute_bbox(self, indices: List[int]) -> PurePythonAABB:
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")
        for idx in indices:
            tri = self.triangles[idx]
            for v in tri:
                if v[0] < min_x: min_x = v[0]
                if v[0] > max_x: max_x = v[0]
                if v[1] < min_y: min_y = v[1]
                if v[1] > max_y: max_y = v[1]
                if v[2] < min_z: min_z = v[2]
                if v[2] > max_z: max_z = v[2]
        return PurePythonAABB((min_x, min_y, min_z), (max_x, max_y, max_z))

    def _build_tree(self) -> None:
        centroids = []
        for tri in self.triangles:
            c = (
                (tri[0][0] + tri[1][0] + tri[2][0]) / 3.0,
                (tri[0][1] + tri[1][1] + tri[2][1]) / 3.0,
                (tri[0][2] + tri[1][2] + tri[2][2]) / 3.0,
            )
            centroids.append(c)

        all_indices = list(range(len(self.triangles)))

        def _recursive_build(indices: List[int], depth: int) -> PurePythonBVHNode:
            bbox = self._compute_bbox(indices)
            if len(indices) <= 4 or depth >= 22:
                return PurePythonBVHNode(bbox, indices, is_leaf=True)

            extents = [bbox.max_pt[i] - bbox.min_pt[i] for i in range(3)]
            axis = extents.index(max(extents))

            indices_sorted = sorted(indices, key=lambda i: centroids[i][axis])
            mid = len(indices_sorted) // 2
            left_idxs = indices_sorted[:mid]
            right_idxs = indices_sorted[mid:]

            if not left_idxs or not right_idxs:
                return PurePythonBVHNode(bbox, indices, is_leaf=True)

            node = PurePythonBVHNode(bbox, indices, is_leaf=False)
            node.left = _recursive_build(left_idxs, depth + 1)
            node.right = _recursive_build(right_idxs, depth + 1)
            return node

        self.root = _recursive_build(all_indices, 0)

    def find_nearest(
        self, co: Union[Tuple[float, float, float], List[float], Any], max_dist: float = 1e9
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float]], Optional[int], Optional[float]]:
        """
        Queries closest point on mesh using branch-and-bound traversal.
        Returns (location, normal, polygon_index, distance).
        """
        if self.root is None:
            return None, None, None, None

        p = (float(co[0]), float(co[1]), float(co[2]))
        best_dist = float(max_dist)
        best_pt: Optional[Tuple[float, float, float]] = None
        best_norm: Optional[Tuple[float, float, float]] = None
        best_idx: Optional[int] = None

        pq: List[Tuple[float, int, PurePythonBVHNode]] = []
        counter = 0
        init_dist = math.sqrt(self.root.bbox.distance_squared(p))
        heapq.heappush(pq, (init_dist, counter, self.root))

        while pq:
            node_dist, _, node = heapq.heappop(pq)
            if node_dist >= best_dist:
                continue

            if node.is_leaf:
                for idx in node.tri_indices:
                    tri = self.triangles[idx]
                    cp, norm, d = point_to_triangle_distance_eberly(p, tri[0], tri[1], tri[2])
                    if d < best_dist:
                        best_dist = d
                        best_pt = cp
                        best_norm = norm
                        best_idx = self.tri_orig_indices[idx]
            else:
                if node.left:
                    counter += 1
                    d_l = math.sqrt(node.left.bbox.distance_squared(p))
                    if d_l < best_dist:
                        heapq.heappush(pq, (d_l, counter, node.left))
                if node.right:
                    counter += 1
                    d_r = math.sqrt(node.right.bbox.distance_squared(p))
                    if d_r < best_dist:
                        heapq.heappush(pq, (d_r, counter, node.right))

        if best_pt is None:
            return None, None, None, None

        return best_pt, best_norm, best_idx, best_dist

    def ray_cast(
        self,
        origin: Union[Tuple[float, float, float], List[float], Any],
        direction: Union[Tuple[float, float, float], List[float], Any],
        distance: float = 1e9,
    ) -> Tuple[Optional[Tuple[float, float, float]], Optional[Tuple[float, float, float]], Optional[int], Optional[float]]:
        """
        Casts ray against mesh.
        Returns (location, normal, polygon_index, distance).
        """
        if self.root is None:
            return None, None, None, None

        o = (float(origin[0]), float(origin[1]), float(origin[2]))
        d_raw = (float(direction[0]), float(direction[1]), float(direction[2]))
        d = _norm_vec(d_raw)

        best_t = float(distance)
        best_pt: Optional[Tuple[float, float, float]] = None
        best_norm: Optional[Tuple[float, float, float]] = None
        best_idx: Optional[int] = None

        stack = [self.root]
        while stack:
            node = stack.pop()
            if not node.bbox.intersects_ray(o, d, best_t):
                continue

            if node.is_leaf:
                for idx in node.tri_indices:
                    tri = self.triangles[idx]
                    res = ray_triangle_intersection_moller_trumbore(o, d, tri[0], tri[1], tri[2], max_dist=best_t)
                    if res is not None:
                        hit_pt, norm, hit_t = res
                        if hit_t < best_t:
                            best_t = hit_t
                            best_pt = hit_pt
                            best_norm = norm
                            best_idx = self.tri_orig_indices[idx]
            else:
                if node.left: stack.append(node.left)
                if node.right: stack.append(node.right)

        if best_pt is None:
            return None, None, None, None

        return best_pt, best_norm, best_idx, best_t

    def overlap(self, other_tree: PurePythonBVHTree) -> List[Tuple[int, int]]:
        """
        Simultaneous dual-tree descent finding overlapping triangle pairs.
        Returns list of (orig_poly_idx_a, orig_poly_idx_b).
        """
        if self.root is None or other_tree.root is None:
            return []

        pairs: Set[Tuple[int, int]] = set()
        stack = [(self.root, other_tree.root)]

        while stack:
            node_a, node_b = stack.pop()
            if not node_a.bbox.intersects_aabb(node_b.bbox):
                continue

            if node_a.is_leaf and node_b.is_leaf:
                for idx_a in node_a.tri_indices:
                    tri_a = self.triangles[idx_a]
                    for idx_b in node_b.tri_indices:
                        tri_b = other_tree.triangles[idx_b]
                        if triangle_triangle_intersection_moller(
                            tri_a[0], tri_a[1], tri_a[2],
                            tri_b[0], tri_b[1], tri_b[2],
                        ):
                            pairs.add((self.tri_orig_indices[idx_a], other_tree.tri_orig_indices[idx_b]))
            elif node_a.is_leaf:
                if node_b.left: stack.append((node_a, node_b.left))
                if node_b.right: stack.append((node_a, node_b.right))
            elif node_b.is_leaf:
                if node_a.left: stack.append((node_a.left, node_b))
                if node_a.right: stack.append((node_a.right, node_b))
            else:
                if node_a.left and node_b.left: stack.append((node_a.left, node_b.left))
                if node_a.left and node_b.right: stack.append((node_a.left, node_b.right))
                if node_a.right and node_b.left: stack.append((node_a.right, node_b.left))
                if node_a.right and node_b.right: stack.append((node_a.right, node_b.right))

        return sorted(list(pairs))


def get_bvh_tree(
    vertices: Union[List[Any], np.ndarray],
    polygons: Union[List[Any], np.ndarray],
    prefer_blender: bool = True,
) -> Any:
    """
    Factory creating a spatial BVH tree.
    Uses Blender's native C-accelerated mathutils.bvhtree.BVHTree when inside Blender,
    or falls back cleanly to PurePythonBVHTree for offline CI/test environments.
    """
    if prefer_blender and HAS_BLENDER and BlenderBVHTree is not None:
        try:
            return BlenderBVHTree.FromPolygons(vertices, polygons)
        except Exception:
            pass
    return PurePythonBVHTree.FromPolygons(vertices, polygons)

__all__ = [
    "PurePythonBVHNode",
    "PurePythonBVHTree",
    "get_bvh_tree",
    "BlenderBVHTree",
    "HAS_BLENDER",
    "bpy",
]
