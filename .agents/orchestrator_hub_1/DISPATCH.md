# Dispatch Messages

## 2026-09-05T12:57:29Z

You are the Project Orchestrator for Phase 2 of MorphoMesh: Open-Source Integration Hub.
Your working directory is: /Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_hub_1
The workspace root is: /Users/duongnad/Documents/tool/MorphoMesh
The authoritative user request is in: /Users/duongnad/Documents/tool/MorphoMesh/ORIGINAL_REQUEST.md (under header ## 2026-09-05T12:56:31Z).

You must organize, decompose, and lead the team to accomplish all requirements and acceptance criteria:
1. R1: Open-Source Engineering Playbook & Licensing Governance (`docs/OPEN_SOURCE_INTEGRATION_PLAYBOOK.md`):
   - Detailed analysis of 5 SOTA open-source repos:
     * Microsoft TRELLIS / TRELLIS.2 (MIT)
     * 3DAnimals / MagicPony / SMAL (Research)
     * anyCreature (Engine Procedural)
     * MeshAnything V2 (Apache-2.0)
     * Tencent Hunyuan3D-2.1 (Community License)
   - Standard guidelines for:
     * Checkpoints & Weights management (HF Hub caching, git LFS, local cache, quantization FP16/BF16/INT8/NF4/AWQ, VRAM optimization)
     * Serving & Containerization (Docker compose templates, microservices FastAPI/Gradio/ComfyUI headless, API client patterns separated from macOS client)
     * Licensing Governance & Legal Risk (Process & Network Boundary Isolation to ensure compliance with Tencent Hunyuan & Stability AI Community Licenses while maintaining MorphoMesh's open nature)
   - Acceptance: File size > 40 KB, deep technical rigor, complete and comprehensive.

2. R2: Production Open-Source Connectors in `src/morphomesh/connectors/`:
   - `__init__.py`
   - `registry.py` (Automatic connector registration, health checks, dependency checks, circuit breaker & fallback)
   - `trellis_connector.py` (TRELLIS.2 compatibility, local/remote API, structured latent/GLB and PBR texture map conversion into Blender)
   - `animals3d_connector.py` (3DAnimals/SMAL compatibility, joint landmarks and bone weights conversion to Blender Rigify standard format)
   - `anycreature_connector.py` (prompt parsing to JSON spec for anyCreature, procedural creature mesh import and animation clips)
   - `meshanything_connector.py` (loading dense meshes from AI generators and retopology coordination to quad mesh under 1600 faces for games)
   - `hunyuan_connector.py` (backend communication with Hunyuan3D-2.1 for high-fidelity meshes and PBR textures)
   - Typing with Pydantic v2, production-ready, no empty mocks or unfinished TODOs.
   - Smooth integration into `src/morphomesh/inference_adapter.py` and FastMCP tools in `src/morphomesh/server.py`.

3. R3: Automated Tests & Demo Harness:
   - `tests/test_connectors.py`: Full offline/mock test suite testing each connector, JSON spec structure, SMAL transformation matrix, PBR texture pipeline, circuit breaker & fallback.
   - `examples/open_source_pipeline_demo.py`: Comprehensive runnable example demonstrating the end-to-end integration from concept to rigged creature.
   - Full test suite passing 100% with pytest (exit code 0, 0 failures), maintaining existing test pass rate.
