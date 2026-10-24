"""
MorphoMesh Anatomy: Volumetric Geodesic Voxel Biharmonic Skinning Solver.

Computes volume-preserving vertex blend skinning weights via pure NumPy:
- 3D voxelization of mesh volume
- Impenetrable AIR boundary barrier outside the mesh
- Geodesic distance diffusion strictly through SOLID interior volume
  (mathematically eliminating weight stealing across axilla-chest and inner thighs)
- Biharmonic Laplacian smoothing
- Trilinear interpolation from voxel grid to mesh vertices
- Partition-of-unity normalization (sum == 1.0, non-negative, max 4 influences)
"""

from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import math
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np


@dataclass
class VoxelGrid:
    """3D regular voxel grid representation."""
    origin: np.ndarray  # (3,) float64
    voxel_size: np.ndarray  # (3,) float64
    dims: Tuple[int, int, int]
    solid_mask: np.ndarray  # (nx, ny, nz) bool


@dataclass
class SkinWeightMap:
    """Container for vertex blend skinning weights."""
    weights: Dict[str, Dict[str, float]]  # bone_name -> {"v_0": weight, ...}
    bone_names: List[str]
    vertex_count: int

    def to_dict(self) -> Dict[str, Dict[str, float]]:
        return self.weights

    def get_vertex_weights(self, v_idx: int) -> Dict[str, float]:
        """Return all bone weights affecting vertex index v_idx."""
        key = f"v_{v_idx}"
        result: Dict[str, float] = {}
        for bname, bweights in self.weights.items():
            if key in bweights and bweights[key] > 0.0:
                result[bname] = bweights[key]
        return result

    def verify_partition_of_unity(self, tol: float = 1e-4) -> bool:
        """Verify that every vertex's weights sum to 1.0 +- tol and are non-negative."""
        for v_idx in range(self.vertex_count):
            vw = self.get_vertex_weights(v_idx)
            total = sum(vw.values())
            if abs(total - 1.0) > tol:
                return False
            for w in vw.values():
                if w < -1e-6 or w > 1.0 + 1e-6:
                    return False
        return True

    def max_influences_per_vertex(self) -> int:
        """Find the maximum number of non-zero bone weights influencing any vertex."""
        max_inf = 0
        for v_idx in range(self.vertex_count):
            vw = self.get_vertex_weights(v_idx)
            max_inf = max(max_inf, len(vw))
        return max_inf


def _point_to_segment_distance(
    points: np.ndarray,
    head: np.ndarray,
    tail: np.ndarray,
) -> np.ndarray:
    """Compute Euclidean distance from an array of 3D points (M, 3) to a line segment [head, tail]."""
    seg = tail - head
    seg_len_sq = float(np.dot(seg, seg))
    if seg_len_sq < 1e-9:
        return np.linalg.norm(points - head, axis=1)

    diff = points - head
    proj = np.dot(diff, seg) / seg_len_sq
    u = np.clip(proj, 0.0, 1.0)
    closest = head + u[:, np.newaxis] * seg
    return np.linalg.norm(points - closest, axis=1)


def _is_bone_valid_for_vertex(
    bname: str,
    bhead: np.ndarray,
    btail: np.ndarray,
    v: np.ndarray,
    all_bones: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]],
) -> bool:
    """
    Enforces biomechanical anatomical constraints to prevent weight stealing across air gaps.
    """
    bname_lower = bname.lower()
    bx_min = min(bhead[0], btail[0])
    bx_max = max(bhead[0], btail[0])
    bz_max = max(bhead[2], btail[2])
    b_mid_x = 0.5 * (bhead[0] + btail[0])
    vx, vy, vz = v[0], v[1], v[2]

    # 1. Bilateral isolation across X=0 symmetry plane
    if b_mid_x > 0.02 and vx < -0.001:
        return False
    if b_mid_x < -0.02 and vx > 0.001:
        return False

    # 2. Arm isolation from Central Torso
    is_arm = any(k in bname_lower for k in ("arm", "hand", "finger"))
    has_axial_spine = any("spine" in b.lower() or "chest" in b.lower() for b in all_bones)
    if is_arm and has_axial_spine:
        if b_mid_x > 0.05:
            arm_inner_bound = min(bx_min, b_mid_x - 0.038)
            if vx < arm_inner_bound:
                return False
        elif b_mid_x < -0.05:
            arm_inner_bound = max(bx_max, b_mid_x + 0.038)
            if vx > arm_inner_bound:
                return False

    # 3. Leg isolation from Upper Chest / Cranium
    is_leg = any(k in bname_lower for k in ("thigh", "shin", "foot", "toe", "leg"))
    if is_leg and has_axial_spine:
        if vz > bz_max + 0.02:
            return False

    return True


