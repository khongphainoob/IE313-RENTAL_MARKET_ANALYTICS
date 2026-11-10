"""Interactive Streamlit Web Application: IE313 Rental Market Analytics.

Features:
1. Geospatial Market Analysis & Heatmaps (Distance decay, District comparisons)
2. AI Fair-Value Pricing Calculator (Real-time rental estimation)
3. Scam & Good Deal Radar (Valuation gap residual plots & flagged listings)
"""

from pathlib import Path
import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Setup page config
st.set_page_config(
    page_title="Rental Market Analytics | IE313",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent.parent
PROCESSED_SCORED_PATH = BASE_DIR / "data" / "processed" / "rental_scored_deals.csv"
PROCESSED_FULL_PATH = BASE_DIR / "data" / "processed" / "rental_cleaned_full.csv"
LGBM_MODEL_PATH = BASE_DIR / "models" / "lgbm_fair_price.joblib"


@st.cache_data
def load_data():
    """Load scored dataset if available, else load cleaned full dataset."""
    if PROCESSED_SCORED_PATH.exists():
        df = pd.read_csv(PROCESSED_SCORED_PATH)
    elif PROCESSED_FULL_PATH.exists():
        df = pd.read_csv(PROCESSED_FULL_PATH)
    else:
        st.warning("⚠️ Chưa tìm thấy dữ liệu đã làm sạch. Đang sử dụng dữ liệu mẫu mô phỏng để hiển thị giao diện.")
        # Generate representative mock data so the app runs smoothly out of the box
        np.random.seed(42)
        n = 1000
        districts = ["Quận 1", "Quận Bình Thạnh", "Quận Gò Vấp", "Thành phố Thủ Đức", "Thành phố Dĩ An", "Quận 7", "Quận Tân Bình"]
        sizes = np.random.uniform(15, 45, n)
        dists_q1 = np.random.uniform(1.5, 20.0, n)
        dists_vnu = np.random.uniform(1.0, 22.0, n)
        ac = np.random.binomial(1, 0.65, n)
        mezz = np.random.binomial(1, 0.45, n)
        curfew = np.random.binomial(1, 0.8, n)
        base_price = (sizes * 0.12) + (ac * 0.8) + (mezz * 0.4) - (dists_q1 * 0.08) + np.random.normal(0, 0.4, n)
        prices = np.clip(np.round(base_price + 1.8, 1), 1.2, 18.0)
        df = pd.DataFrame({
            "ad_id": np.arange(100000, 100000 + n),
            "list_id": np.arange(200000, 200000 + n),
            "area_name": np.random.choice(districts, n),
            "region_name": ["TP. Hồ Chí Minh"] * 850 + ["Bình Dương"] * 150,
            "ward_name": "Phường Mẫu",
            "street_name": "Đường Mẫu",
            "size_m2": np.round(sizes, 1),
            "price_million": prices,
            "price_per_m2_k": np.round((prices * 1000) / sizes, 1),
            "deposit_million": prices,
            "furnishing_status": np.random.choice(["Đầy đủ", "Cơ bản", "Nhà trống"], n),
            "has_mezzanine": mezz,
            "has_ac": ac,
            "is_free_curfew": curfew,
            "has_balcony_window": np.random.binomial(1, 0.5, n),
            "dist_to_q1_km": np.round(dists_q1, 1),
            "dist_to_vnuhcm_km": np.round(dists_vnu, 1),
            "latitude": 10.77 + (dists_q1 * 0.008) + np.random.normal(0, 0.01, n),
            "longitude": 106.69 + (dists_q1 * 0.008) + np.random.normal(0, 0.01, n),
            "seller_type": np.random.choice(["Chính chủ", "Môi giới công khai", "Môi giới trá hình"], n, p=[0.4, 0.35, 0.25]),
            "market_cluster": np.random.choice(["Tier 1: Sinh viên/Bình dân", "Tier 2: Tiện nghi tầm trung", "Tier 3: Studio/Căn hộ dịch vụ"], n),
            "predicted_price": prices + np.random.normal(0, 0.4, n),
        })
        df["valuation_gap_pct"] = np.round(((df["price_million"] - df["predicted_price"]) / df["predicted_price"]) * 100, 1)
        
        def assign_status(row):
            if row["valuation_gap_pct"] <= -25 and row["seller_type"] == "Môi giới trá hình":
                return "SCAM_RISK"
            elif row["valuation_gap_pct"] <= -15 and row["seller_type"] == "Chính chủ":
                return "GOOD_DEAL"
            elif row["valuation_gap_pct"] >= 20:
                return "OVERPRICED"
            return "FAIR_PRICE"
            
        df["deal_status"] = df.apply(assign_status, axis=1)
    return df


@st.cache_resource
def load_trained_model():
    """Load saved LightGBM model for interactive prediction."""
    if LGBM_MODEL_PATH.exists():
        try:
            return joblib.load(LGBM_MODEL_PATH)
        except Exception:
            return None
    return None


df_raw = load_data()
model_artifact = load_trained_model()

# ==========================================
# SIDEBAR CONTROLS & FILTERS
# ==========================================
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/619/619153.png", width=70)
st.sidebar.title("Bộ lọc Thị trường")

all_regions = sorted(df_raw["region_name"].dropna().unique().tolist())
selected_regions = st.sidebar.multiselect("Tỉnh / Thành phố", all_regions, default=all_regions)

filtered_by_region = df_raw[df_raw["region_name"].isin(selected_regions)]
all_districts = sorted(filtered_by_region["area_name"].dropna().unique().tolist())
selected_districts = st.sidebar.multiselect("Quận / Huyện", all_districts, default=all_districts[:6] if len(all_districts) > 6 else all_districts)

price_min, price_max = float(df_raw["price_million"].min()), float(df_raw["price_million"].max())
selected_price_range = st.sidebar.slider("Khoảng giá thuê (Triệu VNĐ/tháng)", price_min, price_max, (price_min, min(12.0, price_max)), step=0.5)

size_min, size_max = float(df_raw["size_m2"].min()), float(df_raw["size_m2"].max())
selected_size_range = st.sidebar.slider("Diện tích phòng (m²)", size_min, size_max, (size_min, min(60.0, size_max)), step=1.0)

# Filter dataset
df = df_raw[
    (df_raw["region_name"].isin(selected_regions))
    & (df_raw["area_name"].isin(selected_districts))
    & (df_raw["price_million"] >= selected_price_range[0])
    & (df_raw["price_million"] <= selected_price_range[1])
    & (df_raw["size_m2"] >= selected_size_range[0])
    & (df_raw["size_m2"] <= selected_size_range[1])
].copy()

# ==========================================
# HEADER & OVERVIEW KPIS
# ==========================================
st.title("🏠 Southern Vietnam Rental Market Analytics")
st.markdown(
    "**Đồ án môn học IE313 - Phân tích và Trực quan hóa Dữ liệu | UIT - VNUHCM**  \n"
    "*Mô hình Định giá Hợp lý (Fair-Value Pricing) & Hệ thống Phát hiện Bất thường (Scam & Good Deal Radar)*"
)

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric("Tổng tin đăng đang lọc", f"{len(df):,} tin")
with col2:
    med_price = df["price_million"].median() if not df.empty else 0
    st.metric("Giá thuê trung vị", f"{med_price:.1f} tr/th")
with col3:
    med_m2 = df["price_per_m2_k"].median() if not df.empty else 0
    st.metric("Đơn giá trung vị", f"{med_m2:.0f} k/m²")
with col4:
    deals_count = (df["deal_status"] == "GOOD_DEAL").sum() if "deal_status" in df.columns else 0
    st.metric("Kèo thơm (Good Deals)", f"{deals_count} tin", delta="Cơ hội thuê", delta_color="normal")
with col5:
    scam_count = (df["deal_status"] == "SCAM_RISK").sum() if "deal_status" in df.columns else 0
    st.metric("Nghi vấn tin ảo (Scam Risk)", f"{scam_count} tin", delta="-Rủi ro cọc", delta_color="inverse")

st.markdown("---")

# ==========================================
# MAIN APPLICATION TABS
# ==========================================
tab_eda, tab_pricing, tab_radar = st.tabs([
    "🗺️ 1. Góc nhìn Thị trường & Không gian",
    "🤖 2. Mô hình Định giá AI (Fair-Value Calculator)",
    "🎯 3. Radar Kèo thơm & Cảnh báo Tin ảo (Scam Radar)",
])

# ------------------------------------------
# TAB 1: GEOSPATIAL MARKET EDA
# ------------------------------------------
with tab_eda:
    st.subheader("Phân tích Không gian & Suy giảm Giá thuê theo Khoảng cách (Spatial Distance Decay)")
    
    col_map, col_decay = st.columns([1.1, 0.9])
    with col_map:
        st.markdown("##### 📍 Bản đồ phân bố phòng trọ & Mức giá")
        if not df.empty and "latitude" in df.columns and "longitude" in df.columns:
            fig_map = px.scatter_mapbox(
                df.sample(min(800, len(df)), random_state=42),
                lat="latitude",
                lon="longitude",
                color="price_million",
                size="size_m2",
                hover_name="area_name",
                hover_data={"price_million": ":.2f", "size_m2": ":.1f", "price_per_m2_k": ":.0f"},
                color_continuous_scale="Viridis",
                zoom=10,
                center={"lat": 10.7769, "lon": 106.7009},
                mapbox_style="carto-positron",
                height=420,
            )
            fig_map.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.info("Không có đủ tọa độ để vẽ bản đồ.")

    with col_decay:
        st.markdown("##### 📉 Đi xa trung tâm 1 km thì tiết kiệm bao nhiêu?")
        if not df.empty:
            fig_decay = px.scatter(
                df.sample(min(800, len(df)), random_state=42),
                x="dist_to_q1_km",
                y="price_per_m2_k",
                color="area_name",
                trendline="ols",
                labels={"dist_to_q1_km": "Khoảng cách tới Quận 1 (km)", "price_per_m2_k": "Đơn giá (Nghìn VNĐ/m²)"},
                title="Quy luật suy giảm đơn giá thuê theo cự ly tới Chợ Bến Thành",
                height=420,
            )
            fig_decay.update_layout(showlegend=False)
            st.plotly_chart(fig_decay, use_container_width=True)

    st.markdown("---")
    st.subheader("Phân phối Giá thuê & Đơn giá giữa các Quận")
    col_box1, col_box2 = st.columns(2)
    with col_box1:
        if not df.empty:
            fig_box1 = px.box(
                df,
                x="area_name",
                y="price_million",
                color="area_name",
                labels={"area_name": "Quận/Huyện", "price_million": "Giá thuê (Triệu/tháng)"},
                title="Phân phối Tổng giá thuê (price_million)",
            )
            fig_box1.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_box1, use_container_width=True)
    with col_box2:
        if not df.empty:
            fig_box2 = px.box(
                df,
                x="area_name",
                y="price_per_m2_k",
                color="area_name",
                labels={"area_name": "Quận/Huyện", "price_per_m2_k": "Đơn giá (k/m²)"},
                title="Phân phối Đơn giá thuê theo m² (price_per_m2_k)",
            )
            fig_box2.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig_box2, use_container_width=True)

