# 📦 BÀN GIAO CÔNG VIỆC — THÀNH VIÊN B

> Đồ án IE313 – Phân tích thị trường phòng trọ TP.HCM & Bình Dương (dữ liệu Chợ Tốt)
> Bàn giao ngày 21/11/2026 · Người bàn giao: Hoàng (A) · Hạn nộp dự kiến: **13/12/2026**
> Kế hoạch tổng của cả nhóm: [`reports/KE_HOACH_3_TUAN.md`](KE_HOACH_3_TUAN.md). File này chỉ ghi **phần việc của B**.

---

## 1. Tóm tắt trong 1 phút

- Nhóm đã crawl phòng trọ từ Chợ Tốt (30 quận/huyện) qua nhiều đợt, gộp được **7.046 tin** không trùng, làm sạch còn **6.324 tin**. Crawl tự động mỗi tối nên con số còn tăng tới ngày đóng băng (CN 29/11).
- Code thu thập, làm sạch, mô hình đã có trong `src/`. **Phần còn thiếu là phân tích, biểu đồ, báo cáo, slide** — phần này B phụ trách chính.
- Chia việc theo "tầng":
  - **A** lo phần **thượng nguồn**: crawler, làm sạch, ghép feature, mô hình, Streamlit.
  - **B** lo phần **hạ nguồn**: feature từ văn bản & bản đồ, EDA, kiểm định thống kê, Power BI, báo cáo, slide.
- Để không giẫm chân nhau trên git, mỗi người **chỉ sửa file của mình** (bảng ở mục 3).

**Vai trò của B trong đồ án:** trả lời 3 câu hỏi nghiên cứu
- **RQ1** – Mặt bằng giá thuê hiện nay ra sao, khác nhau thế nào giữa các khu vực?
- **RQ3** – Mỗi tiện ích (máy lạnh, gác, WC riêng…) đáng giá bao nhiêu % khi đã tính tới diện tích và vị trí?
- **RQ4** – Chính chủ và môi giới khác nhau thế nào?

(A trả lời RQ2-phần mô hình và RQ5 – định giá & tin bất thường. B vẫn phải hiểu hai phần này để vấn đáp.)

---

## 2. Cài đặt (làm ngay hôm nay, ~30 phút)

```bash
git clone https://github.com/khongphainoob/IE313-RENTAL_MARKET_ANALYTICS.git
cd IE313-RENTAL_MARKET_ANALYTICS
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
jupyter notebook                # hoặc mở bằng VS Code
```

Kiểm tra chạy được:
```bash
python -c "import pandas as pd; print(pd.read_csv('data/processed/rental_cleaned_full.csv').shape)"
# kỳ vọng: (6324, 140)
```

> 🆕 **Cập nhật 21/11 (A đã làm xong phần sửa lỗi):**
> - **Dữ liệu đã lên v2 sớm:** gộp đợt 10/11 + 21/11 = **7.046 tin thô → 6.324 tin sạch** (giữ 89.75%). Dùng luôn bản này; CN 29/11 A chạy lại lần cuối với các đợt crawl thêm (B chỉ cần Restart & Run All).
> - Bản thô gộp: `data/raw/merged/chotot_merged_raw.jsonl.gz` (mở bằng `pd.read_json(path, lines=True)`; muốn CSV/Excel thì chạy `python -m src.merge_snapshots`). Có thêm cột `_first_seen`, `_last_seen`, `_n_seen`, `_price_first_seen`.
> - Mô hình đã bỏ tiền cọc, dùng out-of-fold. R² CV thật = **0.67** (baseline 0.40). Kết quả chi tiết: `data/processed/model_report.json`.
> - Cột mới B dùng được ngay: `area_group` (gộp 5 huyện ít mẫu — **dùng cột này cho boxplot/Kruskal-Wallis**), `is_shared_or_dorm` (KTX/sleepbox/ở ghép, giá theo giường), `is_main_street`, `is_alley`, `has_price_change`, `price_change_pct`, `listing_age_days`, `n_images`, `has_video`, `is_paid_promo`, `has_shop`, `seller_rating`, `seller_n_ratings`, `body_length`, `account_n_areas`. Đưa hết vào bảng B1.
> - ⚠️ **Mọi phân tích giá phòng (B5, B6) lọc `is_shared_or_dorm == 0`**; KTX/ở ghép phân tích riêng như 1 phân khúc (giá theo giường). Kiểm tra độ chính xác cờ này luôn trong B2.
> - Nhãn `deal_status` giờ có thêm `SHARED_DORM`.

