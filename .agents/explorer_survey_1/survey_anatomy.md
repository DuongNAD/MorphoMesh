# BÁO CÁO KHẢO SÁT CHUYÊN SÂU: HỆ THỐNG GIẢI PHẪU CƠ THỂ NGƯỜI VÀ KHUNG XƯƠNG HOẠT HỌA RIGIFY (R1 SURVEY)
**Mã phân nhiệm**: `explorer_survey_1` | **Dự án**: MorphoMesh  
**Thời gian lập**: 2026-09-07T13:06:00Z  
**Tài liệu thẩm quyền**: `E:\tool\mcp\MorphoMesh\ORIGINAL_REQUEST.md` (Phiên bản `2026-09-07T13:01:03Z`)  
**Tài liệu tham chiếu y khoa & hình ảnh**:
- Sơ đồ hệ xương giải phẫu y học: `media_1788785935854.png`
- Bảng vẽ thiết kế nhân vật Dư Niệm An (余念安): `media_1788716034772.jpg`
- Thời trang nếp gấp vải & Giày xăng-đan bệt: `media_1788785935849.jpg` & `media_1788785935824.jpg`

---

## TỔNG QUAN ĐIỀU HÀNH (EXECUTIVE SUMMARY)

Đợt nâng cấp Milestone R1 đòi hỏi hệ thống MorphoMesh chuyển dịch từ mô hình người bán thủ công đơn giản sang chuẩn giải phẫu cơ thể người thực tế (Photorealistic Digital Human Anatomy), tích hợp khung xương Rigify 163 DEF chuẩn công nghiệp bám sát vị trí xương thật, tái cấu trúc bàn chân chân thực với 5 ngón phân tách rõ ràng mang giày xăng-đan bệt, và giải quyết triệt để hiện tượng biến dạng, bẹp dẹp (mesh pinch / volume collapse) khi uốn gập đùi, gối, cổ chân và ngón chân.

Qua khảo sát toàn diện mã nguồn hiện hữu (`human_generator.py`, `human_rigging.py`) và đối chiếu với bản vẽ y khoa `media_1788785935854.png`, báo cáo này làm rõ:
1. **Hiện trạng hình học cơ thể**: Lưới cơ thể trong `human_generator.py` được xây dựng từ các lát cắt hình elip (rings of 24/16/14 sectors). Mặc dù đạt tỉ lệ quad cao (~96.5%), mô hình còn mang tính chắp vá từ các khối rời rạc (torso, upper/lower limbs, ellipsoidal palm, floating ellipsoidal toes), thiếu các mốc giải phẫu cốt lõi như xương đòn cong chữ S, hõm ức tam giác, gờ mào chậu nữ giới, khối xương bánh chè nhô tự nhiên và độ bất đối xứng của mắt cá trong/ngoài.
2. **Khuyết tật bàn chân hiện tại**: Bàn chân hiện hữu chỉ gồm 1 hình bầu dục gót (tarsus), 1 hình bầu dục ức bàn chân (metatarsus) và 5 quả cầu elip đơn lẻ xếp ngang. Không có phân đốt ngón (đốt gần, đốt giữa, đốt xa), không có móng chân, vòm bàn chân phẳng lì và không có khe kẽ tự nhiên để luồn quai giày xăng-đan.
3. **Hiện trạng khung xương Rigify 163 DEF**: Khung xương đã thiết lập đủ 163 xương DEF (64 xương thân + 99 xương mặt). Tuy nhiên, các trục xoay sinh học (biological joint pivots) hiện đặt tại tâm hình học đơn giản thay vì tâm xoay giải phẫu (như khớp háng đặt ngang đáy quần thay vì chỏm xương đùi, khớp gối chưa lùi về trục lồi cầu xương đùi, mắt cá chân nằm ngang thay vì chéo góc ~8° theo trục liên mắt cá).
4. **Chiến lược trọng số da (Vertex Weighting)**: Trọng số vùng mắt cá và bàn chân hiện dùng ngưỡng cứng `vy < -0.10`, gán toàn bộ 5 ngón chân vào duy nhất một xương `DEF-toe.L/R` mà không có phân vùng gradient giải phẫu, dễ gây dính ngón hoặc biến dạng khi gập bàn chân.

---

## PHẦN 1: KHẢO SÁT GIẢI PHẪU NỮ GIỚI TRONG `human_generator.py`

### 1.1. Bản Đồ 6 Mốc Giải Phẫu Cốt Lõi (Anatomical Landmarks Mapping)

Đối chiếu cấu trúc mã nguồn trong `human_generator.py` (dòng 269–398) với sơ đồ hệ xương `media_1788785935854.png`:

