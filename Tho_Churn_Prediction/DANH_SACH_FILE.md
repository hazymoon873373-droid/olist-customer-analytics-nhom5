# File của phần dự đoán không mua lại

Đầu vào dùng chung tại `../Tho_Shared/data/`; báo cáo hiện tại là `reports/bao_cao_temporal_v3.md`.

| File | Vai trò |
|---|---|
| `source-code/run_all.py` | Lệnh chạy toàn bộ temporal v3 |
| `source-code/evaluate_temporal.py` | Tạo mẫu/nhãn 180 ngày, chia thời gian, fit và so sánh model |
| `source-code/predict_churn.py` | Dự đoán file feature bằng model hiện tại |
| `source-code/prediction_utils.py` | Quy tắc decile dùng chung |
| `source-code/export_temporal_summary.py` | Xuất Excel từ kết quả |
| `outputs/temporal_v3_provisional/` | Model, dữ liệu đánh giá, bảng BI, metric, baseline, chart và Excel hiện tại |
| `tests/test_temporal_evaluation.py` | Biên thời gian, nhãn, leakage và metric |
| `tests/test_temporal_artifacts.py` | Đối soát model với file đánh giá và BI |
| `tests/test_predict_churn.py` | Dự đoán bằng model hiện tại, schema tương thích và CLI |
| `README.md` | Hướng dẫn chạy và giới hạn |
| `requirements.txt` | Thư viện |

Các code/model/kết quả cũ đã chuyển sang lưu bằng lịch sử Git. Xem snapshot `89faa7f` nếu cần khôi phục đối chiếu; không dùng kết quả cũ làm bản bàn giao hiện tại.
