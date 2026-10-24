# Original User Request

## 2026-09-05T11:21:54Z

Xây dựng dự án MorphoMesh: Hệ thống pipeline tự động và MCP Server kết nối Google Antigravity 2.0 với Blender, chuyên biệt hóa cho bài toán tạo sinh vật/động vật 3D (Creature Generation) từ câu lệnh mô tả (Prompt -> Image Concept -> 3D Mesh & PBR Texture -> Retopology -> Auto-rigging -> Hoàn thiện trong Blender scene). Ưu tiên giai đoạn 1: Biên soạn toàn diện bộ tài liệu nghiên cứu, kiến trúc kỹ thuật và đặc tả MCP Server, sau đó xây dựng khung mã nguồn thực thi PoC (MCP Server + Blender Bridge).

Working directory: /Users/duongnad/Documents/tool/MorphoMesh
Integrity mode: development

## Requirements

### R1. Bộ tài liệu nghiên cứu & phân tích chuyên sâu (Comprehensive Research & Benchmark Docs)
- Nghiên cứu, đánh giá và lập ma trận so sánh chi tiết ít nhất 20 mô hình và framework mã nguồn mở SOTA chia làm 3 nhóm chính:
  1. **Chuyên biệt Động vật & Khớp nối (Articulated Animals)**: 3DAnimals (MagicPony, 3D Fauna, Ponymation), 4D-Animal, Animal Avatar, YouDream, GART, LASSIE, SAOR, BARC, BITE, anyCreature, Meow-Generator, animalclub, Muses.
  2. **Tạo 3D tổng quát chất lượng cao cho Creature**: TRELLIS / TRELLIS.2, Hunyuan3D-2 / 2.1, Step1X-3D, Hi3DGen / Stable3DGen, SPAR3D, Stable Fast 3D, TripoSR, InstantMesh, Unique3D, OpenLRM, LGM, CRM.
  3. **Tái cấu trúc lưới & Rigging tự động**: MeshAnything / MeshAnything V2, Mesh2Motion, SMAL / SMALify, Blender Rigify procedural creatures.
- Phân tích chi tiết theo các tiêu chí: License (MIT, Apache-2.0, Tencent/Stability Community License), Yêu cầu phần cứng & VRAM, Độ trung thực hình học (Geometry fidelity), Định dạng xuất (Mesh OBJ/GLB/FBX, Gaussian splatting, PBR materials), Trạng thái xương/rigging, và Khả năng triển khai (Local vs Cloud API).
- Đưa ra khuyến nghị lộ trình kết hợp tối ưu cho 3 use-case: (A) Fantasy Creature đa dạng, (B) Động vật thực tế có animation/rig, (C) Game-ready low-poly asset.
- Tài liệu lưu trữ tại: `docs/RESEARCH_BENCHMARK.md`.

### R2. Thiết kế Kiến trúc Hệ thống & Luồng dữ liệu (System Architecture & Pipeline Specification)
- Thiết kế kiến trúc tổng thể theo mô hình Hybrid phù hợp chạy client trên macOS (Apple Silicon) tương tác với Blender:
  - **Tầng Client & Điều phối**: Antigravity 2.0 kết nối với MorphoMesh MCP Server.
  - **Tầng Giao tiếp Blender**: IPC/Socket/JSON-RPC Bridge giao tiếp với Blender Python environment (`bpy`).
  - **Tầng Tính toán AI (Inference Engine)**: Adapter module hỗ trợ cả Remote GPU Endpoint (Replicate API, Hugging Face Inference Endpoints, Custom Linux GPU Server) cho các mô hình nặng (TRELLIS.2 4B, Hunyuan3D 2.1, FLUX) và Local fallback cho các tác vụ tiền xử lý, remesh, và test.
- Đặc tả chi tiết luồng xử lý (End-to-End Dataflow):
  1. *Prompt Engineering & Concept Gen*: Tối ưu prompt tạo creature (silhouette rõ, A-pose/T-pose tự nhiên, đa góc nhìn hoặc orthographic view).
  2. *Single-image to 3D Generation*: Sinh 3D geometry và PBR materials.
  3. *Topology Optimization*: Chuyển đổi sang topology sạch, phân bổ quad/tri tối ưu cho deforming mesh.
  4. *Skeleton & Rigging Automation*: Tự động định vị khớp (landmarks) và tạo armature thích ứng (quadruped, biped, winged, multi-limbed).
  5. *Blender Scene Assembly*: Thiết lập ánh sáng, vật liệu Principled BSDF, modifier, và camera preview.
- Tài liệu lưu trữ tại: `docs/ARCHITECTURE.md`.

### R3. Đặc tả chuẩn MCP Server cho Antigravity 2.0 (MCP Interface Specification)
- Thiết kế đặc tả Model Context Protocol (MCP) chi tiết với đầy đủ JSON Schema cho các tool:
  - `morphomesh_generate_concept`: Tạo ảnh sinh vật 2D chuẩn hoá góc nhìn.
  - `morphomesh_create_3d_asset`: Gửi ảnh sang pipeline tạo 3D mesh và PBR texture.
  - `morphomesh_optimize_topology`: Giảm poly / retopology lưới theo ngân sách poly mong muốn.
  - `morphomesh_auto_rig`: Tự động tạo bộ xương và gán skin weights cho sinh vật trong Blender.
  - `morphomesh_blender_execute`: Thực thi script `bpy` tùy biến an toàn trong phiên làm việc của Blender.
  - `morphomesh_get_scene_status`: Kiểm tra danh sách đối tượng, mesh stats, hierarchy trong Blender scene.
  - `morphomesh_render_preview`: Render ảnh xem trước từ camera của Blender và trả về cho agent.
- Tài liệu lưu trữ tại: `docs/MCP_SPECIFICATION.md`.

### R4. Cài đặt Khung mã nguồn Thực thi (Runnable PoC Skeleton & Blender Bridge)
- Xây dựng mã nguồn MCP Server bằng Python (chuẩn MCP SDK / FastMCP):
  - Định nghĩa đầy đủ các tool với schema typing, docstrings và error handling.
  - Xây dựng module `blender_bridge.py`: Giao tiếp 2 chiều với Blender qua socket hoặc headless `bpy` script runner.
  - Xây dựng module `inference_adapter.py`: Cơ chế plug-and-play cho các backend (Mock/Offline cho dev test, Replicate/HF API cho production).
  - Cung cấp Blender Addon / Script template để chạy bên trong Blender và lắng nghe lệnh từ MCP Server.
- Bộ kịch bản hướng dẫn cài đặt và cấu hình nhanh (`README.md`, `SETUP_GUIDE.md`).

## Acceptance Criteria

### Documentation Verification
- [ ] File `docs/RESEARCH_BENCHMARK.md` hoàn thành đầy đủ, chứa ma trận phân tích bảng so sánh ít nhất 20 mô hình/repo, phân loại rõ 3 nhóm (Articulated Animals, General 3D, Retopology & Rig), có thông tin License, VRAM, và đánh giá tính khả thi.
- [ ] File `docs/ARCHITECTURE.md` hoàn thành với sơ đồ kiến trúc (Mermaid diagram), phân tích chi tiết thiết kế Hybrid (Local Mac + Remote GPU + Blender Bridge), và chi tiết từng bước trong 5 giai đoạn của pipeline.
- [ ] File `docs/MCP_SPECIFICATION.md` hoàn thành với đầy đủ JSON schemas, danh sách tool, tham số vào/ra, mã lỗi, và ví dụ payload tương tác giữa Antigravity và Blender.
- [ ] File `docs/ROADMAP.md` mô tả lộ trình thực hiện từ giai đoạn PoC đến bản hoàn thiện.

### Code & Execution Verification
- [ ] Dự án khởi tạo với cấu trúc thư mục rõ ràng: `docs/`, `src/morphomesh/`, `blender_addon/`, `tests/`.
- [ ] Toàn bộ MCP Tools khai báo đúng chuẩn Model Context Protocol, nạp thành công không lỗi cú pháp.
- [ ] Bộ kiểm thử tự động (`pytest`):
  - Kiểm thử định nghĩa và schemas của tất cả MCP Tools.
  - Kiểm thử `inference_adapter` ở chế độ mock và validation logic.
  - Kiểm thử `blender_bridge` module (kiểm tra serialization lệnh, validation script an toàn).
- [ ] Tất cả các test case đều PASS với exit code 0 (`pytest -v tests/`).
- [ ] Hướng dẫn kiểm thử thực tế với Blender được tài liệu hóa rõ ràng trong `README.md`.

## 2026-09-05T12:56:31Z

Xây dựng hệ thống Tham khảo và Tích hợp Mã nguồn mở Tối ưu (Open-Source Integration Hub) cho MorphoMesh: Thiết lập bộ Cẩm nang Kỹ thuật (Engineering Playbook & Licensing Governance) và phát triển các Adapter Connectors chuyên dụng trong `src/morphomesh/connectors/` để kết nối và chuẩn hóa dữ liệu từ 5 dự án SOTA hàng đầu (Microsoft TRELLIS.2, 3DAnimals / SMAL, anyCreature, MeshAnything V2, và Tencent Hunyuan3D-2.1) vào hệ sinh thái Blender MCP Server.

