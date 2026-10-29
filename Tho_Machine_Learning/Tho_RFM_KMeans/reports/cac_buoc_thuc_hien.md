# Các bước thực hiện RFM và K-Means

## 1. Kiểm tra dữ liệu đầu vào

File sử dụng là `Tho_Shared/data/olist_powerbi_orders_master_20261028.csv`, gồm 99.441 đơn hàng. Các cột cần dùng:

- `order_id`
- `customer_unique_id`
- `order_status`
- `order_purchase_timestamp`
- `total_products_value`

## 2. Tạo lại bảng RFM

Lọc đơn `delivered` trong toàn bộ lịch sử đến hết ngày 30/08/2018, loại dòng thiếu khóa khách hàng, thời gian mua hoặc giá trị sản phẩm. Nếu có một `order_id` xuất hiện nhiều lần thì chỉ giữ một dòng để tránh cộng tiền hai lần. Không dùng `valid_delay_kpi` để lọc RFM vì cờ này chỉ phục vụ KPI giao hàng.

Công thức:

```text
Recency   = ngày tham chiếu - ngày mua gần nhất
Frequency = số order_id khác nhau
Monetary  = tổng total_products_value
```

Ngày tham chiếu được cố định là 30/08/2018 để phần RFM của Tâm và phần K-Means của Thọ dùng cùng cách tính. Ngày mua lớn nhất trong dữ liệu hiện có là 29/08/2018. Kết quả có 93.358 khách hàng.

## 3. Tiền xử lý trước K-Means

RFM có độ lệch lớn, đặc biệt là Frequency và Monetary. Áp dụng `log1p` cho cả ba biến, sau đó dùng `StandardScaler`. Hai bước này được đặt trong pipeline để lúc dùng model không bị thiếu bước xử lý.

## 4. Đánh giá số cụm

Chạy K-Means từ K=2 đến K=10. Mỗi K được đánh giá bằng:

- Inertia và biểu đồ Elbow.
- Silhouette Score.
- Davies-Bouldin Index.
- Calinski-Harabasz Score.
- ARI trung bình qua các seed 7, 21, 42, 84 và 168.
- Tỷ lệ cụm nhỏ nhất và lớn nhất.

K=2 có Silhouette 0,7099 nhưng cụm lớn chiếm gần 97%. Cách chia này chủ yếu tách nhóm mua lặp lại khỏi toàn bộ khách còn lại, chưa đủ để xây dựng chính sách riêng.

K=4 nằm tại điểm elbow, cụm lớn nhất chiếm 40,34%, cụm nhỏ nhất chiếm 3,00% và ARI đạt 0,9992. Vì vậy chọn K=4.

## 5. Huấn luyện model cuối

Model cuối dùng:

```text
log1p -> StandardScaler -> KMeans(K=4, n_init=30, random_state=42)
```

Tên cụm được gán từ hồ sơ RFM sau khi train, không gắn cố định vào cluster ID trước khi xem kết quả.

## 6. Xuất kết quả

- `outputs/rfm_rebuilt.csv`: bảng RFM tạo lại.
- `outputs/rfm_customers_kmeans.csv`: RFM kèm cluster và segment.
- `outputs/k_evaluation.csv`: kết quả K=2 đến K=10.
- `outputs/cluster_profiles.csv`: đặc trưng bốn cụm.
- `outputs/model_metrics.json`: metric chính.
- `models/rfm_kmeans_pipeline.joblib`: model dùng cho ứng dụng.
- `outputs/charts/`: sáu biểu đồ phục vụ báo cáo.
- `outputs/Ketqua_KMeans.txt`: kết quả dạng văn bản.
- `outputs/rfm_kmeans_summary.xlsx`: bảng Excel gồm metric, hồ sơ cụm và đánh giá K.

## 7. Kiểm tra

Bộ test kiểm tra cách lọc đơn, công thức Frequency/Monetary, khả năng xử lý giá trị 0 và việc dự đoán từ RFM chưa chuẩn hóa. Model sau khi lưu được nạp lại và cho kết quả trùng 93.358/93.358 dòng so với lúc train.

Lịch sử chính trên Git:

- `c399619`: tạo lại bảng RFM và test công thức.
- `1202e45`: đánh giá K, huấn luyện model và xuất kết quả.
