# Task Assignment: Explorer 2 (Survey - MCP Server, Tools, API Surface & Compatibility)

## Context
Project Orchestrator has initiated Phase 0 Survey for MorphoMesh re-architecture and modularization.

## Mission
Investigate the public API surface, FastMCP tool definitions, and socket bridge protocol to define strict backward compatibility contracts:
1. Catalog every FastMCP tool exposed in `src/morphomesh/server.py`:
   - Exact tool name, parameters (names, types, defaults), return types, docstrings.
   - Gating environment variables (`MORPHOMESH_INCLUDE_ALL_TOOLS`, `MORPHOMESH_INCLUDE_HUMAN_TOOLS`, `MORPHOMESH_INCLUDE_INSPECTION_TOOLS`).
2. Catalog top-level public exports in `src/morphomesh/__init__.py`:
   - Which symbols, classes, and functions are imported and re-exported.
   - What external consumers rely on them.
3. Investigate the Blender Socket Bridge protocol:
   - Socket IPC in `src/morphomesh/blender_bridge.py` and `blender_addon/morphomesh/listener.py`.
   - Framing (NDJSON), port (9876), command types, request/response schema.
   - Identify how to modularize `blender_bridge.py` without breaking any socket commands or protocols.

## Input Files
- `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (read section `## 2026-09-09T04:28:41Z` and overall context)
- `src/morphomesh/server.py`
- `src/morphomesh/__init__.py`
- `src/morphomesh/blender_bridge.py`
- `blender_addon/morphomesh/listener.py`

## Output Deliverables
Write detailed findings to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\analysis.md` and a complete handoff report to `E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\handoff.md`.

## 2026-09-09T04:30:52Z
You are Explorer 2 for MorphoMesh Survey. Your working directory is E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2. Read your task assignment in E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\DISPATCH.md and ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md. Investigate the public API surface, all FastMCP tool definitions in src/morphomesh/server.py, public exports in src/morphomesh/__init__.py, and the Blender socket bridge protocol in src/morphomesh/blender_bridge.py and blender_addon/morphomesh/listener.py. Define strict backward-compatibility invariants. Write your detailed report to E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\analysis.md and E:\tool\mcp\MorphoMesh\.agents\teamwork_preview_explorer_survey_2\handoff.md. Send a message to orchestrator when finished.

