"""
MorphoMesh: Blender Socket Bridge & Headless Execution Subsystem.

Provides bidirectional communication with Blender 5.2.1 LTS via interactive
localhost TCP socket (127.0.0.1:9876) and headless subprocess CLI fallback,
two-tier AST code safety validation, and automated camera auto-framing.
"""

from __future__ import annotations

from morphomesh.bridge.bridge import BlenderBridge
from morphomesh.bridge.client import BlenderSocketClient
from morphomesh.bridge.constants import (
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
)
from morphomesh.bridge.headless import resolve_blender_binary, run_headless_script
from morphomesh.bridge.validator import BlenderExecutionError, BpyCodeValidator, SecurityException

__all__ = [
    "BlenderBridge",
    "BpyCodeValidator",
    "SecurityException",
    "BlenderExecutionError",
    "BlenderSocketClient",
    "resolve_blender_binary",
    "run_headless_script",
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