**Đọc trước (theo thứ tự, ~1–2 giờ):**
1. `README.md` — tổng quan đề tài
2. `data/DATASET_DESCRIPTION.txt` — từ điển 26 cột cuối
3. `reports/CRAWLING_PLAN.md` — dữ liệu được lấy thế nào
4. `reports/KE_HOACH_3_TUAN.md` mục 0 — **các lỗi đã phát hiện** (quan trọng)

**Hai file dữ liệu B sẽ dùng:**
| File | Dùng khi nào |
|---|---|
| `data/processed/rental_cleaned_full.csv` (118 cột, **có cột `body` mô tả tin**) | Làm regex, làm feature, EDA |
| `data/processed/rental_scored_deals.csv` (26 cột gọn) | Power BI, bảng tóm tắt |

> ⚠️ Từ nay đến CN 29/11, dữ liệu là **bản v1** — cứ dùng để viết code và vẽ nháp. CN 29/11 A giao **bản v2** (thêm cột, sửa lỗi), lúc đó B chỉ cần **Restart & Run All** lại notebook.

---

## 3. Quy ước làm việc chung

### File B được sửa / tạo
| File | Ghi chú |
|---|---|
| `src/text_features.py` (**tạo mới**) | Toàn bộ regex mới. Xuất 1 hàm `add_text_features(df) -> df` |
| `src/external_features.py` (**tạo mới**) | Feature POI OpenStreetMap. Xuất 1 hàm `add_poi_features(df) -> df` |
| `data/external/` (**tạo mới**) | File POI `.csv`, ranh giới `.geojson` |
| `notebooks/03_eda_and_statistical_tests.ipynb` | Notebook chính của B |
| `src/stats_tests.py` | Được thêm hàm mới |
| `reports/hieu_du_lieu.md`, `reports/regex_check/`, `reports/figures/03_*.png` | Đầu ra của B |
| `dashboard/IE313_Rental_Dashboard.pbix` | Power BI |

**Không sửa** `src/cleaner.py`, `src/features.py`, `src/models.py`, `src/crawler.py`, notebook 01/02/04 — đó là phần A. Cần thay đổi gì ở đó thì nhắn A. A sẽ gọi `add_text_features` và `add_poi_features` của B bên trong `src/features.py`.

### Git
- Không push thẳng lên `main`. Mỗi việc 1 nhánh: `b/regex`, `b/poi`, `b/eda`, `b/stats`…
- Xong việc → mở Pull Request → A review rồi merge. A làm cũng sẽ nhờ B review như vậy.
- Commit message dạng: `feat(text): thêm regex wc riêng, máy giặt` / `docs: hiểu dữ liệu nhóm 2`.
- Trước khi commit notebook: **Restart & Run All** để output khớp với code.

### Chuẩn biểu đồ (áp dụng cho mọi hình)
```python
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = "DejaVu Sans"   # hiển thị được tiếng Việt
FIG_DIR = Path("..") / "reports" / "figures"

def save_fig(name):
    plt.savefig(FIG_DIR / f"03_{name}.png", dpi=300, bbox_inches="tight")
```
Mỗi biểu đồ phải có: tiêu đề · nhãn trục **kèm đơn vị** (triệu VNĐ/tháng, nghìn VNĐ/m², km) · chú thích "Nguồn: Chợ Tốt, 11/2026, n = …" · **1 ô markdown ngay bên dưới ghi kết luận** (biểu đồ không có kết luận = mất điểm).

### Dữ liệu cá nhân
File thô có `account_name`, `full_name`, `avatar`, `facebook_id`. **Không đưa các cột này vào slide, báo cáo hay Power BI.** Khi chụp màn hình tin đăng, che tên và số điện thoại.

