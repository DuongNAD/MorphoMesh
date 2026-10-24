"""
MorphoMesh: Blender Bridge Module (Backward-Compatible Facade).

Re-exports all authoritative bridge symbols, constants, and validators
from the modularized morphomesh.bridge sub-package.
"""

from __future__ import annotations

from morphomesh.bridge import (
    ALL_163_DEF_BONES,
    ALL_SEVEN_COLLECTIONS,
    ARKIT_52_BLENDSHAPES,
    BUFFER_SIZE,
    DEFAULT_HOST,
    DEFAULT_PORT,
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
    MAX_BUFFER_BYTES,
    SENTINEL_END,
    SENTINEL_START,
    SOCKET_TIMEOUT,
    BlenderBridge,
    BlenderExecutionError,
    BlenderSocketClient,
    BpyCodeValidator,
    SecurityException,
    resolve_blender_binary,
    run_headless_script,
)

__all__ = [
    "BlenderBridge",
    "BpyCodeValidator",
    "SecurityException",
    "BlenderExecutionError",
    "BlenderSocketClient",
    "resolve_blender_binary",
    "run_headless_script",
    "SENTINEL_START",
    "SENTINEL_END",
    "DEFAULT_HOST",
    "DEFAULT_PORT",
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