Working directory: /Users/duongnad/Documents/tool/MorphoMesh
Integrity mode: development

## Requirements

### R1. Cẩm nang Kỹ thuật Tích hợp & Quản trị Mã Nguồn Mở (Open-Source Engineering Playbook & Licensing Governance)
- Phân tích chi tiết phương thức khai thác, trích xuất và tích hợp tối ưu nhất cho 5 dự án mã nguồn mở tiêu biểu:
  1. **Microsoft TRELLIS / TRELLIS.2** (MIT): Kiến trúc O-Voxel, DiT, trích xuất PBR material pipeline, tối ưu hóa suy luận và tích hợp Gradio/ComfyUI backend.
  2. **3DAnimals / MagicPony / SMAL** (Research): Tái tạo giải phẫu quadruped/animal, mapping hệ xương parametric SMAL sang Blender Armature/Rigify, cơ chế articulation và motion transfer.
  3. **anyCreature** (Engine Procedural): Cấu trúc JSON specification, biên dịch từ prompt sang body parts, procedural skinning và gắn animation clips thời gian thực.
  4. **MeshAnything V2** (Apache-2.0): Kiến trúc autoregressive sequence model tạo artist-like quad mesh dưới 1600 faces, giải pháp retopology cho game-ready assets.
  5. **Tencent Hunyuan3D-2.1** (Community License): Trích xuất mesh high-res và PBR textures, phương án container hóa độc lập.
- Xây dựng hướng dẫn chuẩn mực cho:
  - **Quản lý Checkpoints & Weights**: Phân tầng lưu trữ (Hugging Face Hub caching, git LFS, local cache), quantized formats (FP16, BF16, INT8, NF4/AWQ) và tối ưu VRAM.
  - **Kiến trúc Triển khai (Serving & Containerization)**: Docker compose templates, mô hình microservices (FastAPI / Gradio / ComfyUI headless), và API client patterns tách biệt hoàn toàn khỏi macOS client.
  - **Quản trị Bản quyền & Rủi ro Pháp lý (Licensing Governance)**: Thiết kế ranh giới tiến trình (Process & Network Boundary Isolation) để bảo đảm tuân thủ Tencent Hunyuan Community License và Stability AI Community License mà không làm ảnh hưởng tính mở của MorphoMesh.
- Tài liệu lưu trữ tại: `docs/OPEN_SOURCE_INTEGRATION_PLAYBOOK.md`.

### R2. Bộ Module Connectors Sản Xuất (Production Open-Source Connectors)
- Xây dựng gói module `src/morphomesh/connectors/` với cấu trúc hướng đối tượng, typing an toàn (Pydantic v2) và cơ chế xử lý lỗi chuẩn:
  - `trellis_connector.py`: Connector tương thích TRELLIS.2, hỗ trợ cả gọi qua Local/Remote API, chuyển đổi structured latent / GLB và PBR texture maps vào Blender.
  - `animals3d_connector.py`: Connector tương thích 3DAnimals / SMAL, chuyển đổi dữ liệu joint landmarks và bone weights sang định dạng chuẩn của Blender Rigify.
  - `anycreature_connector.py`: Connector phân tích prompt thành JSON specification cho anyCreature engine, hỗ trợ import procedural creature meshes và animation clips.
  - `meshanything_connector.py`: Connector nạp dense meshes từ AI generators và điều phối quy trình retopology tạo quad mesh cho game.
  - `hunyuan_connector.py`: Connector giao tiếp với backend Hunyuan3D-2.1 sinh high-fidelity meshes.
  - `registry.py`: Cơ chế Registry tự động đăng ký các connector, kiểm tra trạng thái hoạt động (Health Checks, Dependency Checks), và cung cấp cơ chế Circuit Breaker & Fallback thông minh.
- Tích hợp các connector này vào `src/morphomesh/inference_adapter.py` và các FastMCP tools trong `src/morphomesh/server.py`.

### R3. Bộ Kiểm Thử Tự Động & Kịch Bản Minh Họa (Automated Tests & Demo Harness)
- Xây dựng bộ test toàn diện tại `tests/test_connectors.py`:
  - Kiểm thử độc lập cho từng connector ở chế độ offline/mock (đảm bảo không phụ thuộc kết nối mạng bên ngoài trong lúc test).
  - Kiểm thử cấu trúc dữ liệu JSON spec, transformation matrix của SMAL armature, và quy trình xử lý PBR texture.
  - Kiểm thử cơ chế Circuit Breaker và chuyển đổi dự phòng (Fallback) khi remote service mất kết nối.
- Bổ sung kịch bản minh họa (Example scripts) tại `examples/open_source_pipeline_demo.py` chứng minh quy trình tích hợp liền mạch từ concept đến rigged creature trong Blender.

## Acceptance Criteria

### Documentation Verification
- [ ] File `docs/OPEN_SOURCE_INTEGRATION_PLAYBOOK.md` hoàn thành đầy đủ, chi tiết (dung lượng >40 KB), phân tích sâu sắc cả 5 repo (TRELLIS.2, 3DAnimals, anyCreature, MeshAnything V2, Hunyuan3D-2.1), có hướng dẫn Docker/Serving, chiến lược weights caching, và sơ đồ quy chuẩn pháp lý bản quyền.

### Code & Execution Verification
- [ ] Thư mục `src/morphomesh/connectors/` được tạo với đầy đủ các tệp: `__init__.py`, `registry.py`, `trellis_connector.py`, `animals3d_connector.py`, `anycreature_connector.py`, `meshanything_connector.py`, `hunyuan_connector.py`.
- [ ] Mã nguồn tuân thủ tiêu chuẩn code chất lượng cao, không chứa TODO dở dang hay mock rỗng, có typing đầy đủ với Pydantic v2.
- [ ] Tích hợp trơn tru vào `InferenceAdapter` và các công cụ FastMCP hiện có.
- [ ] Kịch bản chạy mẫu `examples/open_source_pipeline_demo.py` thực thi thành công.
- [ ] Toàn bộ bộ test mới `tests/test_connectors.py` và bộ test hiện có chạy thành công 100% với `pytest` (exit code 0, 0 failures).

## 2026-09-05T15:44:52Z

Re-engineer and synthesize a photorealistic, anatomically authentic Armored War Bear in MorphoMesh and Blender, featuring organically sculpted facial features, forward-curving claws, a full volumetric fur grooming system, and battle-hardened PBR war armor.

Working directory: /Users/duongnad/Documents/tool/MorphoMesh
Integrity mode: development

## Requirements

### R1. Anatomical Accuracy & Organic Facial Detailing
The bear geometry must accurately embody plantigrade ursine anatomy. All claws on front and hind paws must curve naturally forward and downward toward the ground (correcting inverted claw orientations). The head must feature fully articulated facial structures: a sculpted snout with distinct nostrils, an anatomically defined mouth with jaw and teeth, dimensional eyes with eyelids, and natural cupped ears.

### R2. Volumetric Fur & Hair Grooming System
The creature must possess a multi-layer volumetric fur system (dense undercoat and coarse guard hairs) rather than flat polygon faces or low-poly approximations. The hair flow must follow authentic biological growth patterns radiating from the dorsal spine down across the torso, shoulders, and limbs, with realistic strand thickness, clumping, and tapering.

### R3. High-Fidelity PBR Material Suite & War Armor Integration
The asset must feature genuine PBR shading: organic coat scattering/roughness, high specular gloss and moisture on the nose and corneas, sharp keratin on claws, and weathered metallic armor (steel plates and brass/gold accents) cleanly fitted to the bear's shoulders and forelegs without severe clipping.

### R4. Multi-Angle Verification & Production Export
The complete creature must be assembled into a dedicated Blender scene, exported into high-quality 3D formats (.glb and .blend), and accompanied by an automated programmatic test script verifying claw orientation vectors, facial mesh landmark presence, and fur strand metrics.

## Acceptance Criteria

### Anatomical & Geometric Precision
- [ ] Claw orientation check: Claws on all four paws point forward in the direction of travel (dot product of claw tip vector with character forward axis > 0.6) and curve downward.
- [ ] Facial features check: Snout, nostrils, opened/modeled mouth cavity with teeth, eyes with eyelids, and ears are distinct geometric elements.
- [ ] Tail and plantigrade paw pads are anatomically proportioned and positioned.

### Fur Grooming & Hair Simulation
- [ ] Volumetric hair/fur curves system is active with visible depth and clumping (strand count >= 10,000 guide/render strands).
- [ ] Fur grooming flows smoothly along biological lines without chaotic intersecting spikes or bald artifact patches.

### Shading & Armor
- [ ] 4-channel PBR material workflow applied (Albedo, Normal/Displacement, Roughness, Metallic) with distinct physical properties for fur, skin, claws, and armor.
- [ ] War armor plates fit the dorsal shoulders and wrists without degenerate self-intersection.

### Programmatic & Visual Verification
- [ ] An automated inspection script (verify_bear_anatomy.py) executes and asserts: claw forward orientation, feature vertex groups/objects presence, and fur curve density.
- [ ] High-resolution multi-angle beauty renders (Front 3/4 perspective, Head close-up, Paw/claw close-up, and Full body) are saved to disk.
- [ ] Asset successfully saved as examples/Armored_War_Bear_HD.glb and active in the Blender session.

