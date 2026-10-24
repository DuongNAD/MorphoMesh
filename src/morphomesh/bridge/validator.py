"""
MorphoMesh: Blender Code AST Static Analysis Security Validator.

Inspects Python scripts submitted for execution inside Blender to completely
neutralize remote code execution (RCE), arbitrary process spawning,
filesystem destruction, and reflection bypasses.
"""

from __future__ import annotations

import ast
from typing import Any, Dict, Optional

from morphomesh.models import MorphoMeshException


class SecurityException(MorphoMeshException):
    """Raised when an untrusted script violates AST safety rules."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="ERR_SCRIPT_SECURITY_VIOLATION",
            message=message,
            details=details or {},
        )


class BlenderExecutionError(MorphoMeshException):
    """Raised when Blender execution fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            code="ERR_BLENDER_EXECUTION_FAILED",
            message=message,
            details=details or {},
        )


class BpyCodeValidator(ast.NodeVisitor):
    """
    Two-Tier AST Static Analysis Engine.

    Inspects Python scripts submitted for execution inside Blender to completely
    neutralize remote code execution (RCE), arbitrary process spawning,
    filesystem destruction, and reflection bypasses.
    """

    ALLOWED_MODULES = {
        "bpy",
        "math",
        "mathutils",
        "bmesh",
        "numpy",
        "random",
        "json",
        "collections",
        "itertools",
        "time",
        "morphomesh",
    }

    FORBIDDEN_MODULES = {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
        "http",
        "urllib",
        "requests",
        "ctypes",
        "multiprocessing",
        "threading",
        "signal",
        "pty",
        "importlib",
        "builtins",
        "posix",
    }

    FORBIDDEN_CALLS = {
        "eval",
        "exec",
        "__import__",
        "compile",
        "open",
        "input",
        "breakpoint",
        "globals",
        "locals",
        "getattr",
        "setattr",
        "delattr",
    }

    FORBIDDEN_ATTRIBUTES = {
        "__subclasses__",
        "__globals__",
        "__code__",
        "__dict__",
        "__bases__",
        "__mro__",
        "__class__",
    }

    FORBIDDEN_NAMES = {
        "__builtins__",
        "eval",
        "exec",
        "open",
        "compile",
        "__import__",
        "globals",
        "locals",
        "getattr",
        "setattr",
        "delattr",
        "os",
        "sys",
        "subprocess",
        "shutil",
        "socket",
    }

    MAX_SCRIPT_LENGTH = 10000

    def validate(self, script_code: str) -> None:
        """Parse and statically validate script against security rules."""
        if not script_code or not script_code.strip():
            raise SecurityException("Script is empty.")

        if len(script_code) > self.MAX_SCRIPT_LENGTH:
            raise SecurityException(
                f"Script exceeds maximum length of {self.MAX_SCRIPT_LENGTH} characters "
                f"(received {len(script_code)})."
            )

        try:
            tree = ast.parse(script_code)
        except SyntaxError as e:
            raise MorphoMeshException(
                code="ERR_SCRIPT_SYNTAX_ERROR",
                message=f"Script contains Python syntax error: {e.msg} at line {e.lineno}",
                details={"lineno": e.lineno, "offset": e.offset, "text": e.text},
            )

        self.visit(tree)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_module = alias.name.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES or base_module not in self.ALLOWED_MODULES:
                raise SecurityException(
                    f"Forbidden module import: '{alias.name}' on line {node.lineno}. "
                    f"Permitted modules: {sorted(self.ALLOWED_MODULES)}"
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_module = node.module.split(".")[0]
            if base_module in self.FORBIDDEN_MODULES or base_module not in self.ALLOWED_MODULES:
                raise SecurityException(
                    f"Forbidden from-import: '{node.module}' on line {node.lineno}. "
                    f"Permitted modules: {sorted(self.ALLOWED_MODULES)}"
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            if node.func.id in self.FORBIDDEN_CALLS:
                raise SecurityException(
                    f"Forbidden built-in call: '{node.func.id}()' on line {node.lineno}."
                )
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in self.FORBIDDEN_ATTRIBUTES:
            raise SecurityException(
                f"Forbidden reflection attribute access: '{node.attr}' on line {node.lineno}."
            )
        if node.attr.startswith("__") and node.attr.endswith("__"):
            raise SecurityException(
                f"Forbidden dunder attribute access: '{node.attr}' on line {node.lineno}."
            )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id in self.FORBIDDEN_NAMES or node.id == "__builtins__":
            raise SecurityException(
                f"Forbidden name access: '{node.id}' on line {node.lineno}."
            )
        if node.id.startswith("__") and node.id.endswith("__"):
            raise SecurityException(
                f"Forbidden dunder identifier: '{node.id}' on line {node.lineno}."
            )
        self.generic_visit(node)


__all__ = [
    "SecurityException",
    "BlenderExecutionError",
    "BpyCodeValidator",
]