| Mốc Giải Phẫu | Thuật Ngữ Y Khoa | Tọa Độ & Cấu Trúc Hiện Tại Trong Code | Đánh Giá Độ Chuẩn Xác Giải Phẫu | Giải Pháp Tái Cấu Trúc Đề Xuất |
| :--- | :--- | :--- | :--- | :--- |
| **Xương đòn** | *Clavicula* (Clavicle) | Điểm mốc `clavicle_L` tại `(0.045*s, -0.015*s, 1.350*s)`, `shoulder_L` tại `(0.175*s, -0.020*s, 1.340*s)`. Lát cắt Z=1.350m là elip trơn `rx=0.165, ry=0.080`. | **Thiếu gờ xương nổi**: Bề mặt da phẳng lì, không có đường cong chữ S đặc trưng kéo từ chuôi ức ra mỏm cùng vai (acromion). | Bổ sung hàm biến dạng mặt trước (Z=1.320–1.355m): tạo gờ lồi nổi nhẹ ở mặt trước-trên và hõm dưới đòn (infraclavicular fossa). |
| **Hõm ức** | *Fossa suprasternalis* (Suprasternal notch / Jugular notch) | Điểm chuyển tiếp giữa cổ Z=1.370m và thân Z=1.350m; chỉ là đường elip tròn đơn giản, không có điểm lõm. | **Hoàn toàn biến mất**: Cổ và ngực nối liền như một khối trụ elip, thiếu hõm tam giác giữa hai đầu xương đòn và cơ ức - đòn - chũm. | Tại kinh độ $\theta \approx \frac{3\pi}{2}$ (chính diện trước, góc $270^\circ$), đưa độ lõm $\Delta y > 0$ (+0.008m vào trong) tại độ cao $Z \in [1.345, 1.370]\text{m}$. |
| **Khung lồng ngực** | *Cavea thoracis* (Ribcage & Costal Arch) | Lát cắt ngực Z=1.110–1.270m; ngực chỉ tăng bán kính `mod_y = ry * (1.0 + 0.35*(-sin_t - 0.3))` khi $\sin\theta < -0.3$. | **Dạng nón elip thô**: Chưa có rãnh giữa hai bầu ngực (sternal cleft), chân ngực (inframammary fold), góc hạ ức (infrasternal angle) và độ dốc xương sườn 10–12. | Điều chỉnh thiết diện ngực: tạo cúp ngực hình giọt nước (teardrop profile), rãnh ức thẳng đứng lõm nhẹ, mở rộng góc nghiêng vòm sườn về phía hông. |
| **Gờ mào chậu & Góc chậu** | *Crista iliaca* & *Spina iliaca anterior superior* (ASIS) | Lát cắt hông Z=0.825–0.900m với `rx=0.155–0.175, ry=0.110–0.120`. | **Dạng trụ tròn**: Xương chậu nữ giới thực tế có độ mở ngang rộng (subpubic angle $>90^\circ$, ASIS nhô rõ ra hai bên trước bụng dưới). | Tạo gờ mào chậu nhô nhẹ sang hai bên tại Z=0.890m, gờ ASIS nổi nhẹ ở góc trước-ngoài, tạo rãnh chữ V mềm mại nối xuống bẹn. |
| **Khớp gối & Xương bánh chè** | *Articulatio genus* & *Patella* | Lát cắt Z=0.420, 0.445, 0.470m với pre-bend $cy = -0.020\text{m}$. | **Ống trụ bẻ cong**: Không có khối nổi hình khiên của xương bánh chè, thiếu rãnh gân bánh chè và hai lồi cầu đùi (femoral condyles). | Tạo khối xương bánh chè dạng tam giác lồi ở mặt trước (Z=0.435–0.460m, $Y < -0.025\text{m}$), hai hố mỡ Hoffa hai bên và thắt lại ở gân bánh chè. |
| **Mắt cá chân (trong/ngoài)** | *Malleolus medialis* & *Malleolus lateralis* | Lát cắt Z=0.082–0.120m là hình tròn đối xứng `rx=0.030–0.032, ry=0.032–0.034`. | **Trụ tròn đối xứng sai y học**: Không có độ nhô của đầu dưới xương chày và xương mác. Mắt cá trong và ngoài hoàn toàn phẳng. | Bất đối xứng y khoa: Mắt cá trong (xương chày) nhô cao ($Z \approx 0.088\text{m}$) và dịch trước; Mắt cá ngoài (xương mác) nhô thấp ($Z \approx 0.076\text{m}$) và dịch sau. |

### 1.2. Phân Tích Topology Lưới và Tỉ Lệ Quads Hiện Tại

