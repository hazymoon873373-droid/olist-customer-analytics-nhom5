# Các bước thực hiện dự đoán churn proxy 180 ngày

## 1. Xác định bài toán

Bài toán được xây dựng dưới dạng phân loại nhị phân. Mục tiêu là dự đoán một khách hàng có ngừng mua trong 180 ngày tiếp theo hay không.

Do Olist không có cột churn chính thức, nhãn trong bài là nhãn thay thế:

```text
1 = không có đơn delivered trong 180 ngày sau snapshot
0 = có ít nhất một đơn delivered trong 180 ngày sau snapshot
```

Không gọi đây là khách rời bỏ vĩnh viễn vì dữ liệu kết thúc ngày 29/08/2018.

## 2. Chọn mốc thời gian

- Snapshot: 02/03/2018 23:59:59.
- Cửa sổ quan sát nhãn: 03/03/2018 đến 29/08/2018.
- Độ dài cửa sổ: 180 ngày.

Mốc này cho phép dùng đủ phần dữ liệu còn lại để kiểm tra khách có quay lại hay không.

## 3. Lọc dữ liệu lịch sử

Feature chỉ lấy từ đơn thỏa cả ba điều kiện:

1. `order_status = delivered`.
2. `order_purchase_timestamp <= T0`.
3. `order_delivered_customer_date <= T0`.

Điều kiện thứ ba loại các đơn đã đặt nhưng chưa giao tại thời điểm snapshot. Nhờ vậy feature không dùng thông tin chỉ xuất hiện sau `T0`.

Sau khi lọc có 54.173 đơn lịch sử của 52.522 khách hàng.

## 4. Tạo feature

Mỗi khách hàng có 18 feature:

| Nhóm | Feature | Cách tính |
|---|---|---|
| RFM | `recency` | Số ngày từ lần mua cuối đến `T0` |
| RFM | `frequency` | Số đơn khác nhau trước `T0` |
| RFM | `monetary` | Tổng giá trị sản phẩm trước `T0` |
| Gần đây | `orders_last_30d`, `orders_last_90d`, `orders_last_180d` | Số đơn trong từng cửa sổ |
| Gần đây | `spend_last_30d`, `spend_last_90d`, `spend_last_180d` | Chi tiêu sản phẩm trong từng cửa sổ |
| Giá trị | `avg_order_value` | Monetary chia Frequency |
| Thời gian | `customer_tenure_days` | Số ngày từ đơn đầu tiên đến `T0` |
| Thời gian | `avg_days_between_orders` | Số ngày trung bình giữa hai lần mua |
| Đơn hàng | `avg_items_per_order` | Số sản phẩm trung bình mỗi đơn |
| Vận chuyển | `avg_freight_value` | Phí vận chuyển trung bình mỗi đơn |
| Vận chuyển | `freight_to_product_ratio` | Tổng phí vận chuyển chia tổng giá trị sản phẩm |
| Thanh toán | `avg_installments` | Số kỳ trả góp trung bình |
| Địa lý | `customer_state`, `region_name` | Vị trí ở đơn gần nhất trước `T0` |

Khách chỉ có một đơn sẽ thiếu `avg_days_between_orders`. Giá trị này được điền bằng median học từ tập train, đồng thời pipeline tạo thêm cột đánh dấu missing.

## 5. Tạo nhãn

Tìm các đơn `delivered` có thời gian mua sau `T0` và không muộn hơn 29/08/2018. Khách xuất hiện trong tập này nhận nhãn 0. Các khách còn lại nhận nhãn 1.

Kết quả:

- Quay lại, nhãn 0: 595 khách.
- Churn proxy, nhãn 1: 51.927 khách.
- Tỷ lệ churn proxy: 98,87%.

## 6. Chia dữ liệu

Dữ liệu được chia 80% train và 20% test bằng:

```text
train_test_split(test_size=0.2, random_state=42, stratify=y)
```

- Train: 42.017 khách.
- Test: 10.505 khách.