## 2026-09-05T15:47:35Z

CRITICAL SCOPE CLARIFICATION DIRECTLY FROM USER:
The user has clarified the scope: The objective is NOT merely to create one static/hardcoded Armored War Bear model. The primary goal is to upgrade the MorphoMesh ENGINE ITSELF (`src/morphomesh/` - procedural mesh generators in `inference_adapter.py`, connectors such as `anycreature_connector.py` & `trellis_connector.py`, `blender_bridge.py`, and fur/grooming pipelines) so that MorphoMesh can generate high-fidelity, photorealistic creatures in general!

Key engine requirements:
1. Reusable Anatomy Generator: Upgrade procedural mesh generation across biological archetypes (quadrupeds including Ursine/Canine/Feline, bipeds, chimeras) with:
   - Proper paw & claw anatomy: Claws MUST curve forward & downward (correcting the inverted claw bug globally).
   - Organic facial features: Detailed snout, distinct nostrils, articulated mouth/jaw cavity with teeth, spherical eyes with eyelids, cupped ears.
   - Proportional tail, limb musculature, and plantigrade/digitigrade pads.
2. Volumetric Fur & Hair Curves Pipeline: Implement a reusable Geometry Nodes / Hair Curves grooming system in the MorphoMesh Blender Bridge/pipeline, allowing any creature to be equipped with realistic multi-layer volumetric fur following natural growth flow.
3. Organic PBR Shader Engine: Upgrade texture baking and shader setups with organic coat scattering, specular gloss on wet facial areas, and sharp keratin on claws.
4. Validation & Demonstration: The Armored War Bear serves as the canonical test benchmark and demonstration verifying that the upgraded MorphoMesh engine successfully produces photorealistic, detailed creatures with correct claw orientation and realistic fur.

## 2026-09-06T04:00:05Z

Server has restarted. Please resume execution, revive the active orchestrator (Gen 2 in `.agents/orchestrator_bear_gen2/`), and complete Milestone M4 Iteration 2 remediation:
1. Anatomical continuity and smooth organic transitions in `creature_generator.py` (connecting paws, capping/blending limb junctions, organic muzzle and head contours).
2. Pauldron repositioning and true BVH clearance ($d_{\min} \ge 0.015\text{m}$).
3. Verification test suites update and re-running master assembly and beauty renders.
4. Final Victory Audit and handoff.

## 2026-09-06T17:35:53Z

# Teamwork Project Prompt

Nâng cấp MorphoMesh thành pipeline tạo mô hình người 3D chân thực đạt chuẩn công nghiệp (Photorealistic Digital Human Pipeline) kết nối Blender qua FastMCP/Socket Bridge, đồng thời tạo mô hình 3D hoàn chỉnh của nhân vật Dư Niệm An (余念安 - Yu Nian An) theo phong cách bán thực tế cao cấp (Semi-Realistic / Stylized Photorealism) bám sát tuyệt đối bản vẽ tham chiếu.

Working directory: E:\tool\mcp\MorphoMesh
Integrity mode: development
Reference Image: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg

## Requirements

### R1. MorphoMesh Digital Human Engine Upgrade
- Xây dựng module tạo dựng và nắn chỉnh giải phẫu cơ thể người (`src/morphomesh/human_generator.py` & `src/morphomesh/human_rigging.py`) tích hợp khung xương Rigify Human Metarig (163 xương DEF, 10 ngón tay và các khớp xoay chuẩn hoạt họa).
- Xây dựng hệ thống vật liệu da người PBR với Subsurface Scattering (Random Walk), mắt 2 buồng khúc xạ, tóc sợi hạt (Geometry Nodes Curves) và trang phục động (`src/morphomesh/human_materials.py`, `src/morphomesh/human_grooming.py`, `src/morphomesh/wardrobe.py`).
- Cập nhật Blender Socket Bridge (port 9876) và FastMCP server (`src/morphomesh/server.py`) để cung cấp bộ công cụ tự động hóa quá trình dựng hình, rigging, gán vật liệu và kết xuất trực tiếp trên Blender 4.5+.

### R2. Tạo Mô Hình 3D Nhân Vật Dư Niệm An (Yu Nian An) Đạt Đỉnh Cao Thẩm Mỹ
- Dựng mô hình 3D toàn diện cho nhân vật Dư Niệm An theo phong cách Semi-Realistic / High-End Stylized Photorealism: giữ trọn vẹn nét thanh tú thuần khiết, đôi mắt có hồn và biểu cảm tĩnh lặng/u buồn từ bản vẽ 4 góc nhìn (chính diện, 3/4, góc ngang, lưng).
- Dựng trang phục váy hai dây trắng thắt đai eo và dép bệt chuẩn phom dáng bản vẽ với độ rủ và nếp gấp vải tự nhiên.
- Dựng hệ thống đạo cụ đặc trưng: bàn tay mảnh mai gắn các sợi chỉ đỏ ma thuật điều khiển đàn bướm trắng phát sáng theo concept.
- Xây dựng hệ thống tóc đen dài mái bằng (hime cut / straight bangs) dạng sợi Curves tự nhiên, bóng mượt.
- Thiết lập hệ thống xương Rigify hoàn chỉnh, gắn trọng số da (vertex weighting) chuẩn xác, cùng bộ Shape Keys biểu cảm khuôn mặt (52 ARKit FACS blendshapes) sẵn sàng cho mocap/lip-sync.

### R3. Kiểm Thử và Đóng Gói Tự Động
- Bộ kiểm thử tự động xác thực tính toàn vẹn của mã nguồn, socket bridge và quy trình tạo mesh người.
- Xuất file mô hình 3D hoàn chỉnh sang các định dạng chuẩn (.blend sẵn shader Cycles/EEVEE, .fbx, .gltf) kèm đầy đủ bộ texture maps PBR (4K resolution).

## Acceptance Criteria

### MorphoMesh Core Engine
- [ ] Module `human_rigging.py` tự động sinh và nắn chỉnh armature Rigify Human 163 xương DEF trực tiếp trên Blender qua socket bridge 127.0.0.1:9876 mà không gặp bất kỳ lỗi thực thi nào.
- [ ] FastMCP server cung cấp và đăng ký thành công các công cụ quản lý human pipeline (`morphomesh_create_human_asset`, `morphomesh_auto_rig_human`, `morphomesh_setup_human_materials`, `morphomesh_groom_human`, `morphomesh_dress_human`).
- [ ] Toàn bộ unit tests mới và tests hiện tại (`pytest tests/`) đạt 100% pass.

### Mô Hình 3D Dư Niệm An
- [ ] Tỷ lệ nhân trắc học, mắt, mũi, miệng, đường viền hàm và góc nhìn 3/4 đối chiếu trùng khớp với bản vẽ thiết kế `media_1788716034772.jpg`.
- [ ] Lưới cơ thể và trang phục hoàn toàn là quads (tối thiểu 95% quads ở các vùng cử động, không có non-manifold edges, không có inverted normals).
- [ ] Shader da hiển thị tán xạ dưới bề mặt SSS chân thực, mắt có độ sâu khúc xạ và phản xạ ánh sáng tự nhiên khi render trong Blender.
- [ ] Mái tóc đen dài được cấu hình bằng hệ thống Hair Curves với độ bồng bềnh và mượt mà.
- [ ] Đạo cụ chỉ đỏ và bướm trắng gắn chính xác vào các ngón tay theo đúng tư thế biểu diễn rối/phép thuật trong ảnh.
- [ ] Khung xương hoạt động trơn tru, uốn gập tay chân không bị móp/méo bất thường tại khớp khuỷu tay, đầu gối và vai.
- [ ] File dự án `.blend` hoàn chỉnh được lưu lại với cấu trúc phân tầng rõ ràng (Collection: Body, Hair, Dress, Accessories, Armature, Lights/Camera).

## 2026-09-07T03:34:32Z

Nâng cấp toàn diện dự án MorphoMesh (Blender MCP Server) với hệ thống Camera giám sát đa góc tự động (Auto-Inspector Camera Rig), khả năng bắt khung hình Viewport siêu tốc, cơ chế phản hồi khuyết điểm trực quan tự động (Closed-Loop Visual Quality Critique), và hoàn thiện kết nối socket tương tác 2 chiều với Blender.

Working directory: e:\tool\mcp\MorphoMesh
Integrity mode: development

## Requirements

### R1. Multi-Angle Inspector Camera & Fast Viewport Capture
The system must support an automated inspection camera rig in Blender that frames the active 3D character/mesh based on its bounding box and anatomical center. It must support standard inspection viewpoints (Front, Side, Back, Three-Quarter Perspective, and Close-ups for head/hands) and provide fast image capture in both interactive socket mode (e.g. Viewport OpenGL grab) and headless batch rendering mode.

### R2. Closed-Loop Visual Quality Critique (Auto-Critic QA)
The MCP server must expose an automated visual quality inspection mechanism. This system must trigger multi-angle captures of the character, evaluate structural integrity (such as garment clipping/mesh penetration, abnormal body proportions, unnatural rig/skinning pinching, and grooming intersections), and output structured, actionable diagnostic feedback to guide automated remediation.