### Liên lạc
- Nhắn ngay khi bị kẹt quá **2 tiếng** — đừng ngồi một mình.
- 3 buổi họp cố định: **CN 29/11**, **CN 06/12**, **T7 12/12** (chi tiết ở mục 5).

---

## 4. DANH SÁCH VIỆC CỦA B

Ký hiệu: ⏰ hạn · 📥 cần gì từ A · 📤 nộp gì · ✅ thế nào là xong

### TUẦN 1 (23/11 – 29/11) — Hiểu dữ liệu & làm thêm feature

#### B1. Bảng "hiểu từng cột" ⏰ T4 25/11
Tạo `reports/hieu_du_lieu.md`, mỗi cột trong 26 cột cuối (+ các cột thô mục 2.A trong kế hoạch tổng) là 1 dòng:

| Cột | Ý nghĩa | Nguồn (API / tính ra / regex / mô hình) | Kiểu & miền giá trị | % khuyết & cách xử lý | Phân phối (1 câu) | Lỗi/nhiễu đã thấy | Dự đoán quan hệ với giá |
|---|---|---|---|---|---|---|---|

- Dùng `df[col].describe()`, `value_counts()`, `isna().mean()`, vẽ nhanh histogram.
- 📤 File md. ✅ Đủ hết cột; A đọc và không có câu hỏi nào chưa trả lời được.
- 💡 Đây là việc giúp B **trả lời được mọi câu hỏi về dữ liệu** khi vấn đáp — đừng làm qua loa.

#### B2. Regex tiện ích mới + kiểm tra độ chính xác ⏰ T6 27/11
Viết vào `src/text_features.py`. Dữ liệu: `text = (subject + " " + body).lower()`.

| Cột mới | Gợi ý từ khóa | Tỉ lệ đo sơ bộ |
|---|---|---|
| `has_kitchen` | bếp, kệ bếp | 31.8% |
| `has_washing_machine` | máy giặt | 25.6% |
| `has_parking` | để xe, giữ xe, hầm xe | 22.9% |
| `has_elevator` | thang máy | 14.1% |
| `has_private_wc` | wc riêng, vệ sinh riêng, toilet riêng, wc trong phòng | 13.6% |
| `female_only` | chỉ nhận nữ, ưu tiên nữ | ~5% |
| `allow_pet` | nuôi thú cưng, nuôi chó/mèo | ~2.6% |
| `shared_room` | ở ghép, tìm người ở ghép | ~2.3% |
| `elec_price_k` (**số**, không phải 0/1) | "điện 3.5k", "điện 4k/kwh", "điện 3500đ" → trích **con số** | 13.8% |
| `water_price_k` (số, tùy chọn) | "nước 100k/người", "nước 20k/khối" | — |

Cẩn thận phủ định & bắt nhầm: *"không có máy giặt"*, *"bếp chung"* (khác bếp riêng), *"gần chợ"* chứa "chợ"…

**Kiểm tra độ chính xác (bắt buộc, giảng viên rất hay hỏi):**
1. Với mỗi cột 0/1: lấy ngẫu nhiên 30 tin có flag = 1 và 20 tin flag = 0 (`df.sample(..., random_state=42)`).
2. Xuất ra `reports/regex_check/<ten_cot>.csv` gồm `ad_id`, đoạn text quanh từ khóa (~80 ký tự), flag, cột `dung_khong` để B tự điền Đ/S.
3. Tính precision = số Đ trong 30 tin flag=1 / 30. Nếu < 80% → sửa regex rồi kiểm lại.
4. Gom thành 1 bảng tổng `reports/regex_check/TONG_HOP.md` (cột, precision, ví dụ bắt nhầm, đã sửa gì). Làm luôn cho **4 regex cũ** (`has_ac`, `has_mezzanine`, `is_free_curfew`, `has_balcony_window`).

- 📤 `src/text_features.py` + thư mục `reports/regex_check/`. ✅ Mọi regex precision ≥ 80%, có bảng tổng hợp.

#### B3. Dữ liệu OpenStreetMap ⏰ T7 28/11
Viết vào `src/external_features.py`, lưu dữ liệu thô vào `data/external/`.

