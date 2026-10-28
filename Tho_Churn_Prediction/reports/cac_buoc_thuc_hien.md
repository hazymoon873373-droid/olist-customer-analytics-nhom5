# Các bước thực hiện dự đoán churn proxy 180 ngày

> Tài liệu này ghi lại phiên bản cũ chia theo nhóm khách. Quy ước nhãn, cơ sở chọn 180 ngày
> và kết quả theo thời gian của bản mới được trình bày trong `bao_cao_temporal_v2.md`.

## 1. Xác định bài toán

Bài toán dự đoán khách hàng đang hoạt động có ngừng mua trong 180 ngày tiếp theo hay không. Do Olist không có cột churn chính thức, nhãn trong bài là nhãn thay thế:

```text
0 = có đơn delivered trong 180 ngày sau snapshot
1 = không có đơn delivered trong 180 ngày sau snapshot
```

## 2. Chọn nhóm khách hàng

Chỉ đưa một khách vào snapshot khi khách đó:

1. Đã có ít nhất hai đơn `delivered`.
2. Có mua hàng trong 180 ngày gần nhất.

Điều kiện này tránh gọi một người chỉ mua thử một lần là khách hàng đã rời bỏ.

## 3. Tạo rolling snapshot

Sử dụng 12 snapshot theo tháng, từ 01/04/2017 đến 01/03/2018. Mỗi snapshot phải còn đủ 180 ngày dữ liệu tương lai để tạo nhãn.

Một khách có thể xuất hiện ở nhiều snapshot. Mỗi dòng có `sample_id` bằng mã khách kết hợp ngày snapshot.

Kết quả có:

- 5.920 mẫu customer-snapshot.
- 1.484 khách hàng khác nhau.
- 299 mẫu quay lại.
- 5.621 mẫu churn proxy.

## 4. Tránh sử dụng thông tin tương lai

Đơn dùng để tính feature phải thỏa:

- `order_status = delivered`.
- Ngày mua không sau snapshot.
- Ngày giao hàng không sau snapshot.

Đơn mua trước snapshot nhưng giao sau snapshot không được dùng làm feature.

## 5. Tạo feature

Mô hình sử dụng 18 feature:

| Nhóm | Feature |
|---|---|
| RFM | `recency`, `frequency`, `monetary` |
| Gần đây | `orders_last_30d`, `orders_last_90d`, `orders_last_180d` |
| Gần đây | `spend_last_30d`, `spend_last_90d`, `spend_last_180d` |
| Giá trị đơn | `avg_order_value` |
| Thời gian | `customer_tenure_days`, `avg_days_between_orders` |
| Đơn hàng | `avg_items_per_order`, `avg_installments` |
| Vận chuyển | `avg_freight_value`, `freight_to_product_ratio` |
| Địa lý | `customer_state`, `region_name` |

Các feature được tính lại tại từng snapshot.

## 6. Chia train và test trước khi huấn luyện

Dữ liệu được chia bằng `StratifiedGroupKFold` năm fold. Một fold được dùng làm test, tương đương khoảng 20% dữ liệu.

```text
Train: 4.737 mẫu, 1.187 khách
Test:  1.183 mẫu,   297 khách
Khách trùng giữa hai tập: 0
```

Việc chia theo `customer_unique_id` ngăn một snapshot của khách nằm ở train và snapshot khác của cùng khách nằm ở test.

## 7. Pipeline tiền xử lý

Biến số dùng:

```text
SimpleImputer(strategy="median", add_indicator=True)
```

Biến phân loại dùng:

```text
SimpleImputer(strategy="most_frequent")
OneHotEncoder(handle_unknown="ignore")
```

Các bước này được đặt trong `Pipeline` cùng Random Forest. Khi GridSearchCV chia fold, median và danh mục chỉ được học từ phần train của fold đó.

## 8. GridSearchCV

GridSearchCV chạy ba fold trên tập train. Các fold tiếp tục được chia theo mã khách hàng.

