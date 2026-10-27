# Nội dung báo cáo: Dự đoán khách hàng rời bỏ

## Mục tiêu

Nhóm xây dựng mô hình phân loại để dự đoán khách hàng đang hoạt động có ngừng mua trong 180 ngày tiếp theo hay không. Olist không có trạng thái rời bỏ chính thức nên bài sử dụng nhãn churn proxy dựa trên giao dịch.

## Cách tạo nhãn

Khách hàng chỉ được đưa vào bài toán khi đã có ít nhất hai đơn giao thành công và có mua hàng trong 180 ngày gần nhất. Điều kiện này giúp bài toán tập trung vào khách đã hình thành hành vi mua lặp lại.

Dữ liệu được tạo tại 12 snapshot hàng tháng từ tháng 04/2017 đến tháng 03/2018. Tại mỗi snapshot, khách có đơn giao thành công trong 180 ngày tiếp theo được gán nhãn 0. Khách không có đơn được gán nhãn 1.

Feature chỉ sử dụng thông tin đã có trước snapshot. Những đơn chưa giao xong tại thời điểm snapshot không được tính.

## Dữ liệu sau khi tạo nhãn

Bảng cuối có 5.920 mẫu customer-snapshot của 1.484 khách hàng. Trong đó có 299 mẫu quay lại và 5.621 mẫu churn proxy. Tỷ lệ churn là 94,95%.

So với cách đưa toàn bộ khách hàng vào một snapshot, tỷ lệ mẫu quay lại đã tăng từ 1,13% lên 5,05%. Dữ liệu vẫn mất cân bằng nhưng có nhiều trường hợp mua lại hơn để mô hình học.

## Chia dữ liệu

Dữ liệu được chia khoảng 80% train và 20% test bằng `StratifiedGroupKFold`. `customer_unique_id` được dùng làm group nên tất cả snapshot của một khách chỉ thuộc một tập.

Tập train có 4.737 mẫu của 1.187 khách. Tập test có 1.183 mẫu của 297 khách. Không có khách hàng trùng giữa hai tập.

## Pipeline và huấn luyện

Pipeline gồm bước điền missing cho feature số, one-hot encoding cho feature phân loại và Random Forest. Việc đặt tiền xử lý trong Pipeline giúp mỗi fold chỉ học median và danh mục từ dữ liệu train.

GridSearchCV ba fold được chạy trên tập train và tiếp tục chia theo mã khách hàng. Model được chọn bằng macro F1. Cấu hình cuối sử dụng 250 cây, độ sâu tối đa 8, `min_samples_leaf=5` và `class_weight="balanced"`.

Ngưỡng xác suất 0,57 được chọn từ dự đoán out-of-fold của train. Tập test chỉ được dùng ở bước đánh giá cuối.

## Kết quả

Trên tập test, mô hình đạt accuracy 0,8791, balanced accuracy 0,6445, macro F1 0,5888 và ROC-AUC 0,7168.

Đối với lớp khách quay lại, precision đạt 0,1783, recall đạt 0,3833 và F1 đạt 0,2434. Mô hình phát hiện đúng 23 trong 60 mẫu quay lại. Đối với lớp churn, F1 đạt 0,9343.

Feature có mức độ quan trọng cao gồm khoảng cách trung bình giữa các lần mua, tỷ lệ phí vận chuyển trên giá trị sản phẩm, tổng chi tiêu, giá trị đơn trung bình, chi tiêu 180 ngày và recency. Feature importance chỉ cho biết mức đóng góp trong Random Forest, không chứng minh quan hệ nhân quả.

## Tính năng hệ thống

Model được lưu thành một pipeline hoàn chỉnh. Script dự đoán nhận file CSV feature, tự xử lý missing, mã hóa biến phân loại và xuất xác suất churn. Thành phần này có thể được website hoặc API của nhóm gọi lại sau này.

## Hạn chế

Dữ liệu vẫn có ít mẫu quay lại, chỉ chiếm 5,05%. Precision lớp quay lại còn thấp nên danh sách dự đoán cần được xem là danh sách ưu tiên kiểm tra, không phải kết luận chắc chắn.

Ngoài ra, nhiều snapshot của cùng một khách có thể tạo ra các mẫu gần nhau theo thời gian. Bài đã giảm rò rỉ bằng cách chia theo khách hàng, nhưng kết quả vẫn cần được kiểm tra thêm trên dữ liệu mới trước khi ứng dụng thực tế.