Lấy tọa độ bằng Overpass API (miễn phí, không cần key):
```python
import requests, pandas as pd

BBOX = "10.35,106.35,11.50,107.00"   # nam, tây, bắc, đông: phủ HCM + Bình Dương

def overpass(selector: str) -> pd.DataFrame:
    q = f'[out:json][timeout:180];({selector}({BBOX}););out center;'
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": q}, timeout=200)
    r.raise_for_status()
    rows = []
    for e in r.json()["elements"]:
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        rows.append({"name": e.get("tags", {}).get("name"), "lat": lat, "lon": lon})
    return pd.DataFrame(rows).dropna(subset=["lat", "lon"])

uni = pd.concat([overpass('nwr["amenity"="university"]'), overpass('nwr["amenity"="college"]')])
uni.to_csv("data/external/poi_university.csv", index=False)
```
Các nhóm POI cần lấy:
| File | Selector gợi ý | Ghi chú |
|---|---|---|
| `poi_university.csv` | `amenity=university`, `amenity=college` | |
| `poi_metro.csv` | `nwr["railway"="station"]` rồi lọc tay | Chỉ giữ **14 ga Metro số 1** (Bến Thành – Suối Tiên); thiếu thì gõ tay tọa độ từ Google Maps |
| `poi_industrial.csv` | `nwr["landuse"="industrial"]["name"~"Khu công nghiệp\|KCN"]` | Quan trọng cho Bình Dương |
| `poi_market.csv` | `amenity=marketplace`, `shop=supermarket` | |

Tính khoảng cách tới điểm gần nhất và mật độ POI:
```python
import numpy as np
from sklearn.neighbors import BallTree
R = 6371.0

def nearest_km(df, poi):
    tree = BallTree(np.radians(poi[["lat", "lon"]].values), metric="haversine")
    d, _ = tree.query(np.radians(df[["latitude", "longitude"]].values), k=1)
    return d[:, 0] * R

def count_within(df, poi, km=1.0):
    tree = BallTree(np.radians(poi[["lat", "lon"]].values), metric="haversine")
    return tree.query_radius(np.radians(df[["latitude", "longitude"]].values), r=km / R, count_only=True)
```
Cột mới: `dist_nearest_university_km`, `dist_nearest_metro_km`, `dist_nearest_industrial_km`, `n_market_1km`.

**Ranh giới hành chính để vẽ bản đồ:** tải GADM Việt Nam level 2 (quận/huyện **cũ**, khớp với `area_name` trong dữ liệu) → lọc HCM + Bình Dương → `data/external/districts_hcm_bd.geojson`. Tên quận trong GADM viết khác (không dấu, "Quan 1"…) → làm bảng ánh xạ tên.

> Lưu ý hành chính: từ 01/07/2025 Bình Dương đã nhập vào TP.HCM và bỏ cấp quận/huyện. Chợ Tốt vẫn trả cả tên cũ (`area_name`, `ward_name`) và tên phường mới (`ward_name_v3`). Nhóm phân tích theo **ranh giới cũ** vì đó là đơn vị có đủ dữ liệu — ghi rõ điều này trong báo cáo.

- 📤 `src/external_features.py`, `data/external/*`. ✅ Hàm `add_poi_features(df)` chạy trên `rental_cleaned_full.csv` không lỗi; in ra `describe()` các cột mới thấy hợp lý (khoảng cách 0–40 km).

#### B4. Họp 1 ⏰ CN 29/11 (1 tiếng)
- A giải thích pipeline làm sạch + lỗi leakage tiền cọc đã sửa ra sao.
- B trình bày bảng hiểu dữ liệu + regex + POI.
- 📥 **Nhận từ A: dataset v2** (đã ghép feature của B, có cột `area_group` gộp các huyện ít mẫu).

---

### TUẦN 2 (30/11 – 06/12) — Phân tích (notebook 03)

Cấu trúc notebook 03 nên chia thành các phần đúng theo câu hỏi nghiên cứu:

