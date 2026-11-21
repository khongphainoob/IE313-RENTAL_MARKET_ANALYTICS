# 🏠 Southern Vietnam Rental Market Analytics: Fair-Value Pricing & Anomaly Detection
> **Đồ án môn học:** IE313 - Phân tích và Trực quan hóa Dữ liệu (Data Analysis and Visualization)  
> **Trường:** Đại học Công nghệ Thông tin - ĐHQG TP.HCM (UIT - VNUHCM)  
> **Khoa:** Hệ thống Thông tin (Information Systems)  

### 👥 Nhóm sinh viên thực hiện:
| STT | Họ và tên | MSSV | Lớp | Vai trò | GitHub / Email |
| :---: | :--- | :---: | :---: | :--- | :--- |
| **1** | **Trương Huy Hoàng** | **24520574** | CNTT2024 | Trưởng nhóm (Leader) | [@khongphainoob](https://github.com/khongphainoob) |
| **2** | **Lê Huy Hoàng** | **24520541** | CNTT2024 | Thành Viên | [@24520541-cmyk](https://github.com/Hhoang156) |

Phân công & tiến độ: [`reports/KE_HOACH_3_TUAN.md`](reports/KE_HOACH_3_TUAN.md) · Việc của thành viên 2: [`reports/BAN_GIAO_THANH_VIEN_B.md`](reports/BAN_GIAO_THANH_VIEN_B.md)

> 📌 **Số liệu cập nhật ngày 21/11/2026** — dataset v2 (gộp 2 đợt crawl). Crawl tự động vẫn chạy mỗi tối; dataset sẽ được **đóng băng ngày 29/11/2026** và README cập nhật lại lần cuối.

---

## 📌 1. Giới thiệu bài toán (Project Overview & Case Study)
Thị trường thuê phòng trọ và căn hộ dịch vụ tại **TP. Hồ Chí Minh và Bình Dương** luôn sôi động nhưng tồn tại sự bất cân xứng thông tin lớn giữa người cho thuê/môi giới và người đi thuê (sinh viên, người lao động). Người thuê thường đối mặt với hai vấn đề:
1. **Không biết mức giá hợp lý (Fair Value):** Khó định lượng được việc đi xa trung tâm thêm vài km hay có thêm gác lửng, máy lạnh sẽ làm thay đổi giá thuê bao nhiêu.
2. **Tin rẻ bất thường:** Có những tin đăng phòng đẹp với giá thấp hơn mặt bằng rất nhiều — có thể là "kèo thơm" thật, cũng có thể là tin câu khách / câu cọc.

Dự án xây dựng một **pipeline phân tích dữ liệu end-to-end**: tự thu thập **7.046 tin đăng thực tế** (không trùng) từ **Chợ Tốt (Nhà Tốt)**, làm sạch còn **6.324 tin**, phân tích thống kê không gian, huấn luyện mô hình **định giá hợp lý** và gắn cờ các tin **rẻ / đắt bất thường so với mặt bằng** để người dùng kiểm chứng.

> ⚠️ Nhãn "nghi vấn" (`SCAM_RISK`) chỉ có nghĩa là *giá thấp bất thường so với mô hình + có dấu hiệu bất thường khác* — **không phải kết luận tin đó là lừa đảo**. Nhóm kiểm chứng thủ công một mẫu các tin này (xem kế hoạch).

---

## 📈 2. Kết quả chính (cập nhật 21/11/2026)

### 2.1. Dữ liệu
| Hạng mục | Giá trị |
| :--- | :--- |
| Nguồn | API công khai của Chợ Tốt — danh mục Phòng trọ (`cg=1050`), 30 quận/huyện TP.HCM & Bình Dương |
| Các đợt crawl | 10/11/2026 (140 tin/quận) và 21/11/2026 (300 tin/quận); crawl tự động mỗi ngày đến 06/12/2026 |
| Tin thô không trùng | **7.046** (TP.HCM 6.509 · Bình Dương 537) — 1.237 tin xuất hiện ở cả 2 đợt, 157 tin đã đổi giá giữa 2 đợt |
| Tin sạch | **6.324** (TP.HCM 6.048 · Bình Dương 276), 28 quận/huyện, giữ lại **89,75%** |
| Giá thuê | trung vị **3,7 triệu/tháng** (trung bình 3,82; từ 0,6 đến 13,5) |
| Diện tích | trung vị **25 m²** · đơn giá trung vị **148,6 nghìn/m²** |

**Phễu làm sạch** (`data/processed/data_audit_report.json`):

| Bước | Còn lại | Loại bỏ | Lý do |
| :--- | ---: | ---: | :--- |
| 0. Dữ liệu gộp | 7.046 | – | |
| 1a. Trùng `ad_id` | 7.046 | 0 | đã khử khi gộp các đợt crawl |
| 1b. Môi giới đăng trùng 1 phòng | 6.807 | 239 | cùng tài khoản + phường + diện tích + giá |
| 2. Miền giá trị hợp lệ | 6.611 | 196 | giá ngoài [0,5; 25] triệu hoặc diện tích ngoài [5; 120] m² / **không ghi diện tích** |
| 3. Ngoại lai đơn giá theo từng quận (Grouped IQR) | 6.324 | 287 | |

### 2.2. Mô hình định giá hợp lý (5-fold cross-validation, `data/processed/model_report.json`)
Huấn luyện trên **6.104 tin phòng** (đã loại 220 tin KTX / sleepbox / ở ghép — giá tính theo giường).

| Mô hình | R² | MAE (triệu) | RMSE (triệu) | MAPE |
| :--- | ---: | ---: | ---: | ---: |
| Baseline: đơn giá trung vị quận × diện tích | 0,400 | 0,799 | 1,135 | 22,4% |
| Ridge (log giá) | 0,583 | 0,666 | 0,947 | 18,6% |
| Random Forest | 0,655 | 0,626 | 0,861 | 17,9% |
| **LightGBM** (được chọn) | **0,666** | **0,616** | **0,847** | **17,6%** |

Đóng góp của từng nhóm biến (LightGBM, cộng dồn): diện tích + quận **0,591** → + khoảng cách tới Q1 & ĐHQG **0,619** → + nội thất & tiện ích **0,663** → + mặt tiền/hẻm **0,666**.

**Hai lỗi phương pháp đã phát hiện và sửa** (so với bản đầu):
1. **Rò rỉ biến mục tiêu:** 82% tin có tiền cọc đúng bằng 1 tháng tiền thuê → dùng tiền cọc làm biến đầu vào thì R² "đẹp" giả tạo **0,917**. Đã **bỏ tiền cọc** khỏi mô hình.
2. **Tin KTX / ở ghép:** chiếm phần lớn các tin "rẻ bất thường" nhất trong bản đầu nhưng thực ra là **giá theo giường**, không phải tin ảo → tách riêng (`is_shared_or_dorm`, nhãn `SHARED_DORM`).

Giá hợp lý của mỗi tin là **dự đoán out-of-fold** (mô hình chưa từng thấy tin đó khi huấn luyện).

### 2.3. Phân loại tin (`deal_status`) — ngưỡng theo phân vị độ lệch giá
| Nhãn | Số tin | Quy tắc |
| :--- | ---: | :--- |
| `FAIR_PRICE` | 4.880 | Giá nằm trong mặt bằng |
| `GOOD_DEAL` | 525 | Rẻ hơn dự đoán từ **23,9%** trở lên (10% tin rẻ nhất) |
| `SCAM_RISK` (nghi vấn – cần kiểm chứng) | 87 | Rẻ hơn dự đoán từ **31,4%** trở lên (5% rẻ nhất) **và** bị Isolation Forest đánh dấu bất thường hoặc người đăng là "môi giới trá hình" |
| `OVERPRICED` | 612 | Đắt hơn dự đoán từ **26,6%** trở lên (10% đắt nhất) |
| `SHARED_DORM` | 220 | KTX / sleepbox / ở ghép — không định giá theo phòng |

---

## 🎯 3. Phương pháp & đóng góp chính
- **Tự xây dựng dataset (Data Acquisition):** crawler phân tầng theo từng quận/huyện qua API công khai của Chợ Tốt (không cần đăng nhập, nghỉ 0,4–0,5 giây giữa các request); **crawl hằng ngày** để có dữ liệu theo thời gian (tin sống bao lâu, đổi giá ra sao) — có kiểm tra chất lượng từng đợt, tự thử lại, không ghi đè dữ liệu tốt.
- **Tiền xử lý & đặc trưng (Wrangling & Feature Engineering):**
  - Khử trùng lặp tin môi giới và lọc ngoại lai theo từng quận (**Grouped IQR**).
  - 4 đặc trưng tiện ích bằng **regex** trên tiêu đề + mô tả (`has_mezzanine`, `has_ac`, `is_free_curfew`, `has_balcony_window`) và cờ **KTX / ở ghép** trên tiêu đề.
  - 16 đặc trưng từ các trường API chưa dùng: mặt tiền/hẻm, đổi giá, tuổi tin, số ảnh, video, tin trả phí, cửa hàng, đánh giá người đăng, độ dài mô tả…
  - Khoảng cách **Haversine** tới Chợ Bến Thành (Q.1) và Khu đô thị ĐHQG-HCM.
- **Kiểm định giả thuyết:** `Mann-Whitney U`, `Kruskal-Wallis`, `Spearman`, hồi quy hedonic (đang thực hiện — notebook 03).
- **Mô hình:** so sánh Ridge / Random Forest / LightGBM với baseline bằng CV 5-fold; **Isolation Forest** trên độ lệch giá để gắn cờ bất thường.
- **Trực quan hóa:** ứng dụng web **Streamlit**; báo cáo **Power BI** (đang thực hiện).

---

## 🛠️ 4. Hướng dẫn cài đặt và chạy dự án (Quick Start)

### Bước 1: Cài đặt môi trường (Python 3.10+)
```bash
git clone https://github.com/khongphainoob/IE313-RENTAL_MARKET_ANALYTICS.git
cd IE313-RENTAL_MARKET_ANALYTICS
pip install -r requirements.txt
```

### Bước 2: Chạy pipeline (dữ liệu đã có sẵn trong repo — có thể bỏ qua phần crawl)
```bash
# (Tùy chọn) Crawl 1 đợt snapshot trong ngày -> data/raw/snapshots/YYYY-MM-DD.jsonl.gz
python -m src.crawler --snapshot --max-per-area 300

# (Tùy chọn) Gộp mọi đợt crawl -> data/raw/merged/ + data/interim/deduplicated_data.parquet
python -m src.merge_snapshots

# Làm sạch + trích xuất đặc trưng -> data/processed/rental_cleaned_full.csv
python -m src.features

# Huấn luyện, chấm điểm, gắn nhãn -> data/processed/rental_scored_deals.csv + model_report.json
python -m src.models
```

### Bước 3: Dashboard
```bash
streamlit run dashboard/streamlit_app.py
```

### Crawl tự động hằng ngày (Windows)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\register_daily_task.ps1   # đăng ký task 21:00 mỗi ngày
python -m src.snapshot_monitor                                              # xem tình trạng các đợt crawl
```

Mở dữ liệu gộp nén bằng pandas: `pd.read_json("data/raw/merged/chotot_merged_raw.jsonl.gz", lines=True)`.

---

## 📊 5. Notebooks & tiến độ
| Notebook | Nội dung | Tình trạng |
| :--- | :--- | :--- |
| `01_data_collection_and_audit.ipynb` | Quy mô dữ liệu thô, tỉ lệ khuyết, kiểm toán chất lượng | ✅ đã chạy (dataset v2) |
| `02_data_cleaning_and_fe.ipynb` | Phễu làm sạch, kết quả trích xuất đặc trưng | ✅ đã chạy (dataset v2) |
| `03_eda_and_statistical_tests.ipynb` | EDA, bản đồ, kiểm định, định giá tiện ích | 🔄 đang thực hiện |
| `04_modeling_and_case_study.ipynb` | Đánh giá mô hình, SHAP, danh sách tin bất thường + kiểm chứng | 🔄 đang thực hiện |

| Sản phẩm nộp | Tình trạng |
| :--- | :--- |
| Báo cáo `reports/IE313_Final_Report.pdf` | 🔄 đang thực hiện |
| Slide `reports/IE313_Presentation_Slides.pptx` | 🔄 đang thực hiện |
| Power BI `dashboard/IE313_Rental_Dashboard.pbix` | 🔄 đang thực hiện |
| Biểu đồ 300 DPI `reports/figures/` | 🔄 đang thực hiện |

---

## 📁 6. Cấu trúc Repository
```text
IE313-RENTAL_MARKET_ANALYTICS/
├── data/
│   ├── raw/
│   │   ├── chotot_raw_hcm_bd.jsonl / .csv / .xlsx  # Đợt crawl đầu 10/11/2026 (2.970 tin, có cột ad_url)
│   │   ├── crawl_metadata.json                     # Log đợt crawl đầu
│   │   ├── merged/
│   │   │   ├── chotot_merged_raw.jsonl.gz          # ⭐ Gộp mọi đợt crawl, không trùng (7.046 tin)
│   │   │   └── merge_metadata.json                 # Số tin theo từng đợt
│   │   └── snapshots/                              # Đợt crawl hằng ngày (file .gz chỉ lưu trên máy crawl)
│   │       ├── YYYY-MM-DD_metadata.json
│   │       └── status_history.jsonl                # Lịch sử từng lần chạy (đạt / lỗi)
│   ├── interim/deduplicated_data.parquet           # Đầu vào của bước làm sạch
│   └── processed/
│       ├── rental_cleaned_full.csv                 # Dataset sạch đầy đủ (6.324 × 140 cột)
│       ├── rental_scored_deals.csv                 # 26 cột chuẩn + 18 cột mở rộng, đã định giá & gắn nhãn
│       ├── model_report.json                       # Benchmark, ablation, ngưỡng nhãn
│       └── data_audit_report.json                  # Phễu làm sạch
├── notebooks/                                      # 01 → 04 (xem mục 5)
├── src/
│   ├── config.py            # Hằng số: mã vùng, mốc tọa độ, regex, danh sách cột
│   ├── crawler.py           # Crawl API Chợ Tốt phân tầng theo quận; chế độ --snapshot hằng ngày
│   ├── snapshot_monitor.py  # Kiểm tra chất lượng & báo cáo tình trạng các đợt crawl
│   ├── merge_snapshots.py   # Gộp mọi đợt crawl thành 1 dataset không trùng
│   ├── cleaner.py           # Làm sạch 5 tầng, Grouped IQR, điền khuyết
│   ├── features.py          # Regex, Haversine, metadata tin, cờ KTX, seller_type, K-Means
│   ├── stats_tests.py       # Mann-Whitney U, Kruskal-Wallis, Spearman
│   └── models.py            # Baseline, Ridge, RF, LightGBM (CV), Isolation Forest, gắn nhãn
├── scripts/
│   ├── daily_snapshot.ps1        # Crawl hằng ngày: kiểm tra, thử lại 3 lần, gộp, báo cáo
│   └── register_daily_task.ps1   # Đăng ký Windows Task Scheduler
├── dashboard/streamlit_app.py
├── models/                       # lgbm_fair_price.joblib, iso_forest_anomaly.joblib
├── reports/                      # Kế hoạch, bàn giao, CRAWLING_PLAN, DATASET_METADATA, figures/
├── requirements.txt
└── README.md
```

---

## 📋 7. Từ điển dữ liệu (`data/processed/rental_scored_deals.csv`)

### 7.1. 26 cột chuẩn
| STT | Tên cột | Kiểu | Nguồn | Mô tả |
| :---: | :--- | :---: | :---: | :--- |
| **1** | `ad_id` | `int64` | API | Mã định danh duy nhất của tin đăng (khóa chính). |
| **2** | `list_id` | `int64` | API | Mã bài viết, ghép URL `https://www.nhatot.com/{list_id}.htm`. |
| **3** | `account_id` | `int64` | API | Mã tài khoản người đăng. |
| **4** | `list_time` | `datetime` | Biến đổi | Thời điểm đăng/đẩy tin gần nhất (từ Unix ms). |
| **5** | `region_name` | `category` | API | Tỉnh/thành (`Tp Hồ Chí Minh`, `Bình Dương`) — theo địa giới **cũ** trước 01/07/2025. |
| **6** | `area_name` | `category` | API | Quận/huyện/thành phố (địa giới cũ). |
| **7** | `ward_name` | `category` | API | Phường/xã (địa giới cũ). |
| **8** | `street_name` | `string` | API | Tên đường. |
| **9** | `longitude` | `float64` | Làm sạch | Kinh độ (nội suy theo tâm phường nếu khuyết/sai). |
| **10** | `latitude` | `float64` | Làm sạch | Vĩ độ (nội suy theo tâm phường nếu khuyết/sai). |
| **11** | `size_m2` | `float64` | Làm sạch | Diện tích (m²), miền hợp lệ [5; 120]. |
| **12** | `price_million` | `float64` | Làm sạch | **Biến mục tiêu:** giá thuê (triệu VNĐ/tháng), miền [0,5; 25]. |
| **13** | `price_per_m2_k` | `float64` | Tạo mới | Đơn giá (nghìn VNĐ/m²) = `price_million × 1000 / size_m2`. |
| **14** | `deposit_million` | `float64` | Điền khuyết | Tiền cọc (triệu VNĐ), khuyết thì điền theo trung vị tỉ lệ cọc/giá của quận. **Không dùng làm biến mô hình** (rò rỉ). |
| **15** | `furnishing_status` | `category` | Làm sạch | Nội thất: `Đầy đủ`, `Cơ bản`, `Nhà trống`, `Không rõ`. |
| **16** | `has_mezzanine` | `0/1` | Regex | Có gác (gác lửng, gác cao, gác đúc…). |
| **17** | `has_ac` | `0/1` | Regex | Có máy lạnh / điều hòa. |
| **18** | `is_free_curfew` | `0/1` | Regex | Giờ giấc tự do / không chung chủ / khóa vân tay. |
| **19** | `has_balcony_window` | `0/1` | Regex | Có ban công / cửa sổ / thoáng. |
| **20** | `dist_to_q1_km` | `float64` | Không gian | Khoảng cách Haversine (km) tới Chợ Bến Thành. |
| **21** | `dist_to_vnuhcm_km` | `float64` | Không gian | Khoảng cách Haversine (km) tới Khu đô thị ĐHQG-HCM. |
| **22** | `seller_type` | `category` | Hành vi | `Môi giới công khai` (tự khai môi giới trên Chợ Tốt, 4.520 tin) · `Môi giới trá hình` (tự khai cá nhân nhưng ≥ 4 tin hoặc đăng ở ≥ 2 quận, 104 tin) · `Chính chủ` (còn lại, 1.700 tin). |
| **23** | `market_cluster` | `category` | K-Means | Phân khúc: `Tier 1: Sinh viên/Bình dân`, `Tier 2: Tiện nghi tầm trung`, `Tier 3: Studio/Căn hộ dịch vụ`. |
| **24** | `predicted_price` | `float64` | LightGBM | Giá hợp lý (triệu VNĐ/tháng), **dự đoán out-of-fold**. Trống với tin `SHARED_DORM`. |
| **25** | `valuation_gap_pct` | `float64` | Mô hình | Độ lệch giá (%) = `(price_million − predicted_price) / predicted_price × 100`. Âm = rẻ hơn mặt bằng. |
| **26** | `deal_status` | `category` | Case study | `FAIR_PRICE`, `GOOD_DEAL`, `SCAM_RISK` (nghi vấn – cần kiểm chứng), `OVERPRICED`, `SHARED_DORM` — quy tắc ở mục 2.3. |

### 7.2. 18 cột mở rộng (dataset v2)
| Tên cột | Mô tả |
| :--- | :--- |
| `area_group` | `area_name` nhưng gộp các huyện < 30 tin thành "HCM - Ngoại thành khác" / "Bình Dương - Khác" (dùng cho so sánh nhóm) |
| `is_shared_or_dorm` | 1 = KTX / sleepbox / ở ghép (giá theo giường) — loại khỏi mô hình giá phòng |
| `is_main_street` | 1 = mặt tiền đường (cờ của API) |
| `is_alley` | 1 = địa chỉ trong hẻm/kiệt/ngõ |
| `has_price_change` | 1 = giá hiện tại khác giá đăng ban đầu |
| `price_change_pct` | % thay đổi so với giá đăng ban đầu (âm = đã giảm giá) |
| `listing_age_days` | Số ngày từ lúc đăng lần đầu tới lần đẩy tin gần nhất |
| `n_images` | Số ảnh đính kèm |
| `has_video` | 1 = có video |
| `is_paid_promo` | 1 = tin trả phí đẩy/ghim |
| `has_shop` | 1 = người đăng có trang cửa hàng trên Chợ Tốt |
| `seller_rating` | Điểm đánh giá trung bình người đăng (trống = chưa có) |
| `seller_n_ratings` | Số lượt đánh giá người đăng |
| `body_length` | Số ký tự mô tả |
| `account_ad_count` | Số tin của tài khoản trong mẫu |
| `account_n_areas` | Số quận/huyện tài khoản đăng tin trong mẫu |
| `is_iso_anomaly` | Isolation Forest đánh dấu bất thường |
| `anomaly_score` | Điểm bất thường (càng cao càng bất thường) |

`rental_cleaned_full.csv` chứa thêm toàn bộ trường gốc của API (tổng 140 cột).

---

## ⚠️ 8. Hạn chế đã biết
- **Thời gian:** dữ liệu là 2 lát cắt crawl ngày 10/11 và 21/11/2026 (tin đang hiển thị, đăng/đẩy từ 04/10 đến 21/11/2026), chưa đủ để kết luận xu hướng giá theo mùa.
- **Lấy mẫu có hạn ngạch** (140–300 tin mới nhất/quận) → tỉ lệ giữa các quận không phản ánh quy mô thật của thị trường; tin "biến mất" giữa 2 đợt có thể chỉ là bị đẩy ra ngoài top 300.
- **Bình Dương ít mẫu sạch** (537 → 276): 170 tin Bình Dương **không ghi diện tích** nên bị loại; nhiều huyện chỉ có 1–8 tin.
- **Giá niêm yết ≠ giá chốt**; tọa độ nhiều tin là tâm phường/đường (xấp xỉ); regex có sai số (đang kiểm tra độ chính xác bằng tay).
- **Địa giới hành chính:** dữ liệu dùng tên quận/huyện cũ (trước sáp nhập 01/07/2025); API có thêm tên phường mới (`ward_name_v3`).
- Nhãn bất thường **không có ground truth** — chỉ là gợi ý để kiểm chứng.
- Dữ liệu chứa thông tin công khai của người đăng (tên tài khoản, avatar): chỉ dùng cho phân tích, không công bố trong báo cáo/slide.
