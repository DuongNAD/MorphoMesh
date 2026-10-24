# Task Dispatch — M3 Challenger 1 (Props, Cords & Flocking Adversarial Verification)

## 2026-09-07T20:04:06Z

### Objective
Perform adversarial empirical verification of Milestone 3 props:
1. Verify 10 Crimson Marionette Strings:
   - Snapping tolerance: verify distance between cord root and fingertip landmark is strictly 0.000mm.
   - Catenary curve sag and tension: verify proper parabolic curvature without kinks.
   - Topology: verify pure-quad ribbon (14 vertices per string), 0 non-manifold edges.
2. Verify 10 Glowing Swallowtail Butterflies:
   - Geometry: 24 pure quads (48 vertices, 0 triangles) per butterfly.
   - Flocking formation: verify pairwise distance between all pairs is strictly >= 150mm.
   - Flocking bounds: verify butterflies orbit within $Z \in [0.88, 1.32]$m and $|X| \ge 0.35$m.
3. Run test verification:
   `uv run pytest tests/test_challenger_m3_props.py tests/test_wardrobe_m3.py -v`
4. Document exact measurements and issue a binary verdict: `APPROVE` or `REQUEST_CHANGES`.

### Reference Materials
- `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Mandatory reading)
- `E:\tool\mcp\MorphoMesh\.agents\orchestrator_female_mold_1\PROJECT.md`
- `E:\tool\mcp\MorphoMesh\.agents\m3_worker_assembly_rigging_1\handoff.md`

### Output
Write report to `E:\tool\mcp\MorphoMesh\.agents\m3_challenger_1\handoff.md`
Notify orchestrator via `send_message` when done.