#### B5. Phần 1 – Bức tranh thị trường (RQ1) ⏰ T3 01/12
- Histogram + KDE của `price_million`, `size_m2`, `price_per_m2_k` (thêm 1 bản thang log).
- Kiểm tra **giá làm tròn**: % tin có giá là bội của 0.5 triệu → nói lên điều gì về cách chủ trọ đặt giá?
- Bar chart tỉ lệ có tiện ích (cũ + mới), tình trạng nội thất, loại người đăng.
- Boxplot `price_per_m2_k` theo `area_group`, **sắp theo median**, tô 2 màu HCM cũ / Bình Dương cũ.
- Bảng: median giá, median diện tích, median đơn giá, n theo từng quận.
- **Bản đồ**: choropleth đơn giá trung vị theo quận (Plotly `choropleth_mapbox` + GeoJSON ở B3). Thêm 1 bản hexbin theo tọa độ. **Không** vẽ chấm từng tin (47% tin trùng tọa độ vì bị gán tâm phường).
- Distance decay (phần mô tả): scatter `dist_to_q1_km` vs `price_per_m2_k` + LOWESS; bảng median theo vành đai 0–3 / 3–6 / 6–10 / 10–15 / >15 km.
- 📤 ~8–10 hình `03_*.png`.

#### B6. Phần 2 – Kiểm định & định giá tiện ích (RQ3, RQ4) ⏰ T5 03/12
**(a) Premium thô của từng tiện ích**
- Mann-Whitney U (có vs không) cho từng tiện ích → p-value.
- **Effect size**: rank-biserial `r = 2U/(n1·n2) − 1` (vì p nhỏ chưa chắc ảnh hưởng lớn).
- Hiệu chỉnh đa kiểm định: `statsmodels.stats.multitest.multipletests(pvals, method="holm")`.
- Premium thô = (median có − median không) / median không × 100%.

**(b) Premium có kiểm soát — hồi quy hedonic (phần "ăn điểm" nhất)**
```python
import numpy as np
import statsmodels.formula.api as smf

df["log_price"] = np.log(df["price_million"])
df["log_size"] = np.log(df["size_m2"])
amen = ["has_ac", "has_mezzanine", "is_free_curfew", "has_balcony_window",
        "has_private_wc", "has_kitchen", "has_washing_machine", "has_parking", "has_elevator"]
formula = "log_price ~ log_size + dist_to_q1_km + C(area_group) + C(furnishing_status) + C(seller_type) + " + " + ".join(amen)
m = smf.ols(formula, data=df).fit(cov_type="HC3")      # sai số chuẩn bền vững
print(m.summary())

coef = m.params[amen]
ci = m.conf_int().loc[amen]
premium = (np.exp(coef) - 1) * 100                      # % tăng giá khi có tiện ích
premium_ci = (np.exp(ci) - 1) * 100
```
- Kiểm tra đa cộng tuyến bằng VIF (`statsmodels.stats.outliers_influence.variance_inflation_factor`), ghi kết quả.
- Đọc hệ số `log_size`: tăng 1% diện tích thì giá tăng bao nhiêu %?
- **Biểu đồ chốt — forest plot**: mỗi tiện ích 1 dòng, 2 điểm (premium thô vs premium có kiểm soát) kèm khoảng tin cậy 95%.
- Viết giải thích: tiện ích nào premium giảm mạnh sau khi kiểm soát → vì sao (ví dụ phòng có máy lạnh hay nằm ở quận đắt).

**(c) Chính chủ vs môi giới (RQ4)**
- So sánh 2–3 nhóm `seller_type` về: giá, đơn giá, số ảnh, độ dài mô tả, % tin trả phí, % tin đã đổi giá.
- Kruskal-Wallis (nếu 3 nhóm) hoặc Mann-Whitney (2 nhóm) + effect size.
- Đọc hệ số `C(seller_type)` trong hồi quy (b): cùng điều kiện thì môi giới đắt/rẻ hơn bao nhiêu %?

**(d) Tương quan**: heatmap Spearman giữa các biến số.

- 📤 Bảng kết quả kiểm định (xuất thêm `reports/bang_kiem_dinh.csv`), forest plot, heatmap. Hàm tái sử dụng thêm vào `src/stats_tests.py`.
- ✅ Mỗi kiểm định ghi rõ: giả thuyết H0/H1, vì sao chọn kiểm định này, p-value đã hiệu chỉnh, effect size, kết luận bằng lời.

