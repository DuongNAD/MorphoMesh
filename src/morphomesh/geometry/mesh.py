"""
MorphoMesh: Core In-Memory 3D Mesh Geometry Container.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Union

from morphomesh.models import BoundingBox

from .exporters import export_glb, export_obj
from .primitives import GeometryPrimitivesMixin


class MeshGeometry(GeometryPrimitivesMixin):
    """In-memory 3D mesh container supporting procedural generation and GLB/OBJ export."""

    def __init__(self) -> None:
        self.vertices: List[Tuple[float, float, float]] = []
        self.normals: List[Tuple[float, float, float]] = []
        self.uvs: List[Tuple[float, float]] = []
        self.faces: List[Tuple[int, int, int]] = []  # Triangular face indices
        self.vertex_groups: Dict[str, List[int]] = {}

    def add_vertex(
        self,
        pos: Tuple[float, float, float],
        normal: Tuple[float, float, float] = (0.0, 0.0, 1.0),
        uv: Tuple[float, float] = (0.0, 0.0),
    ) -> int:
        idx = len(self.vertices)
        self.vertices.append(pos)
        self.normals.append(normal)
        self.uvs.append(uv)
        return idx

    def add_triangle(self, i0: int, i1: int, i2: int) -> None:
        self.faces.append((i0, i1, i2))

    def add_quad(self, i0: int, i1: int, i2: int, i3: int) -> None:
        """Adds a quad as two triangles (i0, i1, i2) and (i0, i2, i3)."""
        self.add_triangle(i0, i1, i2)
        self.add_triangle(i0, i2, i3)

    def add_to_vertex_group(self, group_name: str, vertex_indices: Union[int, List[int]]) -> None:
        """Register vertex index or list of indices into a named vertex group."""
        if group_name not in self.vertex_groups:
            self.vertex_groups[group_name] = []
        if isinstance(vertex_indices, int):
            self.vertex_groups[group_name].append(vertex_indices)
        else:
            self.vertex_groups[group_name].extend(vertex_indices)

    def compute_bounding_box(self) -> BoundingBox:
        """Calculate geometric bounds of vertices."""
        if not self.vertices:
            return BoundingBox(
                min_point=[0.0, 0.0, 0.0],
                max_point=[0.0, 0.0, 0.0],
                dimensions=[0.0, 0.0, 0.0],
            )

        min_x = min(v[0] for v in self.vertices)
        min_y = min(v[1] for v in self.vertices)
        min_z = min(v[2] for v in self.vertices)
        max_x = max(v[0] for v in self.vertices)
        max_y = max(v[1] for v in self.vertices)
        max_z = max(v[2] for v in self.vertices)

        return BoundingBox(
            min_point=[round(min_x, 4), round(min_y, 4), round(min_z, 4)],
            max_point=[round(max_x, 4), round(max_y, 4), round(max_z, 4)],
            dimensions=[
                round(max_x - min_x, 4),
                round(max_y - min_y, 4),
                round(max_z - min_z, 4),
            ],
        )

    def export_obj(self, filepath: str) -> None:
        """Export geometry to standard Wavefront .obj file."""
        export_obj(self, filepath)

    def export_glb(self, filepath: str) -> None:
        """Export geometry to standard binary glTF 2.0 (.glb) container."""
        export_glb(self, filepath)


__all__ = [
    "MeshGeometry",
]