### R3. Interactive Blender Socket Bridge Parity & Reliability
The interactive socket listener (`blender_addon/morphomesh/listener.py`) and the bridge client (`src/morphomesh/blender_bridge.py`) must achieve full parity. All high-level MCP preview, grooming, wardrobe, and scene inspection methods must be cleanly dispatched and executed in Blender's main thread via timers without dropped connections, race conditions, or unhandled exceptions.

### R4. Automated Verification Suite & Visual Preview Artifacts
The project must include comprehensive automated tests validating the camera positioning mathematics, multi-view rendering pipeline, socket RPC communications, and visual critique diagnostic outputs.

## Acceptance Criteria

### Camera Rig & Viewport Capture
- [ ] Camera rig automatically calculates bounding box and positions cameras correctly for at least `front`, `side`, `three_quarter`, and `turntable_4views` without clipping the character.
- [ ] Viewport capture functions seamlessly in interactive mode and saves valid image files (PNG) with correct metadata and base64 preview encoding.

### Visual Quality Critique
- [ ] Auto-critic tool returns a structured report including defect classifications (e.g., `clipping`, `proportion_deviation`, `skinning_artifact`), affected mesh objects, confidence scores, and pass/fail recommendations.
- [ ] A baseline verification demo confirms that intentionally introduced clipping or deformations are accurately flagged in the diagnostic report.

### Socket Listener & Bridge Parity
- [ ] All MCP preview and execution commands run through the Blender socket listener without unhandled method errors.
- [ ] Ping and scene status queries return complete scene statistics (cameras, lights, meshes, polycounts, materials).

### Testing & Verification
- [ ] Automated test suite covering the new camera rig, preview rendering, and visual critic runs and passes completely via `pytest`.
- [ ] Documentation and tool definitions in `server.py` and README are updated to reflect the new capabilities.

## 2026-09-07T13:01:03Z

# Teamwork Project Prompt

> Requested team: Full Team chuyên sâu: Gồm Chuyên gia Giải phẫu & Khung xương chuẩn y khoa (Rigging DEF), Chuyên gia Điêu khắc & Nếp gấp vải hữu cơ (Cloth Drapery), Chuyên gia Chi tiết Cơ thể & Vật liệu PBR Cycles

Nâng cấp toàn diện MorphoMesh và mô hình 3D nhân vật Dư Niệm An (Yu Nian An) đạt chuẩn giải phẫu cơ thể người thực tế: tích hợp hệ xương khớp chuẩn y khoa (Rigify 163 DEF) bám đúng vị trí xương thật, tạo hình váy liền thân với nếp gấp và độ rủ vải hữu cơ chân thực (organic cloth drape & gravity folds), tái tạo bàn chân giải phẫu rõ 5 ngón mang giày xăng-đan đế bệt tinh xảo, cùng các đường nét cơ thể thanh thoát bám sát tuyệt đối concept gốc và các tài liệu tham chiếu.

Working directory: E:\tool\mcp\MorphoMesh
Integrity mode: development
Reference Images:
- Concept Sheet: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg
- Skeletal Anatomy: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935854.png
- Realistic Dress Drapery & Flat Sandals: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935849.jpg
- Fashion Silhouette & Cloth Folds: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935824.jpg

## Requirements

### R1. Tái Cấu Trúc Giải Phẫu Cơ Thể & Khung Xương Chuẩn Y Khoa (Anatomical Human Rig)
- Xây dựng mô hình giải phẫu cơ thể người nữ hoàn chỉnh, thanh thoát dựa trên tài liệu xương y khoa tham chiếu (`media_1788785935854.png`): xương đòn (clavicle), hõm ức, khung lồng ngực, góc xương chậu, khớp đầu gối xương bánh chè và mắt cá chân rõ nét.
- Điêu khắc bàn chân giải phẫu chân thực với 5 ngón chân phân tách rõ ràng (ngón cái, ngón trỏ, ngón giữa, ngón áp út, ngón út), móng chân tinh tế, độ cong mu bàn chân và mắt cá chân (trong/ngoài) sắc sảo.
- Thiết lập khung xương Rigify DEF tiêu chuẩn công nghiệp với hệ thống trục xoay bám đúng cấu trúc giải phẫu sinh học (biological joint pivots), trọng số da (vertex weighting / skinning) mượt mà để các chuyển động uốn gập đùi, gối, cổ chân và ngón chân giữ nguyên thể tích cơ bắp tự nhiên, không bị biến dạng hay bẹp dẹp.

### R2. Thiết Kế Váy Liền Thân Hữu Cơ Với Nếp Gấp Và Độ Rủ Vải Chân Thực (Realistic Organic Dress)
- Tái thiết kế váy thành dạng váy liền thân cao cấp dựa trên tham chiếu đời thực và minh họa thời trang (`media_1788785935849.jpg` & `media_1788785935824.jpg`): loại bỏ hoàn toàn các nếp gấp nón cơ học cứng nhắc, thay bằng các nếp gấp vải hữu cơ tự nhiên (gravity folds, tension lines từ ngực và eo, nếp gấp mềm mại rủ xuống ngang gối).
- Phần thân trên ôm sát cơ thể với cúp ngực tự nhiên (teardrop profile), rãnh ngực thanh thoát, cổ áo sweetheart scoop và dây áo spaghetti mảnh mai tự nhiên qua vai.
- Đai thắt lưng satin xanh băng (ice-blue sash) ôm khít 100% bên ngoài eo váy kèm nút thắt nơ và dải ruy-băng rủ tự nhiên, triệt tiêu hoàn toàn hiện tượng Z-fighting hay đốm xuyên thấu.

### R3. Giày Xăng-Đan Đế Bệt & Đạo Cụ Đặc Trưng
- Dựng mô hình giày xăng-đan nữ đế bệt (flat strappy sandals) theo ảnh thực tế `media_1788785935849.jpg`: đế mỏng ôm sát theo đường cong bàn chân, hệ thống quai da/vải ngang mu bàn chân và quai ôm cổ chân thanh lịch, làm lộ rõ các ngón chân thon đẹp.
- Hoàn thiện hệ thống phụ kiện theo concept gốc: 10 sợi chỉ đỏ ma thuật nối từ các đầu ngón tay điều khiển đàn bướm trắng phát sáng lượn quanh nhân vật.
- Mái tóc đen dài suôn mượt buông xõa phía sau lưng với mái bằng thanh tú bám sát concept gốc.

### R4. Shader PBR, Ánh Sáng Studio & Đóng Gói Xuất File Chuẩn
- Thiết lập hệ thống vật liệu PBR cao cấp: da Subsurface Scattering (Random Walk SSS) ấm áp, vải lụa trắng và satin xanh có độ nhám, óng ánh (Sheen) chân thực.
- Thiết lập trường quay và ánh sáng 3 điểm (Key, Fill, Rim Light) làm nổi bật khối cơ thể, rãnh ngực, cơ chân và nếp gấp trang phục.
- Xuất đầy đủ các định dạng chuẩn: `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx` kèm bộ ảnh render chất lượng cao (chính diện, góc 3/4, toàn thân).

## Acceptance Criteria

### Giải Phẫu & Khung Xương
- [ ] Bàn chân hiển thị đầy đủ 5 ngón chân riêng biệt, có móng chân, mắt cá trong/ngoài và vòm bàn chân rõ ràng khi nhìn cận cảnh.
- [ ] Khung xương Rigify bám sát vị trí giải phẫu xương người thật; uốn cong khớp gối, cổ chân và ngón chân đạt chuyển động tự nhiên, không làm suy giảm thể tích lưới (no volume loss).
- [ ] Đường cong ngực, eo thắt đáy lưng ong và đường lượn hông hiển thị rõ ràng, mềm mại và thanh thoát.

### Trang Phục & Phụ Kiện
- [ ] Váy liền thân thể hiện nếp gấp vải hữu cơ tự nhiên như vải thật (linen/cotton trong ảnh `media_1788785935849.jpg`), không còn dạng nón xếp ly hình học cứng nhắc.
- [ ] Đai thắt lưng satin xanh băng và nơ ruy-băng ôm khít eo ngoài váy, 0% Z-fighting hoặc đốm xuyên thấu.
- [ ] Giày xăng-đan đế bệt có quai dây thanh mảnh, ôm đúng mu bàn chân và để lộ ngón chân.

### Kiểm Thử & Kết Xuất
- [ ] Toàn bộ unit tests trong `pytest tests/` đạt 100% pass.
- [ ] File `.blend`, `.glb`, `.fbx` mở trực tiếp trong Blender 4.5+ và hiển thị hoàn hảo ở chế độ Material / Cycles render.

## 2026-09-07T13:15:05Z

