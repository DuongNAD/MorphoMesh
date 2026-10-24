# Dispatch for Worker M3 — Asset Normalization, Headless Rendering & Viewer Synchronization

## Identity
- Role: Asset Normalization, Rendering & Viewer Engineer
- Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_m3
- Parent Conversation ID: c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4

## Mission & Instructions
You are assigned Milestone 3 & Milestone 4: Asset Normalization, Ground Snapping, Headless Blender Rendering, Manifest Aggregation, and Interactive Viewer Synchronization for the Vegetation Library Rebuild.

### Authoritative Files
- Original Request: `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (under `## 2026-09-10T11:11:31Z`)
- Project Scope: `E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md`
- Subproject Directory: `E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library`
- Worker M2 Report: `E:\tool\mcp\MorphoMesh\.agents\worker_m2\handoff.md`

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Your Tasks
1. **Asset Normalization & Ground Snapping (Milestone 3)**:
   - For all downloaded genuine Meshy models (`raw_meshy_model.glb`), run `post_processor.process_and_export()`:
     * Uniform metric scale normalization to real-world botanical heights (target $\pm 10\%$).
     * Ground pivot snapping strictly at $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$.
     * Base contact centroid centering at $(X=0, Y=0)$.
     * Embed full 4-channel PBR textures (Albedo, Normal, Roughness, Metallic) with double-sided foliage and $N_{\text{bones}} = 0$.
     * Export production `<species_id>.glb` and companion Wavefront `<species_id>.obj` / `<species_id>.mtl`.
2. **Headless Blender Rendering (Milestone 3)**:
   - Run `renderer.py` using Headless Blender 4.5 (`C:\Program Files\Blender Foundation\Blender 4.5\blender.exe`):
     * Re-render high-resolution 4-angle turntable previews (`turntable_01.png` - `04.png`) with botanical 3-point studio lighting and shadow catcher.
     * Re-render 1024x1024 2x2 contact sheet montages (`thumbnail.png`).
3. **Manifest Aggregation & Verification (Milestone 4)**:
   - Aggregate master `manifest.json` in `teamwork_projects/vegetation_library/output/manifest.json`:
     * Include genuine Meshy cloud task provenance (`task_id`, `model_type`, `refine_status`, remote URLs).
     * Include accurate vertex counts, face counts, dimensions, and validation status.
4. **Interactive Viewer Synchronization (Milestone 4)**:
   - Synchronize `teamwork_projects/vegetation_library/output/viewer.html` and `viewer.html`:
     * Ensure all plant cards display genuine Meshy AI-generated models and metrics.
     * Ensure thumbnail previews, turntable renders, and 3D GLB download links are fully synchronized.
5. **Automated Verification**:
   - Run `uv run pytest teamwork_projects/vegetation_library/tests/ -v`.
   - Confirm 100% of tests pass with 0 failures.

Write your completion report to `E:\tool\mcp\MorphoMesh\.agents\worker_m3\handoff.md`.
When finished, send a message back to parent (`c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4`).

## 2026-09-10T12:06:35Z
You are Worker M3 (Asset Normalization, Rendering & Viewer Engineer).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\worker_m3
Your detailed dispatch assignment is in: E:\tool\mcp\MorphoMesh\.agents\worker_m3\DISPATCH.md
Read DISPATCH.md, ORIGINAL_REQUEST.md (under ## 2026-09-10T11:11:31Z), PROJECT.md (E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md), and Worker M2 handoff (E:\tool\mcp\MorphoMesh\.agents\worker_m2\handoff.md).

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Your Tasks:
1. Normalize and post-process all genuine Meshy models via post_processor.process_and_export():
   - Ground pivot snapping strictly at Z_min = 0.000m +- 0.005m.
   - Base contact centroid centered at (X=0, Y=0).
   - Uniform scale to real-world botanical metric height (+-10%).
   - Embed full 4-channel PBR textures (Albedo, Normal, Roughness, Metallic) with double-sided foliage rendering and N_bones = 0.
   - Export production <species_id>.glb and companion OBJ/MTL.
2. Re-render 4-angle turntable previews (turntable_01.png - 04.png) and contact sheets (thumbnail.png) using Headless Blender 4.5.
3. Update master output/manifest.json with genuine cloud provenance and accurate face/vertex counts.
4. Synchronize interactive viewer.html so all cards display genuine AI-generated models and distinct renders.
5. Run the full automated verification test suite: uv run pytest teamwork_projects/vegetation_library/tests/ -v. Confirm 100% tests pass.

Write your completion report to:
E:\tool\mcp\MorphoMesh\.agents\worker_m3\handoff.md
When finished, send a message to parent (conversation ID c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4).
