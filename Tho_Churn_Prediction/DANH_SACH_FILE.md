# Danh sách file dự đoán churn

Các file mới có phiên bản tạm thời nằm trong `outputs/temporal_v3_provisional/`.
Đọc `reports/bao_cao_temporal_v3.md` để biết quy ước, nguồn và hạn chế trước khi dùng.

## Code

- `source-code/prepare_churn_data.py`: tạo feature và nhãn churn proxy 180 ngày.
- `source-code/train_churn_model.py`: chia train/test, tối ưu, huấn luyện và đánh giá Random Forest.
- `source-code/predict_churn.py`: dùng model đã lưu để dự đoán file feature mới.
- `source-code/run_all.py`: chạy đánh giá temporal mới, yêu cầu bảng đơn sạch có cờ chất lượng.
- `source-code/evaluate_temporal.py`: tạo snapshot, huấn luyện và đánh giá theo thời gian.
- `source-code/export_temporal_summary.py`: xuất Excel từ kết quả temporal.

## Dữ liệu và model

- `data/customer_churn_180d.csv`: một dòng cho mỗi customer-snapshot, gồm feature và nhãn.
- `models/random_forest_churn_pipeline.joblib`: pipeline tiền xử lý, model và ngưỡng dự đoán.

## Kết quả

- `outputs/test_predictions.csv`: nhãn thật, xác suất và nhãn dự đoán trên tập test.
- `outputs/train_test_split.csv`: danh sách sample thuộc train hoặc test để kiểm tra trùng khách.
- `outputs/model_metrics.json`: tham số và metric chính.
- `outputs/classification_report.csv`: precision, recall và F1 theo lớp.
- `outputs/classification_report_train.csv`: precision, recall và F1 trên tập train.
- `outputs/confusion_matrix.csv`: confusion matrix.
- `outputs/confusion_matrix_train.csv`: confusion matrix trên tập train.
- `outputs/performance_metrics.csv`: bảng so sánh đầy đủ metric train và test.
- `outputs/feature_importance.csv`: mức độ quan trọng của feature sau tiền xử lý.
- `outputs/cross_validation_results.csv`: kết quả tám cấu hình Random Forest.
- `outputs/Ketqua_RandomForest_Churn.txt`: kết quả dạng văn bản.
- `outputs/churn_model_summary.xlsx`: file Excel tổng hợp bốn sheet.
- `outputs/charts/`: sáu biểu đồ dùng trong báo cáo.

## Tài liệu và kiểm tra

- `reports/cac_buoc_thuc_hien.md`: quy trình làm bài và cách kiểm tra.
- `reports/noi_dung_bao_cao.md`: nội dung có thể đưa vào báo cáo cuối kỳ.
- `tests/test_prepare_churn_data.py`: kiểm tra mốc thời gian, nhãn và công thức feature.
- `tests/test_model_artifacts.py`: kiểm tra model lưu và CSV dự đoán.
- `README.md`: hướng dẫn chạy trên máy khác.
- `requirements.txt`: phiên bản thư viện đã sử dụng.