Tập test không tham gia chọn tham số và chọn ngưỡng.

## 7. Tiền xử lý

- Biến số: `SimpleImputer(strategy="median", add_indicator=True)`.
- Biến phân loại: điền mode rồi `OneHotEncoder(handle_unknown="ignore")`.
- Không dùng `StandardScaler` vì Random Forest không cần chuẩn hóa thang đo.

Toàn bộ bước tiền xử lý nằm trong `Pipeline`, tránh học median hoặc danh mục từ tập test.

## 8. Huấn luyện Random Forest

Chỉ sử dụng Random Forest. Không huấn luyện thêm thuật toán cạnh tranh.

Tám cấu hình được đánh giá bằng GridSearchCV 3-fold trên tập train. Tiêu chí chọn là macro F1 vì dữ liệu mất cân bằng. Tất cả cấu hình giữ `class_weight="balanced"`.

Tham số được chọn:

```text
n_estimators = 400
max_depth = None
min_samples_leaf = 5
min_samples_split = 2
max_features = sqrt
criterion = gini
class_weight = balanced
```

Ngưỡng 0,68 được chọn từ dự đoán out-of-fold trên tập train để tối đa macro F1. Sau đó model được fit lại trên toàn bộ train và đánh giá một lần trên test.

## 9. Kết quả trên tập test

| Chỉ số | Kết quả |
|---|---:|
| Accuracy | 0,9780 |
| Balanced accuracy | 0,5195 |
| Macro F1 | 0,5191 |
| Precision lớp quay lại | 0,0484 |
| Recall lớp quay lại | 0,0504 |
| F1 lớp quay lại | 0,0494 |
| F1 lớp churn | 0,9889 |
| ROC-AUC | 0,5529 |
| Average precision lớp quay lại | 0,0173 |

Confusion matrix:

```text
                     Dự đoán quay lại   Dự đoán churn
Thực tế quay lại              6               113
Thực tế churn                118            10.268
```

Mốc tham chiếu đoán tất cả khách là churn có macro F1 bằng 0,4972 và balanced accuracy bằng 0,5000. Đây chỉ là mốc kiểm tra, không phải thuật toán thứ hai.

## 10. Tự đánh giá

Mô hình hoàn thành đúng quy trình supervised learning và không có rò rỉ dữ liệu theo thời gian. Tuy nhiên chất lượng phân biệt còn thấp:

- Chỉ 595 khách thuộc lớp quay lại.
- Phần lớn khách chỉ có một đơn trước snapshot nên thông tin hành vi lặp lại rất ít.
- ROC-AUC 0,5529 chỉ cao hơn mức ngẫu nhiên một khoảng nhỏ.
- F1 lớp quay lại 0,0494 cho thấy model chưa nhận diện tốt lớp hiếm.

Vì vậy accuracy 97,80% không được dùng làm bằng chứng rằng model tốt. Mô hình hiện phù hợp để minh họa quy trình và xếp hạng thử nghiệm, chưa phù hợp để tự động quyết định chiến dịch giữ chân.

## 11. Xuất model và tính năng sử dụng

`random_forest_churn_pipeline.joblib` lưu:

- bước xử lý missing;
- one-hot encoding;
- Random Forest;
- danh sách feature;
- ngưỡng 0,68;
- định nghĩa nhãn và mốc thời gian.

`predict_churn.py` nhận một file CSV feature và xuất xác suất churn cùng nhãn dự đoán. Đây là phần có thể được gọi từ website hoặc API của nhóm sau này. Trong phạm vi bài hiện tại chưa tạo giao diện web riêng.

## 12. Kiểm tra

Tám test tự động kiểm tra:

- đơn hủy hoặc nằm ngoài cửa sổ không được tính là quay lại;
- đơn giao sau snapshot không đi vào feature;
- công thức Frequency, Monetary, AOV và khoảng cách giữa các đơn;
- model không dùng ID, target hoặc cột thời gian snapshot làm feature;
- xác suất và nhãn trong CSV khớp model đã lưu.
