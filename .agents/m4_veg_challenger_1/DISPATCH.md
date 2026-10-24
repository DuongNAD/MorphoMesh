## 2026-09-10T07:07:13Z

You are Challenger 1 for Milestone 4 (M4: Automated Inspection Suite & Preview Visuals).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m4_veg_challenger_1
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Root User Request: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Worker Handoff: E:\tool\mcp\MorphoMesh\.agents\m4_veg_worker_1\handoff.md or m4_worker_1
- Implementation: teamwork_projects/vegetation_library/vegetation_pipeline/validator.py
- CLI Runner: teamwork_projects/vegetation_library/pipeline.py

Mission:
Adversarially challenge and stress-test `validator.py` and `pipeline.py` with corrupted, malformed, out-of-bounds, and edge-case inputs.

Scope of Adversarial Challenge:
1. Write adversarial test scripts in your working directory to verify:
   - Corrupt GLB binaries: test truncated headers, corrupted magic bytes, invalid JSON chunk syntax, missing BIN chunks. Assert graceful failure without unhandled exceptions.
   - Vertex budget bounds: test meshes with 10 verts, 2,999 verts, 45,001 verts, and 100,000 verts. Assert `vertex_count_budget` correctly flags out-of-budget meshes.
   - Coordinate corruptions: test meshes with NaNs, positive infinity, negative infinity, and extreme coordinates ($10^{12}$). Assert `zero_nan_inf_coordinates` fails.
   - Ground alignment bounds: test meshes with $Z_{\min} = 10.0\text{m}$, $Z_{\min} = -5.0\text{m}$, $Z_{\min} = 0.010\text{m}$. Assert `ground_contact_base_aligned` fails.
   - Centroid centering bounds: test meshes with base centroid at $(0.10, 0.0)$m (offset $0.10\text{m} > 0.05\text{m}$). Assert `base_contact_centroid_centered` fails.
   - Static mesh rigging injections: inject active `skins`, `animations`, `JOINTS_0`, `WEIGHTS_0`, or node `skin` into GLB structure; add `g bone_pelvis` or `skin` directives into companion OBJ. Assert static mesh invariants fail.
   - Texture corruptions: test missing channels, 0-byte images, solid-black albedos, non-dielectric metallics (e.g. metallic = 1.0), and flat normal maps. Assert texture checks fail.
   - CLI stress: test `pipeline.py` with invalid species, invalid modes, invalid categories, `--validate-only`, `--render-only`, `--summary`. Assert proper exit codes (0 for valid, 1 for invalid/failed, 2 for CLI arg errors).
2. Execute your adversarial test scripts via `uv run python`.
3. Deliver an empirical verdict: APPROVE or REQUEST_CHANGES with detailed evidence.

Rules:
- Do not modify project source code files outside your working directory.
- Maintain progress.md in your working directory.
- Deliver your findings and verdict in E:\tool\mcp\MorphoMesh\.agents\m4_veg_challenger_1\handoff.md.
- Send completion message to parent when finished.