[USER GUIDANCE UPDATE]:
Người dùng đặc biệt yêu cầu nhấn mạnh và điêu khắc rõ nét các chi tiết giải phẫu cơ thể sau trong Milestone M1 & M2:
1. Nét ngực: Cúp ngực giọt nước mềm mại, rãnh ngực tự nhiên, độ dốc êm từ xương đòn xuống ngực.
2. Xương quai xanh: S-curve của xương đòn (clavicle) nổi rõ thanh tú dưới cổ và hõm ức (suprasternal notch).
3. Nét khớp chân tay:
   - Khớp gối: Xương bánh chè (patella) và hõm khớp hai bên gối rõ ràng.
   - Khớp khuỷu tay: Mỏm khuỷu (olecranon) và nếp gấp cùi chỏ tự nhiên.
   - Cổ chân & Cổ tay: Mắt cá chân trong/ngoài (medial/lateral malleoli) bất đối xứng tự nhiên, mỏm trâm xương quay/trụ ở cổ tay rõ nét.
4. Nét hàm & Cằm: Đường viền xương hàm dưới (mandible) thanh tú, cằm V-line sắc sảo, góc hàm dưới tai sắc nét phân tách rõ ràng với cổ.

Vui lòng ghi nhận các điểm giải phẫu này vào đặc tả và kiểm thử của Milestone M1 & M2.

## 2026-09-07T13:20:42Z

Nâng cấp hệ sinh thái MorphoMesh bằng việc xây dựng Động cơ Giải phẫu học Khung xương (Anatomical Skeletal Estimation & Biomechanical Auto-Rigging Engine) cho cả con người và động vật, đồng thời khắc phục triệt để 19 bài test failing trong bộ Master Production Deliverables của nhân vật Yu Nian An.

Working directory: e:\tool\mcp\MorphoMesh
Integrity mode: development

## Requirements

### R1. Khắc phục triệt để 19 bài test failing & Hoàn thiện Production Deliverables
Đồng bộ hóa lại quy trình lắp ráp và xuất file binary (`Yu_Nian_An.fbx`, `Yu_Nian_An.glb`, `Yu_Nian_An_Master.blend`) trong thư mục `output/yu_nian_an/`. Đảm bảo tất cả 163 DEF bones, 52 ARKit FACS morph targets (với chuyển dịch delta hợp lệ), cấu trúc UV map `TEXCOORD_0`, đặt tên mesh môi/mặt đồng nhất, và độ hở dây marionette đạt đầy đủ các điều kiện kiểm thử của dự án.

### R2. Động cơ Phân loại Dáng đi & Trích xuất Mốc Lồi Xương Giải phẫu
Xây dựng module `src/morphomesh/anatomy/` có khả năng tự động phân loại dáng đi cơ sinh học của sinh vật (Humanoid 2 chân, Plantigrade đi bằng bàn, Digitigrade đi bằng ngón, Unguligrade đi bằng móng guốc), tự động phát hiện các mốc lồi xương bề mặt (Bony Landmarks) và ước lượng chính xác tâm xoay tức thời của khớp (Instantaneous Center of Rotation - ICR).

### R3. Bộ giải Trục xoay Xương (Bone Roll) & Pre-Bend Cơ sinh học
Cung cấp thuật toán tính toán vector pháp tuyến mặt phẳng gập bản lề sinh học $\vec{n}_{\text{hinge}}$, tự động mớm góc gập tự nhiên (pre-bend) cho các khớp 1 bậc tự do (khuỷu tay, đầu gối, cổ chân thú), và chuẩn hóa trục roll của xương để triệt tiêu hoàn toàn hiện tượng xoắn vặn (candy-wrapper collapse) và lật ngược Pole Target trong Rigify và game engines.

### R4. Thuật toán Gán trọng số Da Y sinh (Biharmonic Skinning)
Thay thế cơ chế mock skinning và fallback dồn trọng số vào xương sống bằng bộ giải trọng số da phân tán thể tích (Geodesic Voxel Biharmonic Diffusion), ngăn chặn hiện tượng "weight stealing" giữa nách-ngực và hai đùi.

### R5. Tích hợp & Kiểm chứng Tự động
Tạo bộ kiểm thử đơn vị toàn diện tại `tests/test_anatomy.py` để kiểm tra độ chính xác của các thuật toán phân loại dáng đi, tính toán mốc xương và bone roll; đồng thời đảm bảo toàn bộ test suite của MorphoMesh chạy qua lệnh `uv run pytest` đạt 100% kết quả PASS.

## Acceptance Criteria

### Test Suite Integrity
- [ ] Lệnh `uv run pytest -q` hoàn thành với **0 tests FAILED** (toàn bộ 1681+ tests đều PASSED).
- [ ] Cả 11 bài test Master Assembler (bao gồm `test_adversarial_character_assembler.py` và `test_character_assembler.py`) đều PASSED.
- [ ] Cả 8 bài test Production Exports (bao gồm `test_production_exports.py` và `test_challenger_m5_empirical.py`) đều PASSED.

### Production Binary Assets
- [ ] `output/yu_nian_an/Yu_Nian_An.fbx` chứa đầy đủ 163 DEF bones và dữ liệu animation/bind pose chuẩn.
- [ ] `output/yu_nian_an/Yu_Nian_An.glb` chứa đầy đủ 52 ARKit FACS blendshapes trong `extras.targetNames` và tất cả mesh primitives đều có thuộc tính `TEXCOORD_0`.
- [ ] `output/yu_nian_an/Yu_Nian_An_Master.blend` có đầy đủ 52 shape keys với delta di chuyển chuẩn xác và các dây rối marionette snap khít với xương ngón tay.

### Anatomical Engine Package
- [ ] Package `src/morphomesh/anatomy/` được khởi tạo hoàn chỉnh, có `__init__.py` export đầy đủ các interface chính: `classify_locomotor_stance`, `compute_bony_landmarks`, `solve_biomechanical_bone_roll`, và `compute_geodesic_skin_weights`.
- [ ] File `tests/test_anatomy.py` kiểm chứng thành công các ca thử nghiệm cho cả người và 3 dáng đi động vật (Plantigrade, Digitigrade, Unguligrade).
- [ ] Headless creature rig trong `src/morphomesh/blender_bridge.py` và `animals3d_connector.py` được kết nối hoặc cập nhật để không còn trả về trọng số da rác hay tọa độ tĩnh không khớp mesh.

## 2026-09-07T17:26:57Z

# Teamwork Project Prompt

Nâng cấp MorphoMesh thành hệ thống tạo dựng khuôn cơ thể người nữ chuẩn giải phẫu y khoa (Anatomical Female Human Base Mold / Digital Human Engine) dựa trên template base mesh chuẩn nhân trắc học (MakeHuman/CC0), tái tạo hoàn hảo đường nét ngực giọt nước, vòng mông nở nang, đường lượn eo hông, bờ vai và tay chân mềm mại tự nhiên; sau đó ứng dụng khuôn mẫu này cùng công nghệ mô phỏng vật lý vải (Cloth Simulation) để tạo mô hình 3D nhân vật Dư Niệm An (余念安) hoàn mỹ bám sát tuyệt đối concept gốc.

Working directory: E:\tool\mcp\MorphoMesh
Integrity mode: development
Reference Images:
- Concept Sheet: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg
- User Feedback Screenshots (Lỗi giải phẫu cần khắc phục triệt để):
  - Tay và vai bị dị dạng / góc cạnh: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788701589498.png
  - Váy xếp ly nón cứng đơ dạng chụp đèn: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788801618516.png
- Realistic Dress Drapery & Flat Sandals Reference: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935849.jpg
- Skeletal Anatomy Reference: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935854.png

## Requirements

### R1. Khuôn Cơ Thể Người Nữ Chuẩn Giải Phẫu Nhân Trắc Học (Anatomical Female Base Mold)
- Tích hợp template base mesh nữ chuẩn giải phẫu (MakeHuman/CC0) làm khuôn mẫu gốc (Base Mold) cho MorphoMesh (`src/morphomesh/human_generator.py`), loại bỏ hoàn toàn việc cắt vá vụn vặt từ model mặc áo:
  - **Ngực chân thực (Teardrop Volumetric Bust)**: Cúp ngực dáng giọt nước tự nhiên có độ võng trọng lực sinh học, rãnh ngực (cleavage valley) mềm mại và nếp gấp dưới ngực (inframammary fold) rõ nét, thể tích đầy đặn mềm mại.
  - **Mông & Đường lượn hông (Gluteal & Hip Curves)**: Vòng 3 nở nang tròn đầy tự nhiên, độ cong cột sống thắt lưng (lumbar lordosis) thanh thoát, tỷ lệ eo/hông chuẩn nhân trắc học nữ tính (~0.70).
  - **Cốt thế bờ vai & Tay chân mềm mại**: Triệt tiêu 100% hiện tượng tay bị gãy góc/co quắp và vai bị nhọn góc ở ảnh `media_1788801589498.png`. Bờ vai có độ dốc cơ thang thoai thoải thanh mảnh, cánh tay trần buông xuôi thư thái tự nhiên.
  - **Bàn chân 5 ngón & Bàn tay**: 5 ngón chân phân tách rõ ràng có móng và vòm bàn chân nâng cao; bàn tay mảnh mai thanh nhã.

