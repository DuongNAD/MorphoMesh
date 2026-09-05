"""
MorphoMesh: Pytest Configuration and Shared Test Fixtures.

Provides isolated temporary storage environments, sample assets (concept images,
GLB/OBJ meshes, PBR textures), in-memory MCP client sessions, and mock Blender bridge fixtures.
"""

from __future__ import annotations

import shutil
from collections.abc import Generator
from pathlib import Path

import numpy as np
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from PIL import Image

import morphomesh.server as server_module
from morphomesh.blender_bridge import BlenderBridge
from morphomesh.inference_adapter import MeshGeometry, MockInferenceAdapter
from morphomesh.server import mcp


@pytest.fixture(scope="function")
def temp_storage_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[Path, None, None]:
    """Provide an isolated temporary cache storage directory for each test."""
    cache_path = tmp_path / "cache"
    concepts_dir = cache_path / "concepts"
    assets_dir = cache_path / "assets"
    renders_dir = cache_path / "renders"
    scenes_dir = cache_path / "scenes"

    concepts_dir.mkdir(parents=True, exist_ok=True)
    assets_dir.mkdir(parents=True, exist_ok=True)
    renders_dir.mkdir(parents=True, exist_ok=True)
    scenes_dir.mkdir(parents=True, exist_ok=True)

    cache_str = str(cache_path)
    monkeypatch.setenv("MORPHOMESH_STORAGE_DIR", cache_str)
    monkeypatch.setattr(server_module, "_storage_dir", cache_str)
    
    # Point server inference adapter to the isolated cache
    adapter = MockInferenceAdapter(cache_dir=cache_str)
    monkeypatch.setattr(server_module, "inference_adapter", adapter)

    yield cache_path

    # Teardown
    if cache_path.exists():
        shutil.rmtree(cache_path, ignore_errors=True)


@pytest.fixture(scope="function")
def sample_concept_image(temp_storage_dir: Path) -> str:
    """Generate a sample 1024x1024 RGB concept PNG on disk."""
    img_path = temp_storage_dir / "concepts" / "test_concept.png"
    arr = np.full((1024, 1024, 3), 200, dtype=np.uint8)
    arr[256:768, 256:768, :] = [45, 52, 64]  # Creature silhouette proxy
    img = Image.fromarray(arr, "RGB")
    img.save(str(img_path))
    return str(img_path)


@pytest.fixture(scope="function")
def sample_rgba_image(temp_storage_dir: Path) -> str:
    """Generate a sample 1024x1024 RGBA concept PNG on disk."""
    img_path = temp_storage_dir / "concepts" / "test_concept_rgba.png"
    arr = np.zeros((1024, 1024, 4), dtype=np.uint8)
    arr[256:768, 256:768, :3] = [60, 80, 110]
    arr[256:768, 256:768, 3] = 255  # Solid alpha in center
    img = Image.fromarray(arr, "RGBA")
    img.save(str(img_path))
    return str(img_path)


@pytest.fixture(scope="function")
def sample_mesh_glb(temp_storage_dir: Path) -> str:
    """Generate a valid test binary glTF (.glb) file on disk."""
    mesh_path = temp_storage_dir / "assets" / "sample_creature.glb"
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (0.6, 0.4, 0.8))
    geom.add_sphere((0.0, 0.0, 1.2), 0.3, rings=8, sectors=12)
    geom.export_glb(str(mesh_path))
    return str(mesh_path)


@pytest.fixture(scope="function")
def sample_mesh_obj(temp_storage_dir: Path) -> str:
    """Generate a valid test Wavefront (.obj) file on disk."""
    mesh_path = temp_storage_dir / "assets" / "sample_creature.obj"
    geom = MeshGeometry()
    geom.add_box((0.0, 0.0, 0.5), (0.6, 0.4, 0.8))
    geom.add_cylinder((0.0, 0.0, 0.0), radius=0.2, height=1.0, segments=8)
    geom.export_obj(str(mesh_path))
    return str(mesh_path)


@pytest.fixture(scope="function")
def mock_adapter(temp_storage_dir: Path) -> MockInferenceAdapter:
    """Provide a standalone MockInferenceAdapter instance bound to the temp cache."""
    return MockInferenceAdapter(cache_dir=str(temp_storage_dir))


@pytest.fixture(scope="function")
def mock_blender_bridge(monkeypatch: pytest.MonkeyPatch) -> BlenderBridge:
    """Provide a BlenderBridge configured for offline testing."""
    bridge = BlenderBridge(host="127.0.0.1", port=9876)
    # Default to simulated offline responses if bridge socket is not needed
    return bridge


@pytest.fixture(scope="function")
def mcp_session_factory():
    """
    Provide an async context manager factory to connect an authentic in-memory ClientSession.
    Entering and exiting in the same task prevents anyio cancel scope task mismatch.
    """
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _create_session():
        async with create_connected_server_and_client_session(mcp._mcp_server) as session:
            await session.initialize()
            yield session

    return _create_session
