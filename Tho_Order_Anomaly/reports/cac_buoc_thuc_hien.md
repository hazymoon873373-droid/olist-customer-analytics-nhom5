# Các bước thực hiện

## 1. Xác định bài toán

Mục tiêu là tìm các đơn hàng đã giao có đặc điểm khác nhiều so với phần lớn dữ liệu.
Đây là bài toán học không giám sát vì dữ liệu không có cột nhãn cho biết đơn nào thật sự bất thường.

Isolation Forest được chọn vì phù hợp với dữ liệu nhiều chiều, chạy được trên gần 100 nghìn đơn
và có thể xuất điểm bất thường cho từng đơn. Phần này không so sánh thêm thuật toán khác.

## 2. Chuẩn bị dữ liệu

Nguồn dữ liệu là `olist_powerbi_orders_master.csv` đã được nhóm tổng hợp trước đó.
Các bước xử lý:

1. Giữ lại đơn có trạng thái `delivered`.
2. Loại bản ghi trùng theo `order_id`.
3. Ép kiểu các cột số.
4. Tạo `freight_to_product_ratio` bằng phí vận chuyển chia giá trị sản phẩm.
5. Tạo `late_days` bằng phần dương của `delay_days`.

Ban đầu có thể dùng trực tiếp `delay_days`, nhưng giá trị âm là giao sớm. Nếu đưa nguyên giá trị âm
vào mô hình, các đơn giao rất sớm cũng có thể bị xem là vấn đề. Vì vậy feature cuối cùng chỉ giữ số ngày giao trễ.

## 3. Tiền xử lý trong Pipeline

- Điền giá trị thiếu bằng trung vị.
- Dùng `log1p` cho giá trị sản phẩm, phí vận chuyển, tỷ lệ phí và số sản phẩm.
- Dùng `RobustScaler` để giảm ảnh hưởng của các giá trị rất lớn.
- Đưa dữ liệu sau xử lý vào Isolation Forest.

Tiền xử lý và model nằm chung trong một Pipeline để khi dự đoán lại không bị lệch cách xử lý.

## 4. Cấu hình model

```text
n_estimators = 200
max_samples = 4096
contamination = 0.01
random_state = 42
```

`contamination = 0.01` nghĩa là mô hình khoanh vùng khoảng 1% đơn khác biệt nhất để kiểm tra.
Đây là ngưỡng sàng lọc, không có nghĩa 1% đơn chắc chắn sai hoặc gian lận.

## 5. Kiểm tra và điều chỉnh

Lần chạy đầu thu được 965 đơn bất thường. Khi xem biểu đồ profile, `late_days` không xuất hiện vì
trung vị của cả hai nhóm đều bằng 0, làm tỷ lệ trung vị thành 0/0. Phần vẽ biểu đồ được sửa để trường
hợp này hiển thị tại mốc 1. Kết quả model không thay đổi sau khi sửa.

Sau đó chạy lại 6 kiểm thử:

- 3 kiểm thử bước chuẩn bị dữ liệu.
- 3 kiểm thử model và các file kết quả.

Tất cả kiểm thử đều đạt.

## 6. Đánh giá kết quả

Vì không có nhãn thật, không dùng accuracy, precision, recall hoặc F1. Các cách kiểm tra phù hợp hơn:

- Tỷ lệ đơn bị gắn cờ: 1,00%.
- So sánh profile feature của nhóm bình thường và bất thường.
- Xem thủ công các đơn có anomaly score cao nhất.
- Chạy lại với seed 7 và so sánh với seed 42 bằng Jaccard.

Jaccard đạt 0,8021, cho thấy phần lớn đơn bị gắn cờ vẫn được giữ lại khi thay seed.

## 7. Chốt kết quả

Mô hình phát hiện 965 trong 96.478 đơn delivered. Nhóm bất thường có trung vị phí vận chuyển
cao khoảng 2,91 lần và thời gian giao hàng cao khoảng 2,47 lần nhóm bình thường.
Danh sách này nên được dùng làm đầu vào cho bước kiểm tra nghiệp vụ, không dùng như kết luận gian lận tự động.
