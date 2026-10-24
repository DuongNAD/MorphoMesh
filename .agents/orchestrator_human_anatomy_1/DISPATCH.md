## 2026-09-07T13:02:41Z
You are the Project Orchestrator for MorphoMesh.

Your working directory is:
E:\tool\mcp\MorphoMesh\.agents\orchestrator_human_anatomy_1

Your task is defined by the latest user request in:
E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md (under timestamp ## 2026-09-07T13:01:03Z)

Working Directory / Project Root: E:\tool\mcp\MorphoMesh
Integrity mode: development

User Reference Images:
- Concept Sheet: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788716034772.jpg
- Skeletal Anatomy: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935854.png
- Realistic Dress Drapery & Flat Sandals: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935849.jpg
- Fashion Silhouette & Cloth Folds: C:/Users/Admin/.gemini/antigravity/brain/df2fd097-8a99-4a14-8a06-9aa137171d4e/.user_uploaded/media_1788785935824.jpg

Requested specialized team composition:
- Chuyên gia Giải phẫu & Khung xương chuẩn y khoa (Rigging DEF)
- Chuyên gia Điêu khắc & Nếp gấp vải hữu cơ (Cloth Drapery)
- Chuyên gia Chi tiết Cơ thể & Vật liệu PBR Cycles

Core Requirements:
- R1. Tái Cấu Trúc Giải Phẫu Cơ Thể & Khung Xương Chuẩn Y Khoa (Anatomical Human Rig):
  * Xây dựng mô hình giải phẫu cơ thể người nữ hoàn chỉnh, thanh thoát dựa trên tài liệu xương y khoa tham chiếu (media_1788785935854.png): xương đòn (clavicle), hõm ức, khung lồng ngực, góc xương chậu, khớp đầu gối xương bánh chè và mắt cá chân rõ nét.
  * Điêu khắc bàn chân giải phẫu chân thực với 5 ngón chân phân tách rõ ràng (ngón cái, ngón trỏ, ngón giữa, ngón áp út, ngón út), móng chân tinh tế, độ cong mu bàn chân và mắt cá chân (trong/ngoài) sắc sảo.
  * Thiết lập khung xương Rigify DEF tiêu chuẩn công nghiệp với hệ thống trục xoay bám đúng cấu trúc giải phẫu sinh học (biological joint pivots), trọng số da (vertex weighting / skinning) mượt mà để các chuyển động uốn gập đùi, gối, cổ chân và ngón chân giữ nguyên thể tích cơ bắp tự nhiên, không bị biến dạng hay bẹp dẹp.
- R2. Thiết Kế Váy Liền Thân Hữu Cơ Với Nếp Gấp Và Độ Rủ Vải Chân Thực (Realistic Organic Dress):
  * Tái thiết kế váy thành dạng váy liền thân cao cấp dựa trên tham chiếu đời thực và minh họa thời trang (media_1788785935849.jpg & media_1788785935824.jpg): loại bỏ hoàn toàn các nếp gấp nón cơ học cứng nhắc, thay bằng các nếp gấp vải hữu cơ tự nhiên (gravity folds, tension lines từ ngực và eo, nếp gấp mềm mại rủ xuống ngang gối).
  * Phần thân trên ôm sát cơ thể với cúp ngực tự nhiên (teardrop profile), rãnh ngực thanh thoát, cổ áo sweetheart scoop và dây áo spaghetti mảnh mai tự nhiên qua vai.
  * Đai thắt lưng satin xanh băng (ice-blue sash) ôm khít 100% bên ngoài eo váy kèm nút thắt nơ và dải ruy-băng rủ tự nhiên, triệt tiêu hoàn toàn hiện tượng Z-fighting hay đốm xuyên thấu.
- R3. Giày Xăng-Đan Đế Bệt & Đạo Cụ Đặc Trưng:
  * Dựng mô hình giày xăng-đan nữ đế bệt (flat strappy sandals) theo ảnh thực tế media_1788785935849.jpg: đế mỏng ôm sát theo đường cong bàn chân, hệ thống quai da/vải ngang mu bàn chân và quai ôm cổ chân thanh lịch, làm lộ rõ các ngón chân thon đẹp.
  * Hoàn thiện hệ thống phụ kiện theo concept gốc: 10 sợi chỉ đỏ ma thuật nối từ các đầu ngón tay điều khiển đàn bướm trắng phát sáng lượn quanh nhân vật.
  * Mái tóc đen dài suôn mượt buông xõa phía sau lưng với mái bằng thanh tú bám sát concept gốc.
- R4. Shader PBR, Ánh Sáng Studio & Đóng Gói Xuất File Chuẩn:
  * Thiết lập hệ thống vật liệu PBR cao cấp: da Subsurface Scattering (Random Walk SSS) ấm áp, vải lụa trắng và satin xanh có độ nhám, óng ánh (Sheen) chân thực.
  * Thiết lập trường quay và ánh sáng 3 điểm (Key, Fill, Rim Light) làm nổi bật khối cơ thể, rãnh ngực, cơ chân và nếp gấp trang phục.
  * Xuất đầy đủ các định dạng chuẩn: Yu_Nian_An_Master.blend, Yu_Nian_An.glb, Yu_Nian_An.fbx kèm bộ ảnh render chất lượng cao (chính diện, góc 3/4, toàn thân).
  * 100% passing tests in pytest tests/.

## 2026-09-07T13:15:57Z
Sender: 61f2912d-f450-4bd9-bec3-739272828a07 (parent)
[USER GUIDANCE UPDATE]:
Người dùng đặc biệt yêu cầu nhấn mạnh và điêu khắc rõ nét các chi tiết giải phẫu cơ thể sau trong Milestone M1 & M2:
1. Nét ngực: Cúp ngực giọt nước mềm mại, rãnh ngực tự nhiên, độ dốc êm từ xương đòn xuống ngực.
2. Xương quai xanh: S-curve của xương đòn (clavicle) nổi rõ thanh tú dưới cổ và hõm ức (suprasternal notch).
3. Nét khớp chân tay:
   - Khớp gối: Xương bánh chè (patella) và hõm khớp hai bên gối rõ ràng.
   - Khớp khuỷu tay: Mỏm khuỷu (olecranon) và nếp gấp cùi chỏ tự nhiên.
   - Cổ chân & Cổ tay: Mắt cá chân trong/ngoài (medial/lateral malleoli) bất đối xứng tự nhiên, mỏm trâm xương quay/trụ ở cổ tay rõ nét.
4. Nét hàm & Cằm: Đường viền xương hàm dưới (mandible) thanh tú, cằm V-line sắc sảo, góc hàm dưới tai sắc nét phân tách rõ ràng với cổ.

This guidance has been recorded in ORIGINAL_REQUEST.md. Please incorporate these specific anatomical requirements into your PROJECT.md feature inventory, milestone worker briefs, and automated test assertions.
