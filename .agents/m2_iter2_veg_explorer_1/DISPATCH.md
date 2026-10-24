## 2026-09-10T05:59:36Z

You are Explorer 1 for Milestone 2 Iteration 2 (Remediation Strategy: Cache Provenance, Dispatch Integrity & Test Isolation).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_explorer_1
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Root User Request: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Gate Status: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\GATE_STATUS.md
- Full Forensic Auditor Evidence Report: E:\tool\mcp\MorphoMesh\.agents\m2_veg_auditor_1\handoff.md
- Reviewer 1 Report: E:\tool\mcp\MorphoMesh\.agents\m2_veg_reviewer_1\handoff.md
- Challenger 1 Report: E:\tool\mcp\MorphoMesh\.agents\m2_veg_challenger_1\handoff.md
- Current Implementation: teamwork_projects/vegetation_library/vegetation_pipeline/generator.py
- Current Test Suite: teamwork_projects/vegetation_library/tests/test_generator.py

Mission:
Investigate and design the exact fix strategy for the cache masquerading integrity violation, cross-engine cache pollution, GLB header verification, and test isolation.

Scope of Investigation:
1. Cache Masquerading & API Key Bypass Defect:
   - In `generator.py`, lines 1395-1408, `generate_plant()` executes `check_cache()` BEFORE checking `mode == "meshy"` and validating credentials.
   - `check_cache()` currently returns cached assets even if their source was `"procedural"`, allowing procedural assets to satisfy explicit Meshy requests without API keys.
   - Design the exact code fix:
     - For `mode == "meshy"`: credential validation MUST occur before accepting or returning any asset.
     - `check_cache()` must support an `expected_source: Optional[str] = None` parameter. When checking for Meshy cache (`expected_source="meshy"`), verify that `manifest_data.get("source") == "meshy"`.
     - When `mode == "procedural"`, ensure `expected_source="procedural"` (or skip Meshy cache).
2. Binary GLB Header Verification in `check_cache`:
   - Before accepting `{species_id}.glb`, verify file integrity by checking the binary header: read first 12 bytes and assert `magic == b"glTF"` and `version == 2`.
   - Reject 0-byte, truncated, or non-GLB files as cache misses (`continue`).
   - If `cache_manifest.json` fails `json.load`, treat as cache miss rather than swallowing empty metadata.
3. Test Isolation in `test_generator.py`:
   - In `test_dispatch_mode_meshy_explicit_without_key_raises`, pass `output_dir=tmp_path / "meshy_no_key"` so ambient files in `./output` do not mask credential validation.
   - Verify all tests in `TestGeneratePlantDispatch` and `TestMeshyGeneratorUnit` use isolated `tmp_path` directories.
4. Formulate the exact code changes and proposed implementation diffs for Worker 2.

Rules:
- Read-only exploration. DO NOT modify source code files.
- Maintain progress.md in your working directory.
- Deliver your structured handoff report to E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_explorer_1\handoff.md.
- Send a completion message back to parent using send_message.
