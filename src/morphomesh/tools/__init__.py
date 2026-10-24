"""
MorphoMesh Tools Subsystem.

Provides modular implementations of all 19 FastMCP tools, dependency singletons,
runtime gating, context logging helpers, and tool registration logic.
"""

from __future__ import annotations

from morphomesh.tools.animation import (
    morphomesh_animate_asset,
    morphomesh_list_animations,
)
from morphomesh.tools.base import _safe_ctx_info, _safe_ctx_progress
from morphomesh.tools.creature import (
    morphomesh_auto_rig,
    morphomesh_blender_execute,
    morphomesh_create_3d_asset,
    morphomesh_generate_concept,
    morphomesh_get_scene_status,
    morphomesh_optimize_topology,
    morphomesh_render_preview,
)
from morphomesh.tools.dependencies import (
    _backend_mode,
    _storage_dir,
    blender_bridge,
    inference_adapter,
    logger,
    meshy_connector,
)
from morphomesh.tools.gating import (
    ALL_TOOL_NAMES,
    ANIMATION_TOOL_NAMES,
    CREATURE_TOOL_NAMES,
    HUMAN_TOOL_NAMES,
    INSPECTION_TOOL_NAMES,
    _get_active_allowed_tool_names,
    apply_tool_gating,
)
from morphomesh.tools.human import (
    morphomesh_assemble_master_character,
    morphomesh_auto_rig_human,
    morphomesh_create_human_asset,
    morphomesh_dress_human,
    morphomesh_export_production_character,
    morphomesh_groom_human,
    morphomesh_setup_human_materials,
)
from morphomesh.tools.inspection import (
    VALID_COLOR_TYPES,
    VALID_INSPECTOR_VIEWPOINTS,
    VALID_SHADING_MODES,
    VALID_TARGET_PRESETS,
    morphomesh_capture_viewport,
    morphomesh_critique_visual_quality,
    morphomesh_setup_inspector_camera_rig,
)
from morphomesh.tools.registry import register_all_tools
from morphomesh.tools.server_instance import create_mcp_server, mcp

__all__ = [
    # Server instance & factory
    "mcp",
    "create_mcp_server",
    # Singletons & Dependencies
    "blender_bridge",
    "inference_adapter",
    "meshy_connector",
    "logger",
    "_backend_mode",
    "_storage_dir",
    # Context helpers
    "_safe_ctx_info",
    "_safe_ctx_progress",
    # Gating & Registry
    "ALL_TOOL_NAMES",
    "CREATURE_TOOL_NAMES",
    "HUMAN_TOOL_NAMES",
    "INSPECTION_TOOL_NAMES",
    "ANIMATION_TOOL_NAMES",
    "_get_active_allowed_tool_names",
    "apply_tool_gating",
    "register_all_tools",
    # Creature Tools
    "morphomesh_generate_concept",
    "morphomesh_create_3d_asset",
    "morphomesh_optimize_topology",
    "morphomesh_auto_rig",
    "morphomesh_blender_execute",
    "morphomesh_get_scene_status",
    "morphomesh_render_preview",
    # Animation Tools
    "morphomesh_animate_asset",
    "morphomesh_list_animations",
    # Human Tools
    "morphomesh_create_human_asset",
    "morphomesh_auto_rig_human",
    "morphomesh_setup_human_materials",
    "morphomesh_groom_human",
    "morphomesh_dress_human",
    "morphomesh_assemble_master_character",
    "morphomesh_export_production_character",
    # Inspection Tools & Sets
    "morphomesh_setup_inspector_camera_rig",
    "morphomesh_capture_viewport",
    "morphomesh_critique_visual_quality",
    "VALID_INSPECTOR_VIEWPOINTS",
    "VALID_SHADING_MODES",
    "VALID_COLOR_TYPES",
    "VALID_TARGET_PRESETS",
]