# ------------------------------------------
# TAB 2: AI FAIR-VALUE PRICING CALCULATOR
# ------------------------------------------
with tab_pricing:
    st.subheader("🤖 Công cụ Định giá Phòng trọ Hợp lý (Fair-Value Regression Calculator)")
    st.markdown("Nhập thông số căn phòng bạn định thuê hoặc đăng cho thuê để mô hình AI ước tính mức giá chuẩn thị trường:")

    with st.form("pricing_form"):
        p_col1, p_col2, p_col3 = st.columns(3)
        with p_col1:
            input_district = st.selectbox("Quận / Huyện", all_districts, index=0)
            input_size = st.number_input("Diện tích phòng (m²)", min_value=8.0, max_value=100.0, value=25.0, step=1.0)
            input_furnish = st.selectbox("Nội thất", ["Đầy đủ", "Cơ bản", "Nhà trống"])

        with p_col2:
            input_dist_q1 = st.slider("Khoảng cách tới Quận 1 (km)", 0.5, 30.0, 7.5, step=0.5)
            input_dist_vnu = st.slider("Khoảng cách tới Làng Đại học ĐHQG (km)", 0.5, 30.0, 12.0, step=0.5)
            input_seller = st.selectbox("Người đăng", ["Chính chủ", "Môi giới công khai", "Môi giới trá hình"])

        with p_col3:
            st.markdown("**Tiện ích đi kèm:**")
            input_ac = st.checkbox("Có máy lạnh / điều hòa", value=True)
            input_mezz = st.checkbox("Có gác lửng / gác đúc", value=True)
            input_curfew = st.checkbox("Giờ giấc tự do / Khoá vân tay", value=True)
            input_balcony = st.checkbox("Có ban công / Cửa sổ lớn", value=False)
            input_deposit = st.number_input("Tiền cọc dự kiến (Triệu VNĐ)", min_value=0.0, max_value=20.0, value=3.5, step=0.5)

        calc_submitted = st.form_submit_button("🚀 Tính toán Mức giá Hợp lý (Predict Fair Price)")

    if calc_submitted:
        # If model artifact exists, run model prediction, otherwise run robust econometric formula
        if model_artifact and "model" in model_artifact and "feature_names" in model_artifact:
            model = model_artifact["model"]
            feat_names = model_artifact["feature_names"]
            input_dict = {f: 0.0 for f in feat_names}
            input_dict["size_m2"] = float(input_size)
            input_dict["dist_to_q1_km"] = float(input_dist_q1)
            input_dict["dist_to_vnuhcm_km"] = float(input_dist_vnu)
            input_dict["deposit_million"] = float(input_deposit)
            input_dict["has_mezzanine"] = 1.0 if input_mezz else 0.0
            input_dict["has_ac"] = 1.0 if input_ac else 0.0
            input_dict["is_free_curfew"] = 1.0 if input_curfew else 0.0
            input_dict["has_balcony_window"] = 1.0 if input_balcony else 0.0

            # Match dummy variables
            for f in feat_names:
                if f"area_name_{input_district}" == f:
                    input_dict[f] = 1.0
                if f"furnishing_status_{input_furnish}" == f:
                    input_dict[f] = 1.0
                if f"seller_type_{input_seller}" == f:
                    input_dict[f] = 1.0

            X_in = pd.DataFrame([input_dict])[feat_names]
            predicted_val = float(model.predict(X_in)[0])
        else:
            # Calibrated econometric regression fallback
            base_sqm_rate = 120.0  # k/m2
            if "Quận 1" in input_district or "Quận 3" in input_district:
                base_sqm_rate = 220.0
            elif "Bình Thạnh" in input_district or "Phú Nhuận" in input_district or "Quận 10" in input_district:
                base_sqm_rate = 175.0
            elif "Thủ Đức" in input_district or "Gò Vấp" in input_district or "Tân Bình" in input_district:
                base_sqm_rate = 145.0
            elif "Dĩ An" in input_district or "Thuận An" in input_district:
                base_sqm_rate = 100.0

            rent_est = (input_size * base_sqm_rate / 1000.0)
            if input_ac:
                rent_est += 0.65
            if input_mezz:
                rent_est += 0.4
            if input_balcony:
                rent_est += 0.3
            if input_furnish == "Đầy đủ":
                rent_est += 0.8
            predicted_val = rent_est

        predicted_val = max(0.8, round(predicted_val, 2))
        lower_bound = max(0.6, round(predicted_val * 0.9, 2))
        upper_bound = round(predicted_val * 1.1, 2)
        price_per_m2 = round((predicted_val * 1000) / input_size, 1)

        st.success("### 🎯 Kết quả Ước tính Mức giá Hợp lý (Fair-Value):")
        res_col1, res_col2, res_col3 = st.columns(3)
        with res_col1:
            st.metric("Giá thuê hợp lý gợi ý", f"{predicted_val:.2f} Triệu/tháng")
        with res_col2:
            st.metric("Khoảng giá hợp lý (±10%)", f"{lower_bound:.2f} - {upper_bound:.2f} Triệu")
        with res_col3:
            st.metric("Đơn giá ước tính", f"{price_per_m2:.0f} Nghìn VNĐ/m²")

        st.markdown(
            f"""
            > **Nhận định từ mô hình:**
            > - Căn phòng diện tích **{input_size} m²** tại **{input_district}** có tiện ích chính (Máy lạnh: {'Có' if input_ac else 'Không'}, Gác lửng: {'Có' if input_mezz else 'Không'}).
            > - Nếu chủ nhà chào giá **thấp hơn {lower_bound:.2f} triệu** $\\rightarrow$ *Kèo thơm tiềm năng* (kiểm tra kỹ uy tín để tránh bẫy tin ảo).
            > - Nếu chủ nhà chào giá **cao hơn {upper_bound:.2f} triệu** $\\rightarrow$ *Mức giá đắt hơn thị trường ({((upper_bound - predicted_val)/predicted_val)*100:.0f}%)*, bạn hoàn toàn có thể thương lượng giảm giá!
            """
        )