1. **Thuật toán tạo lưới hiện tại**:
   - Thân mình (torso): 23 lát cắt z-slice $\times$ 24 sectors = 528 quads.
   - Chóp đỉnh đầu và đáy đũng quần: sử dụng `add_quad_cap` đóng đáy bằng các dải quad thuần túy (pure quad strips), không sinh tam giác.
   - Hai chân: Mỗi chân gồm 12 lát cắt $\times$ 16 sectors = 176 quads, đóng 2 nắp quad.
   - Hai tay: Mỗi tay gồm 7 lát cắt $\times$ 14 sectors = 84 quads, đóng 2 nắp quad.
   - Bàn tay, ngón tay, bàn chân, ngón chân: sinh bằng hàm `add_quad_ellipsoid` (kết hợp các vòng vĩ độ quad-capped), 100% quads.
   - **Tỉ lệ quads thực tế**: Hàm `compute_quad_metrics` kiểm tra trên toàn bộ mesh đạt từ **96.0% đến 96.5% quads** (vượt yêu cầu $\ge 95\%$).
2. **Khuyết tật cấu trúc (Topology Bottlenecks)**:
   - **Lưới phân mảnh (Disconnected Geometry)**: Tay, chân, thân, ngón tay và ngón chân tuy nằm chung trong một đối tượng `MeshGeometry` nhưng là các **khối kín rời rạc** (separate manifold shells) lồng vào nhau, thay vì là một khối da liền mạch 2-manifold duy nhất.
   - **Mật độ đa giác ở các khớp deforming**: Khớp gối chỉ có 3 lát cắt z (0.470, 0.445, 0.420), khớp cổ chân chỉ có 2 lát cắt (0.120, 0.082). Khi uốn gập gối $90^\circ$ hoặc gập cổ chân $45^\circ$, mật độ 3 vòng dây cạnh (edge loops) là quá thưa, dễ gây hiện tượng gãy gập góc cạnh (faceted silhouette) thay vì đường cong hữu cơ tròn trịa.

---

## PHẦN 2: KHẢO SÁT HÌNH HỌC BÀN CHÂN & THIẾT KẾ 5 NGÓN CHÂN TỰ NHIÊN

### 2.1. Đánh Giá Hình Học Bàn Chân Hiện Tại

Trong `human_generator.py` (dòng 527–544):
```python
heel_center = (cx_ankle, 0.055 * s, 0.035 * s * k_leg)
tarsus_indices = add_quad_ellipsoid(mesh, heel_center, (0.032 * s, 0.045 * s, 0.025 * s * k_leg), rings=3, sectors=8)

ball_center = (cx_ankle, -0.065 * s, 0.020 * s * k_leg)
metatarsus_indices = add_quad_ellipsoid(mesh, ball_center, (0.038 * s, 0.055 * s, 0.018 * s * k_leg), rings=3, sectors=8)

for t_idx in range(5):
    t_offset_x = (t_idx - 2.0) * (0.015 * s * sign)
    toe_x = cx_ankle + t_offset_x
    toe_y = -0.135 * s - (0.010 * s if t_idx in (0, 1) else 0.0)
    toe_z = 0.012 * s * k_leg
    t_rad = 0.009 * s if t_idx == 0 else 0.007 * s
    toe_indices = add_quad_ellipsoid(mesh, (toe_x, toe_y, toe_z), (t_rad, 0.018 * s, t_rad * 0.9), rings=3, sectors=8)
```
**Nhận xét chuyên môn**:
- Bàn chân hiện tại chỉ là một tổ hợp các khối bầu dục trôi nổi (floating capsules), không hề có hình dáng giải phẫu của bàn chân người nữ.
- Mỗi ngón chân chỉ là 1 khối elip đơn độc 1 đốt, không phân biệt đốt gần, đốt giữa, đốt xa.
- Vị trí ngón chân được rải đều tuyến tính `(t_idx - 2.0) * 0.015*s`, khiến ngón cái và ngón út bị xếp phẳng lì trên cùng một mặt phẳng ngang, không phản ánh cung vòng bàn chân (transverse metatarsal arch).
- Hoàn toàn không có móng chân (toenails).
- Khi nhân vật mang giày xăng-đan bệt trong concept (`media_1788716034772.jpg` và `media_1788785935849.jpg`), bàn chân lộ 100% trước camera, khiến các khối elip thô thiển này làm phá vỡ hoàn toàn tính thẩm mỹ cao cấp của nhân vật Dư Niệm An.

### 2.2. Đặc Tả Điêu Khắc Bàn Chân Giải Phẫu Chuẩn Y Khoa

Dựa trên tài liệu hệ xương chân `media_1788785935854.png` (gồm khối xương cổ chân - tarsals, khối xương bàn chân - metatarsals, và các đốt ngón - phalanges):

