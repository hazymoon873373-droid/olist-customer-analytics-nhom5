# Dự đoán churn proxy 180 ngày bằng Random Forest

> Bản hiện tại dùng dữ liệu chung và bảng sạch; xem [báo cáo temporal v3](reports/bao_cao_temporal_v3.md). Mốc theo dõi cuối vẫn là giả định cần nhóm xác nhận.

Temporal v3 có thêm Logistic Regression và baseline đa số trên cùng tập test; xem `outputs/temporal_v3_provisional/baseline_comparison.json`. Bảng test và BI có `score_decile` (1 = xác suất không mua lại cao nhất). Hai bảng xếp hạng theo tập khách riêng. Đây vẫn là kết quả thử nghiệm, không sử dụng trực tiếp để quyết định chăm sóc khách hàng.

## Dự đoán bằng model hiện tại

`predict_churn.py` mặc định dùng Random Forest temporal v3. File đầu vào phải có các feature tính từ dữ liệu đã biết trước cutoff, theo đúng phạm vi tối thiểu hai đơn delivered đã xác nhận trước cutoff và còn hoạt động trong 180 ngày. Script kiểm tra frequency/recency và tôn trọng `eligibility_status` nếu cột đó có sẵn, nhưng không tự xác minh lại lịch sử đơn hoặc nguồn của features.

```powershell
python -B Tho_Churn_Prediction/source-code/predict_churn.py --input "customer_features.csv" --output "customer_predictions.csv"
```

Đầu ra giữ các cột đầu vào và thêm xác suất không mua lại/mua lại, dự đoán, ngưỡng, decile (1 = điểm không mua lại cao nhất), phiên bản và trạng thái thử nghiệm. Khách ngoài phạm vi được để trống điểm và dự đoán. File rỗng có đủ header vẫn được xuất với header; thiếu feature hoặc giá trị số không hợp lệ được báo lỗi. Không ghi đè file đầu vào.

Nếu muốn chấm bằng baseline Logistic Regression, chỉ định:

```powershell
python -B Tho_Churn_Prediction/source-code/predict_churn.py --model Tho_Churn_Prediction/outputs/temporal_v3_provisional/logistic_regression_temporal.joblib --input "customer_features.csv" --output "logistic_predictions.csv"
```

Script dự đoán không chia train/test hoặc tính metric. Nếu dùng bảng snapshot có nhiều thời điểm, mỗi dòng vẫn là một khách tại một snapshot; không tính chất lượng trên các dòng train. Nhãn cũ trong file input không được dùng làm feature. Chạy lại toàn pipeline với `run_all.py --output-dir "thu-muc-doi-soat"` để tạo kết quả ở vị trí riêng mà không thay bảng đang bàn giao.

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


## Lịch sử và bản đang dùng

Chỉ `outputs/temporal_v3_provisional/` là đầu ra hiện tại. Luồng chia theo nhóm khách và temporal v2 đã được bỏ khỏi bản làm việc để tránh dùng nhầm. Có thể xem lại tại [snapshot trước khi dọn](https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5/tree/89faa7f8e3909211543a897710e7168f65a0ff87/Tho_Churn_Prediction). Không dùng điểm các phiên bản khác nguồn hoặc cách chia tập như cùng một phép thử.
