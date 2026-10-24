"""
MorphoMesh Geometry Subsystem.

3D Mesh data structures, primitives, procedural generators, and binary glTF/OBJ exporters.
"""
from __future__ import annotations

from .exporters import export_glb, export_obj, pad_4
from .mesh import MeshGeometry
from .primitives import GeometryPrimitivesMixin
from .quad_utils import add_quad_cap, add_quad_ellipsoid, compute_quad_metrics

__all__ = [
    "GeometryPrimitivesMixin",
    "MeshGeometry",
    "add_quad_cap",
    "add_quad_ellipsoid",
    "compute_quad_metrics",
    "export_glb",
    "export_obj",
    "pad_4",
]
