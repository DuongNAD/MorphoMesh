# Dispatch for Final Challenger

## Identity
- Role: Empirical Invariant & Divergence Challenger
- Working Directory: E:\tool\mcp\MorphoMesh\.agents\challenger_final_1
- Parent Conversation ID: c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4

## Mission & Instructions
Empirically stress-test all production botanical deliverables across the entire library:
- Authoritative Request: `E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md` (under `## 2026-09-10T11:11:31Z`)
- Project Scope: `E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_rebuild_1\PROJECT.md`
- Subproject Directory: `E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library`
- Worker M3 Report: `E:\tool\mcp\MorphoMesh\.agents\worker_m3\handoff.md`

Empirical Assertions:
1. Static Mesh Invariant across all 35 GLBs: assert $N_{\text{bones}} == 0$ (zero skins, zero joints, zero weights).
2. Ground Snapping across all 35 GLBs: assert $|Z_{\min}| \le 0.005\text{m}$ and base horizontal centroid within $0.05\text{m}$ of $(0, 0)$.
3. Metric Scale across all 35 GLBs: assert height within $\pm 10\%$ of catalog target.
4. Vertex Divergence across all 35 species: assert pairwise vertex count collision rate < 5%.
5. PBR Texture Completeness: assert Albedo, Normal, Roughness, Metallic textures exist, are readable, have resolution $\ge 256 \times 256$, and satisfy physical dielectric bounds.

Deliver your empirical verdict (APPROVE or REQUEST_CHANGES) in `E:\tool\mcp\MorphoMesh\.agents\challenger_final_1\handoff.md` and send a message back to parent.

## 2026-09-10T12:27:33Z
You are Final Challenger (Empirical Invariant & Divergence Challenger).
Your working directory is: E:\tool\mcp\MorphoMesh\.agents\challenger_final_1
Your task assignment is in: E:\tool\mcp\MorphoMesh\.agents\challenger_final_1\DISPATCH.md
Read DISPATCH.md, ORIGINAL_REQUEST.md (under ## 2026-09-10T11:11:31Z), and Worker M3 handoff (E:\tool\mcp\MorphoMesh\.agents\worker_m3\handoff.md).

Perform empirical stress testing across all 35 library assets:
1. Static Mesh Invariant: assert N_bones == 0 across all 35 GLBs.
2. Ground Contact Snapping: assert |Z_min| <= 0.005m and base centroid offset <= 0.05m across all 35 GLBs.
3. Metric Scale Bounds: assert height within +-10% of catalog target.
4. Pairwise Vertex Collision Rate: compute across all 35 species and confirm < 5%.
5. PBR Texture Completeness: assert Albedo, Normal, Roughness, Metallic textures exist, are readable, and conform to dielectric limits.

Deliver your empirical verdict (APPROVE or REQUEST_CHANGES) in:
E:\tool\mcp\MorphoMesh\.agents\challenger_final_1\handoff.md
When done, send a message to parent (c89d3e85-2d1c-4b25-9e5b-bb4953ad2fc4).
