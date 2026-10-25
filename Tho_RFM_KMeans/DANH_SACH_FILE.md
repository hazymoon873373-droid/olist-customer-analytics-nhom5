# Danh sách file phần RFM và K-Means

## Code

- `source-code/prepare_rfm.py`: tạo lại bảng RFM từ order master.
- `source-code/train_kmeans.py`: đánh giá K, huấn luyện model và xuất kết quả.
- `source-code/kmeans_rfm.py`: tên chạy tương thích với code cũ.
- `source-code/predict_cluster.py`: dùng model đã lưu để gán cụm.

## Model

- `models/rfm_kmeans_pipeline.joblib`: model chính.
- `models/kmeans_rfm_pipeline.pkl`: tên model tương thích với kết quả cũ.

## Dữ liệu và kết quả

- `data/olist_powerbi_orders_master.csv`: dữ liệu đầu vào khi đóng gói trong thư mục cuối kỳ.
- `outputs/rfm_rebuilt.csv`: bảng RFM tạo lại.
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
