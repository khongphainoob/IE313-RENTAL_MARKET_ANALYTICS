# 🏠 Southern Vietnam Rental Market Analytics: Fair-Value Pricing & Scam Detection
> **Đồ án môn học:** IE313 - Phân tích và Trực quan hóa Dữ liệu (Data Analysis and Visualization)  
> **Trường:** Đại học Công nghệ Thông tin - ĐHQG TP.HCM (UIT - VNUHCM)  

---

## 📌 1. Giới thiệu bài toán (Project Overview & Case Study)
Thị trường thuê phòng trọ và căn hộ dịch vụ tại **TP. Hồ Chí Minh và Bình Dương** luôn sôi động nhưng tồn tại sự bất cân xứng thông tin lớn giữa người cho thuê/môi giới và người đi thuê (sinh viên, người lao động). Người thuê thường đối mặt với hai vấn đề:
1. **Không biết mức giá hợp lý (Fair Value):** Khó định lượng được việc đi xa trung tâm thêm vài km hay có thêm gác lửng, máy lạnh sẽ làm thay đổi giá thuê bao nhiêu.
2. **Bẫy "Tin ảo câu cọc" (Bait-and-Switch / Deposit Scams):** Các đối tượng môi giới trá hình đăng tin phòng cực đẹp với mức giá rẻ bất thường (thấp hơn 40-50% thị trường) để thu hút người thuê chuyển tiền giữ chỗ.

Dự án này xây dựng một **End-to-End Data Analytics Pipeline** tự thu thập hơn **15.000+ tin đăng thực tế** từ nền tảng **Chợ Tốt (Nhatot)**, thực hiện làm sạch đa tầng, phân tích thống kê không gian, huấn luyện mô hình định giá hợp lý và cung cấp Dashboard tương tác để phát hiện **"Kèo thơm (Good Deals)"** vs. **"Cảnh báo tin ảo (Scam Risks)"**.

---

## 🎯 2. Mục tiêu & Đóng góp chính (Key Deliverables)
- **Tự xây dựng Dataset thực tế (Data Acquisition):** Crawler phân tầng theo từng Quận/Huyện qua API Gateway của Chợ Tốt, thu thập đầy đủ thông tin giá, diện tích, tọa độ GPS và mô tả văn bản.
- **Tiền xử lý & Trích xuất đặc trưng nâng cao (Wrangling & Feature Engineering):**
  - Khử trùng lặp tin spam môi giới và lọc ngoại lai theo phân nhóm địa lý (**Grouped IQR by District**).
  - Trích xuất 6 đặc trưng tiện ích từ văn bản không cấu trúc bằng **NLP Regex** (`has_mezzanine`, `has_ac`, `is_free_curfew`...).
  - Tính toán khoảng cách không gian (**Haversine Distance**) đến Chợ Bến Thành (Q.1) và Khu Đô thị ĐHQG-HCM (Thủ Đức/Dĩ An).
- **Kiểm định giả thuyết thống kê (Statistical Hypothesis Testing):** Kiểm chứng toán học các nhận định thị trường bằng `Mann-Whitney U test`, `Kruskal-Wallis ANOVA` và `Spearman Correlation`.
- **Mô hình hóa & Giải quyết Case Study (Machine Learning):**
  - **Fair-Value Pricing:** So sánh `Ridge Regression`, `Random Forest` và `LightGBM` để định giá phòng.
  - **Scam & Deal Radar:** Kết hợp phân tích phần dư (**Residual Valuation Gap**) và thuật toán **Isolation Forest** để phân loại tin đăng.
- **Trực quan hóa đa nền tảng:** Ứng dụng Web **Streamlit** tích hợp bản đồ nhiệt và báo cáo **Microsoft Power BI**.

---

## 🛠️ 3. Hướng dẫn cài đặt và chạy dự án (Quick Start)

### Bước 1: Cài đặt môi trường
```bash
git clone https://github.com/khongphainoob/ie313-rental-market-analytics.git
cd ie313-rental-market-analytics
pip install -r requirements.txt
```

### Bước 2: Chạy Pipeline thu thập & xử lý dữ liệu
```bash
# 1. Cào dữ liệu từ API Chợ Tốt (TP.HCM & Bình Dương)
python -m src.crawler --regions 13000 2011 --max-per-area 1000

# 2. Làm sạch dữ liệu, lọc Outliers và trích xuất đặc trưng
python -m src.cleaner
python -m src.features

# 3. Huấn luyện mô hình định giá & chấm điểm bất thường
python -m src.models
```

### Bước 3: Khởi chạy Interactive Dashboard (Case Study App)
```bash
streamlit run dashboard/streamlit_app.py
```