```
                        [CỔ CHÂN / ANKLE MORTISE]
                       /                         \
         [Mắt cá trong: cao & trước]       [Mắt cá ngoài: thấp & sau]
                     |                               |
              [Xương sên / Talus]             [Xương gót / Calcaneus]
                     |                               |
           [Vòm dọc trong - CAO]           [Vòm dọc ngoài - THẤP]
                     \                               /
                [Khối xương bàn chân / Metatarsals 1-5]
           (Độ dốc mu bàn chân dạng vòm cong Transverse Arch)
                               |
               [Đường bẻ khớp MTP / Oblique Break Line] (~65°)
        /          |              |              |             \
   [Ngón Cái]  [Ngón Trỏ]     [Ngón Giữa]    [Ngón Áp Út]    [Ngón Út]
   (2 đốt)     (3 đốt)        (3 đốt)        (3 đốt)         (3 đốt)
   Móng to     Móng thon      Móng nhỏ       Móng nhỏ        Móng út
```

1. **Khối gót và Xương gót (Calcaneus & Heel Pad)**:
   - Gót chân mở rộng về phía sau ($Y \in [0.035, 0.075]\text{m}$), bo tròn phía dưới bằng mô đệm mỡ chịu lực (plantar fat pad).
   - Phía sau gót vuốt thon lên gân gót Achilles (*Tendo calcaneus*) với hai hõm mềm hai bên gân.
2. **Hệ thống 3 Vòm Bàn Chân (Triple Plantar Arches)**:
   - **Vòm dọc trong (Medial longitudinal arch)**: Chạy từ xương gót qua xương sên, xương ghe, các xương chêm đến chỏm xương bàn 1. Tạo độ cong lõm sâu ở bờ trong gan bàn chân (không chạm đất khi đứng thẳng, khoảng hở cách mặt sàn $10–14\text{mm}$).
   - **Vòm dọc ngoài (Lateral longitudinal arch)**: Chạy qua xương hộp và xương bàn 4–5. Thấp hơn nhiều, tiếp xúc nhẹ nhàng với mặt sàn tạo độ thăng bằng.
   - **Vòm ngang (Transverse arch)**: Nằm ở phần giữa bàn chân, tạo độ cong vồng trên mu bàn chân (instep) và dốc thoai thoải từ bờ trong sang bờ ngoài.
3. **Mắt Cá Chân Bất Đối Xứng (Asymmetric Malleoli)**:
   - Mắt cá trong (*Medial malleolus*): Thuộc xương chày, đỉnh nhô ở độ cao $Z = 0.086\text{m}$, vị trí dịch về phía trước ($Y = -0.002\text{m}$), dạng u tròn rộng.
   - Mắt cá ngoài (*Lateral malleolus*): Thuộc xương mác, đỉnh nhô ở độ cao $Z = 0.074\text{m}$ (thấp hơn mắt cá trong $12\text{mm}$), vị trí dịch về phía sau ($Y = 0.012\text{m}$), dạng mấu xương thon sắc hơn.
4. **Cấu Trúc 5 Ngón Chân Khớp Nối (5 Articulated Toes)**:
   - **Ngón cái (Hallux - Digit I)**: Gồm 2 đốt (đốt gần và đốt xa). Trục ngón thẳng hoặc hơi hướng nhẹ ra ngoài ($2–3^\circ$). Bán kính gốc $r \approx 8.5\text{mm}$, đệm thịt ngón (pulp) dày tròn.
   - **Ngón trỏ (Digit II)**: Gồm 3 đốt. Chiều dài xấp xỉ hoặc dài hơn ngón cái nhẹ ($1\text{mm}$ - dạng bàn chân Hy Lạp/Ai Cập thanh thoát). Bán kính $r \approx 6.5\text{mm}$.
   - **Ngón giữa (Digit III)**: Gồm 3 đốt. Ngắn hơn ngón trỏ $4\text{mm}$, bán kính $r \approx 6.0\text{mm}$.
   - **Ngón áp út (Digit IV)**: Gồm 3 đốt. Ngắn hơn ngón giữa, hơi uốn cong nhẹ về phía ngón út, bán kính $r \approx 5.5\text{mm}$.
   - **Ngón út (Digit V)**: Gồm 3 đốt. Ngắn nhất, nằm thuôn ở rìa ngoài bàn chân, bán kính $r \approx 4.8\text{mm}$, đệm ngón chạm nhẹ mặt đất.
   - **Khoảng hở ngón (Interdigital Clefts)**: Phải có khe rãnh rõ ràng giữa ngón 1 và ngón 2 (khoảng cách tối thiểu $3–4\text{mm}$ ở khe kẽ) để xỏ vừa quai kẹp hoặc quai ngang của dép xăng-đan bệt theo concept.
