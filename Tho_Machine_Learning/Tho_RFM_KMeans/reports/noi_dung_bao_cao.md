# Phân khúc khách hàng bằng RFM và K-Means

## 1. Mục tiêu

Mục tiêu của phần này là chia khách hàng Olist thành các nhóm có hành vi mua hàng tương đối giống nhau. Kết quả phân cụm được dùng để mô tả tập khách hàng và hỗ trợ nhóm đề xuất chính sách chăm sóc phù hợp.

## 2. Xây dựng dữ liệu RFM

Dữ liệu được lấy từ bảng order master. Nhóm dùng toàn bộ lịch sử đơn `delivered` đến hết ngày 30/08/2018 vì đây là các giao dịch đã hoàn thành. `valid_delay_kpi` không được dùng để loại đơn vì cờ này chỉ kiểm tra dữ liệu phục vụ KPI giao hàng. Sau bước kiểm tra dữ liệu còn 93.358 khách hàng.

Ba biến được tính như sau:

- Recency: số ngày từ lần mua gần nhất đến ngày tham chiếu 30/08/2018.
- Frequency: số đơn hàng khác nhau của một khách hàng.
- Monetary: tổng giá trị sản phẩm đã mua, chưa gồm phí vận chuyển.

Phần lớn khách hàng chỉ có một đơn hàng. Cụ thể, khoảng 97% khách hàng có Frequency bằng 1. Đây là đặc điểm cần lưu ý khi đọc kết quả vì Frequency không phân tán đều như Recency và Monetary.

## 3. Tiền xử lý

Giá trị RFM có phân phối lệch và khoảng giá trị chênh lệch lớn. Nhóm áp dụng hàm `log1p` để giảm ảnh hưởng của các giá trị quá lớn, sau đó chuẩn hóa bằng `StandardScaler`. Toàn bộ bước xử lý được đặt chung với K-Means trong một pipeline.

## 4. Lựa chọn số cụm

K được kiểm tra từ 2 đến 10 bằng Inertia, Silhouette, Davies-Bouldin, Calinski-Harabasz và độ ổn định ARI qua nhiều random seed.

K=2 có Silhouette cao nhất, đạt 0,7099. Tuy nhiên một cụm chiếm gần 97% khách hàng, nên kết quả chỉ cho biết sự khác nhau giữa nhóm mua một lần và nhóm mua lặp lại. K=4 nằm tại điểm elbow, có cơ cấu cụm cân bằng hơn và độ ổn định ARI đạt 0,9992. Do đó nhóm chọn K=4 làm mô hình cuối.

Các chỉ số của K=4:

| Chỉ số | Giá trị |
|---|---:|
| Silhouette | 0,3918 |
| Davies-Bouldin | 0,7591 |
| Calinski-Harabasz | 73.516,9960 |
| Stability ARI | 0,9992 |
| Inertia | 83.293,0135 |

Silhouette của K=4 thấp hơn K=2, nghĩa là ranh giới giữa một số nhóm không hoàn toàn tách biệt. Đổi lại, bốn nhóm có ý nghĩa sử dụng rõ hơn và quy mô đủ lớn để phân tích.

## 5. Kết quả phân cụm

| Phân khúc | Số khách | Tỷ lệ | Recency TB | Frequency TB | Monetary TB |
|---|---:|---:|---:|---:|---:|
| At-Risk High Spenders | 37.665 | 40,34% | 278,98 | 1,00 | 237,26 |
| Hibernating Low-Value | 36.601 | 39,20% | 285,20 | 1,00 | 45,10 |
| Champions / Loyal | 2.801 | 3,00% | 220,81 | 2,11 | 260,05 |
| Recent Active | 16.291 | 17,45% | 42,93 | 1,00 | 116,99 |

### At-Risk High Spenders

Nhóm này có giá trị mua trung bình cao nhưng đã lâu chưa quay lại. Có thể dùng ưu đãi quay lại, nhắc mua theo ngành hàng cũ hoặc voucher có thời hạn.

### Hibernating Low-Value

Khách đã lâu chưa mua và giá trị đơn thấp. Không nên dùng chương trình tốn chi phí cao; phù hợp hơn với email tự động hoặc ưu đãi đại trà.

### Champions / Loyal

Đây là nhóm duy nhất có Frequency trung bình lớn hơn 2 và Monetary cao nhất. Có thể ưu tiên chăm sóc, chương trình thành viên hoặc giới thiệu sản phẩm mới.

### Recent Active

Nhóm vừa mua gần đây nhưng phần lớn mới mua một lần. Mục tiêu phù hợp là khuyến khích đơn hàng thứ hai bằng gợi ý sản phẩm liên quan hoặc mã giảm giá cho lần mua tiếp theo.

## 6. Hạn chế

- RFM chỉ mô tả lịch sử giao dịch, chưa chứng minh quan hệ nhân quả.
- Tên phân khúc là cách diễn giải từ đặc trưng cụm, không phải nhãn có sẵn trong dữ liệu.
- Frequency rất mất cân bằng do phần lớn khách hàng chỉ mua một lần.
- Kết quả phản ánh giai đoạn dữ liệu Olist đến tháng 08/2018 và cần train lại khi có dữ liệu mới.
- Phân cụm không đồng nghĩa với dự báo churn. Bài toán nguy cơ không mua lại cần mô hình supervised riêng và mốc thời gian rõ ràng.

## 7. Kết luận

K-Means với K=4 tạo được bốn nhóm khách hàng có đặc điểm khác nhau về thời gian mua gần nhất, số lần mua và giá trị giao dịch. Mô hình đã được lưu cùng bước tiền xử lý nên có thể tích hợp vào ứng dụng và gán cụm cho dữ liệu RFM mới.