---

## 📊 4. Cấu trúc các Jupyter Notebooks
1. `notebooks/01_data_collection_and_audit.ipynb`: Thống kê quy mô dữ liệu thô, tỷ lệ khuyết và kiểm toán chất lượng dữ liệu ban đầu.
2. `notebooks/02_data_cleaning_and_fe.ipynb`: Minh họa trực quan phân phối dữ liệu *Before vs. After* khi lọc ngoại lai IQR và kết quả trích xuất biến mới.
3. `notebooks/03_eda_and_statistical_tests.ipynb`: Phân tích đơn biến, hai biến, đa biến và bảng tổng hợp kết quả kiểm định giả thuyết ($p$-value).
4. `notebooks/04_modeling_and_case_study.ipynb`: Đánh giá mô hình ($R^2$, MAE, RMSE, MAPE), phân tích SHAP/Feature Importance và danh sách các phòng Good Deal / Scam Risk thực tế.

---

## 📁 5. Cấu trúc Repository (Repository Architecture)
```text
ie313-rental-market-analytics/
│
├── data/
│   ├── raw/
│   │   ├── chotot_raw_hcm_bd.jsonl        # Dữ liệu JSON Lines gốc cào trực tiếp từ API (Minh chứng gốc)
│   │   └── crawl_metadata.json            # Log thời gian cào, tổng số request, số bản ghi theo từng Quận
│   ├── interim/
│   │   └── deduplicated_data.parquet      # Dữ liệu sau khi gộp và khử trùng lặp
│   └── processed/
│       ├── rental_cleaned_full.csv        # Dataset sạch hoàn chỉnh (26 cột) dùng cho EDA & Modeling
│       ├── rental_scored_deals.csv        # Dataset đã gắn nhãn dự đoán & điểm bất thường (Import vào Power BI)
│       └── data_audit_report.json         # Thống kê số dòng bị loại ở từng bước (vẽ biểu đồ Data Funnel)
│
├── notebooks/
│   ├── 01_data_collection_and_audit.ipynb # Minh chứng quy trình crawl & Kiểm toán chất lượng dữ liệu thô
│   ├── 02_data_cleaning_and_fe.ipynb      # Tiền xử lý, xử lý khuyết/ngoại lai (IQR) & Regex/Geo Feature Engineering
│   ├── 03_eda_and_statistical_tests.ipynb # Trực quan hóa đơn/đa biến (Seaborn/Plotly) & Kiểm định giả thuyết
│   └── 04_modeling_and_case_study.ipynb   # Huấn luyện Regression, K-Means, Isolation Forest & Giải quyết Case Study
│
├── src/
│   ├── __init__.py
│   ├── config.py                          # Hằng số: Mã vùng, danh sách Quận/Huyện, tọa độ mốc, biểu thức Regex
│   ├── crawler.py                         # Script cào API Chợ Tốt phân tầng theo Quận/Huyện (vượt giới hạn phân trang)
│   ├── cleaner.py                         # Pipeline làm sạch, chuẩn hóa đơn vị, lọc Outliers theo IQR từng Quận
│   ├── features.py                        # Trích xuất đặc trưng văn bản (NLP Regex) & khoảng cách Haversine
│   ├── stats_tests.py                     # Các hàm kiểm định Mann-Whitney U, Kruskal-Wallis, Spearman
│   └── models.py                          # Pipeline huấn luyện Ridge, Random Forest, LightGBM & Isolation Forest
│
├── dashboard/
│   ├── streamlit_app.py                   # Web App tương tác: Bản đồ nhiệt, Định giá AI & Radar lọc phòng hời/tin ảo
│   └── IE313_Rental_Dashboard.pbix        # File báo cáo Microsoft Power BI (Đáp ứng Chương 4 đề cương)
│
├── reports/
│   ├── figures/                           # Hình ảnh biểu đồ độ phân giải cao (300 DPI) xuất tự động từ Notebook
│   ├── IE313_Final_Report.pdf             # Báo cáo toàn văn
│   └── IE313_Presentation_Slides.pptx     # Slide thuyết trình
│
├── models/
│   ├── lgbm_fair_price.joblib             # Model định giá đã huấn luyện
│   └── iso_forest_anomaly.joblib          # Model phát hiện bất thường
│
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 📋 6. Từ điển dữ liệu 26 cột (Data Dictionary)

| STT | Tên cột (Column Name) | Kiểu dữ liệu | Nguồn gốc | Mô tả chi tiết & Ý nghĩa phân tích |
| :---: | :--- | :---: | :---: | :--- |
| **1** | `ad_id` | `int64` | API Gốc | Mã định danh duy nhất của tin đăng (Primary Key). |
| **2** | `list_id` | `int64` | API Gốc | Mã bài viết dùng để tạo URL (`https://www.nhatot.com/{list_id}.htm`). |
| **3** | `account_id` | `int64` | API Gốc | Mã định danh tài khoản người đăng. |
| **4** | `list_time` | `datetime64` | Biến đổi | Thời gian đăng/cập nhật tin (chuyển từ Unix timestamp ms). |
| **5** | `region_name` | `category` | API Gốc | Tỉnh/Thành phố (`Tp Hồ Chí Minh`, `Bình Dương`). |
| **6** | `area_name` | `category` | API Gốc | Quận/Huyện/Thành phố (`Thành phố Thủ Đức`, `Quận Bình Thạnh`, `Thành phố Dĩ An`...). |
| **7** | `ward_name` | `category` | API Gốc | Phường/Xã (`Phường Linh Trung`, `Phường Đông Hòa`...). |
| **8** | `street_name` | `string` | API Gốc | Tên đường/trục đường chính. |
| **9** | `longitude` | `float64` | Làm sạch | Kinh độ địa lý (Đã nội suy theo tâm Phường nếu khuyết). |
| **10** | `latitude` | `float64` | Làm sạch | Vĩ độ địa lý (Đã nội suy theo tâm Phường nếu khuyết). |
| **11** | `size_m2` | `float64` | Làm sạch | Diện tích phòng ($m^2$), đã lọc miền hợp lệ $[5.0, 120.0]$. |
| **12** | `price_million` | `float64` | Làm sạch | **Biến mục tiêu ($Y$):** Giá thuê phòng (Triệu VNĐ/tháng), lọc miền $[0.5, 25.0]$. |
| **13** | `price_per_m2_k` | `float64` | Tạo mới | Đơn giá thuê trên mỗi $m^2$ (Nghìn VNĐ/$m^2$) = `(price_million * 1000) / size_m2`. |
| **14** | `deposit_million` | `float64` | Điền khuyết | Tiền đặt cọc (Triệu VNĐ) — Điền khuyết bằng Median tỷ lệ cọc theo Quận. |
| **15** | `furnishing_status` | `category` | Làm sạch | Tình trạng nội thất (`Đầy đủ`, `Cơ bản`, `Nhà trống`, `Không rõ`). |
| **16** | `has_mezzanine` | `int8 (0/1)` | NLP Regex | `1` nếu tiêu đề/mô tả có từ khóa *"có gác", "gác lửng", "gác cao"*. |
| **17** | `has_ac` | `int8 (0/1)` | NLP Regex | `1` nếu có *"máy lạnh", "điều hòa"*. |
| **18** | `is_free_curfew` | `int8 (0/1)` | NLP Regex | `1` nếu *"giờ giấc tự do", "không chung chủ", "khoá vân tay"*. |
| **19** | `has_balcony_window` | `int8 (0/1)` | NLP Regex | `1` nếu có *"ban công", "cửa sổ lớn", "thoáng mát"*. |
| **20** | `dist_to_q1_km` | `float64` | Geospatial | Khoảng cách đường chim bay Haversine (km) tới Chợ Bến Thành, Quận 1. |
| **21** | `dist_to_vnuhcm_km` | `float64` | Geospatial | Khoảng cách đường chim bay Haversine (km) tới Khu Đô thị ĐHQG-HCM (Thủ Đức/Dĩ An). |
| **22** | `seller_type` | `category` | Behavioral | Phân loại người đăng: `Chính chủ` (1-3 tin), `Môi giới công khai`, `Môi giới trá hình` ($\ge 4$ tin nhưng gắn nhãn cá nhân). |
| **23** | `market_cluster` | `category` | K-Means | Phân khúc phòng tự động: `Tier 1: Sinh viên/Bình dân`, `Tier 2: Tiện nghi tầm trung`, `Tier 3: Studio/Căn hộ dịch vụ`. |
| **24** | `predicted_price` | `float64` | LightGBM | Mức giá hợp lý ($\hat{y}$) do mô hình AI định giá (Triệu VNĐ/tháng). |
| **25** | `valuation_gap_pct` | `float64` | Modeling | Độ lệch giá (%) = `((price_million - predicted_price) / predicted_price) * 100`. |
| **26** | `deal_status` | `category` | Case Study | Nhãn phục vụ quyết định: `GOOD_DEAL` (Hời), `FAIR_PRICE` (Chuẩn), `OVERPRICED` (Đắt), `SCAM_RISK` (Nghi vấn tin ảo). |