### R2. Váy Liền Thân Mô Phỏng Vật Lý Vải Tự Nhiên (Cloth Simulation One-Piece Sundress)
- Tái tạo váy liền thân (one-piece sundress) áp trực tiếp lên khuôn cơ thể, xóa bỏ hoàn toàn dạng nón xếp ly cơ học ở ảnh `media_1788801618516.png`:
  - Ứng dụng mô phỏng vật lý vải (Blender Cloth Simulation) kết hợp trọng lực (Gravity) và lực căng bề mặt (Tension/Shear) để sinh ra nếp gấp vải hữu cơ tự nhiên buông rủ êm dịu từ eo xuống dưới đầu gối.
  - Thân trên (bodice) ôm vừa vặn cúp ngực giọt nước với cổ áo sweetheart scoop và 2 quai áo spaghetti mảnh mai ôm sát bờ vai.
  - Đai eo satin xanh băng ôm khít vòng eo với nút thắt nơ và dải ruy-băng rủ mềm mại theo tùng váy, triệt tiêu 100% hiện tượng Z-fighting.

### R3. Áp Khuôn Vào Tạo Mô Hình 3D Dư Niệm An Hoàn Mỹ
- Hoàn thiện mô hình nhân vật Dư Niệm An theo phong cách bán thực tế (Semi-Realistic):
  - Khuôn mặt thanh tú, ánh mắt xanh biếc u buồn tĩnh lặng bám sát tuyệt đối concept gốc `media_1788716034772.jpg`.
  - Mái tóc đen dài Hime Cut bóng mượt buông xõa phía sau lưng ôm nhẹ theo sống lưng.
  - Giày xăng-đan quai da đế bệt ôm sát lòng bàn chân, để lộ trọn vẹn 10 ngón chân.
  - 10 sợi tơ đỏ ma thuật gắn chuẩn xác vào các ngón tay điều khiển 10 cánh bướm trắng phát sáng lơ lửng xung quanh.
  - Gắn khung xương Rigify Metarig 163 xương DEF với trục xoay sinh học, bảo toàn thể tích cơ bắp khi co gập cử động.

### R4. Kiểm Thử Khắt Khe, Shader Cycles SSS & Xuất Bản File Chuẩn
- Bộ kiểm thử tự động xác thực: 0% mắt lưới đâm xuyên (0 penetrations), 100% pháp tuyến hướng ra ngoài, 100% quads ở các khớp cử động.
- Vật liệu da Random Walk SSS ấm áp, vải lụa trắng óng ánh Sheen và mắt có chiều sâu khúc xạ.
- Xuất đầy bộ file sản phẩm: `Yu_Nian_An_Master.blend`, `Yu_Nian_An.glb`, `Yu_Nian_An.fbx` kèm bộ ảnh render đa góc nhìn chuẩn điện ảnh Cycles AgX.

## Acceptance Criteria

### Khuôn Cơ Thể & Giải Phẫu (Anatomical Mold)
- [ ] Khuôn ngực có thể tích giọt nước rõ ràng, rãnh ngực sâu tự nhiên, không phẳng dẹt như bìa cứng.
- [ ] Vòng mông nở nang tròn đầy, độ cong cột sống và lượn hông chuẩn nhân trắc học nữ tính.
- [ ] Bờ vai dốc tự nhiên, cánh tay buông xuôi mềm mại, triệt tiêu 100% các góc nhọn hay vết gãy dị dạng ở khuỷu/nách.
- [ ] Bàn chân hiển thị rõ ràng 5 ngón phân tách riêng biệt, có móng chân và vòm chân.

### Váy Liền Thân & Phụ Kiện (Dress & Accessories)
- [ ] Váy liền thân ôm cúp ngực và xòe rủ mềm mại với nếp gấp vải mô phỏng vật lý chân thực, xóa bỏ hoàn toàn nếp gấp nón xếp ly dạng chụp đèn.
- [ ] Đai eo satin xanh ôm sát eo, không lơ lửng và không có Z-fighting.
- [ ] Dép quai da đế bệt ôm sát lòng bàn chân và để lộ toàn bộ 10 ngón chân.
- [ ] 10 sợi tơ đỏ gắn chuẩn xác vào các đầu ngón tay điều khiển đàn bướm phát quang.

### Kiểm Thử & Tệp Xuất Bản (Verification & Delivery)
- [ ] Toàn bộ unit tests và empirical tests trong repository đạt 100% pass.
- [ ] File `.blend`, `.glb`, `.fbx` hiển thị hoàn mỹ khi mở trực tiếp trong Blender 4.5+.
- [ ] Bộ ảnh kết xuất đa góc nhìn (chính diện, 3/4, góc ngang, sau lưng, cận cảnh) thể hiện rõ ràng độ mềm mại của cơ thể và trang phục.

## 2026-09-08T16:06:11Z

Nâng cấp và hoàn thiện toàn diện dự án MorphoMesh (AI 3D Digital Content Creation Pipeline & Blender FastMCP Server) thành hệ thống hoàn chỉnh đạt chuẩn Production: tích hợp đầy đủ bộ công cụ FastMCP Inspection & Visual QA, hoàn tất các Milestones M4-M5, kiểm định toàn diện End-to-End Scene Inspection và bảo đảm 100% bộ kiểm thử tự động đạt kết quả pass không có lỗi hồi quy.

Working directory: E:\tool\mcp\MorphoMesh
Integrity mode: development

## Requirements

