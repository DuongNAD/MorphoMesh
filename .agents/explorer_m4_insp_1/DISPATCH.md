## 2026-09-07T06:36:26Z

You are Explorer M4_1: FastMCP Tool Gating & Schemas Explorer for Milestone 4.
Your working directory is: e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_1
Your parent orchestrator conversation ID is: 577aaa33-6b3f-4ebc-93eb-fcc632d94bc9
The authoritative user request is at: e:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (specifically § 2026-09-07T03:34:32Z). You MUST read this file first.
The project scope document is at: e:\tool\mcp\MorphoMesh\PROJECT.md (specifically Milestone 4).

Objective:
Detail the exact implementation blueprint for exposing the inspection and critique tools in FastMCP:
1. Tool Registration in `src/morphomesh/server.py`:
   - Design FastMCP tool functions decorated with `@mcp.tool()`:
     * `morphomesh_setup_inspector_camera_rig`:
       Parameters: `viewpoint: str = "three_quarter"`, `target_center: Optional[List[float]] = None`, `sub_region: Optional[str] = None`, `focal_length: float = 50.0`, `camera_name: str = "MorphoMesh_Inspector_Camera"`, `mesh_objects: Optional[List[str]] = None`.
     * `morphomesh_capture_viewport`:
       Parameters: `output_path: Optional[str] = None`, `camera_name: str = "MorphoMesh_Inspector_Camera"`, `resolution: List[int] = [1024, 1024]`, `shading_mode: str = "SOLID"`, `color_type: str = "RANDOM"`. Returns Image or dict with base64 PNG.
     * `morphomesh_critique_visual_quality`:
       Parameters: `character_name: str = "MorphoMesh_Character"`, `target_object: Optional[str] = None`, `camera_angles: Optional[List[str]] = None`, `clearance_tolerance: float = 0.0005`, `target_preset: str = "stylized_heroine"`. Returns structured critique report dict.
2. Backward-Compatible Gating:
   - Define `INSPECTION_TOOL_NAMES = {"morphomesh_setup_inspector_camera_rig", "morphomesh_capture_viewport", "morphomesh_critique_visual_quality"}`.
   - Update `_filtered_list_tools` and `_wrapped_lowlevel_list_tools` in `src/morphomesh/server.py` so that:
     * When `MORPHOMESH_INCLUDE_INSPECTION_TOOLS` is `'1'`, `'true'`, `'yes'`, `'all'` (or when `MORPHOMESH_INCLUDE_ALL_TOOLS` is set), `mcp.list_tools()` includes `INSPECTION_TOOL_NAMES`.
     * When unset, `mcp.list_tools()` returns only the 7 canonical creature tools (guaranteeing that legacy `tests/test_tools_schema.py` expecting exactly 7 tools passes without modification).
3. Error Handling:
   - Handle `MorphoMeshException`, validation errors, and bridge connection errors by raising `ToolError`.

Scope boundaries:
- Read-only exploration. DO NOT edit or create any source code files.
- Write your progress to `e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_1\progress.md`.
- Write your comprehensive handoff report to `e:\tool\mcp\MorphoMesh\.agents\explorer_m4_insp_1\handoff.md`.
- Send completion message to parent orchestrator.