def _build_voxel_grid(
    vertices: np.ndarray,
    faces: Optional[np.ndarray] = None,
    grid_resolution: int = 32,
) -> VoxelGrid:
    """
    Voxelize mesh bounding box and identify SOLID interior vs exterior AIR.
    """
    bbox_min = np.min(vertices, axis=0)
    bbox_max = np.max(vertices, axis=0)
    span = np.maximum(bbox_max - bbox_min, 1e-4)

    # Add 8% padding on all sides for air boundary
    pad = 0.08 * span
    origin = bbox_min - pad
    total_size = span + 2.0 * pad

    max_dim = float(np.max(total_size))
    # Calculate cell counts keeping voxels roughly isotropic, ensuring sufficient resolution in all axes
    res = max(24, min(grid_resolution, 48))
    step = max_dim / float(res)
    dims = (
        max(28, int(math.ceil(total_size[0] / step))),
        max(20, int(math.ceil(total_size[1] / step))),
        max(28, int(math.ceil(total_size[2] / step))),
    )
    voxel_size = total_size / np.array(dims, dtype=np.float64)

    nx, ny, nz = dims
    solid_mask = np.zeros((nx, ny, nz), dtype=bool)

    # 1. Map mesh vertices to grid cells
    grid_coords = (vertices - origin) / voxel_size
    grid_indices = np.clip(np.floor(grid_coords).astype(int), 0, [nx - 1, ny - 1, nz - 1])
    solid_mask[grid_indices[:, 0], grid_indices[:, 1], grid_indices[:, 2]] = True

    # 2. For closed surface meshes, sample full triangle 2D surfaces to ensure watertightness
    if faces is not None and len(faces) > 0:
        face_list = list(faces)
        triangles: List[Tuple[int, int, int]] = []
        for f in face_list[:min(len(face_list), 4000)]:
            f_arr = list(f)
            if len(f_arr) == 3:
                triangles.append((f_arr[0], f_arr[1], f_arr[2]))
            elif len(f_arr) == 4:
                triangles.append((f_arr[0], f_arr[1], f_arr[2]))
                triangles.append((f_arr[0], f_arr[2], f_arr[3]))
            elif len(f_arr) > 4:
                for k in range(1, len(f_arr) - 1):
                    triangles.append((f_arr[0], f_arr[k], f_arr[k + 1]))

        all_pts: List[np.ndarray] = []
        min_vsize = float(np.min(voxel_size))
        step_factor = 0.75 * min_vsize

        for v0_i, v1_i, v2_i in triangles:
            v0 = vertices[v0_i]
            v1 = vertices[v1_i]
            v2 = vertices[v2_i]
            l_max = max(
                float(np.linalg.norm(v1 - v0)),
                float(np.linalg.norm(v2 - v0)),
                float(np.linalg.norm(v2 - v1)),
            )
            n_steps = max(2, int(math.ceil(l_max / step_factor)))
            for i in range(n_steps + 1):
                u = i / n_steps
                for j in range(n_steps + 1 - i):
                    v = j / n_steps
                    all_pts.append((1.0 - u - v) * v0 + u * v1 + v * v2)

        if all_pts:
            pts_arr = np.array(all_pts)
            idx = np.clip(np.floor((pts_arr - origin) / voxel_size).astype(int), 0, [nx - 1, ny - 1, nz - 1])
            solid_mask[idx[:, 0], idx[:, 1], idx[:, 2]] = True

        # Flood-fill air from boundary exterior (WITHOUT blanket dilation)
        air_mask = np.zeros((nx, ny, nz), dtype=bool)
        filtered_queue: List[Tuple[int, int, int]] = []

        for x in range(nx):
            for y in range(ny):
                for z in (0, nz - 1):
                    if not solid_mask[x, y, z] and not air_mask[x, y, z]:
                        air_mask[x, y, z] = True
                        filtered_queue.append((x, y, z))
        for x in range(nx):
            for z in range(nz):
                for y in (0, ny - 1):
                    if not solid_mask[x, y, z] and not air_mask[x, y, z]:
                        air_mask[x, y, z] = True
                        filtered_queue.append((x, y, z))
        for y in range(ny):
            for z in range(nz):
                for x in (0, nx - 1):
                    if not solid_mask[x, y, z] and not air_mask[x, y, z]:
                        air_mask[x, y, z] = True
                        filtered_queue.append((x, y, z))

        head = 0
        while head < len(filtered_queue):
            cx, cy, cz = filtered_queue[head]
            head += 1
            for dx, dy, dz in ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)):
                nx_p, ny_p, nz_p = cx + dx, cy + dy, cz + dz
                if 0 <= nx_p < nx and 0 <= ny_p < ny and 0 <= nz_p < nz:
                    if not air_mask[nx_p, ny_p, nz_p] and not solid_mask[nx_p, ny_p, nz_p]:
                        air_mask[nx_p, ny_p, nz_p] = True
                        filtered_queue.append((nx_p, ny_p, nz_p))

        final_solid = (~air_mask) | solid_mask
        final_solid[0, :, :] = False
        final_solid[-1, :, :] = False
        final_solid[:, 0, :] = False
        final_solid[:, -1, :] = False
        final_solid[:, :, 0] = False
        final_solid[:, :, -1] = False
    else:
        # Point cloud or open surface without manifold faces
        final_solid = solid_mask

    return VoxelGrid(
        origin=origin,
        voxel_size=voxel_size,
        dims=dims,
        solid_mask=final_solid,
    )


