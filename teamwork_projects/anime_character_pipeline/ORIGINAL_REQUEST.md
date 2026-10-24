# Original User Request

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
