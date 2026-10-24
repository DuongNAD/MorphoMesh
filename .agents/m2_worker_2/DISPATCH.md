## 2026-09-10T06:06:16Z

<USER_REQUEST>
You are Worker 2 for Milestone 2 Iteration 2 (Remediation: Meshy AI Text-to-3D Generation Engine & Procedural Fallback Harness).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m2_worker_2
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Root User Request: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Gate Status & Auditor Findings: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\GATE_STATUS.md
- Full Forensic Auditor Evidence: E:\tool\mcp\MorphoMesh\.agents\m2_veg_auditor_1\handoff.md
- M2 Iteration 2 Explorer 1 Report (Cache & Test Isolation): E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_explorer_1\handoff.md
- M2 Iteration 2 Explorer 2 Report (Meshy API & Backoff Capping): E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_explorer_2\handoff.md
- M2 Iteration 2 Explorer 3 Report (Conifer Stitching & Seed Modulo): E:\tool\mcp\MorphoMesh\.agents\m2_iter2_veg_explorer_3\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Exclusive Write Ownership:
- teamwork_projects/vegetation_library/vegetation_pipeline/generator.py
- teamwork_projects/vegetation_library/vegetation_pipeline/catalog.py
- teamwork_projects/vegetation_library/vegetation_pipeline/taxonomy_catalog.json
- teamwork_projects/vegetation_library/vegetation_pipeline/__init__.py
- teamwork_projects/vegetation_library/tests/test_generator.py
- teamwork_projects/vegetation_library/tests/test_catalog.py

Task Instructions:
1. Cache Provenance & Mode Dispatch Fixes (from Explorer 1):
   - In `generate_plant`:
     - Add mode validation: `if mode not in ("auto", "meshy", "procedural"): raise ValueError(f"Invalid generation mode: '{mode}'")`.
     - When `mode == "meshy"`: validate API key (`api_key = meshy_gen.resolve_api_key()`) FIRST before checking or returning any cache. When checking cache for `mode == "meshy"`, pass `expected_source="meshy"`.
     - When `mode == "auto"`: if cache hit exists, return it. If cache miss, check API key; if key present, attempt Meshy with fallback to procedural; if key absent, dispatch procedural.
   - In `MeshyGenerator.check_cache(self, species, target_dir=None, expected_source: Optional[str] = None) -> Optional[RawAsset]`:
     - Binary GLB header validation: read first 12 bytes of `{species_id}.glb`. Assert length == 12, `magic == b"glTF"`, `version == 2`. If invalid, treat as cache miss (`continue`).
     - JSON manifest error handling: if `cache_manifest.json` exists but fails `json.load`, treat as cache miss (`continue`).
     - Provenance check: if `expected_source is not None`, verify `manifest_data.get("source") == expected_source`. If mismatched, treat as cache miss.
2. Live API Model Upgrade & Resilience (from Explorer 2):
   - In `MeshyGeneratorConfig`: set `ai_model: str = "meshy-6"`.
   - In `catalog.py`: update `MeshyPromptSpec.ai_model` default to `"meshy-6"`.
   - In `taxonomy_catalog.json`: update all 35 occurrences of `"meshy-4"` to `"meshy-6"`.
   - In `_request_with_retry`:
     - Apply backoff max cap AFTER retry_after:
       ```python
       if retry_after is not None:
           delay = max(delay, retry_after)
       delay = min(self.config.backoff_max_seconds, delay)
       ```
     - Fast-fail on non-429 4xx client errors:
       `if 400 <= e.code < 500 and e.code != 429: raise RuntimeError(...)`.
   - In `MeshyGenerator.generate()`:
     - Enforce static mesh invariant: `if not self._verify_static_mesh(glb_path): raise RuntimeError(...)`.
3. Procedural Geometry & Seed Fixes (from Explorer 3):
   - In `_build_conifer`:
     - Connect consecutive branch segment rings with quad faces:
       `mesh.add_quad([b_indices[seg-1][s], b_indices[seg-1][ns], b_indices[seg][ns], b_indices[seg][s]], uv_base=FOLIAGE_UV, double_sided=False)`.
     - Add quad caps at branch start and tip (`add_quad_cap`).
     - Assert zero orphan vertices while preserving `quad_ratio == 1.0`.
   - In `ProceduralBotanicalGenerator.generate`:
     - Modulo normalize seed: `active_seed = abs(int(seed)) % (2**32)` (or hash for strings), safely handling negative, large, or non-uint32 seeds.
   - In `_build_broadleaf_tree`:
     - Scale subcrown radius proportionally: `cr = rng.uniform(0.08, 0.15) * species.dimensions.canopy_spread_m`.
4. Test Suite Isolation & Expansion:
   - In `test_generator.py`:
     - Update `test_dispatch_mode_meshy_explicit_without_key_raises` to pass `output_dir=tmp_path / "meshy_no_key"`.
     - Update all test assertions expecting `"meshy-4"` to `"meshy-6"`.
     - Add unit tests designed by Explorers 1, 2, 3:
       - `test_cache_provenance_rejects_procedural_for_explicit_meshy`
       - `test_corrupted_magic_glb_triggers_cache_miss`
       - `test_meshy_retry_after_strictly_capped_at_backoff_max_seconds`
       - `test_meshy_all_non_429_client_errors_fail_fast`
       - `test_meshy_generate_raises_on_armature_or_skinning_violation`
       - `test_conifer_zero_orphan_vertices_and_quad_faces`
       - `test_seed_modulo_boundary_values`
   - In `test_catalog.py`:
     - Update assertion for `ai_model` to `"meshy-6"`.
5. Verification:
   - Run generator test suite: `uv run pytest teamwork_projects/vegetation_library/tests/test_generator.py -v`.
   - Run catalog test suite: `uv run pytest teamwork_projects/vegetation_library/tests/test_catalog.py -v`.
   - Run full regression test suite: `uv run pytest teamwork_projects/vegetation_library/tests/ -v`.
   - Ensure 100% PASS with zero failures and zero regressions.
6. Delivery:
   - Maintain `progress.md` in your working directory `E:\tool\mcp\MorphoMesh\.agents\m2_worker_2\progress.md`.
   - Write comprehensive report to `E:\tool\mcp\MorphoMesh\.agents\m2_worker_2\handoff.md`.
   - Send completion message back to parent using send_message.
</USER_REQUEST>
