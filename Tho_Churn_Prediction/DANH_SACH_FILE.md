# File của phần dự đoán không mua lại

Đầu vào dùng chung tại `../Tho_Shared/data/`; báo cáo hiện tại là `reports/bao_cao_temporal_v4.md`.

| File | Vai trò |
|---|---|
| `source-code/run_all.py` | Lệnh chạy toàn bộ temporal v4 |
| `source-code/evaluate_temporal.py` | Tạo mẫu/nhãn 180 ngày, chia thời gian, fit và so sánh model |
| `source-code/predict_churn.py` | Dự đoán file feature bằng model hiện tại |
| `source-code/prediction_utils.py` | Quy tắc decile dùng chung |
| `source-code/temporal_selection.py` | Kiểm tra nhãn đã quan sát đủ thời gian; chọn model và ngưỡng bằng validation nếu khả thi |
| `source-code/export_temporal_summary.py` | Xuất Excel từ kết quả |
| `outputs/temporal_v4_provisional/` | Model, dữ liệu đánh giá, bảng BI, metric, baseline, chart và Excel hiện tại |
| `outputs/temporal_v4_provisional/validation_protocol.json` | Quyết định chọn model/ngưỡng; hiện chặn tuning vì validation không đủ hai lớp |
| `outputs/temporal_v4_provisional/validation_fold_audit.csv` | Bằng chứng kiểm tra sáu mốc validation |
| `outputs/temporal_v4_provisional/probability_summary.csv` | Phân bố điểm theo model, tập dữ liệu và nhãn thật |
| `outputs/temporal_v4_provisional/data_contract.json` | Khóa nối, mốc thời gian, quy tắc nhãn và giới hạn sử dụng |
| `outputs/temporal_v4_provisional/test_predictions.csv` | Kết quả test duy nhất một dòng/khách; không dùng tính KPI cho toàn bộ khách BI |
| `tests/test_temporal_evaluation.py` | Biên thời gian, nhãn, leakage và metric |
| `tests/test_temporal_artifacts.py` | Đối soát model với file đánh giá và BI |
| `tests/test_predict_churn.py` | Dự đoán bằng model hiện tại, schema tương thích và CLI |
| `tests/test_selection_protocol.py` | Nhãn chưa chín, hai lớp, chọn ngưỡng, xác suất và baseline không có lợi thế xếp hạng |
| `README.md` | Hướng dẫn chạy và giới hạn |
| `requirements.txt` | Thư viện |

Các code/model/kết quả cũ được giữ trong lịch sử Git. Snapshot `0dae8ad` giữ nguyên bản temporal v3 trước đợt sửa này; không dùng kết quả cũ làm bản bàn giao hiện tại.