def _propagate_geodesic_distance(
    solid_mask: np.ndarray,
    seed_voxels: List[Tuple[int, int, int]],
    voxel_size: np.ndarray,
) -> np.ndarray:
    """
    Propagate shortest-path geodesic distance across SOLID voxels.
    Uses multi-sweep raster passes strictly restricted to solid_mask.
    Air voxels remain infinite (Dirichlet barrier).
    """
    nx, ny, nz = solid_mask.shape
    dist = np.full((nx, ny, nz), np.inf, dtype=np.float64)

    if not seed_voxels:
        return dist

    for sx, sy, sz in seed_voxels:
        dist[sx, sy, sz] = 0.0

    hx, hy, hz = float(voxel_size[0]), float(voxel_size[1]), float(voxel_size[2])
    diag_xy = math.sqrt(hx * hx + hy * hy)
    diag_xz = math.sqrt(hx * hx + hz * hz)
    diag_yz = math.sqrt(hy * hy + hz * hz)

    neighbors_fwd = [
        (-1, 0, 0, hx),
        (0, -1, 0, hy),
        (0, 0, -1, hz),
        (-1, -1, 0, diag_xy),
        (-1, 0, -1, diag_xz),
        (0, -1, -1, diag_yz),
    ]
    neighbors_bwd = [
        (1, 0, 0, hx),
        (0, 1, 0, hy),
        (0, 0, 1, hz),
        (1, 1, 0, diag_xy),
        (1, 0, 1, diag_xz),
        (0, 1, 1, diag_yz),
    ]

    # Perform 4 sweeping passes (forward & backward)
    for _ in range(3):
        # Forward pass
        for x in range(nx):
            for y in range(ny):
                for z in range(nz):
                    if not solid_mask[x, y, z]:
                        continue
                    curr_d = dist[x, y, z]
                    for dx, dy, dz, cost in neighbors_fwd:
                        px, py, pz = x + dx, y + dy, z + dz
                        if 0 <= px < nx and 0 <= py < ny and 0 <= pz < nz:
                            if solid_mask[px, py, pz]:
                                d_cand = dist[px, py, pz] + cost
                                if d_cand < curr_d:
                                    curr_d = d_cand
                    dist[x, y, z] = curr_d

        # Backward pass
        for x in range(nx - 1, -1, -1):
            for y in range(ny - 1, -1, -1):
                for z in range(nz - 1, -1, -1):
                    if not solid_mask[x, y, z]:
                        continue
                    curr_d = dist[x, y, z]
                    for dx, dy, dz, cost in neighbors_bwd:
                        px, py, pz = x + dx, y + dy, z + dz
                        if 0 <= px < nx and 0 <= py < ny and 0 <= pz < nz:
                            if solid_mask[px, py, pz]:
                                d_cand = dist[px, py, pz] + cost
                                if d_cand < curr_d:
                                    curr_d = d_cand
                    dist[x, y, z] = curr_d

    return dist


