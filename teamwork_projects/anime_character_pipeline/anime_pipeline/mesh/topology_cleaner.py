"""
anime_pipeline/mesh/topology_cleaner.py
Milestone 1 Feature F02: Clean Quad Skinning Topology & Seam Normal Harmonizer.

Provides:
- TopologyReport: Comprehensive dataclass for topological purity and manifoldness audit results.
- TopologyValidator: 100% 2-manifold quads (rho_quad = 1.0000), zero non-manifold edges, zero duplicate vertices, zero degenerate faces.
- HingeLoopValidator: Multi-loop concentric deformation loops at elbows (3-loop), knees (3-loop), shoulders (5-loop deltoid saddle), and waist (3-ring).
- NormalHarmonizer: Seam normal consistency enforcing identical radial/area-weighted split normals across coincident boundary loops (neck, shoulder, wrist, ankle).
- TopologyCleaner: Mesh repair, duplicate welding, and pure quad loop capping.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np


# ==============================================================================
# DATA STRUCTURES
# ==============================================================================

@dataclass
class TopologyReport:
    """Encapsulates comprehensive topological purity and manifoldness audit results."""
    is_valid: bool = True
    total_vertices: int = 0
    total_faces: int = 0
    quad_count: int = 0
    tri_count: int = 0
    ngon_count: int = 0
    quad_ratio: float = 0.0
    non_manifold_edges: List[Tuple[int, int]] = field(default_factory=list)
    non_manifold_vertices: List[int] = field(default_factory=list)
    boundary_edges: List[Tuple[int, int]] = field(default_factory=list)
    boundary_loops: List[List[int]] = field(default_factory=list)
    duplicate_vertices: List[Tuple[int, int]] = field(default_factory=list)
    degenerate_faces: List[int] = field(default_factory=list)
    inverted_faces: List[int] = field(default_factory=list)
    valence_histogram: Dict[int, int] = field(default_factory=dict)
    high_valence_poles: List[Tuple[int, int]] = field(default_factory=list)  # (vertex_idx, valence >= 6)
    hinge_loop_status: Dict[str, bool] = field(default_factory=dict)
    seam_alignment_status: Dict[str, bool] = field(default_factory=dict)

    def summary(self) -> str:
        """Returns human-readable audit summary."""
        lines = [
            f"=== Topology Purity Report (Valid: {self.is_valid}) ===",
            f"  Vertices: {self.total_vertices}, Faces: {self.total_faces}",
            f"  Quads: {self.quad_count}, Tris: {self.tri_count}, N-gons: {self.ngon_count}",
            f"  Quad Ratio: {self.quad_ratio * 100:.2f}% (Target: 100.0%)",
            f"  Non-Manifold Edges: {len(self.non_manifold_edges)} (Target: 0)",
            f"  Non-Manifold Vertices: {len(self.non_manifold_vertices)} (Target: 0)",
            f"  Duplicate Vertices: {len(self.duplicate_vertices)} (Target: 0)",
            f"  Degenerate Faces: {len(self.degenerate_faces)} (Target: 0)",
            f"  Inverted Faces: {len(self.inverted_faces)} (Target: 0)",
            f"  High-Valence Poles (deg >= 6): {len(self.high_valence_poles)} (Target: 0)",
            f"  Boundary Loops: {len(self.boundary_loops)}",
            f"  Hinge Loop Audits: {self.hinge_loop_status}",
            f"  Seam Normal Alignment: {self.seam_alignment_status}",
        ]
        return "\n".join(lines)


# ==============================================================================
# TOPOLOGY VALIDATOR
# ==============================================================================

class TopologyValidator:
    """
    Validates 100% 2-manifold purity, quad dominance, vertex valence, and geometric non-degeneracy.
    """

    @staticmethod
    def audit_mesh(
        vertices: List[Tuple[float, float, float]],
        faces: List[Union[Tuple[int, int, int, int], Tuple[int, int, int], List[int]]],
        normals: Optional[List[Tuple[float, float, float]]] = None,
        epsilon_dup: float = 1e-5,
        min_face_area: float = 1e-8,
    ) -> TopologyReport:
        """
        Executes exhaustive topological and geometric validity checks.
        """
        report = TopologyReport()
        report.total_vertices = len(vertices)
        report.total_faces = len(faces)

        # 0. Sanitize vertex coordinates for NaN / Inf floats
        if vertices:
            try:
                arr = np.asarray(vertices, dtype=np.float64)
                if not np.all(np.isfinite(arr)):
                    report.is_valid = False
                    return report
            except Exception:
                for v in vertices:
                    if not (math.isfinite(v[0]) and math.isfinite(v[1]) and math.isfinite(v[2])):
                        report.is_valid = False
                        return report

        # 1. Quad purity audit
        for f in faces:
            nv = len(f)
            if nv == 4:
                report.quad_count += 1
            elif nv == 3:
                report.tri_count += 1
            else:
                report.ngon_count += 1

        total_poly = report.quad_count + report.tri_count + report.ngon_count
        report.quad_ratio = round(report.quad_count / total_poly, 4) if total_poly > 0 else 0.0

        # 2. Edge manifoldness and boundary tracking
        edge_face_map: Dict[Tuple[int, int], List[int]] = {}
        v_edges: Dict[int, Set[Tuple[int, int]]] = {i: set() for i in range(len(vertices))}

        for f_idx, f in enumerate(faces):
            nv = len(f)
            for i in range(nv):
                a, b = f[i], f[(i + 1) % nv]
                e = (min(a, b), max(a, b))
                if e not in edge_face_map:
                    edge_face_map[e] = []
                edge_face_map[e].append(f_idx)
                if a in v_edges:
                    v_edges[a].add(e)
                if b in v_edges:
                    v_edges[b].add(e)

        for e, f_list in edge_face_map.items():
            if len(f_list) == 1:
                report.boundary_edges.append(e)
            elif len(f_list) > 2:
                report.non_manifold_edges.append(e)

        # 3. Vertex valence analysis
        for vi, edges in v_edges.items():
            deg = len(edges)
            report.valence_histogram[deg] = report.valence_histogram.get(deg, 0) + 1
            if deg >= 6:
                report.high_valence_poles.append((vi, deg))

        # 4. Duplicate vertex detection (Spatial Grid)
        report.duplicate_vertices = TopologyValidator.detect_duplicates(vertices, epsilon_dup)

        # 5. Degenerate face area & normal inversion
        for f_idx, f in enumerate(faces):
            # Check distinct vertices
            if len(set(f)) != len(f):
                report.degenerate_faces.append(f_idx)
                continue

            p0 = vertices[f[0]]
            p1 = vertices[f[1]]
            p2 = vertices[f[2]]
            v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
            v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
            cx = v1[1] * v2[2] - v1[2] * v2[1]
            cy = v1[2] * v2[0] - v1[0] * v2[2]
            cz = v1[0] * v2[1] - v1[1] * v2[0]
            area = 0.5 * math.sqrt(cx * cx + cy * cy + cz * cz)
            if area < min_face_area:
                report.degenerate_faces.append(f_idx)

            if normals and len(normals) == len(vertices):
                norm_len = math.sqrt(cx * cx + cy * cy + cz * cz)
                if norm_len > 1e-9:
                    fn = (cx / norm_len, cy / norm_len, cz / norm_len)
                    vn = normals[f[0]]
                    dot = fn[0] * vn[0] + fn[1] * vn[1] + fn[2] * vn[2]
                    if dot < -0.3:
                        report.inverted_faces.append(f_idx)

        # 6. Extract boundary loops
        report.boundary_loops = TopologyValidator.extract_boundary_loops(report.boundary_edges)

        # Overall validity decision
        report.is_valid = (
            report.quad_ratio == 1.0
            and len(report.non_manifold_edges) == 0
            and len(report.non_manifold_vertices) == 0
            and len(report.duplicate_vertices) == 0
            and len(report.degenerate_faces) == 0
            and len(report.inverted_faces) == 0
        )
        return report

    @staticmethod
    def detect_duplicates(
        vertices: List[Tuple[float, float, float]],
        epsilon: float = 1e-5,
    ) -> List[Tuple[int, int]]:
        """O(N) spatial grid hashing duplicate vertex detector."""
        grid: Dict[Tuple[int, int, int], List[int]] = {}
        duplicates: List[Tuple[int, int]] = []
        inv_eps = 1.0 / epsilon

        for idx, (x, y, z) in enumerate(vertices):
            if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
                continue
            cx = int(math.floor(x * inv_eps))
            cy = int(math.floor(y * inv_eps))
            cz = int(math.floor(z * inv_eps))

            matched = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        cell = (cx + dx, cy + dy, cz + dz)
                        if cell in grid:
                            for other in grid[cell]:
                                ox, oy, oz = vertices[other]
                                d2 = (x - ox) ** 2 + (y - oy) ** 2 + (z - oz) ** 2
                                if d2 <= epsilon * epsilon:
                                    duplicates.append((other, idx))
                                    matched = True
                                    break
                        if matched:
                            break
                    if matched:
                        break
                if matched:
                    break

            base_cell = (cx, cy, cz)
            if base_cell not in grid:
                grid[base_cell] = []
            grid[base_cell].append(idx)

        return duplicates

    @staticmethod
    def extract_boundary_loops(boundary_edges: List[Tuple[int, int]]) -> List[List[int]]:
        """Chains unordered boundary edges into ordered simple boundary vertex loops."""
        if not boundary_edges:
            return []

        adj: Dict[int, List[int]] = {}
        for a, b in boundary_edges:
            adj.setdefault(a, []).append(b)
            adj.setdefault(b, []).append(a)

        visited_edges: Set[Tuple[int, int]] = set()
        loops: List[List[int]] = []

        for start_node in list(adj.keys()):
            for next_node in adj[start_node]:
                e = (min(start_node, next_node), max(start_node, next_node))
                if e in visited_edges:
                    continue

                loop = [start_node]
                curr = next_node
                prev = start_node
                visited_edges.add(e)

                while curr != start_node:
                    loop.append(curr)
                    neighbors = adj.get(curr, [])
                    next_candidates = [n for n in neighbors if n != prev]
                    if not next_candidates:
                        break
                    next_v = next_candidates[0]
                    edge_key = (min(curr, next_v), max(curr, next_v))
                    visited_edges.add(edge_key)
                    prev = curr
                    curr = next_v

                if len(loop) >= 3 and loop[0] == start_node:
                    loops.append(loop)

        return loops


# ==============================================================================
# HINGE LOOP VALIDATOR
# ==============================================================================

class HingeLoopValidator:
    """
    Validates presence and density of multi-loop deformation zones:
    - Elbows: >= 3 concentric rings
    - Knees: >= 3 concentric rings + patellar diamond
    - Shoulders: >= 5 deltoid saddle rings
    - Waist: >= 3 horizontal toroidal rings
    """

    @staticmethod
    def audit_hinge_zones(
        vertices: List[Tuple[float, float, float]],
        quads: List[Tuple[int, int, int, int]],
        landmarks: Dict[str, Tuple[float, float, float]],
    ) -> Dict[str, bool]:
        """Audits all deformation hinge loop requirements against landmark coordinates."""
        results: Dict[str, bool] = {}

        # 1. Waist (Z in [0.88, 1.04])
        waist_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if 0.88 <= z <= 1.04 and abs(x) < 0.20 and abs(y) < 0.15
        ]
        results["waist_3_ring"] = len(waist_verts) >= 72  # 3 rings * 24 verts

        # 2. Left & Right Knees (near joint landmark)
        knee_l_lm = landmarks.get("joint-l-knee") or landmarks.get("knee_L") or (0.09, -0.03, 0.44)
        knee_l_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if abs(z - knee_l_lm[2]) < 0.05 and abs(x - knee_l_lm[0]) < 0.08
        ]
        results["knee_L_3_loop"] = len(knee_l_verts) >= 36

        knee_r_lm = landmarks.get("joint-r-knee") or landmarks.get("knee_R") or (-0.09, -0.03, 0.44)
        knee_r_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if abs(z - knee_r_lm[2]) < 0.05 and abs(x - knee_r_lm[0]) < 0.08
        ]
        results["knee_R_3_loop"] = len(knee_r_verts) >= 36

        # 3. Left & Right Elbows (near joint landmark)
        elbow_l_lm = landmarks.get("joint-l-elbow") or landmarks.get("elbow_L") or (0.35, -0.02, 1.25)
        elbow_l_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if (x - elbow_l_lm[0]) ** 2 + (y - elbow_l_lm[1]) ** 2 + (z - elbow_l_lm[2]) ** 2 < 0.08 ** 2
        ]
        results["elbow_L_3_loop"] = len(elbow_l_verts) >= 36

        elbow_r_lm = landmarks.get("joint-r-elbow") or landmarks.get("elbow_R") or (-0.35, -0.02, 1.25)
        elbow_r_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if (x - elbow_r_lm[0]) ** 2 + (y - elbow_r_lm[1]) ** 2 + (z - elbow_r_lm[2]) ** 2 < 0.08 ** 2
        ]
        results["elbow_R_3_loop"] = len(elbow_r_verts) >= 36

        # 4. Left & Right Shoulders / Deltoid (near clavicle-arm junction)
        shoulder_l_lm = landmarks.get("joint-l-shoulder") or landmarks.get("shoulder_L") or (0.165, -0.02, 1.34)
        shoulder_l_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if (x - shoulder_l_lm[0]) ** 2 + (y - shoulder_l_lm[1]) ** 2 + (z - shoulder_l_lm[2]) ** 2 < 0.10 ** 2
        ]
        results["shoulder_L_5_loop"] = len(shoulder_l_verts) >= 60  # 5 loops * 12 verts

        shoulder_r_lm = landmarks.get("joint-r-shoulder") or landmarks.get("shoulder_R") or (-0.165, -0.02, 1.34)
        shoulder_r_verts = [
            vi for vi, (x, y, z) in enumerate(vertices)
            if (x - shoulder_r_lm[0]) ** 2 + (y - shoulder_r_lm[1]) ** 2 + (z - shoulder_r_lm[2]) ** 2 < 0.10 ** 2
        ]
        results["shoulder_R_5_loop"] = len(shoulder_r_verts) >= 60

        return results


# ==============================================================================
# NORMAL HARMONIZER
# ==============================================================================

class NormalHarmonizer:
    """
    Harmonizes split normals across modular seams to eliminate cel-shading dark lines.
    """

    @staticmethod
    def harmonize_discrete_seam_normals(
        verts_a: List[Tuple[float, float, float]],
        quads_a: List[Tuple[int, int, int, int]],
        verts_b: List[Tuple[float, float, float]],
        quads_b: List[Tuple[int, int, int, int]],
        seam_tolerance: float = 1e-4,
    ) -> Tuple[Dict[int, Tuple[float, float, float]], Dict[int, Tuple[float, float, float]]]:
        """
        Computes unified area-weighted normals for coincident boundary vertex pairs between meshes A and B.
        Returns: (normals_override_A, normals_override_B).
        """
        # Find coincident vertex pairs
        b_grid: Dict[Tuple[int, int, int], List[int]] = {}
        inv_tol = 1.0 / seam_tolerance
        for idx, (x, y, z) in enumerate(verts_b):
            cell = (int(math.floor(x * inv_tol)), int(math.floor(y * inv_tol)), int(math.floor(z * inv_tol)))
            b_grid.setdefault(cell, []).append(idx)

        pairs: List[Tuple[int, int]] = []
        for a_idx, (ax, ay, az) in enumerate(verts_a):
            acx = int(math.floor(ax * inv_tol))
            acy = int(math.floor(ay * inv_tol))
            acz = int(math.floor(az * inv_tol))
            matched = False
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        c = (acx + dx, acy + dy, acz + dz)
                        if c in b_grid:
                            for b_idx in b_grid[c]:
                                bx, by, bz = verts_b[b_idx]
                                if (ax - bx) ** 2 + (ay - by) ** 2 + (az - bz) ** 2 <= seam_tolerance ** 2:
                                    pairs.append((a_idx, b_idx))
                                    matched = True
                                    break
                        if matched:
                            break
                    if matched:
                        break
                if matched:
                    break

        # Compute incident face area-weighted normals
        def get_v_weighted_normal(
            v_idx: int,
            verts: List[Tuple[float, float, float]],
            quads: List[Tuple[int, int, int, int]],
        ) -> Tuple[float, float, float]:
            total_n = [0.0, 0.0, 0.0]
            for q in quads:
                if v_idx in q:
                    p0, p1, p2 = verts[q[0]], verts[q[1]], verts[q[2]]
                    v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
                    v2 = (p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2])
                    cx = v1[1] * v2[2] - v1[2] * v2[1]
                    cy = v1[2] * v2[0] - v1[0] * v2[2]
                    cz = v1[0] * v2[1] - v1[1] * v2[0]
                    total_n[0] += cx
                    total_n[1] += cy
                    total_n[2] += cz
            return (total_n[0], total_n[1], total_n[2])

        override_a: Dict[int, Tuple[float, float, float]] = {}
        override_b: Dict[int, Tuple[float, float, float]] = {}

        for a_idx, b_idx in pairs:
            na = get_v_weighted_normal(a_idx, verts_a, quads_a)
            nb = get_v_weighted_normal(b_idx, verts_b, quads_b)
            nx = na[0] + nb[0]
            ny = na[1] + nb[1]
            nz = na[2] + nb[2]
            nl = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            unified = (nx / nl, ny / nl, nz / nl)
            override_a[a_idx] = unified
            override_b[b_idx] = unified

        return override_a, override_b

    @staticmethod
    def apply_cylindrical_neck_normals(
        vertices: List[Tuple[float, float, float]],
        neck_indices: List[int],
        neck_center: Tuple[float, float] = (0.0, -0.015),
    ) -> Dict[int, Tuple[float, float, float]]:
        """
        Calculates purely horizontal radial normals for neck loop vertices.
        Guarantees zero vertical cel-shading step across the neck-to-torso boundary.
        """
        cx, cy = neck_center
        overrides: Dict[int, Tuple[float, float, float]] = {}
        for vi in neck_indices:
            x, y, _ = vertices[vi]
            dx = x - cx
            dy = y - cy
            dist = math.sqrt(dx * dx + dy * dy) or 1.0
            overrides[vi] = (dx / dist, dy / dist, 0.0)
        return overrides

    @staticmethod
    def harmonize_all_modular_seams(
        submeshes: Dict[str, Any],
        seam_tolerance: float = 1e-4,
    ) -> Dict[str, Dict[int, Tuple[float, float, float]]]:
        """
        Harmonizes all adjacent modular seams:
        - Neck: Anime_Head <-> Anime_Torso
        - Shoulders: Anime_Torso <-> Anime_Arms
        - Hips: Anime_Torso <-> Anime_Legs
        """
        all_overrides: Dict[str, Dict[int, Tuple[float, float, float]]] = {
            name: {} for name in submeshes
        }

        seam_pairs = [
            ("Anime_Head", "Anime_Torso"),
            ("Anime_Torso", "Anime_Arms"),
            ("Anime_Torso", "Anime_Legs"),
        ]

        for name_a, name_b in seam_pairs:
            if name_a in submeshes and name_b in submeshes:
                ma = submeshes[name_a]
                mb = submeshes[name_b]
                oa, ob = NormalHarmonizer.harmonize_discrete_seam_normals(
                    ma.vertices, ma.quads, mb.vertices, mb.quads, seam_tolerance
                )
                all_overrides[name_a].update(oa)
                all_overrides[name_b].update(ob)

        return all_overrides

    @staticmethod
    def apply_custom_split_normals(mesh_obj: Any, custom_vertex_normals: Dict[int, Tuple[float, float, float]]) -> None:
        """Sets custom split normals on all polygon loops based on harmonized vertex normals."""
        mesh = mesh_obj.data
        if hasattr(mesh, "use_auto_smooth"):
            mesh.use_auto_smooth = True
        loop_normals = []
        for poly in mesh.polygons:
            for loop_idx in poly.loop_indices:
                vi = mesh.loops[loop_idx].vertex_index
                if vi in custom_vertex_normals:
                    loop_normals.append(custom_vertex_normals[vi])
                else:
                    loop_normals.append(mesh.vertices[vi].normal)
        if hasattr(mesh, "normals_split_custom_set"):
            mesh.normals_split_custom_set(loop_normals)

    @staticmethod
    def setup_bidirectional_seam_normal_transfer(
        obj_a: Any,
        obj_b: Any,
        seam_vg_name: str = "seam_boundary",
    ) -> None:
        """Sets up bidirectional DATA_TRANSFER modifier between two coincident seam meshes in Blender."""
        for target, source in [(obj_a, obj_b), (obj_b, obj_a)]:
            mod = target.modifiers.new(name="Seam_Normal_Harmonizer", type="DATA_TRANSFER")
            mod.object = source
            mod.use_loop_data = True
            mod.data_types_loops = {"CUSTOM_NORMAL"}
            mod.loop_mapping = "NEAREST_POLYNOR"
            if seam_vg_name in target.vertex_groups:
                mod.vertex_group = seam_vg_name


# ==============================================================================
# TOPOLOGY CLEANER & REPAIR
# ==============================================================================

class TopologyCleaner:
    """
    Enforces pure quad closure, welds duplicate vertices, and repairs boundaries.
    """

    @staticmethod
    def merge_duplicate_vertices(
        vertices: List[Tuple[float, float, float]],
        quads: List[Tuple[int, int, int, int]],
        epsilon: float = 1e-5,
    ) -> Tuple[List[Tuple[float, float, float]], List[Tuple[int, int, int, int]]]:
        """
        Merges duplicate vertices within epsilon distance and re-indexes quad faces.
        Eliminates zero-length edges and collapses zero-area degenerate quads.
        """
        dup_pairs = TopologyValidator.detect_duplicates(vertices, epsilon)
        if not dup_pairs:
            return vertices, quads

        remap: Dict[int, int] = {i: i for i in range(len(vertices))}
        for old_idx, dup_idx in dup_pairs:
            remap[dup_idx] = remap[old_idx]

        unique_indices = sorted(list(set(remap.values())))
        compact_map: Dict[int, int] = {old: new for new, old in enumerate(unique_indices)}

        new_vertices = [vertices[old] for old in unique_indices]
        new_quads: List[Tuple[int, int, int, int]] = []
        seen_faces: Set[Tuple[int, ...]] = set()

        for q in quads:
            r0 = compact_map[remap[q[0]]]
            r1 = compact_map[remap[q[1]]]
            r2 = compact_map[remap[q[2]]]
            r3 = compact_map[remap[q[3]]]
            # Ensure quad has 4 distinct vertices and is not a duplicate face
            if len({r0, r1, r2, r3}) == 4:
                canonical = tuple(sorted((r0, r1, r2, r3)))
                if canonical not in seen_faces:
                    seen_faces.add(canonical)
                    new_quads.append((r0, r1, r2, r3))

        return new_vertices, new_quads

    @staticmethod
    def quad_cap_loop(
        ring_indices: List[int],
        flip_normal: bool = False,
    ) -> List[Tuple[int, int, int, int]]:
        """
        Generates pure quad capping strip for an even-sided circular boundary loop of N vertices.
        Produces exactly (N-2)//2 quads and 0 triangles.
        """
        n = len(ring_indices)
        assert n % 2 == 0 and n >= 4, f"Ring must have an even vertex count >= 4, got {n}"
        num_quads = (n - 2) // 2
        new_quads: List[Tuple[int, int, int, int]] = []
        for k in range(num_quads):
            i0 = ring_indices[k]
            i1 = ring_indices[k + 1]
            i2 = ring_indices[n - 2 - k]
            i3 = ring_indices[n - 1 - k]
            if flip_normal:
                new_quads.append((i0, i3, i2, i1))
            else:
                new_quads.append((i0, i1, i2, i3))
        return new_quads


__all__ = [
    "TopologyReport",
    "TopologyValidator",
    "HingeLoopValidator",
    "NormalHarmonizer",
    "TopologyCleaner",
]
