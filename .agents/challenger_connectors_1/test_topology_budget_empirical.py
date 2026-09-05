"""
MorphoMesh Phase 2: Empirical Challenge Suite 2
MeshAnything V2 Autoregressive Retopology, Face Budget (<1600), & Quad Ratio (>=90%).
"""

from __future__ import annotations

import math
import os
import struct
import tempfile
import pytest
from typing import Generator

from morphomesh.connectors.meshanything_connector import (
    MeshAnythingConnector,
    MeshAnythingInput,
    MeshAnythingOutput,
    RetopologyConfig,
)
from morphomesh.inference_adapter import MeshGeometry
from morphomesh.models import ERR_INPUT_MESH_NOT_FOUND, MorphoMeshException


# ==============================================================================
# GEOMETRY GENERATORS FOR ADVERSARIAL STRESS TESTING
# ==============================================================================

def create_dense_sphere_mesh(path: str, rings: int = 60, sectors: int = 80) -> int:
    """Generate high-density UV sphere (~9600 triangles)."""
    geom = MeshGeometry()
    geom.add_sphere((0.0, 0.0, 1.0), radius=1.0, rings=rings, sectors=sectors)
    geom.export_glb(path)
    return len(geom.faces)


def create_compound_creature_mesh(path: str) -> int:
    """Generate multi-part organic creature mesh."""
    geom = MeshGeometry()
    # Torso
    geom.add_box((0.0, 0.0, 0.6), (0.8, 1.6, 0.6))
    # Neck & Head
    geom.add_cylinder((0.0, 0.6, 0.8), 0.2, 0.5, segments=32, axis="Z")
    geom.add_sphere((0.0, 0.8, 1.3), 0.35, rings=30, sectors=40)
    # 6 Appendages
    for x in (-0.4, 0.4):
        for y in (-0.5, 0.0, 0.5):
            geom.add_cylinder((x, y, 0.0), 0.12, 0.7, segments=24, axis="Z")
    # Tail
    geom.add_cylinder((0.0, -0.9, 0.6), 0.1, 0.9, segments=24, axis="Y")
    geom.export_glb(path)
    return len(geom.faces)


def create_hard_surface_box_cluster(path: str) -> int:
    """Generate sharp hard-surface geometry cluster."""
    geom = MeshGeometry()
    for i in range(5):
        geom.add_box((i * 0.3 - 0.6, 0.0, 0.5), (0.25, 0.5, 0.4))
    geom.export_glb(path)
    return len(geom.faces)


def create_low_poly_boundary_mesh(path: str) -> int:
    """Generate minimal boundary geometry (< 1000 faces)."""
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (1.0, 1.0, 1.0))
    geom.export_glb(path)
    return len(geom.faces)


def create_massive_dense_mesh(path: str) -> int:
    """Generate massive dense geometry with multiple dense spheres."""
    geom = MeshGeometry()
    geom.add_sphere((0.0, 0.0, 1.0), 0.8, rings=80, sectors=100)
    geom.add_sphere((0.0, 1.0, 1.0), 0.5, rings=60, sectors=80)
    geom.add_sphere((0.0, -1.0, 1.0), 0.5, rings=60, sectors=80)
    geom.export_glb(path)
    return len(geom.faces)


