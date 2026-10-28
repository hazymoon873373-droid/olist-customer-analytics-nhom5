# Khảo sát và phát hiện điểm bất thường trong dữ liệu

## Mục tiêu

Nhóm xây dựng mô hình Isolation Forest để phát hiện các đơn hàng đã giao có đặc điểm khác biệt
so với phần lớn dữ liệu. Kết quả giúp khoanh vùng các trường hợp có chi phí, số lượng sản phẩm,
thanh toán hoặc thời gian giao hàng cần được kiểm tra thêm.

## Dữ liệu và feature

Dữ liệu đầu vào gồm 96.478 đơn hàng có trạng thái `delivered`. Mỗi dòng tương ứng một đơn hàng.
Tám feature được dùng gồm giá trị sản phẩm, phí vận chuyển, tỷ lệ phí vận chuyển trên giá trị sản phẩm,
số sản phẩm, số kỳ trả góp, số bản ghi thanh toán, thời gian giao hàng và số ngày giao trễ.

Các biến có phân phối lệch được biến đổi `log1p`. Giá trị thiếu được điền bằng trung vị và dữ liệu
được chuẩn hóa bằng RobustScaler. Toàn bộ bước tiền xử lý nằm trong Pipeline cùng model.

Đối chiếu bảng đơn sạch hiện có: 1.381 đơn không đạt cờ `valid_delay_kpi`, gồm 8 đơn thiếu ngày giao.
Nhóm vẫn giữ các đơn này, nhưng để thiếu hai biến thời gian giao hàng và điền trung vị trong Pipeline.
Ngày giao và ngày dự kiến lấy từ bảng sạch, không lấy ngày đã điền của master cũ. Bản này dùng
master nhóm cập nhật ngày 28/10/2026 cùng bảng sạch; phiên bản và hash được lưu trong model_metrics.json.

## Mô hình

Isolation Forest cô lập các quan sát bằng nhiều cây ngẫu nhiên. Những quan sát dễ bị cô lập hơn
thường có đặc điểm khác so với phần lớn dữ liệu và nhận điểm bất thường cao hơn.
Mô hình sử dụng 200 cây, `max_samples = 4096`, `contamination = 0.01` và `random_state = 42`.

## Kết quả

Mô hình gắn cờ 965 đơn, chiếm 1,00% trong 96.478 đơn được khảo sát. Khi chạy lại với seed 7,
Jaccard giữa hai tập đơn bất thường đạt 0,7953. Chỉ số này phản ánh độ trùng giữa hai lần chạy,
không chứng minh nhãn bất thường là đúng.

So với nhóm bình thường, nhóm bất thường có:

- Trung vị giá trị sản phẩm cao 1,84 lần.
- Trung vị phí vận chuyển cao 2,90 lần.
- Trung vị tỷ lệ phí vận chuyển cao 1,44 lần.
- Trung vị thời gian giao hàng cao 2,46 lần, chỉ tính các giá trị thời gian hợp lệ.

Các dấu hiệu thường gặp nhất là nhiều sản phẩm, thời gian giao hàng dài, giao hàng trễ nhiều
và phí vận chuyển cao. Một đơn có thể có nhiều dấu hiệu cùng lúc.

## Hạn chế

Dữ liệu không có nhãn bất thường thực tế, vì vậy không thể kết luận 965 đơn trên đều là lỗi hoặc gian lận.
Các chỉ số accuracy, precision, recall và F1 không được sử dụng trong phần này vì sẽ không có nhãn thật để đối chiếu.
Kết quả phù hợp để sàng lọc và hỗ trợ kiểm tra nghiệp vụ.

## Kết luận

Isolation Forest đã giúp thu hẹp dữ liệu từ hơn 96 nghìn đơn xuống 965 trường hợp cần chú ý.
Mô hình, Pipeline, CSV gán nhãn, biểu đồ và file Excel tổng hợp đã được lưu để nhóm có thể chạy lại
hoặc dùng cho phần trình bày kết quả.
