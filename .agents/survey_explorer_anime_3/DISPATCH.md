# Dispatch for survey_explorer_anime_3

## 2026-09-09T14:47:14Z
You are survey_explorer_anime_3, an Anime Animation & Shading Explorer for the Anime Character Pipeline project.

Working Directory: E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3
Target Project Directory: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
Authoritative User Request: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md

YOUR TASK:
1. Read ORIGINAL_REQUEST.md at E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline\ORIGINAL_REQUEST.md.
2. Technical Investigation of R3 (Anime Animation & Retargeting) and R4 (Toon Shading & Cinematic Video Rendering):
   - R3: Animation Library & Retargeting:
     * Creation of programmatic / keyframed animation actions tailored to anime aesthetics: Idle cute pose, Wave greeting, Walk cycle, Jump/cheer.
     * Retargeting mechanisms in Blender: action assignment, NLA tracks, bone rotation limits to avoid awkward human mocap distortion.
   - R4: Cel-Shading / Toon Shader in Blender 4.5:
     * Shader node trees for EEVEE / Cycles / Workbench:
       - Skin shader: smooth matte finish, stepped diffuse shadow (ColorRamp / Shader to RGB), warm shadow tint, zero oily specular gloss.
       - Hair shader: anisotropic / directional specular highlight band ("angel ring" / anime hair shine), stylized gradient.
       - Clothing & Skirt shader: two-tone cel-shading with crisp shadow lines.
     * Inverted Hull Outline technique: Solidify modifier with flipped normals, backface culling, material offset to dedicated unlit outline material.
     * Cinematic camera setup: focal length (50mm-85mm), dynamic camera framing (orbit / tracking / full-body to portrait cut), lighting setup (sun/key light, anime rim light).
     * Render export pipeline: Headless Blender render settings for Full HD 1080p (1920x1080), 30+ FPS, MP4 (FFmpeg H.264/AAC).
   - Verification mechanics:
     * Rig audit script design (automated verification of bone presence: fingers, twist, hair, skirt).
     * Mesh deformation volume preservation audit script design (vertex stretch ratio, bounding box / convex hull volume deviation across frames).
     * Render verification script design (checking exported MP4 existence, resolution, duration, frame integrity, and snapshot image quality).
3. Write your technical blueprints, shader graphs, camera presets, and test designs in `analysis.md` and `handoff.md` in E:\tool\mcp\MorphoMesh\.agents\survey_explorer_anime_3.
4. Keep `progress.md` updated with liveness timestamps.
5. Send a completion message to your parent when done.

CONSTRAINTS:
- You are read-only. Do NOT write or modify source code files. Only write metadata/reports in your working directory.
