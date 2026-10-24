# Dispatch for m1_worker_anime_1

## 2026-09-09T15:01:57Z
You are m1_worker_anime_1, the Implementation Worker for Milestone 1: Anime Mesh Synthesis & Anatomy Topology.

Working Directory: E:\tool\mcp\MorphoMesh\.agents\m1_worker_anime_1
Target Project Directory: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md
Project Scope Document: E:\tool\mcp\MorphoMesh\.agents\orchestrator_anime_1\PROJECT.md

READ FIRST:
- ORIGINAL_REQUEST.md: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md
- PROJECT.md: E:\tool\mcp\MorphoMesh\.agents\orchestrator_anime_1\PROJECT.md
- Explorer 1 Blueprint: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_anime_1\analysis.md and handoff.md
- Explorer 2 Blueprint: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_anime_2\analysis.md and handoff.md
- Explorer 3 Blueprint: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_anime_3\analysis.md and handoff.md
- Verified Working Prototypes: E:\tool\mcp\MorphoMesh\.agents\m1_explorer_anime_1\test_modular_synthesis.py and test_export_pipeline.py

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE WRITE OWNERSHIP:
You own and must implement:
- `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\__init__.py`
- `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\mesh\__init__.py`
- `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\mesh\generator.py`
- `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\anime_pipeline\mesh\topology_cleaner.py`
- Output files in `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\output\`:
  * `meshes/*.obj` (7 individual sub-meshes + master modular obj)
  * `anime_mesh_clean.blend` (or `anime_character_model.blend`)
  * `anime_mesh_clean.glb` (or `anime_character_model.glb`)

YOUR TASKS:
1. Implement `anime_pipeline/mesh/generator.py` following the complete blueprints from Explorer 1 and Explorer 3:
   - Partition `data/templates/makehuman_clean_body.obj` into 4 core anatomy sub-meshes (`Anime_Head`, `Anime_Torso`, `Anime_Arms`, `Anime_Legs`) with exact 1-manifold boundary loops and 0.000mm rest-pose coincident seams.
   - Procedurally synthesize `Anime_Skirt` (16-20 accordion pleats, $+15\text{mm}$ to $+90\text{mm}$ positive thigh clearance, 0% thigh weight bleeding).
   - Procedurally synthesize `Anime_Hair` (scalp helmet with $+5\text{mm}$ cranial clearance + Left/Right twintail ribbon chains with 5 deformable segments).
   - Procedurally synthesize `Anime_Shoes` (Japanese school idol loafers with planar flat soles grounded at $Z \equiv 0.0000\text{m}$).
   - Multi-format exporter: export 7 individual `.obj` files, master `.obj`, headless Blender 4.5 `.blend` and `.glb`.
2. Implement `anime_pipeline/mesh/topology_cleaner.py` following the blueprint from Explorer 2:
   - `TopologyValidator`: 100% 2-manifold quads ($\rho_{\text{quad}} = 1.0000$), zero non-manifold edges, zero duplicate vertices, zero degenerate faces.
   - `HingeLoopValidator`: Multi-loop concentric deformation loops at elbows (3-loop), knees (3-loop), shoulders (5-loop deltoid saddle with recessed axillary E-poles), and waist (3-ring).
   - `NormalHarmonizer`: Seam normal consistency enforcing identical radial/area-weighted split normals across coincident boundary loops (neck, shoulder, wrist, ankle) to eliminate dark split lines under cel-shading.
3. Run the generator and topology cleaner:
   - Run the generation script and headless Blender 4.5 exporter to create the meshes and verify return code 0.
   - Run topology cleaner audits against the generated meshes to ensure 100% pass on all topological and geometric invariants.
   - Run pytest if applicable (`uv run pytest tests/ -v`).
4. Write a comprehensive `handoff.md` with:
   - Section 1: Observation (what you implemented, commands run, output codes, file paths and sizes).
   - Section 2: Logic Chain (how your implementation fulfills R1, F01, F02, F03).
   - Section 3: Caveats (limitations, assumptions).
   - Section 4: Conclusion (status of M1 deliverables).
   - Section 5: Verification Method (exact commands to run to inspect and verify M1 outputs).
5. Update `progress.md` with liveness timestamps throughout. Send a message to parent when complete.
