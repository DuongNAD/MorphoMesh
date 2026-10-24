"""
MorphoMesh: FastMCP Server Implementation & Facade.

Exposes the authoritative Model Context Protocol (MCP) tools for 3D creature
and digital human generation and digital content creation in Blender LTS.
Modularized under morphomesh.tools with complete backward compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set
from mcp.server.fastmcp import Context, FastMCP

from morphomesh.bridge import BlenderBridge
from morphomesh.connectors.meshy_connector import MeshyConnector
from morphomesh.inference_adapter import BaseInferenceAdapter
from morphomesh.tools import (
    ALL_TOOL_NAMES,
    ANIMATION_TOOL_NAMES,
    CREATURE_TOOL_NAMES,
    HUMAN_TOOL_NAMES,
    INSPECTION_TOOL_NAMES,
    VALID_COLOR_TYPES,
    VALID_INSPECTOR_VIEWPOINTS,
    VALID_SHADING_MODES,
    VALID_TARGET_PRESETS,
    _backend_mode,
    _get_active_allowed_tool_names,
    _safe_ctx_info,
    _safe_ctx_progress,
    _storage_dir,
    apply_tool_gating,
    blender_bridge,
    create_mcp_server,
    inference_adapter,
    logger,
    mcp,
    meshy_connector,
    morphomesh_animate_asset,
    morphomesh_assemble_master_character,
    morphomesh_auto_rig,
    morphomesh_auto_rig_human,
    morphomesh_blender_execute,
    morphomesh_capture_viewport,
    morphomesh_create_3d_asset,
    morphomesh_create_human_asset,
    morphomesh_critique_visual_quality,
    morphomesh_dress_human,
    morphomesh_export_production_character,
    morphomesh_generate_concept,
    morphomesh_get_scene_status,
    morphomesh_groom_human,
    morphomesh_list_animations,
    morphomesh_optimize_topology,
    morphomesh_render_preview,
    morphomesh_setup_human_materials,
    morphomesh_setup_inspector_camera_rig,
    register_all_tools,
)

__all__ = [
    # Server instance and factory
    "mcp",
    "create_mcp_server",
    # Singletons & dependencies
    "blender_bridge",
    "inference_adapter",
    "meshy_connector",
    "logger",
    "_backend_mode",
    "_storage_dir",
    # Context helpers
    "_safe_ctx_info",
    "_safe_ctx_progress",
    # Tool name sets and gating
    "ALL_TOOL_NAMES",
    "CREATURE_TOOL_NAMES",
    "HUMAN_TOOL_NAMES",
    "INSPECTION_TOOL_NAMES",
    "ANIMATION_TOOL_NAMES",
    "_get_active_allowed_tool_names",
    "apply_tool_gating",
    "register_all_tools",
    # 7 Canonical Creature Tools
    "morphomesh_generate_concept",
    "morphomesh_create_3d_asset",
    "morphomesh_optimize_topology",
    "morphomesh_auto_rig",
    "morphomesh_blender_execute",
    "morphomesh_get_scene_status",
    "morphomesh_render_preview",
    # 2 Animation Tools
    "morphomesh_animate_asset",
    "morphomesh_list_animations",
    # 7 Digital Human Tools
    "morphomesh_create_human_asset",
    "morphomesh_auto_rig_human",
    "morphomesh_setup_human_materials",
    "morphomesh_groom_human",
    "morphomesh_dress_human",
    "morphomesh_assemble_master_character",
    "morphomesh_export_production_character",
    # 3 Inspection & Quality Critique Tools
    "morphomesh_setup_inspector_camera_rig",
    "morphomesh_capture_viewport",
    "morphomesh_critique_visual_quality",
    # Inspection Sets
    "VALID_INSPECTOR_VIEWPOINTS",
    "VALID_SHADING_MODES",
    "VALID_COLOR_TYPES",
    "VALID_TARGET_PRESETS",
]
