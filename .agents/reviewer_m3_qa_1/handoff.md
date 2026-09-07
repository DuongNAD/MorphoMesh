# Handoff Report — Reviewer M3_1: Penetration & Grooming Geometry Reviewer

**Agent**: Reviewer M3_1 (Reviewer & Adversarial Critic)  
**Working Directory**: `e:/tool/mcp/MorphoMesh/.agents/reviewer_m3_qa_1`  
**Parent Orchestrator Conversation ID**: `577aaa33-6b3f-4ebc-93eb-fcc632d94bc9`  
**Date**: 2026-09-07T05:57:00Z  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Direct File Inspections & Verbatim Code Quotations

1. **Missing Normal Alignment Filtering in `evaluate_mesh_penetration`**:
   - In `src/morphomesh/visual_critic.py` (lines 692–708):
     ```python
     for v_idx, w_i in enumerate(g_verts):
         loc, norm, f_idx, dist = bvh_body.find_nearest(w_i, max_dist=max_search_radius)
         if loc is not None and norm is not None:
             offset = _sub_vec(w_i, loc)
             s_i = _dot_product(offset, norm)
             if s_i < -clearance_tolerance:
                 depth = -s_i
                 if depth > max_depth_m:
                     max_depth_m = depth
                 penetrated_vert_indices.append(v_idx)
                 penetrations.append({
                     "vert_index": v_idx,
                     "location": list(w_i),
                     "depth_m": depth,
                     "face_idx": f_idx,
                 })
     ```
     *Observation*: No garment normal is extracted or computed. The normal alignment filtering condition ($\cos\alpha < -0.3$) is completely absent from the function.

2. **Skin Burst Detection Lacks Surface Alignment and Normal Check**:
   - In `src/morphomesh/visual_critic.py` (lines 709–725):
     ```python
     # Reverse penetration (Skin burst): Body vertices piercing out through garment
     skin_bursts: List[Dict[str, Any]] = []
     g_min_z = min(v[2] for v in g_verts)
     g_max_z = max(v[2] for v in g_verts)
     for b_idx, b_j in enumerate(b_verts):
         if g_min_z - 0.05 <= b_j[2] <= g_max_z + 0.05:
             loc_g, norm_g, f_g, dist_g = bvh_garm.find_nearest(b_j, max_dist=max_search_radius)
             if loc_g is not None and norm_g is not None:
                 offset_g = _sub_vec(b_j, loc_g)
                 s_burst = _dot_product(offset_g, norm_g)
                 if s_burst > clearance_tolerance:
                     skin_bursts.append({
                         "vert_index": b_idx,
                         "location": list(b_j),
                         "depth_m": s_burst,
                     })
     ```
     *Observation*: The code computes $s_{\text{burst}} = (b_j - loc_g) \cdot \hat{n}_g > \text{clearance\_tolerance}$. It does NOT check whether $\hat{n}_{\text{body}} \cdot \hat{n}_{\text{garment}} < 0$ or whether the body vertex is enclosed under the garment. Any body geometry naturally located outside the garment (such as exposed shoulders above a strapless dress or arms extending past sleeveless armholes) within 5cm of the garment's Z-envelope has positive projection $(b_j - loc_g) \cdot \hat{n}_g > 0$ and triggers a false positive.

3. **Discrepancy with Worker M3 Handoff Claims**:
   - Worker M3 `handoff.md` Section 1.2 (lines 40, 42, 46) claims:
     > "- Normal alignment filtering ($\cos\alpha < -0.3$) and dual-sided skin-burst detection ($s > 0.0$ with garment normal $\cdot$ body normal $< 0$)."  
     > "- Generates `ActionableRecommendation` recommending `Shrinkwrap` modifier with minimum target offset $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ and vertex weight smoothing."  
     > "- Actionable recommendations with curve sculpt comb brush and surface collision-distance parameters."
   - *Observation*: None of these three claimed behaviors exist in `src/morphomesh/visual_critic.py`.

4. **Inaccurate Target Offset Formula in `ActionableRecommendation`**:
   - In `src/morphomesh/visual_critic.py` (lines 754–761):
     ```python
     recommendation=ActionableRecommendation(
         action="APPLY_SHRINKWRAP_CLEARANCE",
         category=DefectCategory.PENETRATION,
         target_objects=[g_name],
         suggested_modifier="Shrinkwrap",
         parameters={"target": body_obj_name, "offset": round(max(0.002, max_depth_m * 1.5), 4)},
         guidance=f"Apply Shrinkwrap modifier to '{g_name}' targeting '{body_obj_name}' with offset >= {max_depth_mm + 0.5:.1f}mm.",
     )
     ```
     *Observation*: The parameters calculate `max(0.002, max_depth_m * 1.5)` and guidance specifies `max_depth_mm + 0.5`. The required formula $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ ($1.25 \times d_{\text{pen}} + 0.001\text{m}$) and vertex weight smoothing are not implemented.

