# Dự đoán không mua lại 180 ngày — temporal v4

Bản đang dùng: `outputs/temporal_v4_provisional/`. Xem
[báo cáo và giới hạn](reports/bao_cao_temporal_v4.md).

Pipeline chạy được không đồng nghĩa mô hình đủ chất lượng triển khai. Sáu fold
validation hiện tại đều thiếu lớp mua lại ở train đủ điều kiện thời gian. Chương trình
chặn tuning, giữ Random Forest/ngưỡng 0,5 làm baseline và xuất bằng chứng. Test lịch sử
đã được xem ở các lần review trước; không gọi đây là holdout mới chưa từng tiếp xúc.

## Chạy từ thư mục Tho_Machine_Learning

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r Tho_Churn_Prediction/requirements.txt
.\.venv\Scripts\python.exe -B Tho_Churn_Prediction/source-code/run_all.py
.\.venv\Scripts\python.exe -B -m unittest discover -s Tho_Churn_Prediction/tests -v
```

Đầu vào chung có sẵn trong `Tho_Shared/data/`. Dùng `--output-dir ket_qua_doi_soat`
để chạy lại mà giữ bản bàn giao. Với gói Thiên export, dùng
`--handover-dir "duong-dan/handover/tho"`; code đọc order_summary và các bảng sạch
cùng phiên bản. Nguồn/khóa/ngày/cờ được kiểm tra trước khi fit. `--observation-end`
mặc định 31/08/2018 00:00 là giả định chưa được xác nhận đầy đủ theo dõi.

## Validation và cấu hình

`temporal_selection.py` không nhận tập test để chọn cấu hình. Nhãn train phải hoàn tất
trước T0 validation, nhãn validation phải hoàn tất trước T0 test. Nhãn được dựng lại
với thông tin biết tại từng mốc; không dùng nhãn tương lai để huấn luyện ngược thời gian.

Guard tối thiểu 5 khách khác nhau/lớp ở train và validation là mức cho thử nghiệm nhỏ,
không phải chứng nhận đủ độ tin cậy thống kê. Fold không đủ hỗ trợ không được fit/tuning.
Nếu có fold hợp lệ, RF/LR được so sánh bằng Average Precision lớp mua lại; ngưỡng chọn
theo F1 lớp mua lại từ lưới cố định 0,05–0,95 trên validation. Không dùng test và không
ép dự đoán xuất hiện đủ hai lớp. Không có fold hợp lệ thì giữ RF/0,5 và trạng thái blocked.

Xem `validation_protocol.json`, `validation_fold_audit.csv`, `validation_predictions.csv`.

## File bàn giao

| File | Ý nghĩa |
|---|---|
| selected_model.joblib | Model dùng chính thức cho lần chạy, features, threshold, danh tính, metric và lý do chọn/giữ |
| random_forest_temporal.joblib, logistic_regression_temporal.joblib | Hai candidate để đối chiếu |
| test_predictions.csv | Một dòng/khách test, nhãn thật, xác suất, dự đoán, split, cutoff, decile và phiên bản |
| snapshot_evaluation.csv | Khách + snapshot; có khách lặp qua tháng, không join chỉ bằng customer_unique_id |
| bi_web_customers.csv | Một dòng/khách tại cutoff BI; nhãn thật tương lai để trống |
| probability_summary.csv | Min/quartile/median/max và số dự đoán theo lớp thật, tập và model |
| data_contract.json | Khóa, nhãn, cutoff, eligibility, decile và giới hạn |
| metrics.json, baseline_comparison.json, charts/, temporal_summary.xlsx | Kết quả cùng lần chạy và model/ngưỡng nhất quán |

Train_in_sample chỉ để chẩn đoán, không phải chất lượng độc lập. File validation có
header nhưng không có dòng nếu không có fold hợp lệ. AP là average precision, không
tự đổi tên thành PR-AUC hình thang. Importance/hệ số không chứng minh nhân quả.

Khách không đủ điều kiện có xác suất, ngưỡng, nhãn dự đoán, rủi ro và decile để trống;
không gán thành 0%. RFM/K-Means là mô tả hồi cứu tới 30/08/2018, không đưa cụm cuối kỳ
vào features của test 01/03/2018. Decile 1 xếp churn_probability cao nhất, test và BI
xếp riêng. Baseline điểm hoàn toàn bằng nhau có lift kỳ vọng 1, không có lợi thế
xếp hạng; khi có hòa ở biên decile, báo rõ số lượng và thứ tự ổn định.

## Dự đoán file feature

```powershell
python -B Tho_Churn_Prediction/source-code/predict_churn.py --input customer_features.csv --output customer_predictions.csv
```

Mặc định đọc selected_model.joblib; `--model` cho phép chọn candidate rõ ràng. File
features phải được tạo từ thông tin biết trước cutoff. Lệnh kiểm tra schema và
frequency/recency/eligibility nhưng không tự xác minh toàn bộ lịch sử. Không ghi đè
input. Xác suất chưa hiệu chuẩn, không phải tỷ lệ chắc chắn.

Artifact v3 đã thay thế được giữ trong lịch sử Git tại commit `0dae8ad`. V4 là thư mục
đầu ra hiện hành duy nhất để tránh dùng nhầm khi bàn giao.
