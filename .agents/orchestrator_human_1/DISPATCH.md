# Dispatch Instructions

## 2026-09-06T17:36:49Z

You are the Project Orchestrator for the MorphoMesh Digital Human Engine Upgrade and Yu Nian An (余念安) 3D Photorealistic Character Project.

Your Working Directory: E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_1
Project Root: E:\tool\mcp\MorphoMesh
Original Request: E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md
Reference Image: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

CORE MISSION:
Nâng cấp MorphoMesh thành pipeline tạo mô hình người 3D chân thực đạt chuẩn công nghiệp (Photorealistic Digital Human Pipeline) kết nối Blender qua FastMCP/Socket Bridge, đồng thời tạo mô hình 3D hoàn chỉnh của nhân vật Dư Niệm An (余念安 - Yu Nian An) theo phong cách bán thực tế cao cấp (Semi-Realistic / Stylized Photorealism) bám sát tuyệt đối bản vẽ tham chiếu.

KEY DELIVERABLES & REQUIREMENTS:
1. Engine Architecture Upgrade (src/morphomesh/):
   - `human_generator.py`: Parametric/procedural female human anatomy generator (realistic proportions, head, torso, limbs, hands with 5 articulated fingers each, feet, quad-dominant topology >=95% quads in deforming regions, manifold, correct normals).
   - `human_rigging.py`: Rigify Human Metarig integration with 163 DEF bones, automated alignment to human anatomy, vertex skinning/weighting, 52 ARKit FACS facial blendshapes/shape keys.
   - `human_materials.py`: High-end PBR human skin shader with Subsurface Scattering (Random Walk), dual-chamber refractive cornea/iris eye shader, specular wetness maps.
   - `human_grooming.py`: Curves-based hair grooming system using Geometry Nodes for realistic straight bangs (hime cut) long black hair.
   - `wardrobe.py`: Dynamic clothing generator/dresser for the white two-strap dress with waist belt and flat sandals.
   - Blender Socket Bridge (port 9876) & FastMCP server (`src/morphomesh/server.py`): Expose and register `morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_setup_human_materials`, `morphomesh_groom_human`, `morphomesh_dress_human`.

2. 3D Character Asset: Dư Niệm An (余念安 - Yu Nian An):
   - Semi-realistic/high-end stylized photorealism strictly matching reference image `media_1788716034772.jpg` (4 views: front, 3/4, side profile, back).
   - Delicate, pure facial structure, expressive melancholic eyes, distinct jawline, nose, lips.
   - Quad-dominant mesh (>=95% quads in deforming regions, manifold, correct normals).
   - White strap dress with waist tie and flat slip-on sandals.
   - Signature magic props: slender fingers holding glowing red thread marionette strings controlling luminous white butterflies.
   - Long black straight hair with bangs (hime cut) via hair curves.
   - Rigify 163-bone armature with clean deformation (elbows, knees, shoulders without pinching) and 52 FACS blendshapes.
   - Blender project `.blend` with organized collections (Body, Hair, Dress, Accessories, Armature, Lights/Camera).

3. Testing & Production Packaging:
   - Comprehensive unit test suite covering new modules, socket bridge, fastmcp server tools (`pytest tests/`) achieving 100% pass.
   - Export to `.blend`, `.fbx`, `.gltf` with 4K PBR texture sets.
