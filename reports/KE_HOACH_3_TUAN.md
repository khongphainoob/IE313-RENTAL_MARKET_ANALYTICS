# 🗺️ KẾ HOẠCH HOÀN THÀNH ĐỒ ÁN IE313 — 2 NGƯỜI, 3 TUẦN

> Lập ngày 21/11/2026. Mốc thời gian giả định hạn nộp khoảng **13/12/2026** — nếu hạn thật khác, dời cả bảng theo.
> Quy ước: **A** = Hoàng (Trưởng nhóm, phụ trách Dữ liệu & Mô hình) · **B** = thành viên thứ 2 (phụ trách EDA, Trực quan & Báo cáo).
> Hai người chia việc để **làm**, nhưng cả hai phải **hiểu hết** — xem Phần 6 (review chéo) và Phần 7 (câu hỏi vấn đáp).
> 📦 Việc chi tiết của B (kèm hướng dẫn, code mẫu, mốc nhận/giao): [`BAN_GIAO_THANH_VIEN_B.md`](BAN_GIAO_THANH_VIEN_B.md).

---

## 0. HIỆN TRẠNG (kiểm tra thực tế ngày 21/11)

### ✅ Đã có
| Hạng mục | Tình trạng |
|---|---|
| Crawler Chợ Tốt phân tầng 30 quận/huyện | Chạy được, 2.971 tin thô × 104 cột |
| Pipeline làm sạch 5 tầng + audit funnel | Chạy được, còn 2.678 tin sạch × 26 cột *(cập nhật 21/11: bản gộp 7.046 → 6.324 tin sạch)* |
| Feature: regex tiện ích, Haversine, seller_type, K-Means | Có |
| Mô hình Ridge / RF / LightGBM + Isolation Forest | Có (nhưng **có lỗi nghiêm trọng**, xem 0.3) |
| Streamlit dashboard | Có code (429 dòng) |
| Metadata / codebook dữ liệu | Có (`data/DATASET_METADATA.md`, `DATASET_DESCRIPTION.txt`) |

### ❌ Chưa có (đây là phần lớn điểm số)
- **4 notebook mới là khung**: mỗi cái 3 ô code, **chưa chạy, chưa có output**.
- `reports/figures/` **trống** — chưa có biểu đồ nào.
- **Chưa có** báo cáo PDF, slide, file Power BI `.pbix` (README đang ghi là có → phải sửa).
- README ghi *"15.000+ tin đăng"* nhưng thực tế là **2.971** → sửa cho khớp, giảng viên đối chiếu là lộ ngay.
- README mới có tên 1 thành viên → bổ sung thành viên B.

### 🚨 0.3. Lỗi phải sửa TRƯỚC KHI phân tích (nếu không, toàn bộ phần mô hình & Case Study sai)