5. **Chi Tiết Móng Chân Tinh Tế (Subtle Toenails)**:
   - Mỗi ngón chân ở mặt lưng đốt xa có một tấm móng keratin lồi nhẹ.
   - Móng ngón cái: Dạng hình thang/chữ nhật bo góc mềm, kích thước khoảng $9\text{mm} \times 8\text{mm}$, có rãnh móng (nail groove) và gốc móng viền da mềm (eponychium).
   - Móng các ngón 2–5: Nhỏ dần, hình ô-van dẹt tự nhiên, sáng bóng nhẹ.

---

## PHẦN 3: KHẢO SÁT `human_rigging.py` & KHUNG XƯƠNG RIGIFY 163 DEF

### 3.1. Cấu Trúc Khung Xương Rigify 163 DEF Hiện Tại

Khung xương Rigify Metarig trong `human_rigging.py` tuân thủ nghiêm ngặt hằng số 163 xương DEF:
- **64 Xương Thân (Body DEF Bones)**:
  - 10 Xương Trục: `DEF-spine`, `DEF-spine.001` đến `.006`, `DEF-head`, `DEF-eye.L`, `DEF-eye.R`.
  - 12 Xương Chi Trên: `DEF-shoulder.L/R`, `DEF-upper_arm.L/R` (kèm `.001`), `DEF-forearm.L/R` (kèm `.001`), `DEF-hand.L/R`.
  - 30 Xương Ngón Tay: 15 xương mỗi bàn tay (ngón cái, ngón trỏ, ngón giữa, ngón áp út, ngón út $\times$ 3 đốt).
  - 12 Xương Chi Dưới:
    - `DEF-thigh.L`, `DEF-thigh.L.001`
    - `DEF-shin.L`, `DEF-shin.L.001`
    - `DEF-foot.L`
    - `DEF-toe.L`
    (và đối xứng cho bên phải R).
- **99 Xương Mặt (Facial DEF Bones)**:
  - Lông mày (16), Mí mắt (16), Môi (16), Má (8), Cằm (4), Tai (10), Trán (8), Hàm (4 + 1 hàm giữa), Mũi (8), Thái dương (2), Lưỡi (6).

### 3.2. Căn Chỉnh Trục Xoay Sinh Học (Biological Joint Pivots Alignment)

Khi xương uốn gập trong hoạt họa, nếu trục xoay đặt sai so với giải phẫu thật, thể tích cơ thể sẽ bị bẹp dẹp (pinch), teo cơ (volume loss) hoặc phình biến dạng.

```
       [Khớp Háng / Hip Joint] -> Đặt tại Chỏm Xương Đùi (Femoral Head)
                 |                 (Z cao hơn đáy quần +0.035m, X lùi vào trong)
                 v
       [Khớp Gối / Knee Joint] -> Đặt tại Trục Lồi Cầu Xương Đùi (Condylar Axis)
                 |                 (Lùi về phía sau so với xương bánh chè Y ~ 0.000m)
                 v
     [Khớp Cổ Chân / Ankle Joint] -> Đặt nghiêng theo Trục Liên Mắt Cá (Bimalleolar Axis)
                 |                   (Nghiêng xuống ngoài ~8°, xoay ngoài ~15°)
                 v
       [Khớp Ngón / MTP Joint] -> Đặt chéo theo Cung Bàn Chân Oblique (~65°)
```

1. **Khớp Háng (Hip Joint Pivot - Head of `DEF-thigh.L/R`)**:
   - *Hiện trạng*: Đặt tại `lm["hip_L"] = (0.095*s*k_hip, -0.010*s, z_crotch)`.
   - *Sai lệch*: Đặt ngang đáy quần ($Z = z\_crotch$) là quá thấp! Trong cơ thể người thật, chỏm xương đùi nằm sâu trong ổ cối (*acetabulum*) của xương chậu, cao hơn đáy quần khoảng $35–45\text{mm}$. Mấu chuyển lớn (*trochanter major*) mới nằm ở phía ngoài.
   - *Hậu quả*: Khi nâng đùi về phía trước hoặc dạng háng sang bên, cơ mông và đáy chậu bị kéo tụt xuống, làm phẳng lì xương chậu.
   - *Căn chỉnh chuẩn*: Đầu xương `DEF-thigh.L` phải đặt tại:
     $$X_{hip} = \pm 0.088 \cdot s \cdot k_{hip}, \quad Y_{hip} = -0.008 \cdot s, \quad Z_{hip} = z\_crotch + 0.038 \cdot s$$
