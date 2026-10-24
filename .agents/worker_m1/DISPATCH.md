# Dispatch for Worker M1 — Pipeline & Validator Hardening

## Identity
- Role: Pipeline & Validator Engineer
- Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_m1
- Parent Conversation ID: c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4

## Mission & Instructions
You are assigned Milestone 1: Pipeline & Validator Hardening for the Vegetation Library Rebuild.

### Authoritative Files
- Original Request: `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (under `## 2026-09-10T11:11:31Z`)
- Project Scope: `E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md`
- Survey Findings:
  * `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_1\handoff.md`
  * `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_2\handoff.md`
  * `E:\tool\mcp\MorphoMesh\.agents\explorer_survey_3\handoff.md`

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### File Ownership
You exclusively own and may modify:
- `teamwork_projects/vegetation_library/vegetation_pipeline/validator.py`
- `teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py`
- `teamwork_projects/vegetation_library/vegetation_pipeline/generator.py`
- `teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py`
- `teamwork_projects/vegetation_library/tests/test_vegetation_pipeline.py`
- `teamwork_projects/vegetation_library/tests/test_validator.py`
- `teamwork_projects/vegetation_library/output/broadleaf_trees/veg_tree_oak_01/` (re-normalization and validation)

### Specific Tasks
1. Update `validator.py`:
   - Update budget range to 20,000 <= n_verts <= 65,000 (and faces).
   - In `validate_asset` (line 835), specifically pick `<species_id>.glb` (avoiding `raw_meshy_model.glb`).
   - Add Meshy cloud provenance assertion: `provenance.source == "meshy"` and non-empty `task_id`.
2. Update `catalog.py`:
   - In `BotanicalSpecies`, allow `max_vertices` up to 65,000 (`le=65000`).
3. Update `generator.py`:
   - Line 423: fix `getattr(extracted, f"{attr}_path", None)`.
   - In `generate_plant()`: when `mode == "meshy"`, mandate `expected_source == "meshy"` in `check_cache()`, and raise error instead of silently falling back to `ProceduralBotanicalGenerator`.
4. Update `post_processor.py`:
   - Line 649: Fix GLB texture extractor to handle Meshy images without `name` attribute.
5. Update `tests/test_vegetation_pipeline.py` & `test_validator.py`:
   - Align budget assertions to `[20000, 65000]`.
   - Add `encoding="utf-8"` in `test_cli_summary_mode_execution`.
   - Add test for pairwise vertex count collision (< 5%).
   - Add test for Meshy task provenance.
6. Normalize and validate `veg_tree_oak_01`:
   - Re-process `veg_tree_oak_01` through `post_processor.process_and_export()` so it has height = 12.0m, Z_min = 0.000m, centered base, and valid 2K PBR textures.
7. Run the test suite:
   - Execute: `uv run pytest teamwork_projects/vegetation_library/tests/ -v`
   - Document exact passing results (must be 100% pass, 0 failures).

Write your completion report to `E:\tool\mcp\MorphoMesh\.agents\worker_m1\handoff.md`.
When finished, send a message back to parent (`c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4`).

## 2026-09-10T11:20:13Z
<USER_REQUEST>
You are Worker M1 (Pipeline & Validator Engineer).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\worker_m1
Your detailed dispatch assignment is in: E:\tool\mcp\MorphoMesh\.agents\worker_m1\DISPATCH.md
Read DISPATCH.md, ORIGINAL_REQUEST.md (under ## 2026-09-10T11:11:31Z), PROJECT.md (E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md), and the Explorer survey reports (E:\tool\mcp\MorphoMesh\.agents\explorer_survey_1\handoff.md, explorer_survey_2\handoff.md, explorer_survey_3\handoff.md).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your File Ownership:
- teamwork_projects/vegetation_library/vegetation_pipeline/validator.py
- teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py
- teamwork_projects/vegetation_library/vegetation_pipeline/generator.py
- teamwork_projects/vegetation_library/vegetation_pipeline/post_processor.py
- teamwork_projects/vegetation_library/tests/test_vegetation_pipeline.py
- teamwork_projects/vegetation_library/tests/test_validator.py
- teamwork_projects/vegetation_library/output/broadleaf_trees/veg_tree_oak_01/

Implement all 7 tasks detailed in DISPATCH.md:
1. Update validator.py budget bounds (20,000 to 65,000 vertices/faces), fix glb_path discovery to avoid raw_meshy_model.glb, and add Meshy cloud provenance assertion.
2. Update catalog.py max_vertices le=65000.
3. Update generator.py line 423 f"{attr}_path" fix, and enforce expected_source="meshy" without procedural fallback when meshy mode is used.
4. Update post_processor.py line 649 to handle unnamed Meshy images.
5. Update tests/test_vegetation_pipeline.py and test_validator.py for budget bounds, Windows UTF-8 encoding in subprocess, and collision / provenance assertions.
6. Re-normalize veg_tree_oak_01 via post_processor so height is 12m, Z_min = 0.000m +- 0.005m, base centered, and 2K textures linked.
7. Run `uv run pytest teamwork_projects/vegetation_library/tests/ -v` to ensure 100% pass (0 failures).

Write your completion report to:
E:\tool\mcp\MorphoMesh\.agents\worker_m1\handoff.md
Include Observation, Logic Chain, Caveats, Conclusion, and Verification commands with test output.
When finished, send a message to parent (conversation ID c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4).
</USER_REQUEST>
