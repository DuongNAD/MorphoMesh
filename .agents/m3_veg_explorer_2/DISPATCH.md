## 2026-09-10T06:22:40Z
<USER_REQUEST>
You are Explorer 2 for Milestone 3 (M3: Asset Post-Processing, Normalization & Multi-Format Export).
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\m3_veg_explorer_2
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\vegetation_library\ORIGINAL_REQUEST.md
Also refer to:
- Root User Request: E:\tool\mcp\MorphoMesh\.agents\ORIGINAL_REQUEST.md
- Project Specification: E:\tool\mcp\MorphoMesh\.agents\orchestrator_vegetation_1\PROJECT.md
- Existing Exporters: E:\tool\mcp\MorphoMesh\src\morphomesh\geometry\exporters.py, mesh.py, gltf_utils.py
- Generator: teamwork_projects/vegetation_library/vegetation_pipeline/generator.py

Mission:
Investigate and design the mathematical algorithms for ground pivot snapping, metric scale normalization, and dual-format export (production GLB + companion Wavefront OBJ/MTL).

Scope of Investigation:
1. Ground Pivot Snapping & Centering:
   - Mathematical algorithm to compute tight bounding box $(X_{\min}, X_{\max}, Y_{\min}, Y_{\max}, Z_{\min}, Z_{\max})$.
   - Shift vertices so ground base contact $Z_{\min} \equiv 0.000$m (or in glTF $Y_{\min} \approx 0.000$m).
   - Compute centroid of vertices in the bottom 5% height slice ($Z \le Z_{\min} + 0.05 \times \Delta Z$) and translate $(X, Y)$ so the base centroid is exactly at $(0, 0)$.
2. Metric Scale Normalization:
   - Scale mesh to match botanical ground truth dimensions from `catalog.py`: target height `species.dimensions.height_m`, canopy spread `species.dimensions.canopy_spread_m`.
   - Determine optimal scaling strategy (uniform height scaling vs anisotropic scaling preserving aspect ratio) to avoid distortion while ensuring exact real-world scale.
3. Dual-Format Export:
   - Production GLB (`.glb`):
     - Leverage `morphomesh.geometry.exporters.export_glb` or custom binary glTF builder.
     - Embed all 4 PBR textures (Albedo, Normal, Roughness, Metallic) in the GLB binary buffer.
     - Ensure foliage materials specify `"doubleSided": true` for two-sided leaf rendering.
     - Ensure $N_{\text{bones}} = 0$ (zero skins, zero armatures).
   - Companion Wavefront OBJ (`.obj` + `.mtl`):
     - Export vertices, texture coordinates (`vt`), normals (`vn`), and faces (`f`).
     - Generate valid companion `.mtl` material file linking to `textures/albedo.png`, `textures/normal.png`, `textures/roughness.png`, `textures/metallic.png`.
4. Formulate the implementation plan, mathematical formulas, and code diffs for the Worker.

Rules:
- Read-only exploration. DO NOT modify source code files.
- Maintain progress.md in your working directory.
- Deliver your structured handoff report to E:\tool\mcp\MorphoMesh\.agents\m3_veg_explorer_2\handoff.md.
- Send a completion message back to parent using send_message.
</USER_REQUEST>