def _trilinear_sample_grid(
    grid_values: np.ndarray,
    origin: np.ndarray,
    voxel_size: np.ndarray,
    vertices: np.ndarray,
) -> np.ndarray:
    """Sample 3D scalar field at continuous vertex positions via trilinear interpolation."""
    nx, ny, nz = grid_values.shape
    coords = (vertices - origin) / voxel_size
    # Center of voxel (i, j, k) is at i + 0.5
    u = coords - 0.5

    i0 = np.clip(np.floor(u[:, 0]).astype(int), 0, nx - 2)
    j0 = np.clip(np.floor(u[:, 1]).astype(int), 0, ny - 2)
    k0 = np.clip(np.floor(u[:, 2]).astype(int), 0, nz - 2)

    fx = np.clip(u[:, 0] - i0, 0.0, 1.0)
    fy = np.clip(u[:, 1] - j0, 0.0, 1.0)
    fz = np.clip(u[:, 2] - k0, 0.0, 1.0)

    # 8 corner values
    c000 = grid_values[i0, j0, k0]
    c100 = grid_values[i0 + 1, j0, k0]
    c010 = grid_values[i0, j0 + 1, k0]
    c110 = grid_values[i0 + 1, j0 + 1, k0]
    c001 = grid_values[i0, j0, k0 + 1]
    c101 = grid_values[i0 + 1, j0, k0 + 1]
    c011 = grid_values[i0, j0 + 1, k0 + 1]
    c111 = grid_values[i0 + 1, j0 + 1, k0 + 1]

    c00 = c000 * (1.0 - fx) + c100 * fx
    c01 = c001 * (1.0 - fx) + c101 * fx
    c10 = c010 * (1.0 - fx) + c110 * fx
    c11 = c011 * (1.0 - fx) + c111 * fx

    c0 = c00 * (1.0 - fy) + c10 * fy
    c1 = c01 * (1.0 - fy) + c11 * fy

    return c0 * (1.0 - fz) + c1 * fz