Các tham số được thử:

```text
n_estimators: 250, 400
max_depth: 8, None
min_samples_leaf: 1, 5
min_samples_split: 2
max_features: sqrt
criterion: gini
class_weight: balanced
```

Tiêu chí chọn model là macro F1. Cấu hình được chọn:

```text
n_estimators = 250
max_depth = 8
min_samples_leaf = 5
min_samples_split = 2
max_features = sqrt
criterion = gini
class_weight = balanced
```

## 9. Chọn ngưỡng dự đoán

Ngưỡng được chọn từ dự đoán out-of-fold của tập train, không nhìn nhãn tập test. Ngưỡng tối ưu theo macro F1 là 0,57.

Sau khi chọn tham số và ngưỡng, model được fit lại trên toàn bộ train rồi mới đánh giá trên test.

## 10. Kết quả test

| Chỉ số | Kết quả |
|---|---:|
| Accuracy | 0,8791 |
| Balanced accuracy | 0,6445 |
| Macro precision | 0,5716 |
| Macro recall | 0,6445 |
| Macro F1 | 0,5888 |
| Weighted precision | 0,9250 |
| Weighted recall | 0,8791 |
| Weighted F1 | 0,8993 |
| Precision lớp quay lại | 0,1783 |
| Recall lớp quay lại | 0,3833 |
| F1 lớp quay lại | 0,2434 |
| Precision lớp churn | 0,9649 |
| Recall lớp churn | 0,9056 |
| F1 lớp churn | 0,9343 |
| ROC-AUC | 0,7168 |

Confusion matrix:

```text
                     Dự đoán quay lại   Dự đoán churn
Thực tế quay lại             23                37
Thực tế churn               106             1.017
```

Mốc đoán toàn bộ khách là churn có macro F1 bằng 0,4870 và balanced accuracy bằng 0,5000. Đây chỉ là mốc kiểm tra, không phải một thuật toán khác.

Báo cáo phân loại trên test:

| Lớp | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Quay lại (0) | 0,1783 | 0,3833 | 0,2434 | 60 |
| Churn (1) | 0,9649 | 0,9056 | 0,9343 | 1.123 |
| Macro avg | 0,5716 | 0,6445 | 0,5888 | 1.183 |
| Weighted avg | 0,9250 | 0,8791 | 0,8993 | 1.183 |

Trên train, accuracy đạt 0,9533, macro F1 đạt 0,8233 và weighted F1 đạt 0,9596. Các kết quả chi tiết của train được lưu riêng để kiểm tra độ chênh giữa train và test.

## 11. Tự đánh giá

Mô hình đã phân biệt hai lớp tốt hơn phiên bản dùng một snapshot cho toàn bộ khách. ROC-AUC đạt 0,7168 và recall lớp quay lại tăng lên 38,33%.

Tuy vậy, precision lớp quay lại chỉ đạt 17,83%. Trong 129 mẫu được dự đoán quay lại, có 23 mẫu đúng. Mô hình vẫn cần thêm dữ liệu khách mua lặp lại trước khi dùng trong thực tế.

## 12. Kiểm tra

Mười bốn test tự động kiểm tra:

- điều kiện ít nhất hai đơn;
- điều kiện hoạt động trong 180 ngày;
- đơn hủy và đơn giao sau snapshot;
- công thức feature;
- `sample_id` không trùng;
- model không dùng ID hoặc target làm feature;
- xác suất CSV khớp model đã lưu;
- một khách không xuất hiện ở cả train và test;
- tỷ lệ chia tập gần 80/20;
- bảng metric có đủ train, test, macro avg và weighted avg;
- metric trong CSV khớp với file JSON.

Các file `performance_metrics.csv`, `classification_report_train.csv`, `classification_report.csv`, `confusion_matrix_train.csv` và `confusion_matrix.csv` lưu lại đầy đủ kết quả đánh giá.
