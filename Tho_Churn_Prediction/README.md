# Dự đoán churn proxy 180 ngày bằng Random Forest

> **Đọc trước:** Kết quả chia theo nhóm khách bên dưới là bản cũ, dùng master cũ có 8 ngày giao được điền và thời điểm snapshot chưa thống nhất. Bản hiện tại dùng master mới và bảng sạch, xem [báo cáo temporal v3](reports/bao_cao_temporal_v3.md). Mốc theo dõi cuối vẫn là giả định cần nhóm xác nhận.

Temporal v3 có thêm Logistic Regression và baseline đa số trên cùng tập test; xem `outputs/temporal_v3_provisional/baseline_comparison.json`. Bảng test và BI có `score_decile` (1 = xác suất không mua lại cao nhất). Hai bảng xếp hạng theo tập khách riêng. Đây vẫn là kết quả thử nghiệm, không sử dụng trực tiếp để quyết định chăm sóc khách hàng.

Chạy bản mới trên Windows, từ thư mục chứa dự án:

```powershell
git clone https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5.git
cd olist-customer-analytics-nhom5
git switch codex/tho-machine-learning
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Tho_Churn_Prediction/requirements.txt
python -B Tho_Churn_Prediction/source-code/run_all.py
python -B -m unittest discover -s Tho_Churn_Prediction/tests -v
```

Nếu đã tải ZIP đúng nhánh hoặc đã clone, bỏ qua bước `git clone`, đi vào thư mục dự án rồi chạy
các lệnh còn lại; nếu đã ở đúng nhánh thì bỏ qua `git switch`.

Đầu vào mặc định nằm trong `Tho_Shared/data/`. Tham số `--master` và `--clean-orders` chọn nguồn khác;
`--observation-end` là mốc quan sát loại trừ cuối cùng. Mặc định 2018-08-31 00:00:00 chỉ là giả định,
cần nhóm xác nhận thời gian đủ dữ liệu. Kết quả mới trong `outputs/temporal_v3_provisional/`, gồm CSV
snapshot, CSV BI/web, model, metric, biểu đồ và Excel được sinh lại cùng lệnh. Bảng BI chỉ để thử tích hợp
vì model dự đoán toàn bộ test là không mua lại.

Với gói mới do Thiên export, chạy `python -B Tho_Churn_Prediction/source-code/run_all.py --handover-dir "duong-dan/handover/tho"`. Lệnh đọc `order_summary.csv` và ba bảng sạch từ cùng thư mục; snapshot IBGE lấy từ `Tho_Shared/data/ibge_states_raw.json`. Manifest đầu vào được ghi bằng SHA-256. Không dùng file nhãn 90 ngày cũ.

