# Handoff Report: Anime Animation & Shading Pipeline (R3 & R4)

**Agent ID**: `survey_explorer_anime_3`  
**Role**: Anime Animation & Shading Explorer  
**Working Directory**: `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3`  
**Target Project**: `E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline`  
**Parent**: `b92e9874-779a-4b1b-a142-83b44d9febb4` (`orchestrator_anime_1`)  
**Timestamp**: 2026-09-09T14:55:00Z  

---

## 1. Observation

1. **Blender Execution & Environment**:
   - Running `"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" --version` confirmed `Blender 4.5.4 LTS` (build date 2025-10-28, branch `blender-v4.5-release`, hash `b3efe983cc58`).
   - Querying `bpy.context.scene.render.bl_rna.properties['engine'].enum_items` confirmed that `BLENDER_EEVEE_NEXT` is the active EEVEE engine in Blender 4.5.
   - Node availability checks confirmed that `ShaderNodeShaderToRGB`, `ShaderNodeBsdfDiffuse`, `ShaderNodeValToRGB` (ColorRamp), and `ShaderNodeEmission` are fully supported in Blender 4.5 EEVEE-Next.
   - Python environment checks confirmed `NumPy 2.4.6` and `Pillow 12.3.0` in `.venv`, and `NumPy 2.4.6` inside Blender's bundled Python 3.11.
   - FFmpeg & FFprobe confirmed at `C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffprobe.exe` (version 9.0.1).

2. **Existing Meshes & Animation Inspection**:
   - In `output/anime_girl_v2/anime_girl_rigged.glb`:
     - Armature contains exactly 24 bones (`Hips`, `Spine`, `Spine01`, `Spine02`, `LeftUpLeg`, `RightUpLeg`, `LeftLeg`, `RightLeg`, `LeftFoot`, `RightFoot`, `LeftToeBase`, `RightToeBase`, `LeftShoulder`, `RightShoulder`, `LeftArm`, `RightArm`, `LeftForeArm`, `RightForeArm`, `LeftHand`, `RightHand`, `neck`, `Head`, `head_end`, `headfront`).
     - Lacks finger bones (Thumb, Index, Middle, Ring, Pinky), twist bones (`Arm_Twist`, `ForeArm_Twist`), hair bones, and skirt bones.
     - In `scripts/render_fixed_video.py` (lines 35-75), the developer had to manually inject:
       - Line 36: `arm_mod.use_deform_preserve_volume = True` (Dual Quaternion Skinning to prevent torso/joint collapse).
       - Lines 41-50: Manual vertex group weight transfer hack binding outer skirt vertices to `Hips` instead of thigh bones (`LeftUpLeg`, `RightUpLeg`) to stop skirt tearing.
       - Lines 54-75: Manual `LIMIT_ROTATION` constraints on `LeftFoot`, `RightFoot`, `LeftToeBase`, `RightToeBase` to keep shoes from twisting and sinking into the floor plane.
   - In `output/anime_girl/basic_anim_walking_armature_glb_url.glb`:
     - Action is named `Armature|walking_man|baselayer`, exhibiting a masculine cowboy stride that severely distorts anime proportions.

3. **Live Experimental Shading & Outline Verification**:
   - Executed headless Python scripts in Blender 4.5.4 LTS:
     - Verified Cel-Shading node tree (`Diffuse BSDF` -> `Shader to RGB` -> `ColorRamp [CONSTANT]` with warm peach shadow `(0.86, 0.62, 0.56, 1.0)` and porcelain base `(0.98, 0.92, 0.88, 1.0)`).
     - Verified Inverted Hull Solidify modifier (`thickness = -0.015`, `offset = 1.0`, `use_flip_normals = True`, `use_rim = False`, `material_offset = 1`) with unlit emission material (`use_backface_culling = True`).
     - Rendered snapshot `test_cel_split.png` and `test_cel_with_outline.png` in EEVEE-Next in 1.44 seconds.
     - Verified Hair "Angel Ring" (Tenshi no Wa) highlight band using object-space Z coordinate band mixed with diffuse light gating in `test_hair_angel_ring.png` in 4.32 seconds.
     - Verified image results directly using `view_file`.

---

## 2. Logic Chain

1. **Why raw human mocap causes anime character distortion (Observation 2)**:
   - Anime characters have exaggerated proportions (head-to-body ratio 1:5.5 to 1:6.5, long slender limbs, narrow hips, delicate wrists).
   - Raw human mocap files recorded on real human actors have wide foot stances, natural forearm twist, and pronounced heel-strike walk cycles.
   - When retargeted to an anime rig without rotational clamping or twist bones, single forearm bones suffer the "candy wrapper" twist collapse, knees bend inward, and feet rotate abnormally.
   - **Conclusion**: The pipeline must provide programmatic anime keyframed actions (Idle cute, Wave greeting, Walk cycle, Jump/cheer) designed specifically for anime aesthetic standards (narrow center-line footwork, contrapposto hip tilts, cute arm bends, secondary spring lag), combined with rotational limits (`LIMIT_ROTATION`) on hinge joints.

2. **Why standard PBR shaders fail on anime models (Observation 2 & 3)**:
   - Standard Principled BSDF creates smooth continuous gradients with dark muddy shadows and oily specular reflections across cheeks and foreheads.
   - In anime art, shading is strictly stepped (cel-shaded) with intentional color shifts (e.g. skin shadows are warm peach/coral, not black/grey).
   - **Conclusion**: In Blender 4.5 EEVEE-Next, `ShaderNodeBsdfDiffuse` paired with `ShaderNodeShaderToRGB` and `ShaderNodeValToRGB` with `CONSTANT` interpolation produces pristine two-tone and three-tone cel shading. Hair requires a dedicated procedural Z-band for the iconic "Angel Ring" highlight.