| # | Lỗi | Bằng chứng | Cách sửa |
|---|---|---|---|
| 1 | ✅ **ĐÃ SỬA 21/11** — **Rò rỉ biến mục tiêu (target leakage)**: mô hình dùng `deposit_million` làm input, mà **82% tin có tiền cọc = đúng 1 tháng giá thuê** | Có `deposit`: R² CV = 0.90. Bỏ `deposit`: R² CV = 0.54 | Đã bỏ `deposit_million`. Dòng "THAM KHẢO: + tiền cọc" trong `model_report.json` giữ lại để minh chứng trong báo cáo |
| 2 | ✅ **ĐÃ SỬA 21/11** — **Dự đoán trên chính dữ liệu đã train** → `valuation_gap_pct` gần như = 0 (median 0.0%) nên nhãn Deal/Scam vô nghĩa | `src/models.py` cũ: `best_model.predict(X_full)` | Đã chuyển sang **out-of-fold prediction** 5-fold; ngưỡng nhãn theo phân vị phần dư (5% / 10% / 90%) |
| 3 | ✅ **ĐÃ XỬ LÝ 21/11** — `"Môi giới trá hình"` chỉ có 7 tin. *(Đính chính: 114 tài khoản đăng ≥4 tin phần lớn đã tự khai môi giới `company_ad=True`, nên con số 7 không sai — chỉ là nhóm quá nhỏ.)* | Trong nhóm tự khai cá nhân chỉ 13 tin thuộc tài khoản 4–9 tin | Thêm luật "đăng ở ≥2 quận" → 32 tin. Vẫn nhỏ: chỉ dùng mô tả, **không** dùng để kiểm định |
| 8 | ✅ **PHÁT HIỆN & ĐÃ XỬ LÝ 21/11** — Các tin "rẻ bất thường" nhất trong v1 phần lớn là **KTX / sleepbox / ở ghép** — giá **theo giường**, không phải theo phòng → không phải tin ảo | 126 tin (4.7%), độ lệch giá trung vị **−56%** | Cờ `is_shared_or_dorm` (regex trên tiêu đề). Giữ trong dataset để EDA, **loại khỏi mô hình giá phòng**, nhãn `SHARED_DORM`. R² tăng 0.54 → **0.64** |
| 4 | Nhãn `SCAM_RISK` **không có ground truth** | Chỉ là luật tự đặt | Đổi tên thành **"Nghi vấn bất thường – cần kiểm chứng"**; mở thủ công 30–50 tin qua `ad_url`, ghi kết quả → tính tỉ lệ đúng |
| 5 | 47% tin **trùng tọa độ** (tâm phường/tâm đường) | `duplicated(lat,lon)` = 0.47 | Ghi vào phần Hạn chế; khi vẽ bản đồ dùng hexbin/choropleth thay vì chấm điểm |
| 6 | Nhiều huyện quá ít mẫu: Cần Giờ 1, Tân Uyên 1, Bến Cát 7, Củ Chi 9, TDM 14 | `value_counts` | Gộp thành nhóm "Ngoại thành HCM" / "Bình Dương khác", hoặc loại khỏi so sánh theo quận |
| 7 | Dữ liệu chỉ là **1 lát cắt ~5 ngày** (90% tin đăng 06–10/11) | `list_time` | Không được kết luận "xu hướng giá theo thời gian". Muốn có → làm Phần 2.C |

---

## 1. MỤC TIÊU ĐỒ ÁN (viết lại cho rõ và trung thực)

**Đề tài:** Phân tích thị trường phòng trọ TP.HCM & Bình Dương (cũ) trên Chợ Tốt — yếu tố nào quyết định giá thuê, và tin nào đang rẻ/đắt bất thường so với mặt bằng.

**Đối tượng hưởng lợi:** sinh viên & người lao động đi thuê trọ.

**5 câu hỏi nghiên cứu (RQ)** — mọi biểu đồ, kiểm định, mô hình đều phải trả lời 1 trong 5 câu này:

| RQ | Câu hỏi | Kết quả cần có |
|---|---|---|
| RQ1 | Mặt bằng giá thuê hiện nay ra sao, khác nhau thế nào giữa các khu vực? | Phân phối giá, bảng giá theo quận, bản đồ |
| RQ2 | Vị trí ảnh hưởng giá bao nhiêu? (càng xa trung tâm rẻ đi bao nhiêu/km) | Đường cong distance decay, hệ số hồi quy |
| RQ3 | Mỗi tiện ích (máy lạnh, gác, WC riêng, giờ tự do…) **đáng giá bao nhiêu %** khi đã kiểm soát diện tích & vị trí? | Bảng "premium thô" vs "premium có kiểm soát" |
| RQ4 | Chính chủ và môi giới khác nhau thế nào (giá, chất lượng tin đăng)? | So sánh nhóm + kiểm định |
| RQ5 | Có thể ước lượng "giá hợp lý" và phát hiện tin rẻ/đắt bất thường không? Độ tin cậy đến đâu? | Mô hình CV, danh sách tin bất thường + kết quả kiểm chứng thủ công |

---

## 2. LÀM THÊM DỮ LIỆU (xếp theo thứ tự ưu tiên: rẻ & giá trị cao trước)

### A. Tận dụng cột thô có sẵn nhưng chưa dùng (~1 ngày, **bắt buộc**)
Trong 104 cột thô mới dùng ~15. Các cột đáng khai thác:

