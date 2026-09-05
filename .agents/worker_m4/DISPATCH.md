# Worker M4 Dispatch
Milestone: M4 — Runnable PoC Implementation & Blender Bridge
Working Directory: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4
Original Request: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md
Project Plan: /Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_1/PROJECT.md
Architecture Doc: /Users/duongnad/Documents/tool/MorphoMesh/docs/ARCHITECTURE.md
MCP Spec Doc: /Users/duongnad/Documents/tool/MorphoMesh/docs/MCP_SPECIFICATION.md
Benchmark Doc: /Users/duongnad/Documents/tool/MorphoMesh/docs/RESEARCH_BENCHMARK.md
Target Directories Owned: src/morphomesh/, blender_addon/, README.md, SETUP_GUIDE.md, pyproject.toml

## 2026-09-05T12:08:04Z
You are Worker M4 for MorphoMesh Milestone M4 (Runnable PoC Skeleton & Blender Bridge Implementation).
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m4
The authoritative user request is: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md
The project plan is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_1/PROJECT.md
The architecture doc is: /Users/duongnad/Documents/tool/MorphoMesh/docs/ARCHITECTURE.md
The MCP spec doc is: /Users/duongnad/Documents/tool/MorphoMesh/docs/MCP_SPECIFICATION.md
The benchmark doc is: /Users/duongnad/Documents/tool/MorphoMesh/docs/RESEARCH_BENCHMARK.md

READ ORIGINAL_REQUEST.md, ARCHITECTURE.md, and MCP_SPECIFICATION.md FIRST!

Your exclusive write ownership:
`src/morphomesh/`
`blender_addon/`
`pyproject.toml`
`README.md`
`SETUP_GUIDE.md`

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your task:
Build the complete, runnable Python MCP Server and Blender Bridge PoC skeleton:
1. `pyproject.toml`: Complete package setup with dependencies (`mcp>=1.2.0`, `pydantic>=2.0.0`, `pillow`, `numpy`, `pytest`, `pytest-asyncio`) and `morphomesh` CLI script.
2. `src/morphomesh/__init__.py`: Package root, exports, `__version__ = "0.1.0"`.
3. `src/morphomesh/models.py`: Pydantic v2 data models for all 7 tool inputs/outputs, error codes (`ERR_*`), enums (`CreatureType`, `QualityTier`, `TopologyType`, `RigType`, etc.).
4. `src/morphomesh/blender_bridge.py`:
   - Dual-mode bridge:
     * Socket client for interactive session (`127.0.0.1:9876`).
     * Headless runner fallback (`blender -b -P <temp_script>`) extracting sentinel JSON (`MORPHOMESH_START_JSON` ... `MORPHOMESH_END_JSON`). Auto-detects `/Applications/Blender.app/Contents/MacOS/Blender` or `BLENDER_BIN_PATH`.
   - `BpyCodeValidator(ast.NodeVisitor)` with `visit_Name` implementation blocking `__builtins__`, dangerous modules (`os`, `sys`, `subprocess`), builtins (`eval`, `exec`, `open`), and dunder attributes.
   - Blender 5.2.1 LTS engine normalization (`BLENDER_EEVEE_NEXT` -> `BLENDER_EEVEE`).
   - Procedural auto-framing camera setup if scene lacks an active camera.
5. `src/morphomesh/inference_adapter.py`:
   - `BaseInferenceAdapter(ABC)`.
   - `MockInferenceAdapter`: Generates genuine, valid OBJ/GLB 3D meshes (quadrupeds, bipeds, winged chimeras, spheres/cubes) with valid vertex data, faces, normals, UVs, and genuine PBR PNG textures (Albedo, Normal, Roughness, Metallic) generated via PIL/numpy. Completely offline, 0 VRAM!
   - `ReplicateInferenceAdapter` and `HuggingFaceInferenceAdapter`: Remote cloud stubs/APIs.
   - `get_inference_adapter(mode="mock")` factory.
6. `src/morphomesh/server.py`:
   - FastMCP server setup with all 7 tools implemented with full type hints, docstrings, schema validation, and error handling:
     * `morphomesh_generate_concept`
     * `morphomesh_create_3d_asset`
     * `morphomesh_optimize_topology`
     * `morphomesh_auto_rig`
     * `morphomesh_blender_execute`
     * `morphomesh_get_scene_status`
     * `morphomesh_render_preview`
7. `src/morphomesh/main.py`:
   - CLI entrypoint for running the server over stdio or SSE.
8. `blender_addon/morphomesh/`:
   - `__init__.py` with `bl_info`, operator registrations, and timer server startup.
   - `listener.py` with async socket server integrated via `bpy.app.timers`.
   - `operators.py` with creature generation, QuadriFlow remeshing, and Rigify assembly operators.
   - `blender_addon/package_addon.py` packaging script.
9. `README.md` and `SETUP_GUIDE.md`:
   - Publication-grade documentation covering overview, architecture, quickstart, tool specifications, Blender integration, configuration, and verification steps.

When complete, write your handoff report to `handoff.md`, update `progress.md`, and notify me via `send_message`.
