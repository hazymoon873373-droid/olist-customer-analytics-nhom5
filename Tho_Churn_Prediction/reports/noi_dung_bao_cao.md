# Nội dung báo cáo: Dự đoán khách hàng không quay lại

## Mục tiêu

Nhóm xây dựng mô hình phân loại để ước lượng nguy cơ khách hàng không tiếp tục mua hàng trên Olist trong 180 ngày tiếp theo. Olist không cung cấp trạng thái rời bỏ chính thức nên bài sử dụng nhãn churn proxy dựa trên lịch sử giao dịch.

## Thiết kế dữ liệu theo thời gian

Ngày snapshot được chọn là 02/03/2018. Toàn bộ feature được tính từ các đơn đã giao thành công trước thời điểm này. Phần dữ liệu từ 03/03/2018 đến 29/08/2018 chỉ dùng để tạo nhãn.

Khách hàng có ít nhất một đơn giao thành công trong 180 ngày sau snapshot được gán nhãn 0. Khách không phát sinh đơn giao thành công được gán nhãn 1. Cách tách này ngăn thông tin tương lai đi vào feature.

Bộ dữ liệu cuối có 52.522 khách hàng, trong đó 595 khách quay lại và 51.927 khách thuộc nhóm churn proxy. Tỷ lệ churn 98,87% cho thấy dữ liệu mất cân bằng rất mạnh.

## Feature sử dụng

Mô hình sử dụng 16 feature số và hai feature phân loại. Các biến bao gồm RFM, số đơn và chi tiêu trong 30/90/180 ngày, giá trị đơn trung bình, thời gian gắn bó, khoảng cách giữa các lần mua, thông tin sản phẩm, phí vận chuyển, trả góp và khu vực của khách hàng.

Những khách chỉ có một lần mua không thể tính khoảng cách trung bình giữa các đơn. Pipeline điền median học từ tập train và thêm chỉ báo missing. `customer_state` và `region_name` được mã hóa one-hot. Các bước này nằm trong pipeline để xử lý nhất quán khi dự đoán dữ liệu mới.

## Huấn luyện mô hình

Dữ liệu được chia 80% train và 20% test, có giữ tỷ lệ hai lớp bằng `stratify` và sử dụng `random_state=42`. Mô hình chính là Random Forest với `class_weight="balanced"`.

GridSearchCV 3-fold được thực hiện trên tập train để chọn tham số theo macro F1. Cấu hình cuối gồm 400 cây, không giới hạn độ sâu, `min_samples_leaf=5`, `max_features="sqrt"` và tiêu chí Gini. Ngưỡng xác suất 0,68 được chọn từ dự đoán out-of-fold trên tập train. Tập test không tham gia quá trình này.

## Kết quả

Trên 10.505 khách hàng test, mô hình đạt accuracy 0,9780, balanced accuracy 0,5195, macro F1 0,5191 và ROC-AUC 0,5529. F1 của lớp churn là 0,9889 nhưng F1 của lớp khách quay lại chỉ đạt 0,0494.

Mô hình dự đoán đúng 6 trong 119 khách quay lại và dự đoán đúng 10.268 trong 10.386 khách churn. Kết quả cho thấy accuracy cao đến từ lớp churn chiếm gần toàn bộ dữ liệu. Balanced accuracy và ROC-AUC phản ánh rõ hơn rằng khả năng phân biệt hai nhóm còn hạn chế.

Feature importance cao nhất thuộc về `recency`, `customer_tenure_days`, tỷ lệ phí vận chuyển trên giá trị sản phẩm, phí vận chuyển trung bình, `monetary` và giá trị đơn trung bình. Feature importance cho biết mức đóng góp trong Random Forest, không chứng minh quan hệ nhân quả.

## Tính năng hệ thống

Model được lưu thành pipeline hoàn chỉnh. Script dự đoán nhận CSV có đủ feature, tự xử lý missing, mã hóa biến phân loại và xuất xác suất churn. Thành phần này có thể tích hợp vào website của nhóm dưới dạng chức năng tải file khách hàng và nhận danh sách nguy cơ.

Trong phạm vi phần học máy, sản phẩm bàn giao là model, script dự đoán hàng loạt, CSV gán nhãn, biểu đồ và báo cáo. Giao diện web không được tạo trong thư mục này.

## Hạn chế và hướng cải thiện

Nhãn đang mô tả việc không mua lại trong thời gian quan sát, không khẳng định khách đã rời bỏ vĩnh viễn. Số khách quay lại quá ít và đa số khách chỉ có một giao dịch lịch sử, làm feature hành vi chưa đủ mạnh.

Nếu có thêm dữ liệu, nhóm nên kéo dài lịch sử trước snapshot, tạo nhiều snapshot theo thời gian và bổ sung feature về đánh giá, khiếu nại, loại sản phẩm và hành vi mua lặp lại. Mô hình hiện tại nên được xem là thử nghiệm phục vụ đồ án, chưa dùng để tự động ra quyết định kinh doanh.