#### B7. Kiểm chứng tay tin bất thường ⏰ T7 05/12
- 📥 Nhận từ A (T5 03/12): file danh sách tin "rẻ bất thường" + nhóm đối chứng "giá hợp lý", đã chia đôi.
- B kiểm **25 tin** của mình: mở `ad_url` trên trình duyệt, điền vào `reports/kiem_chung_tin_bat_thuong.csv`:

| ad_id | ad_url | nhom (bat_thuong/doi_chung) | tin_con_hien_thi (C/K) | anh_co_ve_that (C/K/?) | mo_ta_cau_khach (C/K) | gia_tren_web_khop (C/K) | ket_luan (Đáng nghi / Bình thường / Không rõ) | ghi_chu | nguoi_kiem |
|---|---|---|---|---|---|---|---|---|---|

- **Chỉ quan sát. Không gọi điện, không nhắn tin, không chuyển tiền** cho người đăng.
- ✅ Đủ 25 dòng, không bỏ trống `ket_luan`.

#### B8. Viết kết luận dưới mỗi biểu đồ ⏰ CN 06/12
- Mỗi hình 1–3 câu: thấy gì · con số cụ thể · ý nghĩa với người đi thuê.
- Ví dụ tốt: *"Đơn giá trung vị Quận 1 (≈ 200k/m²) gấp ~2 lần Dĩ An; người thuê chấp nhận đi xa 10 km có thể tiết kiệm ~x triệu/tháng cho phòng 25 m²."*
- Ví dụ chưa đạt: *"Biểu đồ cho thấy giá các quận khác nhau."*

#### B9. Họp 2 ⏰ CN 06/12 (1.5 tiếng)
- B trình bày notebook 03 cho A **như thuyết trình thật** (15 phút); A trình bày notebook 04.
- Ghi lại mọi câu hỏi chưa trả lời được → xử lý trong tuần 3.

---

### TUẦN 3 (07/12 – 13/12) — Sản phẩm nộp

#### B10. Power BI ⏰ T4 09/12
*(Hỏi lại đề cương môn có bắt buộc không. Nếu không bắt buộc vẫn nên làm bản gọn — 2 trang là đủ.)*
- 📥 Dữ liệu: `rental_scored_deals.csv` bản cuối từ A (T2 07/12).
- Gợi ý 4 trang: **Tổng quan** (thẻ KPI: số tin, giá trung vị, đơn giá trung vị; phân phối) · **Bản đồ & khu vực** (choropleth, bộ lọc quận) · **Tiện ích** (premium từ B6, bộ lọc tiện ích) · **Tin bất thường** (bảng có link `ad_url`, bộ lọc nhãn).
- Đồng bộ màu với biểu đồ trong notebook. Không đưa cột tên/ảnh đại diện người đăng.
- 📤 `dashboard/IE313_Rental_Dashboard.pbix` + 4 ảnh chụp màn hình vào `reports/figures/powerbi_*.png`.

#### B11. Báo cáo — các chương của B ⏰ T6 11/12
| Chương | Người viết |
|---|---|
| 1. Giới thiệu, bối cảnh, câu hỏi nghiên cứu | **B** |
| 2. Thu thập & làm sạch dữ liệu | A |
| 3. Khám phá dữ liệu (EDA) | **B** |
| 4. Kiểm định giả thuyết & định giá tiện ích | **B** |
| 5. Mô hình định giá & phát hiện tin bất thường | A |
| 6. Dashboard | A (Streamlit) + **B** (Power BI) |
| 7. Kết luận, hạn chế, hướng phát triển | **B** (A bổ sung phần mô hình) |
| Phụ lục: bảng đóng góp thành viên | Cả hai |

- Mục Hạn chế bắt buộc nêu: lát cắt thời gian ngắn · 1 nền tảng · lấy mẫu có hạn ngạch 140 tin/quận · giá niêm yết ≠ giá chốt · tọa độ xấp xỉ · regex có sai số (dẫn bảng precision B2) · nhãn bất thường không có ground truth.
- **Mọi con số trong báo cáo phải chép từ output notebook**, không gõ tay theo trí nhớ.

