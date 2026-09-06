## 2026-09-05T16:26:56Z

# Dispatch Assignment: Worker M2 (Volumetric Fur & Grooming Engine)

**Identity**: teamwork_preview_worker
**Assigned Task**: Milestone M2 Implementation — Volumetric Fur & Hair Grooming Engine & Pipeline
**Working Directory**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m2`
**Authoritative Request**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/ORIGINAL_REQUEST.md` (read sections `## 2026-09-05T15:44:52Z` and `## 2026-09-05T15:47:35Z`)
**Project Plan**: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/orchestrator_bear_1/PROJECT.md`
**Technical References**:
- Explorer 3 Survey Report: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/explorer_survey_3/survey_report.md` (Section 2: Volumetric Fur Architecture & Blender 5.2.1 Hair APIs)
- Milestone M1 Handoff: `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m1_2/handoff.md`

## Mandatory Integrity Warning
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

## File Ownership
You exclusively own and may edit/create:
- `src/morphomesh/grooming.py`
- `src/morphomesh/blender_bridge.py` (add grooming dispatch helpers)
- `tests/test_grooming.py`

## Objectives & Deliverables
1. **Implement `src/morphomesh/grooming.py`**:
   - `CreatureGroomingEngine` class providing:
     - `setup_volumetric_fur(mesh_obj_name, undercoat_strands=8000, guard_hair_strands=4000, flow_vertex_group='dorsal_spine', clump_factor=0.4, taper_shape=-0.7)`:
       - Multi-layer fur system: Dense undercoat (8,000 parent strands, length 0.04m, clump 0.3) + coarse guard hairs (4,000 parent strands, length 0.09m, clump 0.5) with interpolated children yielding > 100,000 render strands. Total parent guide strands >= 12,000 (exceeds the >= 10,000 requirement).
       - Biological growth flow radiating from dorsal spine downwards across torso, shoulders, and limbs.
       - Realistic tapering (`shape = -0.7`, `root_radius = 0.0012m`, `tip_radius = 0.0001m`) using Blender 5.2.1 LTS API (`roughness_endpoint`, `clump_shape`, `child_type='INTERPOLATED'`).
       - Vertex group density masking: full density on torso, shoulders, mane; zero fur on nose, mouth cavity, eyes, claws, and paw pads.
     - `evaluate_fur_ribbons_for_gltf(mesh_obj_name, fur_system_names, max_export_strands=5000)`:
       - Generates evaluated polygonal ribbon mesh from hair curves/strands for standard glTF 2.0 export compatibility.
2. **Integrate with `src/morphomesh/blender_bridge.py`**:
   - Add bridge methods `setup_creature_fur()` and script generation helpers for headless and interactive socket execution.
3. **Automated Unit & Integration Tests (`tests/test_grooming.py`)**:
   - Test strand count assertion (>= 10,000 parent guide strands).
   - Test multi-layer configuration (undercoat + guard hairs).
   - Test biological flow direction and vertex group masking.
   - Test glTF ribbon evaluator output.
   - Run `pytest -v tests/` and verify all tests pass with 0 failures.
4. **Blender 5.2.1 LTS Verification**:
   - Execute grooming setup on `Bear_Base_Mesh` in headless Blender and over live socket.
   - Verify that fur curves are active, visible, non-intersecting, and exceed 10,000 strands.
5. **Handoff Report**:
   - Deliver comprehensive 5-component report at `/Users/duongnad/Documents/tool/MorphoMesh/.agents/worker_m2/handoff.md` and notify orchestrator.