2. **Khớp Gối (Knee Joint Pivot - Head of `DEF-shin.L/R` / Tail of `DEF-thigh.L.001`)**:
   - *Hiện trạng*: Đặt tại `lm["knee_L"] = (0.100*s*k_hip, -0.020*s, 0.445*s*k_leg)`. Pre-bend enforced: $Y \le -0.020\text{m}$.
   - *Sai lệch*: Đặt quá thiên về phía trước (sát xương bánh chè). Trục gập bản lề thật của khớp gối nằm ở tâm cong của hai lồi cầu xương đùi (*condyli femoris*), nằm lùi về phía sau khoảng $15–20\text{mm}$ so với bề mặt xương bánh chè.
   - *Hậu quả*: Khi gập gối $90^\circ$, da phía sau hõm khoeo (*fossa poplitea*) bị kéo căng bất thường, trong khi mặt trước gối bị bẹp dí.
   - *Căn chỉnh chuẩn*:
     - Giữ nguyên độ cong mồi (pre-bend) góc gập gối về phía sau để IK solver của Rigify xác định đúng mặt phẳng gập (không bị giật khớp gối).
     - Đặt đầu `DEF-shin.L` tại tâm khối lồi cầu: $Y_{knee} \approx -0.008 \cdot s$. Phần đỉnh xương bánh chè trên bề mặt lưới nằm ở $Y \approx -0.040\text{m}$. Khoảng cách này tạo đòn bẩy tự nhiên giúp mặt trước gối giữ nguyên độ cong tròn khi gập.
3. **Khớp Cổ Chân (Ankle Joint Pivot - Head of `DEF-foot.L/R`)**:
   - *Hiện trạng*: Đặt tại `lm["ankle_L"] = (0.090*s*k_hip, 0.005*s, 0.082*s*k_leg)`.
   - *Sai lệch*: Trục xoay nằm ngang song song trục X. Trong thực tế, khớp sên - cẳng chân xoay quanh trục xiên nối hai đỉnh mắt cá (trục liên mắt cá). Trục này nghiêng xuống dưới về phía ngoài khoảng $8^\circ$ và xoay ngoài khoảng $15^\circ$ so với mặt phẳng trán.
   - *Căn chỉnh chuẩn*:
     - Đầu xương `DEF-foot.L`: $X = 0.088\cdot s, Y = 0.002\cdot s, Z = 0.080\cdot s\cdot k_{leg}$.
     - Đặt góc Roll của xương bàn chân khớp với độ nghiêng của mắt cá ngoài thấp hơn mắt cá trong.
4. **Khớp Bẻ Ngón Chân (MTP Joint Pivot - Head of `DEF-toe.L/R`)**:
   - *Hiện trạng*: Đuôi `DEF-foot.L` và đầu `DEF-toe.L` đặt tại $Y = -0.095\cdot s, Z = 0.035\cdot s$.
   - *Căn chỉnh chuẩn*: Trục bẻ ngón chân phải bám sát đường cong tự nhiên của các chỏm xương bàn chân (nối từ khớp bàn-ngón cái $Y \approx -0.095\cdot s$ chéo lùi dần về khớp bàn-ngón út $Y \approx -0.080\cdot s$).

---

## PHẦN 4: CHIẾN LƯỢC TRỌNG SỐ DA (VERTEX WEIGHTING & SKINNING STRATEGY)

### 4.1. Phân Rã Xoắn Đôi (Dual-Bone Twist Decomposition) Cho Đùi & Cẳng Chân

Để triệt tiêu hiện tượng "vặn kẹo kéo" (candy-wrapper collapse) khi chân xoay quanh trục dọc:
- **Đùi (Thigh)**: Chia làm 2 xương DEF:
  - `DEF-thigh.L`: Chịu 100% xoay tại khớp háng, khử xoắn dần dọc thân đùi.
  - `DEF-thigh.L.001`: Tiếp nhận biến dạng uốn khớp gối.
  - Trọng số phân bố theo hàm cosine mịn:
    $$W_{thigh} = \cos^2\left(\frac{\pi}{2} u\right), \quad W_{thigh.001} = 1.0 - W_{thigh} \quad (u \in [0, 1] \text{ từ háng đến gối})$$
- **Cẳng chân (Shin)**: Chia làm 2 xương:
  - `DEF-shin.L`: Tiếp nhận uốn gối.
  - `DEF-shin.L.001`: Tiếp nhận xoay cổ chân. Phân bổ trọng số tương tự giúp bắp chân giữ nguyên thể tích phình cơ tự nhiên (*gastrocnemius*).

### 4.2. Khóa Cứng Xương Bánh Chè (Patella Rigid Sesamoid Locking)

