# Dispatch for Remediation Explorer

## Identity
- Role: Forensic Remediation Explorer
- Working Directory: E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_1
- Parent Conversation ID: c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4

## Mission & Instructions
The Final Forensic Auditor reported 🔴 **INTEGRITY VIOLATION**: 10 out of 35 species are low-poly procedural fallback meshes (`source: "procedural"`, `task_id: null`).

### Authoritative Files
- Original User Request: `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (under `## 2026-09-10T11:11:31Z`)
- Forensic Auditor Full Evidence Report: `E:\tool\mcp\MorphoMesh\.agents\auditor_final_1\handoff.md`
- Final Reviewer Report: `E:\tool\mcp\MorphoMesh\.agents\reviewer_final_1\handoff.md`
- Final Challenger Report: `E:\tool\mcp\MorphoMesh\.agents\challenger_final_1\handoff.md`

### Specific Instructions
You MUST read the Forensic Auditor's full evidence report (`E:\tool\mcp\MorphoMesh\.agents\auditor_final_1\handoff.md`) in its entirety.
Investigate the 10 missing species:
1. `veg_ground_ostrich_01`
2. `veg_succulent_agave_01`
3. `veg_succulent_aloe_01`
4. `veg_succulent_barrel_01`
5. `veg_succulent_echeveria_01`
6. `veg_vine_ivy_01`
7. `veg_vine_wisteria_01`
8. `veg_vine_bougainvillea_01`
9. `veg_epiphyte_spanishmoss_01`
10. `veg_vine_pothos_01`

Investigate:
- Query Meshy OpenAPI v2 for any existing tasks for these 10 species (e.g. Ostrich Fern `01a08b41-7c5c-71fe-b564-863753864ec2` or background tasks submitted by Worker M2).
- Plan the exact remediation steps for the Worker:
  1. Live Meshy API task submission/polling/download for these 10 species.
  2. Normalization via `post_processor.process_and_export()` with ground snapping, base centering, dielectric clamping, and decimation.
  3. Headless Blender 4.5 rendering of 4-angle turntables and contact sheet thumbnails.
  4. Removal of conditional validation facades in `validator.py` and `test_vegetation_pipeline.py`.
  5. Re-running `test_challenger_final_empirical.py` to ensure all 20 failing tests now pass.

## 2026-09-10T12:38:00Z
You are Forensic Remediation Explorer.
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_1
Your task assignment is in: E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_1\DISPATCH.md
Read DISPATCH.md, ORIGINAL_REQUEST.md (under ## 2026-09-10T11:11:31Z), and the Forensic Auditor's full evidence report at E:\tool\mcp\MorphoMesh\.agents\auditor_final_1\handoff.md.

The Forensic Auditor issued an INTEGRITY VIOLATION because 10 species are low-poly procedural fallback meshes with 100% identical triangle topology clones:
1. veg_ground_ostrich_01
2. veg_succulent_agave_01
3. veg_succulent_aloe_01
4. veg_succulent_barrel_01
5. veg_succulent_echeveria_01
6. veg_vine_ivy_01
7. veg_vine_wisteria_01
8. veg_vine_bougainvillea_01
9. veg_epiphyte_spanishmoss_01
10. veg_vine_pothos_01

Investigate:
1. Check the Meshy account tasks via live API to see what tasks are currently in progress or finished for these 10 species.
2. Formulate the exact remediation plan for the Worker to download the genuine models, normalize, decimate, render in Blender, remove conditional facades in validator.py and tests, and ensure all 20 failing tests in test_challenger_final_empirical.py pass.

Write your report to:
E:\tool\mcp\MorphoMesh\.agents\explorer_remediation_1\handoff.md
When finished, send a message to parent (conversation ID c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4).

