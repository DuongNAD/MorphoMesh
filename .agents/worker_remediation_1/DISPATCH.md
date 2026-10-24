# Dispatch for Worker Remediation 1

## Identity
- Role: Forensic Remediation & Asset Integration Engineer
- Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_remediation_1
- Parent Conversation ID: c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4

## Mission & Instructions
Execute the remediation plan formulated by Forensic Remediation Explorer (`E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_1\handoff.md`):

### Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

### Tasks:
1. **Ingest & Normalize Genuine Meshy Ostrich Fern (`veg_ground_ostrich_01`)**:
   - Download the verified 51.8k-vertex model from Meshy CDN:
     `https://assets.meshy.ai/280758b0-9c97-47ea-9298-e637b11d0e3b/tasks/01a08b41-7c5c-71fe-b564-863753864ec2/output/model.glb`
     to `teamwork_projects/vegetation_library/output/groundcover/veg_ground_ostrich_01/raw_meshy_model.glb`.
   - Run `post_processor.process_and_export()`:
     * Ground pivot snapping ($Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$)
     * Horizontal base centroid centering ($\le 0.05\text{m}$)
     * Normalize height to 1.4m ($\pm 10\%$)
     * Embed 4-channel PBR textures with dielectric clamping ($\le 0.0392$)
     * Export production `veg_ground_ostrich_01.glb` (0 bones) and companion `.obj` / `.mtl`
     * Save `task_id = "01a08b41-7c5c-71fe-b564-863753864ec2"`, `source = "meshy"` in `asset_manifest.json`
   - Render 4-angle turntables (`turntable_01.png` - `04.png`) and contact sheet (`thumbnail.png`) via Headless Blender 4.5.
2. **Remove Conditional Verification Facades**:
   - In `vegetation_pipeline/validator.py`:
     * Make `meshy_cloud_provenance` assertion unconditional for genuine assets.
     * Set standard `min_verts = 20000` for production assets.
   - In `tests/test_vegetation_pipeline.py`:
     * Clean up test assertions so that all genuine Meshy models are verified against the 20k-65k budget, genuine cloud task provenance, and 0% pairwise collisions.
3. **Fix Master Manifest Provenance**:
   - Ensure `veg_tree_oak_01` has its valid `"provenance"` dict in `output/manifest.json`.
   - Ensure `veg_ground_ostrich_01` is updated in `output/manifest.json` with genuine Meshy task ID `01a08b41-7c5c-71fe-b564-863753864ec2` and 51.8k vertices.
4. **Update `viewer.html`**:
   - Synchronize cards, thumbnails, and 3D preview links for all genuine Meshy models.
5. **Run Automated Test Suites**:
   - Run `uv run pytest teamwork_projects/vegetation_library/tests/ -v`.
   - Document results.

Write your completion report to:
`E:\tool\mcp\MorphoMesh\.agents\worker_remediation_1\handoff.md`
When done, send a message to parent (`c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4`).

## 2026-09-10T12:43:53Z
You are Worker Remediation 1 (Forensic Remediation & Asset Integration Engineer).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\worker_remediation_1
Your task assignment is in: E:\tool\mcp\MorphoMesh\.agents\worker_remediation_1\DISPATCH.md
Read DISPATCH.md, ORIGINAL_REQUEST.md (under ## 2026-09-10T11:11:31Z), and Forensic Remediation Explorer report at E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_1\handoff.md.

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

Execute the tasks:
1. Ingest, normalize, and render genuine Meshy Ostrich Fern (veg_ground_ostrich_01) from Meshy CDN (task 01a08b41-7c5c-71fe-b564-863753864ec2, 51,819 vertices) with ground snapping, base centering, 4-channel PBR, and Headless Blender 4.5 rendering.
2. Remove conditional verification facades in validator.py and test_vegetation_pipeline.py.
3. Fix master output/manifest.json provenance for veg_tree_oak_01 and veg_ground_ostrich_01.
4. Synchronize viewer.html cards and thumbnails.
5. Run full test suites: uv run pytest teamwork_projects/vegetation_library/tests/ -v.

Write your completion report to:
E:\tool\mcp\MorphoMesh\.agents\worker_remediation_1\handoff.md
When done, send a message to parent (conversation ID c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4).

