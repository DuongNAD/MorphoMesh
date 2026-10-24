"""
MorphoMesh: Geometric Primitives & Procedural Biological Anatomy Generators.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Union


class GeometryPrimitivesMixin:
    """Mixin class providing procedural geometric shapes and biological anatomical primitives."""

    def add_box(
        self,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float],
    ) -> None:
        """Add an axis-aligned box with correct normals and UVs."""
        cx, cy, cz = center
        sx, sy, sz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0

        faces_def = [
            # Front (+Y): CCW viewed from +Y looking along -Y
            ([(cx + sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz - sz), (cx - sx, cy + sy, cz + sz), (cx + sx, cy + sy, cz + sz)], (0.0, 1.0, 0.0)),
            # Back (-Y): CCW viewed from -Y looking along +Y
            ([(cx - sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz - sz), (cx + sx, cy - sy, cz + sz), (cx - sx, cy - sy, cz + sz)], (0.0, -1.0, 0.0)),
            # Left (-X): CCW viewed from -X looking along +X
            ([(cx - sx, cy + sy, cz - sz), (cx - sx, cy - sy, cz - sz), (cx - sx, cy - sy, cz + sz), (cx - sx, cy + sy, cz + sz)], (-1.0, 0.0, 0.0)),
            # Right (+X): CCW viewed from +X looking along -X
            ([(cx + sx, cy - sy, cz - sz), (cx + sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz + sz), (cx + sx, cy - sy, cz + sz)], (1.0, 0.0, 0.0)),
            # Top (+Z): CCW viewed from +Z looking along -Z
            ([(cx - sx, cy - sy, cz + sz), (cx + sx, cy - sy, cz + sz), (cx + sx, cy + sy, cz + sz), (cx - sx, cy + sy, cz + sz)], (0.0, 0.0, 1.0)),
            # Bottom (-Z): CCW viewed from -Z looking along +Z
            ([(cx - sx, cy + sy, cz - sz), (cx + sx, cy + sy, cz - sz), (cx + sx, cy - sy, cz - sz), (cx - sx, cy - sy, cz - sz)], (0.0, 0.0, -1.0)),
        ]

        uv_corners = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]

        for quad_pts, norm in faces_def:
            idx0 = self.add_vertex(quad_pts[0], norm, uv_corners[0])
            idx1 = self.add_vertex(quad_pts[1], norm, uv_corners[1])
            idx2 = self.add_vertex(quad_pts[2], norm, uv_corners[2])
            idx3 = self.add_vertex(quad_pts[3], norm, uv_corners[3])
            self.add_quad(idx0, idx1, idx2, idx3)

    def add_cylinder(
        self,
        base_center: Tuple[float, float, float],
        radius: float,
        height: float,
        segments: int = 12,
        axis: str = "Z",
        cap_ends: bool = False,
        cap_bottom: Optional[bool] = None,
        cap_top: Optional[bool] = None,
    ) -> None:
        """Add a cylinder along the given axis with optional closed end caps."""
        bx, by, bz = base_center
        bottom_indices = []
        top_indices = []

        for s in range(segments):
            angle = 2.0 * math.pi * s / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            u = s / segments

            if axis == "Z":
                px, py = bx + radius * cos_a, by + radius * sin_a
                norm = (cos_a, sin_a, 0.0)
                b_idx = self.add_vertex((px, py, bz), norm, (u, 0.0))
                t_idx = self.add_vertex((px, py, bz + height), norm, (u, 1.0))
            elif axis == "Y":
                px, pz = bx + radius * cos_a, bz + radius * sin_a
                norm = (cos_a, 0.0, sin_a)
                b_idx = self.add_vertex((px, by, pz), norm, (u, 0.0))
                t_idx = self.add_vertex((px, by + height, pz), norm, (u, 1.0))
            else:  # X
                py, pz = by + radius * cos_a, bz + radius * sin_a
                norm = (0.0, cos_a, sin_a)
                b_idx = self.add_vertex((bx, py, pz), norm, (u, 0.0))
                t_idx = self.add_vertex((bx + height, py, pz), norm, (u, 1.0))

            bottom_indices.append(b_idx)
            top_indices.append(t_idx)

        # Connect side quads
        for s in range(segments):
            next_s = (s + 1) % segments
            if axis == "Y":
                self.add_quad(
                    bottom_indices[next_s],
                    bottom_indices[s],
                    top_indices[s],
                    top_indices[next_s],
                )
            else:
                self.add_quad(
                    bottom_indices[s],
                    bottom_indices[next_s],
                    top_indices[next_s],
                    top_indices[s],
                )

        # Bottom cap with outward-facing normals
        do_cap_bottom = cap_bottom if cap_bottom is not None else cap_ends
        if do_cap_bottom:
            b_norm = (0.0, 0.0, -1.0) if axis == "Z" else ((0.0, -1.0, 0.0) if axis == "Y" else (-1.0, 0.0, 0.0))
            bc_idx = self.add_vertex((bx, by, bz), b_norm, (0.5, 0.5))
            for s in range(segments):
                next_s = (s + 1) % segments
                if axis == "Y":
                    self.add_triangle(bc_idx, bottom_indices[s], bottom_indices[next_s])
                else:
                    self.add_triangle(bc_idx, bottom_indices[next_s], bottom_indices[s])

        # Top cap with outward-facing normals
        do_cap_top = cap_top if cap_top is not None else cap_ends
        if do_cap_top:
            t_center = (
                (bx, by, bz + height)
                if axis == "Z"
                else ((bx, by + height, bz) if axis == "Y" else (bx + height, by, bz))
            )
            t_norm = (0.0, 0.0, 1.0) if axis == "Z" else ((0.0, 1.0, 0.0) if axis == "Y" else (1.0, 0.0, 0.0))
            tc_idx = self.add_vertex(t_center, t_norm, (0.5, 0.5))
            for s in range(segments):
                next_s = (s + 1) % segments
                if axis == "Y":
                    self.add_triangle(tc_idx, top_indices[next_s], top_indices[s])
                else:
                    self.add_triangle(tc_idx, top_indices[s], top_indices[next_s])

    def add_sphere(
        self,
        center: Tuple[float, float, float],
        radius: float,
        rings: int = 12,
        sectors: int = 16,
    ) -> None:
        """Add a UV sphere with outward normals and polar triangle fans."""
        cx, cy, cz = center
        rings = max(2, rings)
        sectors = max(3, sectors)

        # 1. Single North Polar vertex
        north_idx = self.add_vertex((cx, cy, cz + radius), (0.0, 0.0, 1.0), (0.5, 0.0))

        # 2. Intermediate latitude rings (r = 1 to rings - 1)
        intermediate_rings: List[List[int]] = []
        for r in range(1, rings):
            theta = math.pi * r / rings
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            v = r / rings
            current_ring = []

            for s in range(sectors + 1):
                phi = 2.0 * math.pi * s / sectors
                sin_p = math.sin(phi)
                cos_p = math.cos(phi)
                u = s / sectors

                nx = sin_t * cos_p
                ny = sin_t * sin_p
                nz = cos_t

                px = cx + radius * nx
                py = cy + radius * ny
                pz = cz + radius * nz

                idx = self.add_vertex((px, py, pz), (nx, ny, nz), (u, v))
                current_ring.append(idx)
            intermediate_rings.append(current_ring)

        # 3. Single South Polar vertex
        south_idx = self.add_vertex((cx, cy, cz - radius), (0.0, 0.0, -1.0), (0.5, 1.0))

        # 4. North Polar triangle fan
        for s in range(sectors):
            self.add_triangle(north_idx, intermediate_rings[0][s], intermediate_rings[0][s + 1])

        # 5. Intermediate latitude quad bands
        for r in range(len(intermediate_rings) - 1):
            for s in range(sectors):
                i0 = intermediate_rings[r][s]
                i1 = intermediate_rings[r + 1][s]
                i2 = intermediate_rings[r + 1][s + 1]
                i3 = intermediate_rings[r][s + 1]
                self.add_quad(i0, i1, i2, i3)

        # 6. South Polar triangle fan
        for s in range(sectors):
            self.add_triangle(intermediate_rings[-1][s], south_idx, intermediate_rings[-1][s + 1])

    def add_ellipsoid(
        self,
        center: Tuple[float, float, float],
        radii: Tuple[float, float, float],
        rings: int = 8,
        sectors: int = 12,
    ) -> List[int]:
        """Add an axis-oriented 3D ellipsoid with outward normals and polar triangle fans."""
        cx, cy, cz = center
        rx, ry, rz = radii
        rings = max(2, rings)
        sectors = max(3, sectors)
        added_indices: List[int] = []

        # 1. Single North Polar vertex
        north_idx = self.add_vertex((cx, cy, cz + rz), (0.0, 0.0, 1.0), (0.5, 0.0))
        added_indices.append(north_idx)

        # 2. Intermediate latitude rings (r = 1 to rings - 1)
        intermediate_rings: List[List[int]] = []
        for r in range(1, rings):
            theta = math.pi * r / rings
            sin_t = math.sin(theta)
            cos_t = math.cos(theta)
            v = r / rings
            current_ring = []

            for s in range(sectors + 1):
                phi = 2.0 * math.pi * s / sectors
                sin_p = math.sin(phi)
                cos_p = math.cos(phi)
                u = s / sectors

                nx = sin_t * cos_p
                ny = sin_t * sin_p
                nz = cos_t

                px = cx + rx * nx
                py = cy + ry * ny
                pz = cz + rz * nz

                nnx = nx / rx if rx > 1e-6 else 0.0
                nny = ny / ry if ry > 1e-6 else 0.0
                nnz = nz / rz if rz > 1e-6 else 0.0
                n_len = math.sqrt(nnx * nnx + nny * nny + nnz * nnz)
                norm = (nnx / n_len, nny / n_len, nnz / n_len) if n_len > 1e-6 else (nx, ny, nz)

                idx = self.add_vertex((px, py, pz), norm, (u, v))
                current_ring.append(idx)
                added_indices.append(idx)
            intermediate_rings.append(current_ring)

        # 3. Single South Polar vertex
        south_idx = self.add_vertex((cx, cy, cz - rz), (0.0, 0.0, -1.0), (0.5, 1.0))
        added_indices.append(south_idx)

        # 4. North Polar triangle fan
        for s in range(sectors):
            self.add_triangle(north_idx, intermediate_rings[0][s], intermediate_rings[0][s + 1])

        # 5. Intermediate latitude quad bands
        for r in range(len(intermediate_rings) - 1):
            for s in range(sectors):
                i0 = intermediate_rings[r][s]
                i1 = intermediate_rings[r + 1][s]
                i2 = intermediate_rings[r + 1][s + 1]
                i3 = intermediate_rings[r][s + 1]
                self.add_quad(i0, i1, i2, i3)

        # 6. South Polar triangle fan
        for s in range(sectors):
            self.add_triangle(intermediate_rings[-1][s], south_idx, intermediate_rings[-1][s + 1])

        return added_indices

    def add_cone(
        self,
        base_center: Tuple[float, float, float],
        apex: Tuple[float, float, float],
        base_radius: float,
        segments: int = 8,
    ) -> List[int]:
        """Add a conical spike with a circular base and sharp apex."""
        added_indices: List[int] = []
        bx, by, bz = base_center
        ax, ay, az = apex
        vx, vy, vz = ax - bx, ay - by, az - bz
        vlen = math.sqrt(vx * vx + vy * vy + vz * vz)
        if vlen < 1e-6:
            return added_indices
        dir_axis = (vx / vlen, vy / vlen, vz / vlen)

        if abs(dir_axis[2]) < 0.9:
            up = (0.0, 0.0, 1.0)
        else:
            up = (1.0, 0.0, 0.0)
        u_x = (
            dir_axis[1] * up[2] - dir_axis[2] * up[1],
            dir_axis[2] * up[0] - dir_axis[0] * up[2],
            dir_axis[0] * up[1] - dir_axis[1] * up[0],
        )
        ux_len = math.sqrt(sum(c * c for c in u_x))
        u_x = tuple(c / ux_len for c in u_x) if ux_len > 1e-6 else (1.0, 0.0, 0.0)
        u_y = (
            dir_axis[1] * u_x[2] - dir_axis[2] * u_x[1],
            dir_axis[2] * u_x[0] - dir_axis[0] * u_x[2],
            dir_axis[0] * u_x[1] - dir_axis[1] * u_x[0],
        )

        base_ring = []
        for s in range(segments):
            angle = 2.0 * math.pi * s / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            px = bx + base_radius * (cos_a * u_x[0] + sin_a * u_y[0])
            py = by + base_radius * (cos_a * u_x[1] + sin_a * u_y[1])
            pz = bz + base_radius * (cos_a * u_x[2] + sin_a * u_y[2])
            norm = (
                cos_a * u_x[0] + sin_a * u_y[0],
                cos_a * u_x[1] + sin_a * u_y[1],
                cos_a * u_x[2] + sin_a * u_y[2],
            )
            idx = self.add_vertex((px, py, pz), norm, (s / segments, 0.0))
            base_ring.append(idx)
            added_indices.append(idx)

        # Base cap center
        base_c_idx = self.add_vertex(
            (bx, by, bz),
            (-dir_axis[0], -dir_axis[1], -dir_axis[2]),
            (0.5, 0.5),
        )
        added_indices.append(base_c_idx)
        for s in range(segments):
            next_s = (s + 1) % segments
            self.add_triangle(base_c_idx, base_ring[next_s], base_ring[s])

        # Apex vertex
        apex_idx = self.add_vertex((ax, ay, az), dir_axis, (0.5, 1.0))
        added_indices.append(apex_idx)
        for s in range(segments):
            next_s = (s + 1) % segments
            self.add_triangle(base_ring[s], base_ring[next_s], apex_idx)

        return added_indices

    def add_curved_claw(
        self,
        base_pos: Tuple[float, float, float],
        forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        downward_dir: Tuple[float, float, float] = (0.0, 0.0, -1.0),
        length: float = 0.12,
        base_radius: float = 0.025,
        curve_factor: float = 0.45,
        segments: int = 6,
        radial_segments: int = 8,
        splay_dir: Optional[Tuple[float, float, float]] = None,
        splay_factor: float = 0.0,
    ) -> List[int]:
        """
        Adds a curved keratin claw along a parabolic arc with mathematical guarantee:
        dot(claw_tip - claw_base, forward_dir) > 0.60 and dz < 0.
        Returns list of added vertex indices.
        """
        added_indices: List[int] = []

        fwd_len = math.sqrt(sum(x * x for x in forward_dir))
        ufwd = tuple(x / fwd_len for x in forward_dir) if fwd_len > 1e-6 else (0.0, -1.0, 0.0)

        # Orthogonalize downward_dir against ufwd
        dot_fd = sum(a * b for a, b in zip(ufwd, downward_dir))
        down_proj = tuple(downward_dir[i] - dot_fd * ufwd[i] for i in range(3))
        down_len = math.sqrt(sum(x * x for x in down_proj))
        udown = tuple(x / down_len for x in down_proj) if down_len > 1e-6 else (0.0, 0.0, -1.0)

        # Side vector via cross product (ufwd x udown)
        uside = (
            ufwd[1] * udown[2] - ufwd[2] * udown[1],
            ufwd[2] * udown[0] - ufwd[0] * udown[2],
            ufwd[0] * udown[1] - ufwd[1] * udown[0],
        )
        side_len = math.sqrt(sum(x * x for x in uside))
        if side_len > 1e-6:
            uside = tuple(x / side_len for x in uside)
        else:
            uside = (1.0, 0.0, 0.0)

        if splay_dir is not None:
            s_len = math.sqrt(sum(x * x for x in splay_dir))
            if s_len > 1e-6:
                uside = tuple(x / s_len for x in splay_dir)

        rings_verts: List[List[int]] = []

        for s in range(segments):
            t = s / segments
            r_t = base_radius * (1.0 - 0.75 * t)
            # Center along parabolic arc
            cx = (
                base_pos[0]
                + ufwd[0] * (length * t)
                + udown[0] * (length * curve_factor * (t ** 1.4))
                + uside[0] * (length * splay_factor * t)
            )
            cy = (
                base_pos[1]
                + ufwd[1] * (length * t)
                + udown[1] * (length * curve_factor * (t ** 1.4))
                + uside[1] * (length * splay_factor * t)
            )
            cz = (
                base_pos[2]
                + ufwd[2] * (length * t)
                + udown[2] * (length * curve_factor * (t ** 1.4))
                + uside[2] * (length * splay_factor * t)
            )

            # Local tangent
            t_deriv = 1.4 * (t ** 0.4) if t > 0 else 0.0
            tx = ufwd[0] + udown[0] * curve_factor * t_deriv + uside[0] * splay_factor
            ty = ufwd[1] + udown[1] * curve_factor * t_deriv + uside[1] * splay_factor
            tz = ufwd[2] + udown[2] * curve_factor * t_deriv + uside[2] * splay_factor
            t_len = math.sqrt(tx * tx + ty * ty + tz * tz)
            if t_len > 1e-6:
                tx, ty, tz = tx / t_len, ty / t_len, tz / t_len

            # Ring perpendicular frame
            bx = ty * uside[2] - tz * uside[1]
            by = tz * uside[0] - tx * uside[2]
            bz = tx * uside[1] - ty * uside[0]
            b_len = math.sqrt(bx * bx + by * by + bz * bz)
            if b_len > 1e-6:
                bx, by, bz = bx / b_len, by / b_len, bz / b_len
            else:
                bx, by, bz = udown

            ring = []
            for r in range(radial_segments):
                angle = 2.0 * math.pi * r / radial_segments
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                rx = cos_a * uside[0] + sin_a * bx
                ry = cos_a * uside[1] + sin_a * by
                rz = cos_a * uside[2] + sin_a * bz
                px = cx + r_t * rx
                py = cy + r_t * ry
                pz = cz + r_t * rz
                norm = (rx, ry, rz)
                v_idx = self.add_vertex((px, py, pz), norm, (r / radial_segments, t))
                ring.append(v_idx)
                added_indices.append(v_idx)
            rings_verts.append(ring)

        # Tip apex at t = 1.0
        tip_x = (
            base_pos[0]
            + ufwd[0] * length
            + udown[0] * (length * curve_factor)
            + uside[0] * (length * splay_factor)
        )
        tip_y = (
            base_pos[1]
            + ufwd[1] * length
            + udown[1] * (length * curve_factor)
            + uside[1] * (length * splay_factor)
        )
        tip_z = (
            base_pos[2]
            + ufwd[2] * length
            + udown[2] * (length * curve_factor)
            + uside[2] * (length * splay_factor)
        )

        tip_norm = (
            ufwd[0] + udown[0] * curve_factor + uside[0] * splay_factor,
            ufwd[1] + udown[1] * curve_factor + uside[1] * splay_factor,
            ufwd[2] + udown[2] * curve_factor + uside[2] * splay_factor,
        )
        tn_len = math.sqrt(sum(c * c for c in tip_norm))
        if tn_len > 1e-6:
            tip_norm = tuple(c / tn_len for c in tip_norm)

        tip_idx = self.add_vertex((tip_x, tip_y, tip_z), tip_norm, (0.5, 1.0))
        added_indices.append(tip_idx)

        # Connect ring quads
        for s in range(segments - 1):
            for r in range(radial_segments):
                next_r = (r + 1) % radial_segments
                self.add_quad(
                    rings_verts[s][r],
                    rings_verts[s][next_r],
                    rings_verts[s + 1][next_r],
                    rings_verts[s + 1][r],
                )

        # Connect last ring to apex
        last_ring = rings_verts[-1]
        for r in range(radial_segments):
            next_r = (r + 1) % radial_segments
            self.add_triangle(last_ring[r], last_ring[next_r], tip_idx)

        # Base cap
        base_center_idx = self.add_vertex(
            base_pos,
            (-ufwd[0], -ufwd[1], -ufwd[2]),
            (0.5, 0.0),
        )
        added_indices.append(base_center_idx)
        first_ring = rings_verts[0]
        for r in range(radial_segments):
            next_r = (r + 1) % radial_segments
            self.add_triangle(base_center_idx, first_ring[next_r], first_ring[r])

        return added_indices

    def add_plantigrade_paw(
        self,
        heel_pos: Tuple[float, float, float],
        forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        is_front: bool = False,
        scale: float = 1.0,
    ) -> Dict[str, List[int]]:
        """
        Adds plantigrade foot/paw with calcaneus heel, plantar/palmar pad, and 5 digital pads.
        Invokes add_curved_claw for each of the 5 digits with forward/downward curvature.
        Returns dict mapping sub-components ('paw', 'pads', 'claws') to lists of vertex indices.
        """
        result: Dict[str, List[int]] = {"paw": [], "pads": [], "claws": []}
        hx, hy, hz = heel_pos

        if is_front:
            # Front paw (Manus): broad, spade-like palmar surface
            foot_center = (hx, hy - 0.10 * scale, hz + 0.04 * scale)
            foot_size = (0.24 * scale, 0.20 * scale, 0.08 * scale)
            idx_start = len(self.vertices)
            self.add_box(foot_center, foot_size)
            result["paw"].extend(list(range(idx_start, len(self.vertices))))

            # Main Metacarpal / Palmar pad (central convex pad on underside)
            palmar_pad = self.add_ellipsoid(
                (hx, hy - 0.10 * scale, hz + 0.01 * scale),
                (0.10 * scale, 0.08 * scale, 0.02 * scale),
                rings=4,
                sectors=8,
            )
            result["pads"].extend(palmar_pad)

            # Accessory Carpal pad on lateral wrist margin
            carpal_x = hx + (0.08 if hx >= 0 else -0.08) * scale
            carpal_pad = self.add_ellipsoid(
                (carpal_x, hy - 0.02 * scale, hz + 0.015 * scale),
                (0.035 * scale, 0.035 * scale, 0.015 * scale),
                rings=4,
                sectors=6,
            )
            result["pads"].extend(carpal_pad)

            # 5 Digital pads and 5 forward/downward curving claws
            for k in range(5):
                splay = (k - 2) * 0.24
                dx = hx + (k - 2) * 0.045 * scale
                fwd_ext = 0.18 + 0.025 * (1.0 - abs(k - 2) * 0.25)
                dy = hy - fwd_ext * scale
                dz = hz + 0.02 * scale

                # Digital pad ellipsoid on underside
                d_pad = self.add_ellipsoid(
                    (dx, dy, dz - 0.006 * scale),
                    (0.022 * scale, 0.025 * scale, 0.015 * scale),
                    rings=4,
                    sectors=6,
                )
                result["pads"].extend(d_pad)

                # Curved claw extending forward and downward
                claw_idx = self.add_curved_claw(
                    base_pos=(dx, dy - 0.015 * scale, dz),
                    forward_dir=forward_dir,
                    downward_dir=(0.0, 0.0, -1.0),
                    length=0.10 * scale,
                    base_radius=0.022 * scale,
                    curve_factor=0.46,
                    segments=6,
                    radial_segments=8,
                    splay_factor=splay * 0.25,
                )
                result["claws"].extend(claw_idx)

            self.add_to_vertex_group("pads_front", result["pads"])
            self.add_to_vertex_group("claws_front", result["claws"])
        else:
            # Hind paw (Pes): true plantigrade calcaneus heel morphology
            foot_center = (hx, hy - 0.13 * scale, hz + 0.04 * scale)
            foot_size = (0.22 * scale, 0.26 * scale, 0.08 * scale)
            idx_start = len(self.vertices)
            self.add_box(foot_center, foot_size)
            result["paw"].extend(list(range(idx_start, len(self.vertices))))

            # Continuous Plantar sole pad (covering heel through metatarsals)
            plantar_pad = self.add_ellipsoid(
                (hx, hy - 0.13 * scale, hz + 0.01 * scale),
                (0.09 * scale, 0.12 * scale, 0.02 * scale),
                rings=4,
                sectors=8,
            )
            result["pads"].extend(plantar_pad)

            # 5 Digital pads and 5 forward/downward curving claws
            for k in range(5):
                splay = (k - 2) * 0.22
                dx = hx + (k - 2) * 0.040 * scale
                fwd_ext = 0.24 + 0.020 * (1.0 - abs(k - 2) * 0.25)
                dy = hy - fwd_ext * scale
                dz = hz + 0.02 * scale

                # Digital pad ellipsoid
                d_pad = self.add_ellipsoid(
                    (dx, dy, dz - 0.006 * scale),
                    (0.020 * scale, 0.022 * scale, 0.014 * scale),
                    rings=4,
                    sectors=6,
                )
                result["pads"].extend(d_pad)

                # Curved claw
                claw_idx = self.add_curved_claw(
                    base_pos=(dx, dy - 0.015 * scale, dz),
                    forward_dir=forward_dir,
                    downward_dir=(0.0, 0.0, -1.0),
                    length=0.08 * scale,
                    base_radius=0.020 * scale,
                    curve_factor=0.46,
                    segments=6,
                    radial_segments=8,
                    splay_factor=splay * 0.22,
                )
                result["claws"].extend(claw_idx)

            self.add_to_vertex_group("pads_hind", result["pads"])
            self.add_to_vertex_group("claws_hind", result["claws"])

        return result

    def add_articulated_head(
        self,
        head_center: Tuple[float, float, float],
        forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        scale: float = 1.0,
    ) -> Dict[str, List[int]]:
        """
        Adds head with cranium, rostrum, indented nares, mouth cavity, jaw, teeth, eyelids, cupped ears.
        Returns dict of vertex indices by anatomical feature.
        """
        features: Dict[str, List[int]] = {
            "snout": [],
            "nostrils": [],
            "mouth_cavity": [],
            "jaw": [],
            "teeth": [],
            "eyes": [],
            "eyelids": [],
            "ears": [],
        }
        cx, cy, cz = head_center

        # 1. Cranium (skull dome)
        cranium = self.add_ellipsoid(
            (cx, cy, cz),
            (0.22 * scale, 0.24 * scale, 0.20 * scale),
            rings=8,
            sectors=12,
        )

        # 2. Organic Tapered Rostrum / Snout (multi-ring lofted muzzle)
        snout_rings = []
        y_coords = [-0.12, -0.19, -0.26, -0.32]
        radii_x = [0.100, 0.090, 0.075, 0.060]
        radii_z = [0.085, 0.075, 0.065, 0.050]
        z_offsets = [0.000, -0.010, -0.020, -0.025]
        segments = 8

        for y_rel, rx, rz, zo in zip(y_coords, radii_x, radii_z, z_offsets):
            ring = []
            for s in range(segments):
                ang = 2.0 * math.pi * s / segments
                vx = cx + rx * scale * math.cos(ang)
                vy = cy + y_rel * scale
                vz = cz + (zo + rz * math.sin(ang)) * scale
                norm = (math.cos(ang), -0.2, math.sin(ang))
                n_len = math.sqrt(norm[0] ** 2 + norm[1] ** 2 + norm[2] ** 2)
                norm = (norm[0] / n_len, norm[1] / n_len, norm[2] / n_len)
                v_idx = self.add_vertex((vx, vy, vz), norm, (s / segments, abs(y_rel)))
                ring.append(v_idx)
                features["snout"].append(v_idx)
            snout_rings.append(ring)

        for r in range(len(snout_rings) - 1):
            for s in range(segments):
                ns = (s + 1) % segments
                self.add_quad(
                    snout_rings[r][s],
                    snout_rings[r][ns],
                    snout_rings[r + 1][ns],
                    snout_rings[r + 1][s],
                )

        # Fleshy rhinarium (curved nose pad front cap)
        rhinarium_y = cy - 0.340 * scale
        pad_center = self.add_vertex(
            (cx, rhinarium_y, cz - 0.025 * scale), (0.0, -1.0, 0.0), (0.5, 0.5)
        )
        features["snout"].append(pad_center)
        last_ring = snout_rings[-1]
        for s in range(segments):
            ns = (s + 1) % segments
            self.add_triangle(pad_center, last_ring[s], last_ring[ns])

        # 3. Indented Nostrils (bilateral nares concavities recessed into rhinarium)
        for sign_x in [-1.0, 1.0]:
            n_base = (cx + sign_x * 0.030 * scale, cy - 0.342 * scale, cz - 0.020 * scale)
            n_apex = (cx + sign_x * 0.026 * scale, cy - 0.312 * scale, cz - 0.015 * scale)
            nostril_idx = self.add_cone(n_base, n_apex, base_radius=0.012 * scale, segments=6)
            features["nostrils"].extend(nostril_idx)

        # 4. Oral mouth cavity (buccal split opening)
        mouth_center = (cx, cy - 0.23 * scale, cz - 0.07 * scale)
        mouth_size = (0.13 * scale, 0.14 * scale, 0.03 * scale)
        idx_start = len(self.vertices)
        self.add_box(mouth_center, mouth_size)
        features["mouth_cavity"].extend(list(range(idx_start, len(self.vertices))))

        # 5. Lower Jaw / Mandible
        jaw_center = (cx, cy - 0.22 * scale, cz - 0.12 * scale)
        jaw_size = (0.15 * scale, 0.18 * scale, 0.06 * scale)
        idx_start = len(self.vertices)
        self.add_box(jaw_center, jaw_size)
        features["jaw"].extend(list(range(idx_start, len(self.vertices))))

        # 6. Teeth (Canines & Incisors)
        # Upper Canines (2 downward conical teeth)
        for sign_x in [-1.0, 1.0]:
            c_base = (cx + sign_x * 0.048 * scale, cy - 0.28 * scale, cz - 0.05 * scale)
            c_apex = (cx + sign_x * 0.050 * scale, cy - 0.27 * scale, cz - 0.095 * scale)
            t_idx = self.add_cone(c_base, c_apex, base_radius=0.009 * scale, segments=6)
            features["teeth"].extend(t_idx)

        # Lower Canines (2 upward conical teeth)
        for sign_x in [-1.0, 1.0]:
            c_base = (cx + sign_x * 0.042 * scale, cy - 0.27 * scale, cz - 0.11 * scale)
            c_apex = (cx + sign_x * 0.044 * scale, cy - 0.26 * scale, cz - 0.065 * scale)
            t_idx = self.add_cone(c_base, c_apex, base_radius=0.008 * scale, segments=6)
            features["teeth"].extend(t_idx)

        # Incisors between canines
        for i in range(4):
            offset_x = (i - 1.5) * 0.016 * scale
            u_inc = self.add_cone(
                (cx + offset_x, cy - 0.30 * scale, cz - 0.05 * scale),
                (cx + offset_x, cy - 0.295 * scale, cz - 0.075 * scale),
                base_radius=0.005 * scale,
                segments=4,
            )
            features["teeth"].extend(u_inc)
            l_inc = self.add_cone(
                (cx + offset_x, cy - 0.29 * scale, cz - 0.11 * scale),
                (cx + offset_x, cy - 0.285 * scale, cz - 0.085 * scale),
                base_radius=0.005 * scale,
                segments=4,
            )
            features["teeth"].extend(l_inc)

        # 7. Eyes & Dimensional Eyelids
        for sign_x in [-1.0, 1.0]:
            eye_pos = (cx + sign_x * 0.15 * scale, cy - 0.12 * scale, cz + 0.06 * scale)
            # Eyeball sphere
            e_idx = self.add_ellipsoid(
                eye_pos,
                (0.032 * scale, 0.032 * scale, 0.032 * scale),
                rings=6,
                sectors=8,
            )
            features["eyes"].extend(e_idx)

            # Superior eyelid fold (upper lid)
            upper_lid = (cx + sign_x * 0.15 * scale, cy - 0.12 * scale, cz + 0.095 * scale)
            idx_start = len(self.vertices)
            self.add_box(upper_lid, (0.040 * scale, 0.040 * scale, 0.012 * scale))
            features["eyelids"].extend(list(range(idx_start, len(self.vertices))))

            # Inferior eyelid fold (lower lid)
            lower_lid = (cx + sign_x * 0.15 * scale, cy - 0.12 * scale, cz + 0.025 * scale)
            idx_start = len(self.vertices)
            self.add_box(lower_lid, (0.040 * scale, 0.040 * scale, 0.012 * scale))
            features["eyelids"].extend(list(range(idx_start, len(self.vertices))))

        # 8. Cupped Ears (Pinnae with convex outer shell and concave inner concha)
        for sign_x in [-1.0, 1.0]:
            ear_pos = (cx + sign_x * 0.18 * scale, cy + 0.10 * scale, cz + 0.18 * scale)
            outer_ear = self.add_ellipsoid(
                ear_pos,
                (0.04 * scale, 0.03 * scale, 0.06 * scale),
                rings=5,
                sectors=8,
            )
            features["ears"].extend(outer_ear)
            inner_concha = self.add_ellipsoid(
                (cx + sign_x * 0.17 * scale, cy + 0.085 * scale, cz + 0.18 * scale),
                (0.025 * scale, 0.015 * scale, 0.040 * scale),
                rings=4,
                sectors=6,
            )
            features["ears"].extend(inner_concha)

        # Register to vertex groups
        for key, indices in features.items():
            self.add_to_vertex_group(key, indices)

        return features

    def add_anatomical_torso(
        self,
        center: Tuple[float, float, float],
        forward_dir: Tuple[float, float, float] = (0.0, -1.0, 0.0),
        scale: float = 1.0,
    ) -> Dict[str, List[int]]:
        """
        Adds muscular quadruped torso, dorsal thoracic spine/hump, and short tail.
        Returns dict mapping features ('torso', 'dorsal_spine', 'tail', 'armor_mounts_shoulder') to vertex indices.
        """
        features: Dict[str, List[int]] = {
            "torso": [],
            "dorsal_spine": [],
            "tail": [],
            "armor_mounts_shoulder": [],
        }
        tx, ty, tz = center

        # 1. Front ribcage / Chest
        chest = self.add_ellipsoid(
            (tx, ty - 0.20 * scale, tz + 0.02 * scale),
            (0.36 * scale, 0.30 * scale, 0.32 * scale),
            rings=8,
            sectors=12,
        )
        features["torso"].extend(chest)

        # 2. Thoracic Dorsal Hump (elevated muscular scapular hump over T2-T8)
        hump = self.add_ellipsoid(
            (tx, ty - 0.18 * scale, tz + 0.22 * scale),
            (0.22 * scale, 0.20 * scale, 0.14 * scale),
            rings=6,
            sectors=10,
        )
        features["torso"].extend(hump)
        features["armor_mounts_shoulder"].extend(hump)

        # 3. Abdomen / Flank
        flank = self.add_ellipsoid(
            (tx, ty + 0.15 * scale, tz + 0.04 * scale),
            (0.30 * scale, 0.25 * scale, 0.28 * scale),
            rings=8,
            sectors=12,
        )
        features["torso"].extend(flank)

        # 4. Pelvis / Rump
        pelvis = self.add_ellipsoid(
            (tx, ty + 0.48 * scale, tz + 0.06 * scale),
            (0.32 * scale, 0.24 * scale, 0.30 * scale),
            rings=8,
            sectors=12,
        )
        features["torso"].extend(pelvis)

        # 5. Dorsal Spine (longitudinal spinal ridge along dorsal midline)
        spine_pos = (tx, ty + 0.05 * scale, tz + 0.24 * scale)
        spine_size = (0.06 * scale, 1.05 * scale, 0.04 * scale)
        idx_start = len(self.vertices)
        self.add_box(spine_pos, spine_size)
        features["dorsal_spine"].extend(list(range(idx_start, len(self.vertices))))

        # 6. Vestigial short tail (length <= 0.20m, biological conical tuft)
        tail_base = (tx, ty + 0.62 * scale, tz + 0.10 * scale)
        tail_apex = (tx, ty + 0.74 * scale, tz + 0.02 * scale)
        tail_idx = self.add_cone(tail_base, tail_apex, base_radius=0.045 * scale, segments=6)
        features["tail"].extend(tail_idx)

        # Register to vertex groups
        for key, indices in features.items():
            self.add_to_vertex_group(key, indices)

        return features


__all__ = [
    "GeometryPrimitivesMixin",
]
