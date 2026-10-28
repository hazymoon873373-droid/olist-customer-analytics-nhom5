# Danh sách file phần RFM và K-Means

## Code

- `source-code/prepare_rfm.py`: tạo lại bảng RFM từ order master.
- `source-code/train_kmeans.py`: đánh giá K, huấn luyện model và xuất kết quả.
- `source-code/kmeans_rfm.py`: tên chạy tương thích với code cũ.
- `source-code/predict_cluster.py`: dùng model đã lưu để gán cụm.
- `source-code/verify_rfm.py`: đối soát nguồn mới với RFM của Tâm và model đã lưu, không train lại.
- `source-code/export_summary.py`: tạo lại Excel từ kết quả và metric.

## Model

- `models/rfm_kmeans_pipeline.joblib`: model chính.
- `models/kmeans_rfm_pipeline.pkl`: tên model tương thích với kết quả cũ.

## Dữ liệu và kết quả

- `../Tho_Shared/data/`: master cập nhật, bảng sạch và bảng RFM của Tâm dùng để đối soát.
- `data/olist_powerbi_orders_master.csv`: master cũ, chỉ giữ để đối chiếu lịch sử.
- `outputs/rfm_rebuilt.csv`: bảng RFM tạo lại.
- `outputs/rfm_source_check.json`: hash nguồn và kết quả đối soát R/F/M.
- `outputs/rfm_customers_kmeans.csv`: bảng khách hàng đã gán cụm.
- `outputs/k_evaluation.csv`: kết quả đánh giá K=2 đến K=10.
- `outputs/cluster_profiles.csv`: hồ sơ bốn cụm.
- `outputs/model_metrics.json`: chỉ số mô hình.
- `outputs/Ketqua_KMeans.txt`: kết quả dạng văn bản.
- `outputs/rfm_kmeans_summary.xlsx`: tổng hợp Excel.
- `outputs/charts/`: biểu đồ phân tích.

## Tài liệu và kiểm tra

- `reports/cac_buoc_thuc_hien.md`: toàn bộ quy trình.
- `reports/noi_dung_bao_cao.md`: nội dung dùng cho báo cáo cuối kỳ.
- `tests/`: kiểm tra công thức RFM, pipeline và model đã lưu.
- `requirements.txt`: phiên bản thư viện đã sử dụng.
