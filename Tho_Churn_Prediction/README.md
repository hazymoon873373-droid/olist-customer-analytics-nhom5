# Dự đoán churn proxy 180 ngày bằng Random Forest

Phần này dự đoán khả năng khách hàng không quay lại mua trong 180 ngày sau ngày snapshot. Mô hình chính là `RandomForestClassifier` với `class_weight="balanced"`.

- Người thực hiện: Bui Minh Tho
- Email: buitho5112006@gmail.com
- Nhánh Git: `codex/tho-machine-learning`

## Cách tạo nhãn

- Snapshot `T0`: hết ngày 02/03/2018.
- Cửa sổ nhãn: từ 03/03/2018 đến hết 29/08/2018.
- `churn_proxy_180d = 1`: khách không có đơn `delivered` trong cửa sổ nhãn.
- `churn_proxy_180d = 0`: khách có ít nhất một đơn `delivered` trong cửa sổ nhãn.

Feature chỉ được tính từ đơn đã giao thành công trước hoặc bằng `T0`. Đơn mua trước `T0` nhưng giao sau `T0` không được dùng để tránh lấy thông tin tương lai.

## Chạy trên máy khác

Yêu cầu Python 3.11 trở lên. Sau khi clone GitHub:

```powershell
git clone https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5.git
cd olist-customer-analytics-nhom5
git switch codex/tho-machine-learning
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r Tho_Churn_Prediction/requirements.txt
```

File đầu vào đã nằm tại:

```text
Tho_RFM_KMeans/data/olist_powerbi_orders_master.csv
```

Chạy lại toàn bộ:

```powershell
python -B Tho_Churn_Prediction/source-code/run_all.py
```

Quá trình huấn luyện GridSearchCV mất khoảng 5 đến 6 phút trên máy đã chạy bài này.

Chạy riêng từng bước:

```powershell
python -B Tho_Churn_Prediction/source-code/prepare_churn_data.py
python -B Tho_Churn_Prediction/source-code/train_churn_model.py
```

Chạy kiểm tra:

```powershell
python -B -m unittest discover -s Tho_Churn_Prediction/tests -v
```

## Dự đoán cho file mới

File mới cần có đủ 18 feature ghi trong `reports/noi_dung_bao_cao.md`.

```powershell
python -B Tho_Churn_Prediction/source-code/predict_churn.py `
  --input "duong-dan\customer_features.csv" `
  --output "duong-dan\ket_qua_du_doan.csv"
```

Kết quả có thêm ba cột:

- `churn_probability`
- `predicted_churn`
- `prediction_threshold`

## Kết quả chính

Tập dữ liệu có 52.522 khách hàng. Có 595 khách quay lại và 51.927 khách thuộc nhãn churn proxy. Tập train chiếm 80%, tập test chiếm 20% và được chia có `stratify`.

| Chỉ số trên tập test | Kết quả |
|---|---:|
| Accuracy | 0,9780 |
| Balanced accuracy | 0,5195 |
| Macro F1 | 0,5191 |
| F1 lớp quay lại | 0,0494 |
| F1 lớp churn | 0,9889 |
| ROC-AUC | 0,5529 |

Accuracy cao chủ yếu do 98,87% quan sát mang nhãn churn. Khả năng tách hai lớp còn yếu nên không nên dùng mô hình này để tự động quyết định giữ chân khách hàng. Kết quả phù hợp để trình bày quy trình supervised learning và làm cơ sở cải thiện khi có thêm lịch sử mua lặp lại.

## Cấu trúc thư mục

```text
Tho_Churn_Prediction/
├── data/              # Bảng feature và nhãn theo khách hàng
├── models/            # Pipeline tiền xử lý và Random Forest
├── outputs/           # CSV kết quả, biểu đồ, metric và Excel tổng hợp
├── reports/           # Các bước thực hiện và nội dung báo cáo
├── source-code/       # Code tạo dữ liệu, train và dự đoán
├── tests/             # Test công thức và model đã lưu
├── DANH_SACH_FILE.md
└── requirements.txt
```

Model lưu chung bước điền giá trị thiếu, one-hot encoding, Random Forest và ngưỡng dự đoán. Không cần xử lý lại feature bằng tay khi gọi `predict_churn.py`.
