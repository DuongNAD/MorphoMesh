## 2026-09-07T02:18:52Z
You are worker_human_m3.
Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\worker_human_m3
Your parent is orchestrator_human_1 (conversation ID: fa73b7ae-2239-4440-89d0-f3a69497b7b7).

MANDATORY READING:
1. Read E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md in its entirety.
2. Read E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1\PROJECT.md.
3. Review the Survey Handoff for Shading, Grooming & Wardrobe:
   E:\tool\mcp\MorphoMesh\.agents\explorer_survey_human_3\handoff.md
4. Check reference image turnaround specifications:
   C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_preview_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

YOUR ASSIGNED MILESTONE: Milestone 3 - Shading, Hair Grooming Curves & Wardrobe
You have exclusive write ownership of:
- src/morphomesh/human_materials.py
- src/morphomesh/human_grooming.py
- src/morphomesh/wardrobe.py
- src/morphomesh/blender_bridge.py (human materials, grooming, wardrobe dispatch methods)
- blender_addon/morphomesh/listener.py (dispatch handlers for materials, grooming, wardrobe)
- tests/test_human_materials.py
- tests/test_human_grooming.py
- tests/test_wardrobe.py

TASKS TO COMPLETE:
1. Implement `src/morphomesh/human_materials.py`:
   - Complete PBR shader builder for Blender 4.5+ using Principled BSDF v2 node trees.
   - PBR Skin Shader (`Mat_Human_Skin_SSS`): Random Walk Subsurface Scattering (subsurface_weight 0.28, radius (1.0, 0.2, 0.1), IOR 1.45, roughness 0.35 with micro-roughness specular).
   - Dual-Chamber Refractive Eye Shader:
     * Outer Cornea (`Mat_Human_Eye_Outer_Cornea`): Transmission 1.0, Roughness 0.02, IOR 1.376, transparent glass.
     * Inner Iris & Pupil (`Mat_Human_Eye_Inner_Iris`): Dark brown/black iris with radial fiber gradient, limbal ring, and pupil dilation driver.
     * Sclera (`Mat_Human_Eye_Sclera`): Subtle red vein tint with SSS.
   - Realistic Hair Shader (`Mat_Human_Hair`): Principled Hair BSDF (melanin 0.85 for natural black hair, roughness 0.25, radial roughness 0.45, angel-ring specular sheen).
   - Wardrobe Materials:
     * `Mat_Dress_WhiteSilk`: Off-white (0.95, 0.95, 0.95), sheen 0.6, roughness 0.4.
     * `Mat_Dress_WaistBelt`: Dark sash belt (0.15, 0.15, 0.15), roughness 0.5.
     * `Mat_Sandal_Leather`: Dark leather (0.1, 0.08, 0.07), roughness 0.45.
   - `get_material_setup_script(target_object, material_preset)`: Standalone Python script executable inside Blender 4.5+ creating and assigning all materials to their designated vertex groups / slots.

2. Implement `src/morphomesh/human_grooming.py`:
   - Geometry Nodes Hair Curves generator for Blender 4.5+ (Curves object, not old particle hair).
   - Hairstyle: Yu Nian An signature hime cut with:
     * Straight forehead bangs ending at eyebrow level.
     * Symmetrical sidelocks framing cheeks down to shoulder.
     * Long flowing back hair cascade extending to hips (~1.0m length).
   - Geometry Nodes hair modifier network: Interpolate Hair Curves, Clump, Noise, Taper (Curve Radius modifier).
   - `get_grooming_script(target_object, hair_style)`: Executable script in Blender to generate curves, attach to scalp vertex group, build Geometry Nodes modifier, and assign hair shader.

3. Implement `src/morphomesh/wardrobe.py`:
   - Parametric procedural garment generator matching Yu Nian An's turnaround:
     * White two-strap slip dress: sleeveless, dual thin shoulder straps, scoop neckline, draped A-line silhouette ending above knee, Solidify thickness 0.002m, manifold geometry.
     * Sash waist belt: cinched around waist at waist_girth, small knot / buckle detail.
     * Strappy flat sandals: sole matching foot dimensions, thin strap geometry crossing instep and ankle.
   - Binding / Rigging integration: Parent / Surface Deform or Armature modifier with vertex group transfer so clothing deforms with character rig.
   - `get_wardrobe_script(target_object, outfit_preset)`: Executable script in Blender to generate dress, belt, sandals meshes and bind them to the body/armature.

4. Update `src/morphomesh/blender_bridge.py` & `blender_addon/morphomesh/listener.py`:
   - Wire `setup_human_materials`, `groom_human`, `dress_human` methods to dispatch over socket `127.0.0.1:9876` and fallback to headless execution.
   - Ensure all Windows file paths use forward slashes `/` or `repr()`.
   - Register the RPC handlers in `listener.py`.

5. Unit & Integration Tests:
   - `tests/test_human_materials.py`: Verifies shader graphs, node connections, SSS settings, Principled BSDF v2 parameters.
   - `tests/test_human_grooming.py`: Verifies Geometry Nodes hair curves generation, guide curves, modifier network, scalp attachment.
   - `tests/test_wardrobe.py`: Verifies dress, belt, sandal geometry, dimensions, manifoldness, and armature binding.
   - Run `pytest tests/` in the environment to verify 100% test pass with zero regressions on existing tests.

6. Write your handoff report to `E:\tool\mcp\MorphoMesh\.agents\worker_human_m3\handoff.md` and send a message back to orchestrator_human_1 when finished.
