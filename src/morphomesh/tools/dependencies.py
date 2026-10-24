"""
MorphoMesh Tools Subsystem: Shared Dependencies & Runtime Singletons.

Manages shared instances of Inference Adapter, Blender Bridge,
and Meshy Connector to avoid circular dependencies.
"""

from __future__ import annotations

import logging
import os

from morphomesh.bridge import BlenderBridge
from morphomesh.connectors.meshy_connector import MeshyConnector
from morphomesh.inference_adapter import BaseInferenceAdapter, get_inference_adapter

logger = logging.getLogger("morphomesh.server")

_backend_mode = os.environ.get("MORPHOMESH_BACKEND", "mock")
_storage_dir = os.environ.get("MORPHOMESH_STORAGE_DIR", os.path.expanduser("~/.morphomesh/cache"))

inference_adapter: BaseInferenceAdapter = get_inference_adapter(mode=_backend_mode, cache_dir=_storage_dir)
blender_bridge: BlenderBridge = BlenderBridge(
    host=os.environ.get("BLENDER_HOST", "127.0.0.1"),
    port=int(os.environ.get("BLENDER_PORT", "9876")),
    blender_bin_path=os.environ.get("BLENDER_PATH") or os.environ.get("BLENDER_BIN_PATH"),
)
meshy_connector: MeshyConnector = MeshyConnector()

__all__ = [
    "logger",
    "_backend_mode",
    "_storage_dir",
    "inference_adapter",
    "blender_bridge",
    "meshy_connector",
]