- **Nguyên lý y khoa**: Xương bánh chè là một xương vừng (*sesamoid bone*) nằm trong gân cơ tứ đầu đùi và liên kết với lồi củ chày qua dây chằng bánh chè (*ligamentum patellae*). Dây chằng này không co giãn. Do đó, khi gối gập, xương bánh chè di chuyển đồng bộ với xương cẳng chân (tibia), trượt trên rãnh ròng rọc của xương đùi.
- **Quy tắc gán trọng số**:
  - Toàn bộ đỉnh thuộc vùng xương bánh chè phía trước gối ($Z \in [knee\_z - 0.015, knee\_z + 0.040]\text{m}, Y < knee\_y - 0.005\text{m}$) được **khóa $\ge 92\%$ vào `DEF-shin.L`** và tối đa $8\%$ vào `DEF-thigh.L.001`.
  - Tuyệt đối không để xương đùi trên kéo giãn vùng bánh chè, đảm bảo độ cứng chắc của đầu gối khi render chuyển động.

### 4.3. Phân Vùng Mắt Cá Chân & Gân Gót Achilles

- **Mắt cá trong & Mắt cá ngoài**: Thuộc về đầu dưới xương chày và xương mác. Do đó, đỉnh vùng mắt cá phải thuộc về cẳng chân!
  - Gán **$\ge 80\%$ vào `DEF-shin.L.001`** và $\le 20\%$ vào `DEF-foot.L`.
  - Ngăn chặn triệt để hiện tượng khi bàn chân chúc mũi xuống (plantarflexion), hai mắt cá bị kéo xoay theo bàn chân và xé rách cổ chân.
- **Xương gót (Heel & Calcaneus)**: Gán $90\%$ vào `DEF-foot.L`, $10\%$ vào `DEF-shin.L.001`.
- **Gân gót Achilles**: Gán dải gradient chuyển tiếp mượt từ $Z=0.08\text{m}$ đến $Z=0.15\text{m}$ giữa `DEF-foot.L` và `DEF-shin.L.001`.

### 4.4. Trọng Số 5 Ngón Chân & Phân Lập Trụ (Toe Bounding-Cylinder Isolation)

- **Vấn đề dính màng (Webbing Artifacts)**: Do 5 ngón chân nằm sát nhau, nếu dùng thuật toán khoảng cách Euclid thông thường, các đỉnh của ngón cái sẽ nhận trọng số của ngón trỏ, gây hiện tượng dính màng kẽ ngón khi cử động.
- **Giải pháp phân lập trụ (tương tự thuật toán bàn tay)**:
  - Chia bàn chân thành 5 vùng trụ ranh giới theo trục X (hoặc tọa độ cực cục bộ) dọc theo tia từ khớp bàn chân ra từng đầu ngón:
    - Vùng Ngón Cái (Hallux): $X \in [X_{cleft1-2}, X_{medial}]$. Trọng số ngón cái gán ưu tiên theo đốt ngón.
    - Vùng Ngón Trỏ, Giữa, Áp Út, Út: Tách biệt hoàn toàn theo các ngưỡng ranh giới $X_{border}$.
  - Đối với khung xương 163 DEF chuẩn (có `DEF-foot.L` và `DEF-toe.L`):
    - Đỉnh thuộc thân bàn chân (từ gót đến khớp bàn ngón MTP): Gán vào `DEF-foot.L` ($1.0 \to 0.0$).
    - Đỉnh thuộc 5 ngón chân (từ khớp MTP ra đầu ngón): Gán mượt vào `DEF-toe.L` ($0.0 \to 1.0$), với độ suy giảm mượt theo hàm Hermite Smoothstep:
      $$u_{toe} = \text{clamp}\left(\frac{Y_{MTP} - Y}{Y_{MTP} - Y_{tip}}, 0.0, 1.0\right), \quad W_{toe} = 3 u_{toe}^2 - 2 u_{toe}^3$$
      $$W_{foot} = 1.0 - W_{toe}$$
    - Đảm bảo khi gập ngón chân hoặc nhân vật nhón gót (heels up), toàn bộ 5 ngón chân bẻ cong đồng bộ dọc theo đúng đường gãy MTP mà không bị co kéo hay mất thể tích.

---

## PHẦN 5: MA TRẬN ĐỐI CHIẾU TIÊU CHÍ NGHIỆM THU (ACCEPTANCE CRITERIA MATRIX)