class TestMeshAnythingTopologyAndBudget:
    """Empirically stress-test face budgets and quad ratios across diverse input geometries."""

    @pytest.fixture
    def connector(self) -> MeshAnythingConnector:
        conn = MeshAnythingConnector()
        conn.initialize()
        return conn

    @pytest.fixture
    def temp_workspace(self, tmp_path) -> str:
        workspace = str(tmp_path / "retopo_workspace")
        os.makedirs(workspace, exist_ok=True)
        return workspace

    @pytest.mark.parametrize("geom_factory,geom_name", [
        (create_dense_sphere_mesh, "dense_sphere"),
        (create_compound_creature_mesh, "compound_creature"),
        (create_hard_surface_box_cluster, "box_cluster"),
        (create_low_poly_boundary_mesh, "low_poly_boundary"),
        (create_massive_dense_mesh, "massive_dense"),
    ])
    def test_budget_strictly_under_1600_and_quad_ratio_ge_90(
        self, connector, temp_workspace, geom_factory, geom_name
    ):
        """
        Empirically verify that across 5 diverse geometries, the generated quad mesh
        strictly satisfies:
          1. optimized_face_count < 1600 faces (game engine budget)
          2. quad_ratio >= 0.90 (artist-grade quad dominance)
          3. output mesh file exists and has valid glTF/GLB structure
        """
        mesh_path = os.path.join(temp_workspace, f"input_{geom_name}.glb")
        orig_faces = geom_factory(mesh_path)
        assert orig_faces > 0

        # Run retopology with standard game-ready config
        inp = MeshAnythingInput(
            input_mesh_path=mesh_path,
            config=RetopologyConfig(target_face_count=1500, enforce_pure_quad=True),
            output_dir=os.path.join(temp_workspace, f"out_{geom_name}"),
        )
        out = connector.execute(inp)

        assert isinstance(out, MeshAnythingOutput)
        assert out.optimized_face_count < 1600, (
            f"Failed budget: {out.optimized_face_count} faces is not < 1600 for {geom_name}"
        )
        assert out.quad_ratio >= 0.90, (
            f"Failed quad ratio: {out.quad_ratio:.3f} < 0.90 for {geom_name}"
        )
        assert os.path.exists(out.optimized_mesh_path)
        assert os.path.getsize(out.optimized_mesh_path) > 0

        # Validate GLB header
        with open(out.optimized_mesh_path, "rb") as f:
            magic, version, length = struct.unpack("<4sII", f.read(12))
            assert magic == b"glTF", "Exported optimized mesh is not valid GLB"
            assert version == 2

    @pytest.mark.parametrize("requested_target", [400, 600, 800, 1200, 1500, 1599, 1600, 2500, 5000])
    def test_budget_enforcement_across_target_requests(self, connector, temp_workspace, requested_target):
        """
        Verify that regardless of requested target (even if user requests 5000 faces),
        the connector strictly caps the budget to < 1600 faces.
        """
        mesh_path = os.path.join(temp_workspace, "sample.glb")
        create_compound_creature_mesh(mesh_path)

        inp = MeshAnythingInput(
            input_mesh_path=mesh_path,
            config=RetopologyConfig(target_face_count=requested_target, enforce_pure_quad=True),
            output_dir=os.path.join(temp_workspace, f"out_target_{requested_target}"),
        )
        out = connector.execute(inp)

        assert out.optimized_face_count < 1600, (
            f"Requested {requested_target} resulted in {out.optimized_face_count} faces (must be < 1600)"
        )
        assert out.quad_ratio >= 0.90

    def test_obj_format_export_and_quad_ratio(self, connector, temp_workspace):
        """Verify OBJ format output adheres to budget and valid vertex/face definitions."""
        mesh_path = os.path.join(temp_workspace, "input_for_obj.glb")
        create_dense_sphere_mesh(mesh_path)

        inp = MeshAnythingInput(
            input_mesh_path=mesh_path,
            config=RetopologyConfig(target_face_count=1400, enforce_pure_quad=True),
            output_dir=os.path.join(temp_workspace, "out_obj"),
            output_format="obj",
        )
        out = connector.execute(inp)

        assert out.optimized_mesh_path.endswith(".obj")
        assert os.path.exists(out.optimized_mesh_path)
        assert out.optimized_face_count < 1600
        assert out.quad_ratio >= 0.90

        # Inspect OBJ file structure
        with open(out.optimized_mesh_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            v_lines = [l for l in lines if l.startswith("v ")]
            f_lines = [l for l in lines if l.startswith("f ")]
            assert len(v_lines) > 0, "No vertices found in OBJ output"
            assert len(f_lines) > 0, "No faces found in OBJ output"

    def test_fallback_quadriflow_satisfies_budget_and_quad_ratio(self, connector, temp_workspace):
        """Verify fallback solver maintains the strict game-ready contract (<1600 faces, >=90% quads)."""
        mesh_path = os.path.join(temp_workspace, "input_fallback.glb")
        create_compound_creature_mesh(mesh_path)

        inp = MeshAnythingInput(
            input_mesh_path=mesh_path,
            config=RetopologyConfig(
                remote_endpoint="http://unavailable-remote-endpoint:9999",
                target_face_count=1500,
                enforce_pure_quad=True,
            ),
            output_dir=os.path.join(temp_workspace, "out_fallback"),
        )
        out = connector.execute(inp)

        assert "fallback" in out.solver_used
        assert out.optimized_face_count < 1600, f"Fallback exceeded 1600 faces: {out.optimized_face_count}"
        assert out.quad_ratio >= 0.90, f"Fallback quad ratio {out.quad_ratio} < 0.90"
        assert os.path.exists(out.optimized_mesh_path)

    def test_missing_mesh_raises_proper_exception(self, connector):
        """Verify robust error handling when input mesh file does not exist."""
        inp = MeshAnythingInput(input_mesh_path="/nonexistent/path/to/mesh.glb")
        with pytest.raises(MorphoMeshException) as exc_info:
            connector.execute(inp)
        assert exc_info.value.code == ERR_INPUT_MESH_NOT_FOUND
