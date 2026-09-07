## 2026-09-07T01:43:54Z

Assigned: worker_human_m2
Parent: orchestrator_human_1 (fa73b7ae-2239-4440-89d0-f3a69497b7b7)
Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_human_m2

Milestone: Milestone 2 - Rigify Human Rigging & 52 ARKit FACS Blendshapes
Exclusive write ownership:
- src/morphomesh/human_rigging.py
- src/morphomesh/blender_bridge.py (human auto-rigging dispatch methods)
- tests/test_human_rigging.py

Tasks:
1. Implement `src/morphomesh/human_rigging.py`:
   - `HumanRigConfig` dataclass/Pydantic model.
   - `generate_rigify_human_metarig(landmarks, config)`: Generates Rigify Human metarig with bones snapped to landmarks.
   - When Rigify generates or when metarig DEF bones are generated, it must produce exactly 163 DEF bones:
     * 64 body DEF bones (spine, limbs, hands, fingers, feet, toes).
     * 99 facial DEF bones (eyes, brows, eyelids, cheeks, lips, jaw, tongue).
   - Automated landmark snapping aligning all bones to landmarks from `human_generator.py`.
   - Anti-pinching skin weights calculation:
     * Dual-bone twist decomposition.
     * Deltoid clavicular weighting.
     * Olecranon (elbow) 3-loop hinge cosine gradient.
     * Patella (knee) rigid locking.
     * Finger bounding-cylinder isolation.
     * Normalized weights summing to 1.0 for every vertex.
   - 52 Apple ARKit standard FACS facial blendshapes:
     * Full dictionary of 52 shape keys (eyeBlinkLeft, eyeLookDownLeft, eyeWideLeft, jawOpen, mouthSmileLeft, mouthFrownLeft, etc.).
     * Programmatic deformation vectors displacing vertices in facial regions (mouth, eyes, eyebrows, cheeks, jaw).
   - `get_rigging_script(mesh_name, landmarks)`: Standalone Python script executable inside Blender 4.5+ to generate armature, bind skin weights, and create all 52 shape keys on the mesh.
2. Update `src/morphomesh/blender_bridge.py`:
   - Complete `auto_rig_human()` dispatch over socket (127.0.0.1:9876) and headless runner fallback.
   - Return genuine `HumanRigResult` with bone counts, bone list, and shape key count.
   - Ensure all Windows paths use forward slashes `/`.
3. Create `tests/test_human_rigging.py`:
   - Verify metarig bone hierarchy and 163 DEF bones count.
   - Verify landmark alignment and pre-bend angles.
   - Verify weight normalization (sum=1.0) and anti-pinch properties.
   - Verify all 52 ARKit FACS shape keys (names, displacement).
   - Verify Blender bridge auto_rig_human execution.
4. Run `pytest tests/` to confirm 100% test pass rate with zero regressions.
5. Deliver handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m2\handoff.md` and send message to orchestrator_human_1.
