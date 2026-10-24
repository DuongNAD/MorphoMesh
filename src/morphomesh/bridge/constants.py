"""
MorphoMesh: Blender Bridge Constants.

Defines network defaults, sentinel framing tokens, buffer size limits,
and re-exports canonical bone, collection, and error code constants.
"""

from __future__ import annotations

import os

DEFAULT_HOST = os.environ.get("BLENDER_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("BLENDER_PORT", "9876"))

SENTINEL_START = "MORPHOMESH_START_JSON"
SENTINEL_END = "MORPHOMESH_END_JSON"

BUFFER_SIZE = 65536
MAX_BUFFER_BYTES = 16 * 1024 * 1024
SOCKET_TIMEOUT = 120.0

try:
    from morphomesh.human_rigging import ALL_163_DEF_BONES, ARKIT_52_BLENDSHAPES
except (ImportError, ModuleNotFoundError):
    try:
        from human_rigging import ALL_163_DEF_BONES, ARKIT_52_BLENDSHAPES  # type: ignore[no-redef]
    except (ImportError, ModuleNotFoundError):
        ALL_163_DEF_BONES = []  # type: ignore[assignment]
        ARKIT_52_BLENDSHAPES = []  # type: ignore[assignment]

try:
    from morphomesh.character_assembler import ALL_SEVEN_COLLECTIONS
except (ImportError, ModuleNotFoundError):
    try:
        from character_assembler import ALL_SEVEN_COLLECTIONS  # type: ignore[no-redef]
    except (ImportError, ModuleNotFoundError):
        ALL_SEVEN_COLLECTIONS = [  # type: ignore[assignment]
            "01_Body",
            "02_Hair",
            "03_Wardrobe",
            "04_Props",
            "05_Armature",
            "06_Lights",
            "07_Cameras",
        ]

from morphomesh.models import (
    ERR_BLENDER_EXECUTION_FAILED,
    ERR_BLENDER_UNAVAILABLE,
    ERR_NO_CAMERA,
    ERR_REMESH_FAILED,
    ERR_SCRIPT_EXECUTION_TIMEOUT,
    ERR_SCRIPT_RUNTIME_EXCEPTION,
    ERR_SCRIPT_SECURITY_VIOLATION,
    ERR_SCRIPT_SYNTAX_ERROR,
    ERR_SKINNING_HEAT_FAILURE,
    ERR_TIMEOUT,
)

__all__ = [
    "DEFAULT_HOST",
    "DEFAULT_PORT",
    "SENTINEL_START",
    "SENTINEL_END",
    "BUFFER_SIZE",
    "MAX_BUFFER_BYTES",
    "SOCKET_TIMEOUT",
    "ALL_163_DEF_BONES",
    "ALL_SEVEN_COLLECTIONS",
    "ARKIT_52_BLENDSHAPES",
    "ERR_BLENDER_UNAVAILABLE",
    "ERR_NO_CAMERA",
    "ERR_REMESH_FAILED",
    "ERR_SCRIPT_EXECUTION_TIMEOUT",
    "ERR_SCRIPT_RUNTIME_EXCEPTION",
    "ERR_SCRIPT_SECURITY_VIOLATION",
    "ERR_SCRIPT_SYNTAX_ERROR",
    "ERR_SKINNING_HEAT_FAILURE",
    "ERR_TIMEOUT",
    "ERR_BLENDER_EXECUTION_FAILED",
]
