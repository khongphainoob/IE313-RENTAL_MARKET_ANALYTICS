# 📊 Thư mục Dashboard & Trực quan hóa Tương tác

Thư mục này phục vụ Chương 4 (Dashboard & Trực quan hóa) của đồ án:

1. **`streamlit_app.py`**:
   - Ứng dụng Web tương tác viết bằng Python Streamlit.
   - Hỗ trợ: Bản đồ nhiệt không gian, Công cụ tính toán định giá phòng AI theo thời gian thực (Fair-Value Calculator), và Radar phát hiện kèo thơm / cảnh báo tin ảo.
   - Cách chạy:
     ```bash
     streamlit run dashboard/streamlit_app.py
     ```

2. **`IE313_Rental_Dashboard.pbix`**:
   - File thiết kế Dashboard trên **Microsoft Power BI Desktop**.
   - Nguồn dữ liệu kết nối trực tiếp: `data/processed/rental_scored_deals.csv` (26 cột chuẩn hóa).
   - Thiết kế gồm 3 trang báo cáo:
     - **Trang 1: Executive Market Overview** (KPIs, Bản đồ phân bố, Phân khúc thị trường theo Tier).
     - **Trang 2: Price Elasticity & Spatial Breakdown** (Biểu đồ suy giảm theo khoảng cách tới Q.1 / VNU-HCM, Tác động của các tiện ích máy lạnh/gác lửng).
     - **Trang 3: Deal & Scam Decision Matrix** (Scatter plot Actual Price vs Predicted Price, Bảng tra cứu tin đăng rủi ro cao / giá hời có liên kết URL Chợ Tốt).