| Cột thô | Feature mới | Ý nghĩa phân tích |
|---|---|---|
| `price_diff` | `has_price_change`, `price_change_pct` | **620 tin (21%) đã đổi giá** — tin giảm giá có phải tin "ế"? |
| `orig_list_time`, `list_time` | `listing_age_days` | Tin cũ được đẩy lại vs tin mới |
| `number_of_images` (1–12), `has_video` (710 tin) | `n_images`, `has_video` | Chất lượng tin; tin ảo thường ít ảnh? |
| `is_main_street` | `is_main_street` | Mặt tiền vs hẻm |
| `street_number` | `is_alley` (chứa "hẻm/kiệt/ngõ") | Hẻm có rẻ hơn? |
| `special_display`, `stickyad_feature` | `is_paid_promo` (369 tin) | Tin trả tiền quảng cáo → thường là môi giới |
| `shop`, `company_ad`, `sold_ads` | Làm lại `seller_type` | Sửa lỗi 0.3 #3 |
| `average_rating_for_seller`, `total_rating_for_seller` | `seller_rating`, `n_ratings` | Uy tín người đăng |
| `body` | `body_length`, `n_emoji`, có số điện thoại/Zalo | Chất lượng mô tả |
| `ward_name_v3`, `region_name_v3` | Phường **theo đơn vị hành chính mới** | Sau sáp nhập 01/07/2025 (Bình Dương nhập TP.HCM, bỏ cấp quận) — dữ liệu có cả tên cũ (178 phường) và mới (115 phường). Nêu rõ trong báo cáo, là điểm cộng về hiểu dữ liệu |

### B. Mở rộng NLP regex từ `body` (~1 ngày, **bắt buộc**)
Đã đo tỉ lệ xuất hiện trong mô tả:

| Feature | Từ khóa gợi ý | Tỉ lệ |
|---|---|---|
| `has_kitchen` | bếp | 31.8% |
| `has_furniture_text` | nội thất | 43.0% |
| `has_washing_machine` | máy giặt | 25.6% |
| `has_parking` | để xe, giữ xe, hầm xe | 22.9% |
| `has_elevator` | thang máy | 14.1% |
| `has_private_wc` | wc/vệ sinh/toilet riêng | 13.6% |
| `elec_price_k` | "điện 3.5k", "điện 4k/kWh" → **trích con số** | 13.8% |
| `female_only` | chỉ nhận nữ | ~5% |
| `allow_pet`, `shared_room` | thú cưng, ở ghép | ~2–3% |

> 💡 Insight hay: **chi phí ẩn** — giá điện chủ trọ thu (3.5k–4k/kWh) cao hơn giá điện nhà nước bậc thấp. Tính "giá thuê thực" = giá phòng + điện ước tính.
> ⚠️ Mỗi regex phải **kiểm tra tay 30 tin** (precision) và ghi kết quả vào báo cáo.

### C. Crawl lặp lại mỗi ngày trong 10–14 ngày (**nên làm**, bắt đầu ngay tuần 1)
- Chạy crawler 1 lần/ngày (Task Scheduler Windows), lưu mỗi lần một file `data/raw/snapshots/YYYY-MM-DD.jsonl`.
- Thu được:
  1. **Thêm mẫu**: gộp các ngày → có thể lên 5.000–8.000 tin duy nhất (nên nâng `--max-per-area` lên 250–300 cho quận lớn).
  2. **Chiều thời gian thật**: tin sống bao lâu thì biến mất (đã cho thuê/bị gỡ), giá có giảm dần không.
  3. **Kiểm chứng gián tiếp tin bất thường**: tin "rẻ bất thường" có biến mất nhanh hơn / bị gỡ nhiều hơn không? → đây là bằng chứng mạnh cho RQ5.
- Giữ delay lịch sự (≥0.3s), không crawl dồn dập.

### D. Dữ liệu ngoài từ OpenStreetMap (**nên làm**, ~1–2 ngày)
- Dùng Overpass API (miễn phí) lấy tọa độ: trường ĐH/CĐ, khu công nghiệp, chợ/siêu thị, **ga Metro số 1** (Bến Thành – Suối Tiên).
- Feature: `dist_nearest_university_km`, `dist_nearest_metro_km`, `dist_nearest_industrial_km`, `n_poi_1km`.
- File ranh giới quận/phường (GeoJSON) để vẽ **choropleth** trong Plotly/Power BI.
- Kỳ vọng: giúp R² tăng tiếp từ 0.64 (sau khi bỏ leakage và tách KTX) — đúng chuyện "bỏ leakage, thay bằng feature có ý nghĩa".