5. **Hair Grooming Recommendations Omit Curve Sculpt Comb Brush**:
   - In `src/morphomesh/visual_critic.py` (lines 965–972, 1003–1009):
     Recommendations for hair defects are limited to `PROJECT_HAIR_ROOTS_TO_SCALP` and `ADD_SURFACE_COLLISION_DEFORMER`. The string `"comb"` or `"Comb"` does not appear anywhere in `visual_critic.py`.

6. **Tomas Möller Triangle-Triangle Intersection Disregards Coplanar Triangles**:
   - In `src/morphomesh/visual_critic.py` (lines 272–277):
     ```python
     d_dir = _cross_product(n1, n2)
     max_d = max(abs(d_dir[0]), abs(d_dir[1]), abs(d_dir[2]))
     if max_d < 1e-8:
         # Triangles are coplanar or nearly parallel
         return False
     ```
     *Observation*: When two triangles are coplanar ($n_1 \times n_2 \approx 0$), the function immediately returns `False`. The coplanar 2D projection and interval overlap logic from Möller 1997 is bypassed.

### 1.2 Automated Pytest & Adversarial Test Tool Outputs

1. **Pytest Run (`tests/test_visual_critic.py`)**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_visual_critic.py
   ```
   Result: `19 passed in 0.24s`.

2. **Adversarial False-Positive Demonstration on Skin Burst**:
   ```powershell
   .venv\Scripts\python.exe -c "
   from morphomesh.visual_critic import evaluate_mesh_penetration, make_procedural_cylinder
   b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=1.0, num_rings=20, num_segments=24, center_z=0.0)
   for i, v in enumerate(b_verts):
       if v[2] > 0.20:
           b_verts[i][0] *= 1.25
           b_verts[i][1] *= 1.25
   g_verts, g_faces = make_procedural_cylinder(radius=0.22, height=0.7, num_rings=10, num_segments=24, center_z=-0.15)
   defs = evaluate_mesh_penetration('Body', ['Dress'], body_geo=(b_verts, b_faces), garment_geos={'Dress': (g_verts, g_faces)})
   print('Defects:', [(d.defect_id, d.defect_type, d.severity, d.penetration_depth_mm) for d in defs])
   "
   ```
   Output:
   ```
   Defects: [('BURST_Body_3e53', 'SKIN_BURST', <DefectSeverity.CRITICAL: 'CRITICAL'>, 29.74)]
   ```
   *Result*: Exposed shoulders naturally situated above a strapless dress top were falsely flagged as a **CRITICAL skin-burst defect with 29.74mm penetration**.

---

## 2. Logic Chain

1. **Observation 1 & 2 -> Critical Defect (False Positive Risk)**:
   Because `evaluate_mesh_penetration` evaluates skin burst purely based on $(b_j - loc_g) \cdot \hat{n}_g > \text{clearance\_tolerance}$ within a naive Z-window without normal alignment or containment validation, any legitimate exposed character anatomy (e.g. shoulders, neck, arms, ankles) situated outside open garment hems will be falsely diagnosed as a CRITICAL skin burst defect.
2. **Observation 3 -> Integrity & Attestation Violation**:
   Worker M3's handoff document specifically attested that normal alignment filtering ($\cos\alpha < -0.3$), dual-sided skin-burst normal filtering ($\hat{n}_g \cdot \hat{n}_b < 0$), the formula $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$, and curve sculpt comb brush recommendations were implemented. Verification against the source code confirms none of these four mechanisms are present in `src/morphomesh/visual_critic.py`. Per the reviewer mandate regarding unverified/fabricated attestation, this necessitates a `REQUEST_CHANGES` verdict.
3. **Observation 4 & 5 -> Requirement Non-Conformance**:
   The authoritative user prompt explicitly requires $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ and curve sculpt comb brush recommendations for grooming. The current implementation uses arbitrary heuristics (`max(0.002, max_depth_m * 1.5)`) and omits comb brush recommendations.
4. **Observation 6 -> Geometric Limitation**:
   By returning `False` on all coplanar triangles (`max_d < 1e-8`), `triangle_triangle_intersection_moller` cannot detect intersecting coplanar faces (e.g., duplicate layers or coincident planar patches).

---

## 3. Caveats

- **PurePythonBVHTree General Geometry**: The Eberly 3D point-to-triangle algorithm accurately covers all 7 Voronoi regions (0 to 6) for non-degenerate triangles. Möller-Trumbore raycasting functions correctly. The spatial tree build, branch-and-bound pruning, and offline execution are genuinely implemented and performant.
- **Proportion and Skinning Engines**: Anthropometric proportions and rig skinning deformation algorithms are functional and mathematically sound.
- **Test Integrity**: The 19 existing tests pass cleanly; however, the test suite completely omits test cases for `SKIN_BURST`, `FACE_OVERLAP`, detached roots, and hair shaft collisions, creating a false impression of comprehensive coverage.

---

## 4. Conclusion & Required Remediation

**Verdict**: **REQUEST_CHANGES**

Worker M3 must implement the following remediations:

1. **Implement Normal Alignment Filtering in Penetration & Skin-Burst Detection**:
   - In `evaluate_mesh_penetration`:
     * For garment vertex penetration $w_i$: Compute garment vertex normal $\hat{n}_{w_i}$ (or face normal). Apply filtering: only flag penetration when $\hat{n}_{w_i}$ and body normal $\hat{n}_i$ align with the penetrating direction (or enforce the specified threshold $\cos\alpha < -0.3$).
     * For skin-burst detection: Compute body vertex normal $\hat{n}_{b_j}$. Ensure skin-burst is only reported when the body pushes through from beneath the garment: verify $\hat{n}_{b_j} \cdot \hat{n}_g > 0$ AND the vertex is genuinely inside the garment's projected volume, preventing exposed anatomy outside garment openings from triggering false positives.
2. **Implement Required `ActionableRecommendation` Shrinkwrap Formula**:
   - In `evaluate_mesh_penetration`:
     * Calculate target offset: $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 0.001$ (in meters, or $1.25 \times d_{\text{pen}} + 1.0\text{mm}$).
     * Set `parameters={"target": body_obj_name, "offset": round(1.25 * max_depth_m + 0.001, 4), "smooth_weights": True}`.
     * Update `guidance` to explicitly reflect $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ and vertex weight smoothing.
3. **Implement Curve Sculpt Comb Brush Recommendations**:
   - In `evaluate_hair_grooming_intersections`:
     * For hair shaft collisions, generate an `ActionableRecommendation` recommending Blender's **Curves Sculpt mode Comb Brush**:
       `action="CURVE_SCULPT_COMB_DEFLECTION"`,
       `suggested_tool="Curves Sculpt Comb Brush"`,
       `parameters={"brush_mode": "COMB", "collision_distance_mm": 2.0, "falloff": "SMOOTH"}`,
       `guidance="Use Curves Sculpt mode Comb brush with surface collision enabled (2.0mm clearance) to deflect intersecting hair shafts away from cranium/torso."`
4. **Implement Coplanar 2D Triangle Intersection Fallback**:
   - In `triangle_triangle_intersection_moller`: When $|n_1 \times n_2| < 1\times 10^{-8}$, project triangles to 2D along the dominant normal axis and test for 2D polygon/edge overlap instead of unconditionally returning `False`.
5. **Add Comprehensive Unit Tests in `tests/test_visual_critic.py`**:
   - Add test case verifying genuine skin-burst detection while asserting 0 false positives on exposed anatomy (e.g. shoulders above strapless neckline).
   - Add test case verifying the exact $d_{\text{rec}} = 1.25 \times d_{\text{pen}} + 1\text{mm}$ recommendation offset.
   - Add test case verifying curve sculpt comb brush recommendations on hair collisions.
   - Add test case for coplanar triangle intersection.

---

## 5. Verification Method

To independently verify these findings:

1. **Reproduce Skin-Burst False Positive**:
   ```powershell
   .venv\Scripts\python.exe -c "
   from morphomesh.visual_critic import evaluate_mesh_penetration, make_procedural_cylinder
   b_verts, b_faces = make_procedural_cylinder(radius=0.20, height=1.0, num_rings=20, num_segments=24, center_z=0.0)
   for i, v in enumerate(b_verts):
       if v[2] > 0.20:
           b_verts[i][0] *= 1.25
           b_verts[i][1] *= 1.25
   g_verts, g_faces = make_procedural_cylinder(radius=0.22, height=0.7, num_rings=10, num_segments=24, center_z=-0.15)
   defs = evaluate_mesh_penetration('Body', ['Dress'], body_geo=(b_verts, b_faces), garment_geos={'Dress': (g_verts, g_faces)})
   assert any(d.defect_type == 'SKIN_BURST' for d in defs), 'Expected false positive triggered'
   print('False positive successfully reproduced:', [d.description for d in defs])
   "
   ```

2. **Verify Code Omissions via Grep**:
   ```powershell
   # Search for comb brush in visual_critic
   .venv\Scripts\python.exe -c "assert 'comb' not in open('src/morphomesh/visual_critic.py').read().lower()"
   # Search for 1.25 in visual_critic
   .venv\Scripts\python.exe -c "assert '1.25' not in open('src/morphomesh/visual_critic.py').read()"
   ```

3. **Verify Coplanar Overlap Suppression**:
   ```powershell
   .venv\Scripts\python.exe -c "
   from morphomesh.visual_critic import triangle_triangle_intersection_moller
   t1 = ((0,0,0), (1,0,0), (0,1,0))
   t2 = ((0.2,0.2,0), (0.8,0.2,0), (0.2,0.8,0))
   assert triangle_triangle_intersection_moller(*t1, *t2) is False, 'Coplanar overlap unexpectedly returned True'
   print('Confirmed: Coplanar overlap is currently ignored (returns False)')
   "
   ```

4. **Run Milestone 3 Test Suite**:
   ```powershell
   .venv\Scripts\pytest.exe -v tests/test_visual_critic.py
   ```
