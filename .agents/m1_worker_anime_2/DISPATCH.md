## 2026-09-09T15:22:51Z

You are m1_worker_anime_2, the Remediation Implementation Worker for Milestone 1: Anime Mesh Synthesis & Anatomy Topology.

Working Directory: E:\tool\mcp\MorphoMesh\.agents\m1_worker_anime_2
Target Project Directory: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md
Project Scope Document: E:\tool\mcp\MorphoMesh\.agents\orchestrator_anime_1\PROJECT.md

READ THE THREE REMEDIATION BLUEPRINTS FIRST:
1. Seam Normal Harmonization Patch:
   - E:\tool\mcp\MorphoMesh\.agents\m1_explorer_remediation_1\seam_normal_harmonization.patch
   - Report: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_remediation_1\handoff.md
2. Skirt Clearance Patch:
   - E:\tool\mcp\MorphoMesh\.agents\m1_explorer_remediation_2\skirt_clearance.patch
   - Report: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_remediation_2\handoff.md
3. Shoe Alignment & Topology Robustness Patch:
   - Report & Drop-in code: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_remediation_3\analysis.md and handoff.md
4. Forensic Audit Report:
   - E:\tool\mcp\MorphoMesh\.agents\m1_auditor_anime_1\handoff.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
You own and must modify:
- E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\mesh\generator.py
- E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\mesh\topology_cleaner.py
- Output files in E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\:
  * meshes/*.obj
  * nime_mesh_clean.blend
  * nime_mesh_clean.glb

YOUR TASKS:
1. Apply Seam Normal Harmonization:
   - In generator.py, implement _compute_submesh_normals(), wire NormalHarmonizer.harmonize_all_modular_seams(submeshes), pass normals into AnimeSubMesh, export n lines in OBJ.
   - In export_master_blend(), serialize _normals.json and apply custom split normals (
ormals_split_custom_set_from_vertices()) so Blender 4.5.4 LTS stores identical boundary normal vectors (angular deviation < 0.005 rad).
2. Apply Skirt Clearance Equation:
   - In _synthesize_skirt() in generator.py, update radii with direct skirt_clearance_mm wiring:
     `python
     yc = -0.016 * s
     clearance_m = (self.cfg.skirt_clearance_mm / 1000.0) * s
     rx_waist = 0.193 * s + clearance_m
     ry_waist = 0.157 * s + clearance_m
     rx_hem = 0.295 * s + clearance_m
     ry_hem = 0.237 * s + clearance_m
     amp_waist = 0.006 * s
     amp_hem = 0.022 * s
     `
3. Apply Shoe Alignment & Topology Robustness:
   - In _synthesize_shoes(): pass legs_mesh, dynamically compute foot center-of-mass, and center the left and right shoes directly on the actual feet.
   - In _extract_landmarks(): dynamically extract landmark centroids from actual submesh vertices.
   - In 	opology_cleaner.py:merge_duplicate_vertices(): add quad face deduplication using canonical sorted 4-tuples.
   - In 	opology_cleaner.py:TopologyValidator: add pre-audit sanitization with 
p.all(np.isfinite(arr)) to return eport.is_valid = False on NaN/Inf floats without raising unhandled exceptions.
4. Regenerate deliverables in output/ (OBJ, .blend, .glb).
5. Run builds and tests:
   - uv run pytest tests/test_m1_challenger_seam_and_formats.py -v (must pass 100%)
   - uv run pytest tests/test_m1_adversarial_stress.py -v (must pass 100%)
   - uv run pytest tests/ -v (must pass 100%)
6. Write a comprehensive handoff.md documenting commands and results. Update progress.md with liveness timestamps. Notify parent when complete.