### E. (Tùy chọn, chỉ khi dư thời gian) Nguồn thứ 2
- Lấy một mẫu nhỏ từ trang cho thuê khác để đối chiếu mặt bằng giá theo quận. Kiểm tra điều khoản/robots.txt trước; không bắt buộc.

---

## 3. KHUNG PHÂN TÍCH SÂU (làm gì, bằng cách nào, ra biểu đồ gì)

### Bước 3.0 — "Hiểu từng cột" (cả 2 người, làm trước tiên)
Với **mỗi cột** trong dataset cuối, trả lời 5 câu, ghi vào một bảng chung:
1. Cột này nghĩa là gì, đến từ đâu (API gốc / tính ra / regex / mô hình)?
2. Kiểu dữ liệu, miền giá trị, tỉ lệ khuyết, đã xử lý khuyết thế nào?
3. Phân phối trông ra sao (lệch phải? nhiều số 0? nhiều giá trị tròn như 3.5, 4.0)?
4. Có sai/nhiễu gì (ví dụ: tọa độ trùng, regex bắt nhầm)?
5. Nó liên quan tới giá thế nào (dự đoán trước → kiểm tra sau)?

### 3.1. Phân tích đơn biến (RQ1)
- Histogram + KDE: `price_million`, `size_m2`, `price_per_m2_k` (dùng thêm thang log).
- Bar chart tỉ lệ: tiện ích, nội thất, seller_type.
- Chú ý **hiện tượng làm tròn giá** (heaping): đếm tỉ lệ giá là bội 0.5 triệu.

### 3.2. Phân tích theo không gian (RQ1, RQ2)
- Boxplot đơn giá theo quận, **sắp xếp theo median**, tô màu HCM cũ vs BD cũ.
- Bản đồ: hexbin / choropleth đơn giá trung vị theo phường.
- Distance decay: scatter `dist_to_q1_km` vs `price_per_m2_k` + đường LOWESS; chia vành đai 0–3, 3–6, 6–10, 10–15, >15 km → bảng median từng vành đai.
- Spearman ρ + hồi quy `log(price) ~ dist` → "mỗi km xa trung tâm giá giảm ~x%".

