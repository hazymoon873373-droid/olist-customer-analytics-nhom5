# Danh sách file

## Code

- `source-code/prepare_anomaly_data.py`: lọc đơn delivered và tạo feature.
- `source-code/train_isolation_forest.py`: huấn luyện, chấm điểm và xuất biểu đồ.
- `source-code/predict_anomaly.py`: dùng model đã lưu để chấm điểm file mới.
- `source-code/run_all.py`: chạy lại toàn bộ quy trình.

## Dữ liệu và model

- `data/order_anomaly_features.csv`: dữ liệu 96.478 đơn dùng cho mô hình.
- `models/isolation_forest_order_pipeline.joblib`: Pipeline và model đã huấn luyện.

## Kết quả

- `outputs/order_anomaly_scores.csv`: điểm và nhãn của toàn bộ đơn.
- `outputs/anomalous_orders.csv`: 965 đơn được gắn cờ bất thường.
- `outputs/anomaly_feature_profile.csv`: so sánh trung vị giữa hai nhóm.
- `outputs/anomaly_reason_counts.csv`: số đơn theo từng dấu hiệu mô tả.
- `outputs/model_metrics.json`: cấu hình và số liệu tổng hợp.
- `outputs/Ketqua_IsolationForest.txt`: kết quả dạng văn bản.
- `outputs/anomaly_summary.xlsx`: bảng Excel tổng hợp.
- `outputs/charts/`: 6 biểu đồ PNG.

## Báo cáo và kiểm thử

- `reports/cac_buoc_thuc_hien.md`: quy trình làm, kiểm tra và sửa.
- `reports/noi_dung_bao_cao.md`: nội dung báo cáo ngắn gọn.
- `tests/test_prepare_anomaly_data.py`: kiểm tra bước tạo feature.
- `tests/test_model_artifacts.py`: kiểm tra model và kết quả xuất ra.
