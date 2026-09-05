"""
MorphoMesh: Blender Addon Socket Listener.

Runs a background TCP listener on 127.0.0.1:9876 synchronized with
Blender's main thread via bpy.app.timers to safely execute operators
and custom scripts without race conditions or segmentation faults.
"""

from __future__ import annotations

import ast
import json
import logging
import math
import os
import queue
import socket
import tempfile
import threading
import time
import traceback
import uuid
from typing import Any, Dict, Optional, Tuple

import bpy
import mathutils

logger = logging.getLogger("morphomesh.addon.listener")


class AddonSecurityValidator(ast.NodeVisitor):
    """Server-side redundant AST static analysis guard."""

    ALLOWED = {"bpy", "math", "mathutils", "bmesh", "numpy", "random", "json", "collections", "itertools", "time"}
    FORBIDDEN_CALLS = {"eval", "exec", "__import__", "compile", "open", "input", "globals", "locals", "getattr", "setattr"}
    FORBIDDEN_ATTRIBUTES = {"__subclasses__", "__globals__", "__code__", "__dict__", "__bases__", "__class__"}

    def validate(self, code: str) -> None:
        tree = ast.parse(code)
        self.visit(tree)

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base not in self.ALLOWED:
                raise ValueError(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            base = node.module.split(".")[0]
            if base not in self.ALLOWED:
                raise ValueError(f"Forbidden from-import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id in self.FORBIDDEN_CALLS:
            raise ValueError(f"Forbidden built-in call: {node.func.id}()")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        if node.attr in self.FORBIDDEN_ATTRIBUTES or (node.attr.startswith("__") and node.attr.endswith("__")):
            raise ValueError(f"Forbidden reflection attribute: {node.attr}")
        self.generic_visit(node)


class MorphoMeshSocketServer:
    """Manages the interactive TCP socket server and bpy.app.timers event loop."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9876):
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.running = False
        self.server_thread: Optional[threading.Thread] = None
        self.command_queue: queue.Queue[Tuple[Dict[str, Any], socket.socket]] = queue.Queue()
        self._clients: set[socket.socket] = set()
        self._clients_lock = threading.Lock()
        self.validator = AddonSecurityValidator()

    def is_running(self) -> bool:
        return self.running

    def start(self) -> None:
        if self.running:
            return

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
            self.running = True

            self.server_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self.server_thread.start()

            if not bpy.app.timers.is_registered(self._drain_queue):
                bpy.app.timers.register(self._drain_queue, persistent=True)

            logger.info(f"MorphoMesh server listening on {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to start MorphoMesh socket server: {e}")
            self.stop()

    def stop(self) -> None:
        self.running = False

        if bpy.app.timers.is_registered(self._drain_queue):
            try:
                bpy.app.timers.unregister(self._drain_queue)
            except Exception:
                pass

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        with self._clients_lock:
            for c in self._clients:
                try:
                    c.close()
                except Exception:
                    pass
            self._clients.clear()

        while not self.command_queue.empty():
            try:
                self.command_queue.get_nowait()
            except queue.Empty:
                break

        logger.info("MorphoMesh socket server stopped")

    def _accept_loop(self) -> None:
        self.socket.settimeout(1.0)
        while self.running:
            try:
                client, addr = self.socket.accept()
                threading.Thread(target=self._client_handler, args=(client,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                if not self.running:
                    break

    def _client_handler(self, client: socket.socket) -> None:
        with self._clients_lock:
            self._clients.add(client)
        client.settimeout(1.0)
        buffer = b""

        try:
            while self.running:
                try:
                    data = client.recv(65536)
                    if not data:
                        break
                    buffer += data
                    try:
                        cmd = json.loads(buffer.decode("utf-8"))
                        buffer = b""
                        self.command_queue.put((cmd, client))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue
                except socket.timeout:
                    continue
                except Exception:
                    break
        finally:
            with self._clients_lock:
                self._clients.discard(client)

    def _drain_queue(self) -> float:
        """Executes queued commands on Blender's MAIN THREAD."""
        if not self.running:
            return None

        while not self.command_queue.empty():
            try:
                cmd, client = self.command_queue.get_nowait()
            except queue.Empty:
                break

            req_id = cmd.get("id", "res-1")
            method = cmd.get("method") or cmd.get("type", "")
            params = cmd.get("params", {})

            try:
                result = self._dispatch(method, params)
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "status": "success",
                    "result": result,
                }
            except Exception as e:
                response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "status": "error",
                    "error": {"code": -32000, "message": str(e)},
                }

            try:
                client.sendall(json.dumps(response).encode("utf-8") + b"\n")
            except Exception:
                pass

        return 0.02  # Re-check every 20ms

    def _dispatch(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch RPC methods in main thread context."""
        if method in ("morphomesh.ping", "ping"):
            ver = f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}"
            return {"status": "pong", "blender_version": ver, "mode": "interactive"}

        elif method in ("morphomesh.get_scene_status", "get_scene_info"):
            scene = bpy.context.scene
            objs = []
            v_tot = 0
            f_tot = 0
            for o in scene.objects:
                vc = len(o.data.vertices) if o.type == 'MESH' and o.data else 0
                fc = len(o.data.polygons) if o.type == 'MESH' and o.data else 0
                v_tot += vc
                f_tot += fc
                objs.append({
                    "name": o.name,
                    "type": o.type,
                    "location": list(o.location),
                    "rotation_euler": list(o.rotation_euler),
                    "scale": list(o.scale),
                    "parent": o.parent.name if o.parent else None,
                    "children": [c.name for c in o.children],
                    "vertex_count": vc,
                    "face_count": fc,
                    "triangle_count": fc * 2,
                    "materials": [m.name for m in o.data.materials if m] if o.type == 'MESH' and o.data else [],
                    "modifiers": [m.name for m in o.modifiers],
                })

            armatures = [{"name": a.name, "bone_count": len(a.data.bones)} for a in scene.objects if a.type == 'ARMATURE' and a.data]
            cameras = [{"name": c.name, "lens_focal_length": getattr(c.data, 'lens', 50.0)} for c in scene.objects if c.type == 'CAMERA' and c.data]
            lights = [{"name": l.name, "type": getattr(l.data, 'type', 'POINT'), "energy": getattr(l.data, 'energy', 10.0)} for l in scene.objects if l.type == 'LIGHT' and l.data]

            return {
                "scene_name": scene.name,
                "blender_version": f"{bpy.app.version[0]}.{bpy.app.version[1]}.{bpy.app.version[2]}",
                "active_object": bpy.context.active_object.name if bpy.context.active_object else None,
                "object_count": len(scene.objects),
                "total_vertices": v_tot,
                "total_faces": f_tot,
                "objects": objs,
                "armatures": armatures,
                "cameras": cameras,
                "lights": lights,
            }

        elif method in ("morphomesh.execute_custom_script", "execute_code"):
            code = params.get("script") or params.get("code", "")
            # Server-side AST validation
            self.validator.validate(code)

            return_vars = params.get("return_variables", [])
            local_scope = {"bpy": bpy, "math": math, "mathutils": mathutils}
            exec(code, local_scope, local_scope)

            out_vars = {}
            for v in return_vars:
                if v in local_scope:
                    val = local_scope[v]
                    try:
                        json.dumps(val)
                        out_vars[v] = val
                    except Exception:
                        out_vars[v] = str(val)

            return {
                "success": True,
                "stdout": "",
                "stderr": "",
                "returned_data": out_vars,
            }

        else:
            raise ValueError(f"Unknown RPC method: {method}")


_global_server: Optional[MorphoMeshSocketServer] = None


def get_server() -> MorphoMeshSocketServer:
    global _global_server
    if _global_server is None:
        _global_server = MorphoMeshSocketServer()
    return _global_server
