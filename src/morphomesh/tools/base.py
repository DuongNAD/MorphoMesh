"""
MorphoMesh Tools Subsystem: Base Context Helpers.

Safe execution wrappers for FastMCP Context reporting (info, progress)
preventing exceptions in environments without active context.
"""

from __future__ import annotations

from typing import Optional
from mcp.server.fastmcp import Context


async def _safe_ctx_info(ctx: Optional[Context], message: str) -> None:
    """Safely forward informational logging messages to MCP context if present."""
    if ctx is not None:
        try:
            await ctx.info(message)
        except Exception:
            pass


async def _safe_ctx_progress(ctx: Optional[Context], progress: float, total: float) -> None:
    """Safely report operation progress to MCP context if present."""
    if ctx is not None:
        try:
            await ctx.report_progress(progress=progress, total=total)
        except Exception:
            pass


__all__ = [
    "_safe_ctx_info",
    "_safe_ctx_progress",
]
