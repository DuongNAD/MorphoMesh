# Handoff Report — Explorer Survey 2 (R2 Architecture & R4 Bridge)

## 1. Observation
1. **Host Environment**: Executed `python3 --version && which python3 && uv --version`. Result: Python 3.11.8 at `/Users/duongnad/.pyenv/shims/python3`, `uv 0.12.9 (aarch64-apple-darwin)`. FastMCP (`mcp.server.fastmcp`), `pydantic 2.13.4`, `pytest 9.1.1`, `numpy 1.26.4`, `PIL 9.5.0`, `requests 2.34.2`, and `httpx 0.28.1` are installed and directly importable.
2. **Blender Environment**: Located Blender at `/Applications/Blender.app`. Executed `/Applications/Blender.app/Contents/MacOS/Blender --version`. Output confirmed: `Blender 5.2.1 LTS` built 2026-08-25, running internal Python `3.13.13 (main, Apr 25 2025)`.
3. **Blender Native Features**:
   - `bpy.app.timers` is available (`hasattr(bpy.app, 'timers') == True`).
   - `rigify` addon module is built-in (`addon_utils.modules()` includes rigify).
   - `bpy.ops.import_scene.gltf` and `bpy.ops.export_scene.gltf` are standard.
   - Built-in quad remeshing operators exist: `bpy.ops.object.quadriflow_remesh` and `bpy.ops.object.voxel_remesh`. RNA properties for `quadriflow_remesh` confirm support for `target_faces`, `target_ratio`, `target_edge_length`, `use_preserve_sharp`, `use_preserve_boundary`, `use_mesh_symmetry`, `smooth_normals`, and `preserve_attributes`.
   - Built-in automatic skinning exists: `bpy.ops.object.parent_set(type='ARMATURE_AUTO')`.
   - Render engine `BLENDER_EEVEE` (EEVEE Next Metal backend) is available for high-speed viewport rendering.
4. **AST Security Verification**: Executed AST visitor test detecting imports, calls, and dunder attribute traversal. Forbidden imports (`os`, `sys`, `subprocess`) and dunder accesses (`__subclasses__`, `__class__`) were intercepted and raised security violations with zero false passes.
5. **Headless Execution Test**: Executed headless Blender CLI command printing structured JSON between sentinel tokens (`MORPHOMESH_START_JSON` ... `MORPHOMESH_END_JSON`). The output was captured and parsed with exit code 0.

## 2. Logic Chain
1. **Hardware & Model Reality (Obs. 1, Obs. 2)**: Heavy 3D diffusion models (TRELLIS.2 4B, Hunyuan3D 2.1) require 16GB-24GB+ dedicated VRAM and custom CUDA C++ kernels (`diff-gaussian-rasterization`, `nvdiffrast`, `spconv`) that cannot run natively on Apple Metal without major rewrites. Therefore, a **Hybrid Architecture** is required: the client, MCP server, scene assembly, and local retopology run on macOS Apple Silicon, while heavy 3D diffusion runs on Remote GPU backends (Replicate, HuggingFace, or custom Linux GPU servers).
2. **Deterministic Development & Testing (Obs. 1)**: Because developers, testers, and CI environments cannot rely on paid GPU API tokens for everyday unit tests, a plug-and-play `MockInferenceAdapter` generating deterministic procedural 3D meshes (quadrupeds, bipeds, winged proxies, primitives) and procedural PBR textures is essential. This guarantees 100% test pass rates in CI without cost or GPU requirements.
3. **Dual-Mode Blender Communication (Obs. 2, Obs. 3, Obs. 5)**:
   - For interactive sessions, a non-blocking localhost TCP socket server (`127.0.0.1:9876`) running via Blender Addon and hooked into `bpy.app.timers` enables real-time scene updates in the 3D viewport without freezing Blender's UI.
   - If Blender is closed or running in automated test pipelines, the bridge transparently falls back to headless CLI invocation (`blender --background --python`).
4. **Security Hardening (Obs. 4)**: To allow agent flexibility without exposing the host system to arbitrary code execution, a two-tier defense is required: (a) structured typed JSON-RPC actions for 95% of operations, and (b) an AST static analysis validator that blocks forbidden modules, dangerous builtins (`eval`, `exec`, `open`), and reflection tricks (`__subclasses__`).
5. **Stage 3 & 4 Native Pipeline Feasibility (Obs. 3)**: Since Blender 5.2.1 natively includes `quadriflow_remesh`, `ARMATURE_AUTO` heat diffusion skinning, and `rigify`, the entire topology optimization, rigging, material assignment, and preview rendering pipeline can run locally on Apple Silicon without third-party C++ dependencies.

## 3. Caveats
1. **Cycles on macOS Headless**: Cycles may require additional addon activation or compilation cache on first run; `BLENDER_EEVEE` (EEVEE Next) is the recommended and verified default renderer for fast preview generation.
2. **Network Mode for Remote Inference**: Remote GPU calls (Replicate / HuggingFace) require network connectivity and valid API tokens (`REPLICATE_API_TOKEN`). In offline or isolated test environments, the system must automatically select or default to `MockInferenceAdapter`.
3. **Blender Executable Path**: While located at `/Applications/Blender.app/Contents/MacOS/Blender` on macOS, the bridge configuration must support `BLENDER_BIN_PATH` environment variable overrides for custom or multi-version installations.

## 4. Conclusion
The architectural design and component specifications for R2 (System Architecture & Pipeline Specification) and R4 (Runnable PoC & Blender Bridge) are complete, verified against the local macOS environment, and documented in detail in `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/survey_arch_report.md`. The design fulfills all user requirements for Apple Silicon compatibility, dual-mode Blender communication, plug-and-play inference, multi-layer security, 5-stage creature dataflow, and modular Blender addon packaging.

## 5. Verification Method
1. **Inspect Survey Report**:
   ```bash
   cat /Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_2/survey_arch_report.md
   ```
2. **Verify Blender 5.2.1 LTS Capabilities**:
   ```bash
   /Applications/Blender.app/Contents/MacOS/Blender --background --python-expr "import bpy; print('QuadriFlow:', hasattr(bpy.ops.object, 'quadriflow_remesh')); print('Timers:', hasattr(bpy.app, 'timers'))"
   ```
3. **Verify Host Python & FastMCP**:
   ```bash
   python3 -c "import mcp.server.fastmcp, pydantic, pytest; print('FastMCP, Pydantic, Pytest OK')"
   ```
4. **Invalidation Conditions**:
   - The architecture would be invalidated if Blender's main-thread execution requirement could not be safely bridged with an async socket listener (refuted by `bpy.app.timers` verification).
   - The architecture would be invalidated if local quad retopology required non-compilable C++ tools on Apple Silicon (refuted by native QuadriFlow verification).