3. **Why Inverted Hull is superior to Freestyle for outlines (Observation 3)**:
   - Freestyle is a screen-space post-processing effect that is slow, prone to frame-to-frame temporal flickering, and difficult to tune headlessly.
   - The Inverted Hull method (Solidify modifier with negative thickness, flipped normals, and backface culling) creates real 3D geometry outlines that deform seamlessly with the armature, render in real-time in EEVEE-Next, and maintain consistent pixel contour width.

4. **Why automated verification is necessary (Observation 1 & 2)**:
   - Headless pipelines can silently output broken models (e.g., missing finger bones, torn skirt vertices, 0-byte or corrupted MP4 files).
   - Designing automated audit scripts for:
     1. Rig bone completeness (checking 30 finger bones, twist bones, hair, skirt).
     2. Mesh deformation volume preservation (edge stretch ratio $\le 1.85$, convex hull volume retention $\ge 85\%$).
     3. Render verification (FFprobe video stream check 1920x1080 @ 30fps, frame luminance, cel-shading multi-modal histogram step validation).
   - Guarantees 100% testable acceptance criteria before shipping.

---

## 3. Caveats

1. **Face Shadow Artifacts under Point Lights**:
   - In 3D anime models, direct point lights close to the face can cast triangular shadows from the nose or brow across the cheeks. To prevent this, character faces typically use custom edited vertex normals (pointing radially outward) or a light-direction dot product mask to ensure clean facial lighting.
2. **Skirt Simulation vs Bone Rigging**:
   - Pleated skirts can be controlled either via secondary spring bones (parented to Hips) or Blender cloth simulation. For real-time Game-Ready/VTuber export, spring bones with rotational limits are recommended over heavy cloth sim.
3. **GPU Headless Environment**:
   - Blender EEVEE-Next requires OpenGL / Vulkan GPU context. On headless Windows systems, Blender uses the GPU driver if available (verified working on this system with 1.4s render times).

---

## 4. Conclusion

1. **R3 (Animation & Retargeting)**:
   - Successfully designed 4 programmatic anime actions: `action_anime_idle_cute` (90f loop), `action_anime_wave_greeting` (120f), `action_anime_walk_cycle` (32f loop), `action_anime_jump_cheer` (75f).
   - Formulated humanoid retargeting matrix and `LIMIT_ROTATION` constraints for elbows (0°–145° hinge), knees (0°–140° hinge), ankles, and toes to permanently prevent mocap distortion.
   - Specified NLA non-destructive track blending architecture.
2. **R4 (Toon Shading & Cinematic Rendering)**:
   - Successfully designed and live-verified in Blender 4.5.4 LTS:
     - Skin Cel-Shader (`M_Anime_Skin`): Warm peach shadow tint `(0.86, 0.62, 0.56)`, porcelain base `(0.98, 0.92, 0.88)`, zero oily specular.
     - Hair Cel-Shader (`M_Anime_Hair`): Two-tone cel base with procedural "Angel Ring" specular band.
     - Inverted Hull Outline (`M_Anime_Outline`): Solidify modifier (`thickness = -0.015`, `use_flip_normals = True`, `use_rim = False`, `use_backface_culling = True`).
     - Cinematic camera setup (50–85mm lens, 3-point anime lighting with 550W back rim light).
     - Headless Full HD 1080p (1920x1080) 30 FPS MP4 render pipeline using EEVEE-Next and FFmpeg H.264.
3. **Verification Suite**:
   - Designed 3 automated scripts: `verify_anime_rig.py`, `verify_mesh_deformation.py`, and `verify_render_output.py`.

---

## 5. Verification Method

To independently verify all findings and test renders generated during this survey:

1. **Inspect Rendered Proof Snapshots**:
   - View `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3\test_cel_split.png` to verify crisp stepped cel-shading.
   - View `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3\test_cel_with_outline.png` to verify Inverted Hull outline contouring.
   - View `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3\test_hair_angel_ring.png` to verify the procedural Hair "Angel Ring" specular highlight band.

2. **Run Blender Headless Shading Test**:
   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" -b --python-expr "import bpy; scene = bpy.context.scene; scene.render.engine = 'BLENDER_EEVEE_NEXT'; print('EEVEE-Next Active:', scene.render.engine); mat = bpy.data.materials.new('Test'); mat.use_nodes = True; s2rgb = mat.node_tree.nodes.new('ShaderNodeShaderToRGB'); print('ShaderToRGB Node:', s2rgb.type)"
   ```
   *Expected result*: Prints `EEVEE-Next Active: BLENDER_EEVEE_NEXT` and `ShaderToRGB Node: SHADER_TO_RGB`.

3. **Verify FFprobe Video Metadata Query**:
   ```powershell
   & "C:\Users\Admin\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffprobe.exe" -v error -show_entries stream=width,height,r_frame_rate,codec_name -of json "E:\tool\mcp\MorphoMesh\output\anime_girl_v2\anime_girl_fixed_cinematic.mp4"
   ```
   *Expected result*: Valid JSON containing `codec_name: h264`, `r_frame_rate: 30/1`.

4. **Review Authoritative Analysis Report**:
   - Inspect `E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3\analysis.md` for complete mathematical formulations, node tree connection schemas, and test script designs.