| Tiêu Chí Nghiệm Thu R1 | Hiện Trạng Trong Mã Nguồn | Khoảng Trống Kỹ Thuật (Gaps) | Kế Hoạch Khắc Phục / Đề Xuất Kỹ Thuật |
| :--- | :--- | :--- | :--- |
| **Bàn chân hiển thị đầy đủ 5 ngón riêng biệt, có móng chân** | 5 khối cầu elip đơn lẻ xếp ngang phẳng, không đốt, không móng. | Chưa có khớp ngón chân, chưa có móng, kẽ ngón không rõ để luồn quai xăng-đan. | Nâng cấp `human_generator.py`: Thay khối elip bằng bộ tạo ngón chân giải phẫu (ngón cái 2 đốt, ngón 2–5 có 3 đốt), móng chân nổi PBR, vòm mu chân cong tự nhiên. |
| **Mắt cá trong/ngoài và vòm bàn chân rõ nét khi nhìn cận cảnh** | Cổ chân tròn đều đối xứng, gan bàn chân phẳng lì. | Thiếu hoàn toàn độ lệch cao/thấp của mắt cá và độ lõm vòm dọc trong. | Bổ sung hàm tạo hình mắt cá chân bất đối xứng (trong cao/trước, ngoài thấp/sau) và vòm lõm gan bàn chân cao $12\text{mm}$. |
| **Khung xương Rigify bám sát giải phẫu xương người thật** | Khớp háng đặt ở đáy quần, khớp gối sát da trước, mắt cá chân nằm ngang. | Trục xoay sai lệch gây móp lưới khi nâng đùi hoặc gập gối. | Điều chỉnh tọa độ mốc `landmarks` trong `human_generator.py` & `human_rigging.py`: nâng háng lên chỏm xương đùi, lùi trục gối về lồi cầu đùi, xoay trục mắt cá. |
| **Uốn gập gối, cổ chân, ngón chân không làm suy giảm thể tích (no volume loss)** | Gán trọng số gối có khóa bánh chè, nhưng mắt cá và ngón chân dùng ngưỡng cứng thô `vy < -0.10`. | Mắt cá bị vặn khi xoay bàn chân; ngón chân gãy méo nếu tỉ lệ chân thay đổi. | Áp dụng Dual Quaternion Skinning (DQS), khóa cứng mắt cá vào xương cẳng chân `DEF-shin.001`, làm mịn gradient Hermite qua đường gãy ngón chân MTP. |
| **Đường cong ngực, eo thắt đáy lưng ong và đường lượn hông mềm mại** | Lát cắt elip đơn giản; ngực dạng chóp elip thô; hông phẳng. | Thiếu cúp ngực giọt nước, thiếu gờ mào chậu nữ và rãnh ức. | Điêu khắc tham số hóa: thêm cúp ngực teardrop, rãnh phân tách ngực, thắt eo $0.58\text{m}$, gờ mào chậu nở rộng $0.86\text{m}$. |
| **Bảo toàn tính toàn vẹn hệ thống & Bộ test tự động** | Đạt 163 DEF bones, 52 ARKit FACS shape keys, tỉ lệ quads ~96.5%. | Bàn chân mới cần đảm bảo giữ nguyên số lượng xương DEF 163 và bảo đảm 100% test `pytest` PASS. | Duy trì 163 DEF bones nguyên bản; kiểm tra tính tương thích với toàn bộ test suites hiện hữu. |

---

## PHẦN 6: KẾT LUẬN & ĐỀ XUẤT CHO CÁC PHÂN ĐỘI TIẾP THEO

1. **Khuyến nghị cho Đội ngũ Điêu khắc & Lưới cơ thể (Anatomy Sculptor)**:
   - Thay thế việc ghép nối các khối elip rời rạc của bàn chân bằng module hàm tạo bàn chân hữu cơ `build_anatomical_foot()`, tạo lập đầy đủ 5 ngón chân phân tách, móng chân dẹt tinh xảo và vòm bàn chân uốn lượn tự nhiên.
   - Bổ sung biến dạng vi mô trên bề mặt thân mình: gờ xương đòn (clavicle), hõm ức tam giác (suprasternal notch), gờ mào chậu (pelvic crest), và hai mắt cá chân bất đối xứng.
2. **Khuyến nghị cho Đội ngũ Khung xương & Trọng số (Rigging & Skinning Specialist)**:
   - Tinh chỉnh vị trí chỏm xoay sinh học của xương háng (nâng $+0.038\text{m}$), lùi tâm xoay khớp gối về trục lồi cầu xương đùi ($Y \approx -0.008\text{m}$), và căn chỉnh trục liên mắt cá nghiêng $8^\circ$.
   - Tối ưu hóa trọng số da vùng mắt cá chân (gán $\ge 80\%$ vào `DEF-shin.001`) và phân bổ trọng số ngón chân dọc theo đường uốn MTP bằng hàm Hermite Smoothstep.
   - Đảm bảo 100% các bài test trong `tests/test_adversarial_rigging.py` và `tests/test_adversarial_human_generator.py` tiếp tục vượt qua mà không có bất kỳ sai lệch nào.
