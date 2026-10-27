# Danh sách file dự đoán churn

## Code

- `source-code/prepare_churn_data.py`: tạo feature và nhãn churn proxy 180 ngày.
- `source-code/train_churn_model.py`: chia train/test, tối ưu, huấn luyện và đánh giá Random Forest.
- `source-code/predict_churn.py`: dùng model đã lưu để dự đoán file feature mới.
- `source-code/run_all.py`: chạy bước tạo dữ liệu và huấn luyện liên tiếp.

## Dữ liệu và model

- `data/customer_churn_180d.csv`: một dòng cho mỗi khách hàng, gồm feature và nhãn.
- `models/random_forest_churn_pipeline.joblib`: pipeline tiền xử lý, model và ngưỡng dự đoán.

## Kết quả

- `outputs/test_predictions.csv`: nhãn thật, xác suất và nhãn dự đoán trên tập test.
- `outputs/model_metrics.json`: tham số và metric chính.
- `outputs/classification_report.csv`: precision, recall và F1 theo lớp.
- `outputs/confusion_matrix.csv`: confusion matrix.
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
