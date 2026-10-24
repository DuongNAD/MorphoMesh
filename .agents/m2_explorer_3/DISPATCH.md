## 2026-09-10T05:33:25Z

You are Explorer 3 for Milestone 2 (M2: Generator QA & Integration Test Design).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m2_explorer_3
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Catalog Implementation: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\vegetation_pipeline\catalog.py

Mission:
Design the test strategy and test suite for Milestone 2 in `teamwork_projects/vegetation_library/tests/test_generator.py`.

Scope of Investigation:
1. Design unit tests for `MeshyGenerator`:
   - Mocking Meshy API HTTP endpoints (preview, task polling, refine) with `httpx` or `unittest.mock`.
   - Assert request payload includes positive prompt, negative blacklist, polycount, art style, topology.
   - Assert retry backoff on 429/500 HTTP errors.
   - Assert disk caching skips re-generation when valid cached files exist.
2. Design unit tests for `ProceduralBotanicalGenerator`:
   - Test procedural generation for representative species from each of the 7 biomes.
   - Assert valid GLB output generated and parseable.
   - Assert vertex count within [3000, 45000].
   - Assert Z_min ≈ 0.0 ground alignment.
   - Assert zero skeletal bones/armatures in glTF buffers.
   - Assert all 4 PBR texture maps exist and are valid non-black images.
   - Assert deterministic repeatability (same seed -> identical vertices).
3. Design end-to-end `generate_plant(species, mode="auto")` dispatch tests.
4. Formulate drop-in test suite specifications for the Worker.

Rules:
- Read-only exploration. DO NOT modify source code files.
- Deliver structured handoff report to E:\tool\mcp\MorphoMesh\.agents\m2_explorer_3\handoff.md.
- Send completion message to parent when finished.