#### B12. Slide ⏰ T6 11/12
- Phần B (~8–10 slide): Giới thiệu & RQ · Dữ liệu (tóm tắt) · Bức tranh thị trường · Bản đồ · Distance decay · Định giá tiện ích (forest plot) · Chính chủ vs môi giới · Power BI demo · Kết luận & hạn chế.
- Mỗi slide **1 thông điệp** viết thành câu làm tiêu đề (vd: "Máy lạnh làm giá tăng ~x% dù cùng diện tích và quận").

#### B13. Kiểm tra tái lập ⏰ T7 12/12
- Clone repo **vào thư mục mới**, tạo venv mới, `pip install -r requirements.txt`, chạy lại 4 notebook từ đầu.
- Ghi mọi lỗi gặp phải gửi A. ✅ Chạy hết không lỗi trên máy B.

#### B14. Tổng duyệt ⏰ T7 12/12
- Thuyết trình bấm giờ.
- **Đổi vai**: B trình bày thử phần mô hình của A (và ngược lại).
- Hỏi nhau 15 câu ở mục 7 của `KE_HOACH_3_TUAN.md`.

---

## 5. Lịch tóm tắt & những gì B nhận từ A

| Ngày | B nộp | B nhận từ A |
|---|---|---|
| T2 23/11 | — | Quyền push repo, xác nhận đã cài xong |
| T4 25/11 | B1 bảng hiểu dữ liệu | A review B1 |
| T6 27/11 | B2 regex + bảng precision | — |
| T7 28/11 | B3 POI + GeoJSON | — |
| **CN 29/11** | **Họp 1** | **Dataset v2** |
| T3 01/12 | B5 EDA phần 1 | — |
| T5 03/12 | B6 kiểm định + hedonic | Danh sách tin cần kiểm chứng |
| T7 05/12 | B7 kiểm chứng 25 tin | — |
| **CN 06/12** | B8 kết luận, **Họp 2** | Notebook 04 để B đọc trước |
| T2 07/12 | — | `rental_scored_deals.csv` bản cuối |
| T4 09/12 | B10 Power BI | Streamlit để B dùng thử |
| T6 11/12 | B11 báo cáo + B12 slide | Chương 2, 5 + slide của A |
| **T7 12/12** | B13 tái lập, **Tổng duyệt** | — |
| CN 13/12 | Nộp bài | |

---

## 6. B cần hiểu được phần của A (để vấn đáp)

Trước Họp 2, B đọc và **tự giải thích lại được**:
1. Vì sao lọc ngoại lai theo IQR **từng quận** chứ không phải toàn bộ dữ liệu.
2. Lỗi **leakage tiền cọc**: 82% tin có cọc = 1 tháng tiền thuê → dùng cọc để đoán giá là "chép đáp án"; R² giảm từ 0.90 xuống 0.54 khi bỏ; sau khi tách tin KTX/ở ghép (giá theo giường) thì lên **0.64**. Vì sao đây là điểm cộng chứ không phải điểm trừ.
3. **Out-of-fold prediction** là gì và vì sao phải dùng khi tính độ lệch giá.
4. Đọc được biểu đồ SHAP của A.
5. Vì sao không được gọi tin là "lừa đảo", chỉ là "nghi vấn – cần kiểm chứng".

---

## 7. Khi nào coi là B xong việc

- [ ] `src/text_features.py`, `src/external_features.py` đã được merge vào `main`
- [ ] `reports/hieu_du_lieu.md` và `reports/regex_check/TONG_HOP.md` hoàn chỉnh
- [ ] Notebook 03 **Restart & Run All** không lỗi, mỗi hình có kết luận
- [ ] Hình đã lưu vào `reports/figures/03_*.png` (300 DPI)
- [ ] 25 tin kiểm chứng đã điền đủ
- [ ] File Power BI + ảnh chụp
- [ ] Các chương 1, 3, 4, 7 trong báo cáo + slide phần mình
- [ ] Đã tự chạy lại toàn bộ repo trên máy mình
- [ ] Trả lời được 15 câu hỏi vấn đáp, kể cả phần mô hình của A
