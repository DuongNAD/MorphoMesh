"""
MorphoMesh Tools Subsystem: Skeletal Animation & Retargeting Tools.

Exposes tools interfacing with Meshy Animation Library:
1. morphomesh_animate_asset
2. morphomesh_list_animations
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, Optional

from mcp.server.fastmcp import Context
from mcp.server.fastmcp.exceptions import ToolError

from morphomesh.connectors.meshy_connector import MeshyAnimationInput
from morphomesh.models import (
    AnimateAssetOutput,
    ListAnimationsOutput,
    MorphoMeshException,
)
from morphomesh.tools.base import _safe_ctx_info, _safe_ctx_progress
from morphomesh.tools.dependencies import _storage_dir, meshy_connector


# ==============================================================================
# TOOL: morphomesh_animate_asset
# ==============================================================================

async def morphomesh_animate_asset(
    asset_id: Optional[str] = None,
    rig_task_id: Optional[str] = None,
    input_mesh_path: Optional[str] = None,
    action_id: Optional[int] = None,
    action_name: Optional[str] = None,
    fps: int = 30,
    output_format: str = "glb",
    backend: str = "meshy",
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Retarget an animation action onto a rigged 3D character.

    Supports 340+ preset actions from Meshy Animation Library (e.g. Idle, Run, Walk,
    Attack, Double Combo Attack, Spell Cast, Spartan Kick, Dance...).
    """
    start_time = time.time()
    if ctx:
        await _safe_ctx_info(ctx, f"Initializing Animation Retargeting (action: {action_id or action_name or 'default'})...")
        await _safe_ctx_progress(ctx, progress=20, total=100)

    try:
        # Resolve action_id if only action_name provided
        resolved_action_id = action_id
        if resolved_action_id is None and action_name:
            matched = meshy_connector.list_animation_library(search=action_name)
            if matched:
                resolved_action_id = matched[0].action_id
            else:
                resolved_action_id = 0  # Fallback to Idle
        elif resolved_action_id is None:
            resolved_action_id = 0

        resolved_rig_id = rig_task_id or asset_id or f"rig_{uuid.uuid4().hex[:8]}"

        out_dir = os.path.join(_storage_dir, "animated")
        os.makedirs(out_dir, exist_ok=True)

        anim_inp = MeshyAnimationInput(
            rig_task_id=resolved_rig_id,
            action_id=resolved_action_id,
            fps=fps,
            output_dir=out_dir,
        )
        anim_res = meshy_connector.animate_asset(anim_inp)

        res = AnimateAssetOutput(
            animated_asset_id=f"anim_{anim_res.animation_task_id}",
            animation_task_id=anim_res.animation_task_id,
            rig_task_id=anim_res.rig_task_id,
            action_id=anim_res.action_id,
            action_name=anim_res.action_name,
            animated_glb_path=anim_res.animation_glb_path,
            animated_fbx_path=anim_res.animation_fbx_path,
            preview_url=anim_res.preview_url,
            status="success" if anim_res.execution_mode == "api" else "mock_success",
            duration_seconds=anim_res.duration_seconds or round(time.time() - start_time, 2),
        )

        if ctx:
            await _safe_ctx_progress(ctx, progress=100, total=100)
            await _safe_ctx_info(ctx, f"Animation retargeting completed: {res.action_name} ({res.animated_asset_id})")

        return res.model_dump()
    except MorphoMeshException as e:
        raise ToolError(f"MorphoMesh Tool Error: [{e.code}] {e.message}")
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_animate_asset: {str(e)}")


# ==============================================================================
# TOOL: morphomesh_list_animations
# ==============================================================================

async def morphomesh_list_animations(
    category: Optional[str] = None,
    sub_category: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    ctx: Optional[Context] = None,
) -> Dict[str, Any]:
    """
    Browse and search the 340+ preset animation actions in the Meshy Animation Library.

    Free endpoint (0 credits). Returns action IDs, descriptive names, and preview GIF URLs.
    Categories: 'WalkAndRun', 'BodyMovements', 'DailyActions', 'Fighting', 'Dancing'.
    """
    try:
        if ctx:
            await _safe_ctx_info(ctx, f"Querying Animation Library (category={category}, search={search})...")

        items = meshy_connector.list_animation_library(
            category=category,
            sub_category=sub_category,
            search=search,
        )
        total_count = len(items)
        truncated = items[:limit]

        res = ListAnimationsOutput(
            total_count=total_count,
            animations=truncated,
            categories=["WalkAndRun", "BodyMovements", "DailyActions", "Fighting", "Dancing"],
        )
        return res.model_dump()
    except Exception as e:
        raise ToolError(f"Unexpected Tool Failure in morphomesh_list_animations: {str(e)}")


__all__ = [
    "morphomesh_animate_asset",
    "morphomesh_list_animations",
]