### 3.3. Định giá tiện ích — phần "sâu" nhất (RQ3)
- **Premium thô**: median có vs không có tiện ích + Mann-Whitney U + effect size (rank-biserial / Cliff's delta). Nhớ **hiệu chỉnh đa kiểm định** (Bonferroni/Holm) vì test nhiều tiện ích.
- **Premium có kiểm soát** — Hồi quy hedonic (OLS, `statsmodels`):
  `log(price) ~ log(size) + dist_to_q1 + C(area) + has_ac + has_mezzanine + has_private_wc + ... + furnishing`
  → hệ số β của mỗi tiện ích ≈ `(e^β − 1) × 100%` premium. Báo cáo kèm CI 95%, robust SE (HC3), kiểm tra VIF.
- **Biểu đồ chốt**: forest plot so sánh premium thô vs premium có kiểm soát. Thường premium thô bị phóng đại (vì phòng có máy lạnh hay nằm ở quận đắt) → đây là insight "hiểu sâu" giảng viên đánh giá cao.

### 3.4. Người đăng tin (RQ4)
- So sánh Chính chủ vs Môi giới: giá, đơn giá, số ảnh, độ dài mô tả, tỉ lệ tin trả phí, tỉ lệ đổi giá.
- Kruskal-Wallis + post-hoc Dunn; hoặc đưa `seller_type` vào hồi quy 3.3 để xem môi giới có "đắt hơn" khi cùng điều kiện không.

### 3.5. Phân khúc thị trường (K-Means)
- Chọn k bằng Elbow + **Silhouette** (đừng gán cứng k=3 không giải thích).
- Chuẩn hóa biến trước khi phân cụm; vẽ profile từng cụm (radar/heatmap trung bình chuẩn hóa).
- Đặt tên cụm dựa trên profile thật, không đặt tên trước.

### 3.6. Mô hình giá hợp lý & tin bất thường (RQ5)
1. Bỏ `deposit_million` (leakage). Baseline: dự đoán bằng median đơn giá quận × diện tích → mô hình phải thắng baseline này.
2. So sánh Ridge (trên log price) / Random Forest / LightGBM bằng **5-fold CV** (R², MAE, MAPE).
3. Thêm feature từ Phần 2 → bảng "R² tăng thêm bao nhiêu sau mỗi nhóm feature" (ablation).
4. Giải thích: SHAP summary + dependence plot cho `size_m2`, `dist_to_q1_km`.
5. Tính `valuation_gap_pct` bằng **out-of-fold prediction**.
6. Gắn nhãn: Rẻ bất thường / Hợp lý / Đắt bất thường (ngưỡng theo phân vị residual, ví dụ 5% và 95%, thay vì số cố định).
7. **Kiểm chứng thủ công**: mỗi người mở 25 tin "rẻ bất thường" + 10 tin "hợp lý" (nhóm đối chứng) trên Chợ Tốt, ghi vào bảng: tin còn không, ảnh có thật không, mô tả có dấu hiệu câu khách không, giá thật có khớp không. → Ra con số "x/50 tin đúng là đáng nghi".
8. Nếu làm 2.C: so sánh tỉ lệ biến mất của tin bất thường vs tin thường.

### 3.7. Ghi nhận hạn chế (bắt buộc có 1 mục trong báo cáo)
Lát cắt thời gian ngắn · chỉ 1 nền tảng · lấy mẫu có hạn ngạch (không phải tỉ lệ tự nhiên của thị trường) · giá niêm yết ≠ giá chốt · tọa độ xấp xỉ · regex có sai số · nhãn bất thường không có ground truth.

---

## 4. PHÂN CÔNG CHI TIẾT 3 TUẦN

### 🟦 TUẦN 1 (23/11 – 29/11): SỬA LỖI + LÀM GIÀU DỮ LIỆU
**Mục tiêu cuối tuần: "đóng băng" dataset v2** — sau Chủ nhật không thêm cột nữa.

| Việc | Người | Đầu ra | Hạn |
|---|---|---|---|
| ✅ Sửa leakage `deposit` + chuyển sang OOF prediction trong `src/models.py` (+ baseline, CV 5-fold, ablation, `model_report.json`) | A | Code + bảng R² trước/sau | xong 21/11 |
| ✅ Bật crawl hằng ngày 21:00 (Task Scheduler `IE313_DailySnapshot`, chạy tới 06/12), `max-per-area` 300. Tự kiểm tra dữ liệu, thử lại 3 lần, không ghi đè snapshot tốt, báo lỗi bằng thông báo Windows. **Xem tình trạng: `python -m src.snapshot_monitor`** | A | `data/raw/snapshots/` — đợt 1: 5.318 tin, 4.068 tin mới so với 10/11 | xong 21/11 |
| ✅ Trích feature từ cột thô (Phần 2.A) + sửa `seller_type` + cờ KTX/ở ghép + `area_group` | A | Cột mới trong `src/features.py` | xong 21/11 |
| ✅ Chạy notebook 01 & 02 có output (chạy lại lần cuối khi đóng băng v2) | A | Notebook có output | xong 21/11 |
| ✅ Gộp các đợt crawl (`python -m src.merge_snapshots`, tự chạy mỗi tối) → **7.046 tin thô → 6.324 tin sạch**, R² CV **0.67**. CN 29/11 chạy lại lần cuối với các đợt mới rồi đóng băng | A | `data/raw/merged/chotot_merged_raw.jsonl.gz` | xong 21/11 (chạy lại CN 29/11) |
| Cập nhật `DATASET_DESCRIPTION.txt` / `DATASET_METADATA.md` / README theo v2 (số tin, cột mới, R² thật) | A | Tài liệu khớp số liệu | CN 29/11 |
| Đọc hết codebook, làm bảng "hiểu từng cột" (3.0) | B (A review) | `reports/hieu_du_lieu.md` | T4 25/11 |
| Mở rộng regex (Phần 2.B) + kiểm tay 30 tin/regex | B | `src/text_features.py` + `reports/regex_check/` | T6 27/11 |
| Lấy POI OSM + GeoJSON ranh giới (Phần 2.D) | B | `src/external_features.py` + `data/external/` | T7 28/11 |
| Ghép `add_text_features` + `add_poi_features` của B vào `src/features.py`, thêm cột `area_group` (gộp huyện ít mẫu) | A | Dataset v2 | CN 29/11 |
| Chạy lại toàn pipeline, chạy notebook 01 & 02 có output | A | Notebook có output + `data_audit_report.json` mới | CN 29/11 |
| 🔁 **Họp 1** (1h): A giải thích pipeline cho B, B giải thích feature mới cho A | Cả hai | — | CN 29/11 |

### 🟩 TUẦN 2 (30/11 – 06/12): PHÂN TÍCH & MÔ HÌNH
**Mục tiêu cuối tuần: có đủ mọi con số + biểu đồ để viết báo cáo.**

| Việc | Người | Đầu ra | Hạn |
|---|---|---|---|
| EDA đơn biến + không gian + bản đồ (3.1, 3.2) | B | Notebook 03 phần 1, hình 300 DPI vào `reports/figures/` | T3 01/12 |
| Kiểm định + hồi quy hedonic + forest plot (3.3, 3.4) | B (A hỗ trợ statsmodels) | Notebook 03 phần 2, bảng p-value + premium | T5 03/12 |
| Mô hình CV + ablation + SHAP (3.6 bước 1–5) | A | Notebook 04 phần 1 | T4 02/12 |
| K-Means có silhouette + profile cụm (3.5) | A | Notebook 04 phần 2 | T5 03/12 |
| Gắn nhãn bất thường, xuất danh sách 50 tin cần kiểm chứng, chia đôi cho B | A | File danh sách | T5 03/12 |
| **Kiểm chứng tay 50 tin** (3.6 bước 7) | A + B (mỗi người 25 tin) | `reports/kiem_chung_tin_bat_thuong.csv` | T7 05/12 |
| Phân tích snapshot nhiều ngày (nếu có 2.C) | A | Biểu đồ thời gian sống của tin | T7 05/12 |
| Viết **1 câu insight dưới mỗi biểu đồ** (biểu đồ không có kết luận = mất điểm) | Ai vẽ người đó viết | — | CN 06/12 |
| 🔁 **Họp 2** (1.5h): mỗi người trình bày notebook của mình cho người kia như thuyết trình thật | Cả hai | Danh sách câu hỏi chưa trả lời được | CN 06/12 |

### 🟨 TUẦN 3 (07/12 – 13/12): SẢN PHẨM NỘP
| Việc | Người | Đầu ra | Hạn |
|---|---|---|---|
| Giao `rental_scored_deals.csv` bản cuối cho B làm Power BI | A | CSV | T2 07/12 |
| Cập nhật Streamlit theo kết quả mới (bản đồ, công cụ định giá, danh sách bất thường) | A | `dashboard/streamlit_app.py` chạy được | T4 09/12 |
| Power BI dashboard (nếu đề cương yêu cầu — README có nhắc "Chương 4") | B | `dashboard/IE313_Rental_Dashboard.pbix` | T4 09/12 |
| Báo cáo: A viết Chương Thu thập–Làm sạch–Mô hình; B viết Giới thiệu–EDA–Kiểm định–Kết luận & Hạn chế | A + B | `reports/IE313_Final_Report.pdf` | T6 11/12 |
| Sửa README cho đúng sự thật (số mẫu, file nào có, thêm thành viên B, con số R² thật) | A | README | T6 11/12 |
| Slide 15–20 trang (mỗi người làm phần mình viết) | A + B | `reports/IE313_Presentation_Slides.pptx` | T6 11/12 |
| Kiểm tra tái lập: clone repo sạch → cài `requirements.txt` → chạy lại từ đầu | B | Ghi lỗi nếu có | T7 12/12 |
| 🔁 **Tổng duyệt**: thuyết trình bấm giờ + hỏi nhau bộ câu hỏi Phần 7, **đổi phần** (A trình bày phần B và ngược lại) | Cả hai | — | T7 12/12 |
| Đệm dự phòng / nộp bài | — | — | CN 13/12 |

---

## 5. ĐỊNH NGHĨA "XONG" — CHECKLIST TRƯỚC KHI NỘP

- [ ] `src/models.py` không còn `deposit_million` trong feature; gap tính bằng OOF
- [ ] 4 notebook chạy **Restart & Run All** không lỗi, có đủ output
- [ ] Mỗi biểu đồ: có tiêu đề, nhãn trục có đơn vị, nguồn dữ liệu, 1 câu kết luận
- [ ] Mọi con số trong báo cáo/slide/README **khớp nhau** và khớp notebook
- [ ] Có bảng kết quả kiểm chứng thủ công tin bất thường
- [ ] Có mục Hạn chế & Hướng phát triển
- [ ] README không nhắc tới file không tồn tại; có đủ tên 2 thành viên + phân công
- [ ] Không commit file khóa Office (`~$*.xlsx`), không lộ thông tin cá nhân người đăng tin trong slide (che tên/số điện thoại)
- [ ] Bảng đóng góp thành viên (% công việc) trong báo cáo

---

## 6. CÁCH ĐỂ CẢ HAI NGƯỜI HIỂU HẾT (không chỉ phần mình)

1. **Review chéo mọi Pull Request / commit**: A làm thì B review và ngược lại — người review phải giải thích lại được đoạn code đó.
2. **"Dạy lại" trong mỗi buổi họp**: người làm trình bày 10 phút, người kia hỏi; câu nào không trả lời được ghi vào danh sách và giải quyết trước buổi sau.
3. **Tổng duyệt đổi vai** (tuần 3): mỗi người thuyết trình phần của người kia.
4. **Mỗi người tự tay chạy toàn bộ pipeline ít nhất 1 lần** trên máy mình.

---

## 7. BỘ CÂU HỎI GIẢNG VIÊN HAY HỎI — CẢ HAI PHẢI TRẢ LỜI ĐƯỢC

**Về dữ liệu**
1. Dữ liệu lấy từ đâu, bằng cách nào, có hợp lệ không? Vì sao lấy mẫu 140 tin/quận mà không lấy hết?
2. Vì sao từ 7.046 còn 6.324? Từng bước loại bao nhiêu, vì sao? (xem `data/processed/data_audit_report.json`)
3. Vì sao lọc ngoại lai theo IQR **từng quận** chứ không phải toàn bộ?
4. Tiền cọc khuyết 31% điền thế nào? Có ảnh hưởng kết quả không?
5. Regex `has_ac` có bắt nhầm không? Độ chính xác bao nhiêu?
6. Dữ liệu có tên phường cũ và mới — nhóm xử lý thế nào?

**Về phân tích**
7. Máy lạnh làm giá tăng bao nhiêu? Con số đó đã loại ảnh hưởng của diện tích/vị trí chưa?
8. Vì sao dùng kiểm định phi tham số (Mann-Whitney, Kruskal-Wallis) thay vì t-test/ANOVA?
9. p-value nhỏ có nghĩa là ảnh hưởng lớn không? (Không — phải xem effect size.)
10. Tương quan khoảng cách – giá có phải quan hệ nhân quả không?

**Về mô hình**
11. Vì sao ban đầu R² 0.9 mà sau còn 0.54, rồi lên 0.64? (Leakage tiền cọc → bỏ; rồi phát hiện KTX/ở ghép giá theo giường làm nhiễu → tách riêng. **Nói thẳng, đây là điểm cộng** vì cho thấy nhóm hiểu dữ liệu.)
12. R² ~0.64 có tệ không? (So với baseline 0.39.) Phần còn lại do đâu? (Ảnh, chất lượng thực tế, thương lượng… không có trong dữ liệu.)
13. Làm sao biết tin "nghi vấn" thật sự là tin ảo? (Kiểm chứng tay x/50 tin; không khẳng định là lừa đảo.)
14. Vì sao chọn k=? cho K-Means?
15. Ứng dụng thực tế của đồ án cho người đi thuê là gì?

---

## 8. NẾU CÒN THỜI GIAN SAU 3 TUẦN (hiểu sâu thêm)
- Hồi quy phân vị (quantile regression): tiện ích ảnh hưởng phòng rẻ khác phòng đắt thế nào.
- Tự tương quan không gian (Moran's I) trên giá theo phường.
- Phân tích văn bản: TF-IDF tiêu đề tin bất thường vs tin thường.
- Theo dõi snapshot dài hơn (4–6 tuần) để phân tích thời gian cho thuê (survival analysis).
