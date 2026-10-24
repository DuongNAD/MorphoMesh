# Dispatch for Worker M2 — Meshy Cloud Batch Generation & Divergence

## Identity
- Role: Meshy Cloud Batch Generation Engineer
- Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_m2
- Parent Conversation ID: c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4

## Mission & Instructions
You are assigned Milestone 2: Meshy Cloud Batch Generation & Divergence for the Vegetation Library Rebuild.

### Authoritative Files
- Original Request: `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (under `## 2026-09-10T11:11:31Z`)
- Project Scope: `E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md`
- Working Directory of subproject: `E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library`

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Key Requirements
1. 100% Genuine Meshy AI Cloud Generation:
   - Use `MESHY_API_KEY` from `.env`.
   - Call live Meshy AI Text-to-3D OpenAPI v2 (`/openapi/v2/text-to-3d`).
   - Query existing completed tasks on the account first (`GET /openapi/v2/text-to-3d`) to reuse any previously generated tasks matching species in the catalog.
   - For remaining species, submit Stage 1 Preview and Stage 2 Refine tasks with robust exponential backoff and rate-limit handling (concurrency 2-3 simultaneous tasks).
   - Strictly PROHIBIT procedural fallback geometry or identical clone templates across different species.
2. Botanical Prompt Tuning:
   - Ensure every species prompt specifies distinct, anatomically accurate morphological traits (Fan Palm, Monstera, Banana Plant, Tree Fern, Bird of Paradise, Saguaro, Scots Pine, etc.).
3. High-Fidelity Geometry & Materials:
   - Download the refined GLBs (`raw_meshy_model.glb`) and remote 2K PBR texture maps (`albedo`, `normal`, `roughness`, `metallic`).
   - Ensure mesh detail is within 20,000 to 65,000 polygons.
   - Verify pairwise vertex count collision rate across distinct species is < 5%.
4. Provenance Tracking:
   - Save genuine cloud task provenance (`task_id`, `model_type`, `refine_status`, remote URLs) in each asset's `asset_manifest.json`.



## 2026-09-10T11:42:09Z
You are Worker M2 (Meshy Cloud Batch Generation Engineer).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\worker_m2
Your detailed dispatch assignment is in: E:\tool\mcp\MorphoMesh\.agents\worker_m2\DISPATCH.md
Read DISPATCH.md, ORIGINAL_REQUEST.md (under ## 2026-09-10T11:11:31Z), and PROJECT.md (E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Mission:
Execute Milestone 2: Meshy Cloud Batch Generation & Divergence for the Vegetation Library Rebuild.
1. Inspect the Meshy account for all completed tasks via GET /openapi/v2/text-to-3d using MESHY_API_KEY from .env, matching prompt titles/keywords to the 35 species catalog.
2. For any species not yet generated, submit live Stage 1 Preview and Stage 2 Refine tasks to Meshy API using tuned botanical prompts for distinct morphological traits (Fan Palm fronds, Monstera split leaves, Banana paddle leaves, Tree Fern crown, Bird of Paradise floral spikes, Saguaro ribs, Scots Pine needle pom-poms, etc.).
3. Wait for real cloud completion with robust queue polling and exponential backoff. Strictly 0% procedural dummy fallback meshes.
4. Download the genuine Meshy refined GLBs (raw_meshy_model.glb) and 2K PBR texture maps into each species directory.
5. Record genuine Meshy cloud task provenance (task_id, model_type, refine_status, remote URLs) in each asset manifest.
6. Verify visual and topological divergence: calculate pairwise vertex count collision rate across distinct species and confirm it is < 5%.

Write your completion report to:
E:\tool\mcp\MorphoMesh\.agents\worker_m2\handoff.md
When finished, send a message to parent (conversation ID c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4).