Ngưỡng 180 ngày được tham khảo từ nghiên cứu của Zeinali và cộng sự (2026) trên dữ liệu Olist:
[bài nghiên cứu](https://doi.org/10.1155/tswj/1946904). Bản dự đoán của nhóm dùng cửa sổ
`[T0, T0 + 180 ngày)` và gọi nhãn 1 là “không mua lại trong 180 ngày”, không khẳng định
khách rời bỏ vĩnh viễn. Chi tiết và giới hạn của nguồn được ghi trong báo cáo temporal v3.

---

## Bản đối chiếu cũ theo nhóm khách

Phần này dự đoán khách hàng đang hoạt động có ngừng mua trong 180 ngày tiếp theo hay không. Mô hình sử dụng `RandomForestClassifier` với `class_weight="balanced"`.

- Người thực hiện: Bui Minh Tho
- Email: buitho5112006@gmail.com
- Nhánh Git: `codex/tho-machine-learning`

## Cách tạo mẫu và nhãn

Dữ liệu được tạo theo 12 snapshot hàng tháng, từ 01/04/2017 đến 01/03/2018.

Một khách hàng được đưa vào snapshot khi:

- Đã có ít nhất hai đơn `delivered` trước snapshot.
- Có mua hàng trong 180 ngày gần nhất trước snapshot.

Nhãn được tạo như sau:

- `churn_proxy_180d = 1`: không có đơn `delivered` trong 180 ngày sau snapshot.
- `churn_proxy_180d = 0`: có ít nhất một đơn `delivered` trong 180 ngày sau snapshot.

Mỗi dòng được xác định bằng `sample_id`, gồm mã khách hàng và ngày snapshot. Feature chỉ dùng dữ liệu đã có trước snapshot.

## Chạy lại bản cũ để đối chiếu

Yêu cầu Python 3.11 trở lên và các thư viện trong `requirements.txt`.

File đầu vào đã nằm tại:

```text
Tho_RFM_KMeans/data/olist_powerbi_orders_master.csv
```

Chạy bản cũ riêng để đối chiếu (không dùng làm bản tích hợp):

```powershell
python -B Tho_Churn_Prediction/source-code/prepare_churn_data.py
python -B Tho_Churn_Prediction/source-code/train_churn_model.py
```

Chạy test:

```powershell
python -B -m unittest discover -s Tho_Churn_Prediction/tests -v
```

## Cách chia train và test

Toàn bộ bảng nhãn được tạo trước. Sau đó dữ liệu được chia khoảng 80% train và 20% test bằng `StratifiedGroupKFold`.

`customer_unique_id` được dùng làm group nên một khách hàng không thể xuất hiện đồng thời ở train và test. Kết quả chia:

- Train: 4.737 mẫu của 1.187 khách.
- Test: 1.183 mẫu của 297 khách.
- Số khách trùng giữa hai tập: 0.

GridSearchCV ba fold cũng chia theo `customer_unique_id`. Imputation và one-hot encoding đều nằm trong Pipeline và chỉ học từ phần train của từng fold.

## Kết quả chính

Bảng dữ liệu gồm 5.920 mẫu customer-snapshot của 1.484 khách hàng:

- Quay lại, nhãn 0: 299 mẫu.
- Churn proxy, nhãn 1: 5.621 mẫu.
- Tỷ lệ churn: 94,95%.

| Chỉ số trên tập test | Kết quả |
|---|---:|
| Accuracy | 0,8791 |
| Balanced accuracy | 0,6445 |
| Macro precision | 0,5716 |
| Macro recall | 0,6445 |
| Macro F1 | 0,5888 |
| Weighted precision | 0,9250 |
| Weighted recall | 0,8791 |
| Weighted F1 | 0,8993 |
| Precision lớp quay lại | 0,1783 |
| Recall lớp quay lại | 0,3833 |
| F1 lớp quay lại | 0,2434 |
| Precision lớp churn | 0,9649 |
| Recall lớp churn | 0,9056 |
| F1 lớp churn | 0,9343 |
| ROC-AUC | 0,7168 |

Trên train, weighted F1 đạt 0,9596 nhưng trên test còn 0,8993. Khoảng chênh này cho thấy model học tập train khá mạnh. Vì dữ liệu mất cân bằng, cần đọc balanced accuracy, macro F1 và kết quả từng lớp thay vì chỉ nhìn accuracy hoặc weighted average.

## Dự đoán bằng model cũ

File đầu vào cần có đủ 18 feature ghi trong báo cáo:

```powershell
python -B Tho_Churn_Prediction/source-code/predict_churn.py `
  --input "duong-dan\customer_features.csv" `
  --output "duong-dan\ket_qua_du_doan.csv"
```

Kết quả có thêm xác suất churn, nhãn dự đoán và ngưỡng đã chọn trên train. Script cũ chỉ chấm các dòng có `frequency >= 2` và `0 <= recency <= 180`; điều này không tự chứng minh dữ liệu đặc trưng đã được tính đúng tại T0.

## Cấu trúc thư mục

```text
Tho_Churn_Prediction/
├── data/              # Bảng customer-snapshot, feature và nhãn
├── models/            # Pipeline và Random Forest
├── outputs/           # CSV kết quả, biểu đồ, metric và Excel
├── reports/           # Quy trình và nội dung báo cáo
├── source-code/       # Code tạo dữ liệu, train và dự đoán
├── tests/             # Test công thức, chia tập và model
├── DANH_SACH_FILE.md
└── requirements.txt
```

Model lưu chung bước điền missing, one-hot encoding, Random Forest và ngưỡng 0,57. Không cần xử lý lại feature bằng tay khi gọi `predict_churn.py`.