# ------------------------------------------
# TAB 3: SCAM & GOOD DEAL RADAR
# ------------------------------------------
with tab_radar:
    st.subheader("🎯 Radar Phát hiện Kèo thơm & Cảnh báo Tin ảo (Scam & Good Deal Radar)")
    st.markdown(
        "Hệ thống phát hiện bất thường phân tách giữa **Kèo thơm giá hời (Good Deals)** và **Tin ảo bẫy cọc (Scam Risks)** "
        "dựa trên phân tích phần dư định giá (**Valuation Gap %**) kết hợp phân loại hành vi người đăng."
    )

    if "deal_status" in df.columns and "valuation_gap_pct" in df.columns:
        col_scatter, col_metrics = st.columns([1.2, 0.8])
        with col_scatter:
            st.markdown("##### 🔍 Đồ thị Định giá & Điểm bất thường (Actual vs. Fair-Value Price)")
            sample_df = df.sample(min(800, len(df)), random_state=42)
            color_map = {
                "GOOD_DEAL": "#00CC96",     # Green
                "FAIR_PRICE": "#636EFA",    # Blue
                "OVERPRICED": "#FFA15A",    # Orange
                "SCAM_RISK": "#EF553B",     # Red
            }
            fig_gap = px.scatter(
                sample_df,
                x="predicted_price",
                y="price_million",
                color="deal_status",
                color_discrete_map=color_map,
                hover_name="area_name",
                hover_data=["size_m2", "valuation_gap_pct", "seller_type"],
                labels={"predicted_price": "Giá AI Định giá (Triệu)", "price_million": "Giá Thực tế Đăng bán (Triệu)"},
                title="Độ lệch giữa Giá đăng và Giá hợp lý (Đường chéo = Giá cân bằng)",
                height=440,
            )
            # Add 45 degree line
            max_p = max(sample_df["predicted_price"].max(), sample_df["price_million"].max())
            fig_gap.add_trace(go.Scatter(x=[0, max_p], y=[0, max_p], mode="lines", line=dict(color="gray", dash="dash"), name="Đường Cân bằng"))
            st.plotly_chart(fig_gap, use_container_width=True)

        with col_metrics:
            st.markdown("##### 📊 Tiêu chí Phân loại Radar")
            st.markdown(
                """
                * 🟢 **GOOD_DEAL (Kèo thơm):**
                  * Rẻ hơn $\\ge 15\\%$ so với giá hợp lý của AI.
                  * Đăng bởi **Chính chủ** (tài khoản đăng 1-3 tin).
                * 🔴 **SCAM_RISK (Cảnh báo Tin ảo):**
                  * Rẻ bất thường $\\ge 25\\%$ so với mặt bằng chung.
                  * Đăng bởi **Môi giới trá hình** (tài khoản cá nhân nhưng đăng nhiều tin) hoặc có điểm dị biệt Isolation Forest cao.
                * 🟡 **OVERPRICED (Đắt):**
                  * Đắt hơn $\\ge 20\\%$ so với giá trị thực tế của phòng.
                * 🔵 **FAIR_PRICE (Hợp lý):**
                  * Nằm trong khoảng biến động tự nhiên $[-15\\%, +20\\%]$.
                """
            )

        st.markdown("---")
        st.subheader("📋 Danh sách Tin đăng theo Bộ lọc Radar")
        status_filter = st.selectbox("Chọn nhóm tin cần kiểm tra:", ["GOOD_DEAL", "SCAM_RISK", "FAIR_PRICE", "OVERPRICED"], index=0)
        
        deals_sub = df[df["deal_status"] == status_filter].copy()
        st.write(f"Tìm thấy **{len(deals_sub)}** tin đăng thỏa mãn trạng thái **{status_filter}**:")

        display_cols = [
            "ad_id",
            "area_name",
            "ward_name",
            "size_m2",
            "price_million",
            "predicted_price",
            "valuation_gap_pct",
            "seller_type",
            "has_ac",
            "has_mezzanine",
        ]
        available_display_cols = [c for c in display_cols if c in deals_sub.columns]
        st.dataframe(
            deals_sub[available_display_cols].sort_values("valuation_gap_pct", ascending=True),
            use_container_width=True,
            height=300,
        )
    else:
        st.info("Chưa có cột deal_status. Vui lòng chạy pipeline huấn luyện mô hình (src.models) trước.")

st.markdown("---")
st.caption("IE313 Data Analysis & Visualization Final Project | University of Information Technology - VNUHCM")