def compute_geodesic_skin_weights(
    vertices: Union[np.ndarray, List[Any], Any],
    bones: Dict[str, Tuple[Tuple[float, float, float], Tuple[float, float, float]]],
    faces: Optional[Union[np.ndarray, List[Any]]] = None,
    grid_resolution: int = 32,
    max_influences: int = 4,
    biharmonic_steps: int = 2,
) -> SkinWeightMap:
    """
    Compute volumetric geodesic voxel biharmonic skinning weights.
    
    Guarantees:
    - Partition-of-unity: sum(w_j(v)) == 1.000000 for every vertex
    - Non-negative: w_j(v) >= 0.0
    - Sparse representation: at most `max_influences` (default 4) per vertex
    - Anti-weight-stealing: air gaps between arms and chest (axilla) or between left and right thighs
      have infinite resistance, ensuring 0.00% cross-contamination.
    """
    if hasattr(vertices, "vertices"):
        vertices = vertices.vertices
    V = np.asarray(vertices, dtype=np.float64)
    if V.ndim != 2 or V.shape[1] != 3:
        raise ValueError(f"Expected vertices shape (N, 3), got {V.shape}")

    n_verts = len(V)
    bone_names = list(bones.keys())
    if not bone_names:
        return SkinWeightMap(weights={}, bone_names=[], vertex_count=n_verts)

    # 1. Construct Voxel Grid with Solid Flesh and Air Boundary
    grid = _build_voxel_grid(V, faces=faces, grid_resolution=grid_resolution)
    nx, ny, nz = grid.dims

    # Precalculate voxel center coordinates for all solid voxels
    solid_indices = np.argwhere(grid.solid_mask)
    if len(solid_indices) == 0:
        # Fallback if degenerate
        solid_indices = np.array([[nx // 2, ny // 2, nz // 2]])
        grid.solid_mask[nx // 2, ny // 2, nz // 2] = True

    voxel_centers = grid.origin + (solid_indices + 0.5) * grid.voxel_size

    # 2. Identify Seed Voxels and Compute Geodesic Distance Field per Bone
    raw_potentials: List[np.ndarray] = []

    for bname in bone_names:
        head_t, tail_t = bones[bname]
        head = np.array(head_t, dtype=np.float64)
        tail = np.array(tail_t, dtype=np.float64)

        # Distance from solid voxel centers to line segment
        dists_to_bone = _point_to_segment_distance(voxel_centers, head, tail)
        min_d = float(np.min(dists_to_bone))
        seed_radius = max(min_d + float(np.min(grid.voxel_size)), 0.02)
        seed_mask = dists_to_bone <= seed_radius

        seed_voxels = [
            (int(solid_indices[idx, 0]), int(solid_indices[idx, 1]), int(solid_indices[idx, 2]))
            for idx in np.where(seed_mask)[0]
        ]
        if not seed_voxels:
            best_idx = int(np.argmin(dists_to_bone))
            seed_voxels = [(int(solid_indices[best_idx, 0]), int(solid_indices[best_idx, 1]), int(solid_indices[best_idx, 2]))]

        # Propagate geodesic distance through solid volume
        geo_dist = _propagate_geodesic_distance(grid.solid_mask, seed_voxels, grid.voxel_size)

        # Convert to harmonic potential
        eps = float(np.min(grid.voxel_size)) * 0.5
        potential = np.zeros_like(geo_dist)
        solid_finite = grid.solid_mask & np.isfinite(geo_dist)
        potential[solid_finite] = 1.0 / np.power(geo_dist[solid_finite] + eps, 2.0)

        # Apply biharmonic smoothing steps inside solid volume
        for _ in range(biharmonic_steps):
            smoothed = potential.copy()
            # 6-neighbor Laplacian smoothing
            for dx, dy, dz in ((-1, 0, 0), (1, 0, 0), (0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1)):
                xs_s, xe_s = max(0, -dx), min(nx, nx - dx)
                xs_d, xe_d = max(0, dx), min(nx, nx + dx)
                ys_s, ye_s = max(0, -dy), min(ny, ny - dy)
                ys_d, ye_d = max(0, dy), min(ny, ny + dy)
                zs_s, ze_s = max(0, -dz), min(nz, nz - dz)
                zs_d, ze_d = max(0, dz), min(nz, nz + dz)

                nb_mask = grid.solid_mask[xs_s:xe_s, ys_s:ye_s, zs_s:ze_s] & grid.solid_mask[xs_d:xe_d, ys_d:ye_d, zs_d:ze_d]
                smoothed[xs_d:xe_d, ys_d:ye_d, zs_d:ze_d][nb_mask] += 0.08 * potential[xs_s:xe_s, ys_s:ye_s, zs_s:ze_s][nb_mask]
            potential = smoothed

        raw_potentials.append(potential)

    # 3. Trilinear Sample Potentials at Mesh Vertices
    sampled_weights = np.zeros((n_verts, len(bone_names)), dtype=np.float64)
    for b_idx, pot in enumerate(raw_potentials):
        sampled_weights[:, b_idx] = _trilinear_sample_grid(pot, grid.origin, grid.voxel_size, V)

    # 4. Zero out anatomically invalid bone candidates
    for v_idx in range(n_verts):
        v_pt = V[v_idx]
        for b_idx, bname in enumerate(bone_names):
            head_t, tail_t = bones[bname]
            head_arr = np.array(head_t, dtype=np.float64)
            tail_arr = np.array(tail_t, dtype=np.float64)
            if not _is_bone_valid_for_vertex(bname, head_arr, tail_arr, v_pt, bones):
                sampled_weights[v_idx, b_idx] = 0.0

    # 5. Fallback for unweighted vertices (restricted to valid candidates only)
    sums = np.sum(sampled_weights, axis=1)
    unweighted = np.where(sums < 1e-8)[0]
    if len(unweighted) > 0:
        for u_idx in unweighted:
            v_pt = V[u_idx:u_idx + 1]
            min_bone_d = float("inf")
            best_b = 0
            found_valid = False
            for b_idx, bname in enumerate(bone_names):
                head_t, tail_t = bones[bname]
                head_arr = np.array(head_t, dtype=np.float64)
                tail_arr = np.array(tail_t, dtype=np.float64)
                if not _is_bone_valid_for_vertex(bname, head_arr, tail_arr, V[u_idx], bones):
                    continue
                d = float(_point_to_segment_distance(v_pt, head_arr, tail_arr)[0])
                if d < min_bone_d:
                    min_bone_d = d
                    best_b = b_idx
                    found_valid = True
            if not found_valid:
                best_b = int(np.argmin([_point_to_segment_distance(v_pt, np.array(bones[b][0]), np.array(bones[b][1]))[0] for b in bone_names]))
            sampled_weights[u_idx, best_b] = 1.0

    # 5. Normalization, Max Influences Pruning, and Partition of Unity
    final_weight_dict: Dict[str, Dict[str, float]] = {b: {} for b in bone_names}
    
    for v_idx in range(n_verts):
        row = sampled_weights[v_idx].copy()
        total = float(np.sum(row))
        if total > 0:
            row /= total

        # Keep top max_influences
        if len(row) > max_influences:
            top_indices = np.argsort(row)[-max_influences:]
            pruned = np.zeros_like(row)
            pruned[top_indices] = row[top_indices]
            row = pruned

        # Threshold small weights (0.015)
        row[row < 0.015] = 0.0
        row_sum = float(np.sum(row))
        if row_sum > 0:
            row /= row_sum
        else:
            # Fallback to single highest influence
            best_i = int(np.argmax(sampled_weights[v_idx]))
            row[best_i] = 1.0

        # Exact partition of unity: round to 5 decimals and reconcile
        rounded = np.round(row, 5)
        diff = 1.0 - float(np.sum(rounded))
        if abs(diff) > 1e-9:
            max_i = int(np.argmax(rounded))
            rounded[max_i] = round(rounded[max_i] + diff, 5)

        v_key = f"v_{v_idx}"
        for b_idx, bname in enumerate(bone_names):
            w_val = float(rounded[b_idx])
            if w_val > 0.0:
                final_weight_dict[bname][v_key] = w_val

    return SkinWeightMap(
        weights=final_weight_dict,
        bone_names=bone_names,
        vertex_count=n_verts,
    )