### R1. Tích hợp trọn bộ công cụ FastMCP & Tương thích ngược (FastMCP Tools Integration & Compatibility)
Đảm bảo máy chủ FastMCP công khai và hỗ trợ đầy đủ cả 3 nhóm công cụ: Creature Pipeline (7 công cụ), Human & Wardrobe Generation (7 công cụ), và Inspection & Visual QA (3 công cụ: `morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, `morphomesh_critique_visual_quality`). Cơ chế gating biến môi trường (`MORPHOMESH_INCLUDE_INSPECTION_TOOLS`, `MORPHOMESH_INCLUDE_HUMAN_TOOLS`, `MORPHOMESH_INCLUDE_ALL_TOOLS`) hoạt động chuẩn xác, bảo toàn tương thích ngược tuyệt đối với các schema client hiện có.

### R2. Động cơ phân tích lỗi thị giác và kiểm định tự động (Closed-Loop Visual Critic & Automated QA)
Hệ thống Visual Critic tự động phát hiện và phân loại chính xác các khiếm khuyết hình học: đâm xuyên lưới (mesh penetration / clipping), vi phạm tỷ lệ nhân trắc học (anthropometric proportions), nếp gấp gãy nhọn hoặc sụt giảm thể tích khi biến dạng khớp xương (rigging/skinning pinch & volume collapse), và va chạm sợi tóc/lông (grooming curves collision). Xuất ra báo cáo chẩn đoán có cấu trúc Pydantic v2 chuẩn (`VisualCritiqueOutput`) với danh sách khuyến nghị khắc phục cụ thể và điểm chất lượng tổng thể.

### R3. Hệ thống Camera Inspector đa góc nhìn & Chụp Viewport tốc độ cao (Multi-Angle Inspector & Fast Viewport Capture)
Cung cấp khả năng tự động tính toán bounding box phân cấp, định vị 5 tâm vùng giải phẫu (toàn thân, đầu, thân, bàn tay, bàn chân) và khoảng cách đặt camera tối ưu. Hỗ trợ 6 góc nhìn chuẩn (Front, Side, Back, 3/4, Head closeup, Hands closeup) cùng quỹ đạo xoay turntable 360 độ, kết xuất nhanh qua chế độ grab OpenGL tương tác (<200ms) hoặc chế độ nền headless Workbench / Cycles.

### R4. Kiểm định thực tế End-to-End, Khắc phục lỗi và Đạt chuẩn 100% Test Pass (E2E Hardening & Production Verification)
Thực thi kiểm định toàn diện trên scene nhân vật hoàn chỉnh (như Dư Niệm An và Armored War Bear), tạo đầy đủ các bộ ảnh preview chẩn đoán và file xuất bản (`.blend`, `.glb`, `.fbx`). Giải quyết triệt để mọi lỗi tiềm ẩn trong quá trình giao tiếp socket IPC (`listener.py` ↔ `blender_bridge.py`), xử lý ngoại lệ an toàn và bảo đảm 100% các bài test trong toàn bộ test suite chạy thành công.

## Acceptance Criteria

### FastMCP Server & Compatibility
- [ ] FastMCP Server khởi động chuẩn xác, nạp và phản hồi đúng schema của cả 17 công cụ khi bật `MORPHOMESH_INCLUDE_ALL_TOOLS=1`, đồng thời giữ nguyên schema 7 công cụ chuẩn khi chạy ở chế độ mặc định.
- [ ] Công cụ `morphomesh_setup_inspector_camera_rig`, `morphomesh_capture_viewport`, và `morphomesh_critique_visual_quality` phản hồi đúng cấu trúc JSON/Pydantic chuẩn và tạo ảnh xem trước hợp lệ.

### Visual Critic & Quality Diagnostics
- [ ] Thuật toán phát hiện lỗi Visual Critic đạt độ chính xác >95% trên các bài kiểm tra chẩn đoán lỗi giải phẫu, đâm xuyên lưới và teo cơ khớp xoay.
- [ ] Báo cáo xuất ra chứa đầy đủ danh mục khiếm khuyết (`defects`), mức độ nghiêm trọng (`severity`), khuyến nghị sửa chữa (`actionable_recommendations`) và điểm số chất lượng (`quality_score`).

### Camera Rig & Viewport Capture
- [ ] Camera Inspector tự động căn khung chuẩn xác theo tỷ lệ góc nhìn (FOV) và kích thước đối tượng cho cả 6 góc nhìn chuẩn và 5 vùng giải phẫu.
- [ ] Hỗ trợ chụp viewport cả ở chế độ tương tác OpenGL và chế độ headless Workbench fallback khi Blender chạy không có màn hình hiển thị.

### End-to-End Verification & Test Suite Pass
- [ ] Toàn bộ các test cases trong repository (`pytest -v tests/`) chạy thành công 100% không có lỗi hay failure nào.
- [ ] Kịch bản kiểm thử tích hợp E2E thực thi trơn tru trên scene Blender thực tế hoặc headless session, xuất ra bộ ảnh preview đa góc nhìn tại thư mục `artifacts/` hoặc `output/`.
- [ ] Tài liệu `PROJECT.md` và `README.md` được cập nhật đồng bộ, phản ánh đầy đủ trạng thái hoàn tất của Milestones M4 và M5.

## 2026-09-09T04:28:41Z

Re-architect and modularize the MorphoMesh project (3D digital content creation pipeline & Blender MCP server) for long-term maintainability, extensibility, and performance, while preserving 100% backward compatibility for all MCP tools and public APIs, and producing a complete, production-grade documentation suite.

Working directory: e:\tool\mcp\MorphoMesh
Integrity mode: development

## Requirements

### R1. Modularize Core Subsystems & Preserve Backward Compatibility
- Decompose monolithic source files (>50KB, such as `blender_bridge.py`, `character_assembler.py`, `visual_critic.py`, `wardrobe.py`, `human_rigging.py`, `server.py`) into cohesive, modular packages/submodules with clear domain boundaries and single responsibilities.
- Preserve 100% backward compatibility for all external callers, including FastMCP tool signatures, socket RPC communication protocol with Blender, and public exports via `__init__.py`.

### R2. Code Quality, Typing, and Performance Optimization
- Apply comprehensive Python type hints (PEP 484) and Pydantic v2 schemas across all modularized components.
- Eliminate code duplication, dead code, circular dependencies, and performance bottlenecks in geometry math and bridge serialization.
- Maintain a completely green test suite across all existing test files in `tests/` without any regression.

### R3. Comprehensive Technical Documentation Suite
- Update and complete the full documentation set:
  - System architecture document with Mermaid diagrams illustrating subsystem boundaries, IPC socket bridge flow, and data pipelines (`docs/ARCHITECTURE.md`).
  - Comprehensive FastMCP specification detailing all tools, parameters, schemas, and error codes (`docs/MCP_SPECIFICATION.md`).
  - Contributor and Developer guide covering environment setup, extension patterns, and test execution (`docs/DEVELOPER_GUIDE.md`).
  - Clear and updated root `README.md` with quickstart, CLI usage, architecture overview, and project layout.
- Ensure all public classes, methods, and functions have standard docstrings (Google or Sphinx style) describing parameters, returns, and exceptions.

## Verification Resources
- Test suite runner: `pytest` (using configuration defined in `pyproject.toml`)
- MCP server import verification: `python -c "import morphomesh; from morphomesh.server import mcp; print(mcp)"`
- Package build verification: `python -m build --sdist --wheel` or `pip install -e .`

## Acceptance Criteria

### Test & Regression Invariance
- [ ] `pytest` passes with 0 failures on all existing and new unit/integration tests.
- [ ] FastMCP tools (`server.py`) remain fully functional with identical tool signatures and behavioral contracts.
- [ ] Blender socket bridge communication protocol (NDJSON framing and RPC dispatch) functions without regression.

### Modular Architecture
- [ ] Monolithic files exceeding 50KB in `src/morphomesh/` are refactored into structured sub-packages with clean separation of concerns.
- [ ] Zero circular imports across any modules within `src/morphomesh/`.
- [ ] Top-level imports (`from morphomesh import ...`) continue to resolve as expected via clean `__init__.py` re-exports.

### Complete Documentation
- [ ] `docs/ARCHITECTURE.md` exists and contains up-to-date system component diagrams and pipeline flows in Mermaid format.
- [ ] `docs/MCP_SPECIFICATION.md` documents all exposed MCP tools, input schemas, and return formats.
- [ ] `docs/DEVELOPER_GUIDE.md` details how to develop, test, and add new procedural assets or bridge commands.
- [ ] `README.md` is updated with accurate project structure, setup instructions, and usage examples.
- [ ] 100% of newly structured public modules, classes, and methods have valid docstrings and type annotations.

## 2026-09-09T14:44:57Z

Xây dựng hệ thống pipeline tự động tạo nhân vật 3D Anime Girl chất lượng cao đạt chuẩn Game-Ready/VTuber, trang bị hệ thống khung xương (Rigging) chuyên dụng cho Anime giải quyết triệt để lỗi biến dạng khớp/cổ tay/váy, tích hợp chuyển động mượt mà và render video anime cinematic.

Working directory: E:\tool\mcp\MorphoMesh\teamwork_projects\anime_character_pipeline
Integrity mode: development

## Requirements

### R1. Bộ công cụ tạo hình & Tái tạo 3D Anime Mesh chuẩn giải phẫu
Hệ thống phải tiếp nhận mô tả nhân vật hoặc concept 2D và tái tạo mô hình lưới 3D có cấu trúc topo chuẩn giải phẫu anime: đầu, thân, hai tay, hai chân tách rời độc lập, hình dạng tóc và váy riêng biệt (không dính liền các chi), lưới sạch phù hợp cho biến dạng da (skinning).

### R2. Hệ thống Anime Auto-Rigging & Khắc phục biến dạng khớp/váy/tóc
Trang bị khung xương chuyên dụng cho nhân vật Anime (chuẩn Humanoid/VRM/MMD/Rigify) với đầy đủ cấu trúc:
- Hệ thống xương tay hoàn chỉnh (vai, cánh tay, cẳng tay, xương chống xoắn twist bones, cổ tay và từng ngón tay riêng biệt).
- Hệ thống xương chân & bàn chân có khớp cổ chân và ngón chân tiếp đất tự nhiên.
- Hệ thống xương động (Spring bones / Secondary bones) cho tóc (twintails) và tà váy xếp ly, ngăn chặn hiện tượng váy bị chân kéo rách hoặc tóc đơ cứng khi nghiêng đầu.
- Trọng số da (Skin weights) mượt mà, áp dụng Dual Quaternion Skinning (Preserve Volume) để loại bỏ hoàn toàn hiện tượng bẹp cổ tay, gãy gập khuỷu tay và xẹp cơ thể.

### R3. Hệ thống Animation & Retargeting cử động mượt mà
Tích hợp thư viện cử động tự nhiên phù hợp với tỷ lệ nhân vật anime (không dùng mocap thô của người thật gây vặn vẹo cơ thể), hỗ trợ retargeting cử động mượt mà (vẫy tay chào, nhảy, đi bộ, tạo dáng đáng yêu) mà các khớp không bị xoắn gãy.

### R4. Hệ thống Toon Shading & Render Video Điện ảnh trong Blender 4.5
Thiết lập bộ shader Cel-Shading/Toon Shader chuẩn phong cách hoạt hình Nhật Bản (da matte mịn, không bóng dầu nhựa, viền outline thanh mảnh, đổ bóng phân tầng anime). Tự động thiết lập camera điện ảnh và xuất video Full HD MP4 hoàn hảo.

## Verification Resources & Mechanisms
- Script kiểm tra chất lượng khung xương tự động: xác nhận có đầy đủ các xương ngón tay, cổ tay, tóc và váy.
- Script đo lường biến dạng lưới: kiểm tra độ bảo toàn thể tích của tay/váy qua các frame cử động, phát hiện và cảnh báo nếu có hiện tượng xé lưới (vertex stretching threshold).
- Kiểm tra render tự động: chạy Blender headless xuất video MP4 và ảnh snapshot kiểm tra chất lượng hình ảnh cel-shading.

## Acceptance Criteria

### Mesh & Rigging Quality
- [ ] Model 3D anime có đầy đủ các bộ phận riêng biệt (không dính tay áo vào váy hoặc thân).
- [ ] Khung xương hỗ trợ đầy đủ xương ngón tay linh hoạt, xương cổ tay có cơ chế chống vặn xoắn (twist bones).
- [ ] Váy và tóc có cơ chế kiểm soát riêng (xương phụ / spring bones / physics), váy không bị chân kéo rách khi chân bước hoặc lắc hông.
- [ ] Không có hiện tượng gãy gập cổ tay dị dạng, bẹp đế giày hoặc xẹp thể tích vai khi chuyển động.

### Shading & Rendering
- [ ] Chất liệu hiển thị chuẩn Anime Toon Shading (da mịn matte, màu sắc tươi sáng, không bị bóng dầu trắng búp bê nhựa).
- [ ] Xuất ra video Full HD MP4 mượt mà (tối thiểu 30 FPS) thể hiện trọn vẹn hoạt ảnh tự nhiên, sinh động của nhân vật.
- [ ] Toàn bộ pipeline được đóng gói thành các script có thể tái sử dụng dễ dàng trong working directory.

## 2026-09-10T05:05:10Z

Build an end-to-end automated generation pipeline and high-fidelity 3D botanical asset library using Meshy AI Text-to-3D, producing 30+ diverse, unrigged plant species across major biomes with complete PBR materials and clean quad topology.

Working directory: E:/tool/mcp/MorphoMesh/teamwork_projects/vegetation_library
Integrity mode: development

## Requirements

### R1. Comprehensive Botanical Taxonomy & Catalog Specification
Define an extensive, structured botanical catalog covering at least 30 distinct plant species across >= 6 major categories:
1. Broadleaf & Deciduous Trees (e.g., Oak, Maple, Birch, Willow)
2. Conifers & Evergreens (e.g., Pine, Spruce, Cypress)
3. Tropical Foliage & Palms (e.g., Fan Palm, Monstera, Banana Plant, Fern Tree)
4. Flowering Shrubs & Ornamental Plants (e.g., Rose Bush, Hydrangea, Lavender)
5. Ferns, Grasses & Groundcover (e.g., Boston Fern, Tall Pampas Grass, Forest Moss clump)
6. Succulents & Cacti (e.g., Saguaro Cactus, Aloe Vera, Echeveria)
7. Climbing Vines & Epiphytes (e.g., English Ivy, Wisteria)
Each catalog item must specify scientific name, common name, morphological characteristics, and tuned botanical prompts (canopy shape, leaf clustering, trunk texture, floral accents).

### R2. Meshy AI Text-to-3D Botanical Generation Engine
Implement an automated generation harness leveraging Meshy AI Text-to-3D:
- Structured botanical prompt conditioning optimized for natural vegetation structure.
- Enable full 4-channel PBR material generation (Albedo/BaseColor, Normal map, Roughness map, and Metallic/Specular).
- Remesh to clean quad/triangle topology (target ~15,000 – 30,000 polygons per asset) optimized for real-time rendering.
- Explicitly enforce static mesh generation with ZERO skeletal armatures or rigging weights (plants do not require bones or skinning).
- Robust rate limiting, retry backoff, task polling, and offline deterministic fallback for headless or rate-limited environments.

### R3. Asset Post-Processing, Normalization & Multi-Format Export
Process and normalize all generated botanical models:
- Set object pivot/origin strictly at the ground contact base (Z=0 / Y=0 at root base).
- Normalize real-world metric scales (e.g., trees 4-12m, shrubs 1-2m, small plants 0.2-0.8m).
- Export production-ready GLB (glTF binary with embedded PBR textures) and companion OBJ/MTL formats.
- Organize assets into categorized directory hierarchies with metadata manifests (`manifest.json`).

### R4. Automated Quality Verification & Visual Showcase
Provide an automated inspection and validation suite:
- Programmatically verify geometry integrity (manifold faces, valid normals, zero NaN/Inf coordinates).
- Programmatically verify absence of bone armatures or skeletal data.
- Programmatically verify texture completeness (valid resolution, correct channel assignments).
- Generate multi-angle preview contact sheets and high-resolution thumbnail renders (isometric/turntable) for all 30+ species.

## Acceptance Criteria

### Botanical Catalog & Asset Scale
- [ ] Catalog manifest defines >= 30 distinct species across at least 6 botanical categories.
- [ ] All 30+ species are generated and exported in valid `.glb` format with accompanying metadata.

### Mesh & Geometry Standards
- [ ] Every exported model has pivot point located at the root/base ($Z_{min} \approx 0$ within tolerance).
- [ ] Every exported model contains ZERO armature bones, bone weights, or skinning structures.
- [ ] Geometry vertex count is between 3,000 and 45,000 vertices per asset with zero NaN/Inf coordinates.

### Material & Texture Fidelity
- [ ] Each asset includes valid PBR texture maps (BaseColor/Albedo, Normal, Roughness).
- [ ] PBR textures are verified to be readable images without corrupt data or solid black placeholders.

### Verification & Renders
- [ ] Programmatic test suite (`test_vegetation_pipeline.py` or verification script) passes 100% on all generated assets.
- [ ] Visual preview renders (PNG/JPG) exist for every plant model in the library.

## 2026-09-10T11:11:31Z

Rebuild the entire 3D botanical asset library using 100% genuine Meshy AI Text-to-3D cloud API generation, completely eliminating identical dummy geometry templates and procedural fallbacks, ensuring every plant species exhibits authentic, distinct botanical morphology, 30k-60k polygon detail, photorealistic 4-channel PBR materials, and clean unrigged static meshes.

Working directory: E:/tool/mcp/MorphoMesh/teamwork_projects/vegetation_library
Integrity mode: development

## Requirements

### R1. 100% Genuine Meshy AI Cloud Generation (Zero Procedural Dummy Blobs)
- All 3D plant assets MUST be generated via the live Meshy AI Text-to-3D API (using `MESHY_API_KEY` from `.env`).
- Strictly PROHIBIT the silent emission of identical geometric templates, primitive spheres/cylinders, or synthetic procedural fallback meshes.
- Implement robust queue polling with exponential backoff and rate-limit handling so the pipeline waits for real cloud completion instead of falling back to fake geometry.
- Record genuine Meshy cloud task provenance (`task_id`, `model_type`, `refine_status`) in each asset's manifest.

### R2. Distinct Species-Specific Botanical Morphology & Prompt Tuning
- Every species prompt must specify distinct, anatomically accurate morphological traits:
  * Fan Palm (`veg_trop_palm_01`): Slender ringed trunk with radiating fan-shaped pleated fronds.
  * Monstera (`veg_trop_monstera_01`): Wide fenestrated perforated split leaves with long climbing petioles.
  * Banana Plant (`veg_trop_banana_01`): Huge broad oblong arching paddle leaves on a thick layered pseudostem.
  * Tree Fern (`veg_trop_treefern_01`): Slender fibrous upright trunk topped by an umbrella crown of bipinnate lace-like fronds.
  * Bird of Paradise (`veg_trop_birdofparadise_01`): Clump of erect paddle-shaped leaves with iconic crane-like orange and blue floral spikes.
  * Saguaro (`veg_succ_saguaro_01`): Fluted columnar ribbed succulent with upright candelabra branches and needle aeroles.
  * Scots Pine (`veg_conifer_pine_01`): Straight reddish-brown bark trunk with conical spreading whorls of needle-leaf foliage.
  * English Oak (`veg_tree_oak_01`): Gnarled spreading trunk with sprawling boughs and dense lobed foliage masses.
- Strictly enforce visual and topological divergence: no two species may share identical vertex counts or identical mesh topology.

### R3. High-Fidelity Geometry & Material Standards
- Mesh detail target: 20,000 to 60,000 polygons per asset (quad/triangle optimized).
- Material workflow: Full 4-channel PBR (Albedo/BaseColor, Normal, Roughness, Metallic) with double-sided foliage rendering.
- Static mesh invariant: Strictly zero armature bones, skeletons, joints, or skinning weights ($N_{\text{bones}} = 0$).
- Ground pivot snapping: Object origin set precisely at base contact point ($Z_{\min} = 0.000\text{m}$, base centered at $X=0, Y=0$).

### R4. Asset Normalization, Re-Rendering & Viewer Synchronization
- Post-process and normalize all downloaded Meshy GLB assets to real-world botanical metric scales.
- Re-render high-resolution 4-angle turntable previews (`turntable_01.png` - `04.png`) and contact sheets (`thumbnail.png`) using Headless Blender.
- Update master manifest `manifest.json` with genuine Meshy cloud provenance and updated face/vertex metrics.
- Synchronize interactive `viewer.html` so all cards display the genuine AI-generated models and distinct renders.

## Acceptance Criteria

### Meshy Cloud Provenance & Zero Dummy Geometry
- [ ] Every asset in the library has a verifiable Meshy AI task ID and remote model URL in its metadata.
- [ ] Strictly 0% procedural placeholder geometry or identical clone templates across different species.
- [ ] Pairwise vertex count collision between distinct species is less than 5%.

### Morphological Authenticity & Detail Bar
- [ ] Distinct botanical shapes verified across species (e.g., Monstera exhibits split leaves, Palm exhibits fronds, Banana exhibits paddle leaves, Saguaro exhibits ribbed columns).
- [ ] Average mesh detail is between 20,000 and 60,000 faces per asset.
- [ ] All assets have 4 valid PBR texture maps (Albedo, Normal, Roughness, Metallic).

### Static Mesh Invariants & Grounding
- [ ] Every asset has $N_{\text{bones}} = 0$ (verified static mesh, no armatures).
- [ ] Every asset has ground contact at $Z_{\min} = 0.000\text{m} \pm 0.005\text{m}$.

### Visual Showcase & Viewer Synchronization
- [ ] 4-angle turntable renders and contact sheets updated for all assets with genuine Meshy renders.
- [ ] `viewer.html` updated with distinct thumbnail renders and metadata for every species.
- [ ] Automated verification test suite passes 100%.
