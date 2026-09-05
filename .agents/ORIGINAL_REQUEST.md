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

