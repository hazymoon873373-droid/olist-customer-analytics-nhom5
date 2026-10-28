# Đánh giá Random Forest theo thời gian — bản tạm thời

## Trạng thái dữ liệu

Bản thử dùng `olist_powerbi_orders_master.csv` cũ ngày 23/10/2026 và `olist_orders_clean.csv`
trong thư mục `processed` ngày 24/10/2026. SHA-256 và thời gian sửa file được lưu trong `metrics.json`.
Master mới và bản sạch chính thức chưa được nhóm xác nhận. Bảng sạch có 8 đơn delivered thiếu ngày giao;
master cũ đã điền cả 8 ngày. Phiên bản này lấy ngày giao từ bảng sạch và không dùng ngày master đã điền.

Mốc cuối theo dõi giả định là **2018-08-31 00:00:00**, không bao gồm thời điểm này. Mốc được chọn để
thử với dữ liệu đến hết 30/08/2018, chưa chứng minh dữ liệu đầy đủ hoặc trạng thái các đơn được chốt
đúng tại mốc. Không có timezone trong nguồn nên giữ timestamp không gắn timezone. Cần nhóm xác nhận
nguồn, độ đầy đủ và thời điểm chốt trạng thái trước khi dùng kết quả làm bản cuối.

## Quy ước nhãn và đặc trưng

- Mỗi dòng là một khách `customer_unique_id` tại T0, cửa sổ nhãn `[T0, T0 + 180 ngày)`.
- `0`: có đơn mua lại delivered đã xác nhận; `1`: không quan sát thấy đơn mua lại delivered; thiếu:
  chưa đủ thời gian hoặc còn đơn liên quan chưa xác định được kết quả.
- Lịch sử dùng đơn delivered có thời gian mua và giao đều trước T0, có ngày giao hợp lệ và đạt
  `valid_delay_kpi`. Đây là điều kiện thận trọng cho mô hình churn, không áp dụng để loại đơn khỏi RFM của Tâm.
- Phạm vi model: khách có từ hai đơn đủ điều kiện trở lên và có mua trong 180 ngày trước T0.
- Monetary chỉ cộng giá trị sản phẩm, không gồm cước. Không dùng K-Means làm feature.
- Thiếu timestamp thay đổi trạng thái/hủy và ngày ghi nhận thanh toán chi tiết; đã bỏ feature trả góp
  khỏi bản temporal. Một số trạng thái cuối vẫn chỉ là trạng thái của bản nguồn chứ không có lịch sử cập nhật.
  Đơn hủy trong cửa sổ train được xem là chưa rõ nếu không chứng minh được thời điểm hủy.
- Giá trị sản phẩm, số sản phẩm, cước và địa điểm lấy từ master; bản thử giả định các thông tin này
  đã có khi đơn được giao. Chưa có log thời điểm ghi nhận để xác minh từng trường.
- Tiền xử lý số và mã hóa bang/vùng nằm trong Pipeline, chỉ fit trên tập train.

## So sánh phạm vi khách

Trên 7 snapshot dùng cho phép thử, phạm vi ít nhất 1 đơn có 51.885 khách duy nhất, 120.776 dòng,
1.634 dòng mua lại, 119.099 dòng không mua lại và 43 chưa rõ. Phạm vi từ 2 đơn, hoạt động trong
180 ngày có 1.418 khách duy nhất, 2.371 dòng, 106 dòng mua lại và 2.265 dòng không mua lại.
Đây là số mẫu theo customer-snapshot, không phải số khách mua lại duy nhất.

## Chia theo thời gian và kết quả

Train dùng snapshot từ 01/04 đến 01/09/2017: 1.427 dòng của 495 khách, gồm 58 dòng mua lại và
1.369 dòng không mua lại. T0 test là **01/03/2018 00:00:00**; cửa sổ nhãn train kết thúc muộn nhất
lúc **28/02/2018 00:00:00**, trước T0 test. Test có 944 khách, 48 mua lại và 896 không mua lại;
21 khách xuất hiện ở cả train và test. Cách này đo theo thời gian, không phải đánh giá khách hoàn toàn mới.

Random Forest dùng cấu hình mặc định, `class_weight=balanced` và ngưỡng 0,5 cố định.
Không chọn tham số/ngưỡng bằng test. Do khoảng lịch sử train ngắn so với cửa sổ 180 ngày, chưa thực hiện
GridSearchCV tôn trọng thời gian; không tuyên bố đã tối ưu model hoặc ngưỡng cho phép thử này.

| Chỉ số test | Kết quả |
|---|---:|
| Accuracy | 0,9492 |
| ROC-AUC lớp không mua lại (1) | 0,6420 |
| Average Precision lớp không mua lại (1) | 0,9666 |
| Average Precision lớp mua lại (0) | 0,0806 |
| Macro Precision / Recall / F1 | 0,4746 / 0,5000 / 0,4870 |
| Weighted Precision / Recall / F1 | 0,9009 / 0,9492 / 0,9244 |
| Precision / Recall / F1 lớp mua lại (0) | 0 / 0 / 0 |
| Precision / Recall / F1 lớp không mua lại (1) | 0,9492 / 1,0000 / 0,9739 |
| Top decile lift lớp không mua lại | 1,0314 |

Confusion matrix, hàng là thực tế và cột là dự đoán theo thứ tự mua lại (0), không mua lại (1):
`[[0, 48], [0, 896]]`. Model dự đoán tất cả mẫu test là không mua lại. AP lớp 1 cao cần đặt cạnh
tỷ lệ lớp 1 là 94,92%; không thể xem riêng AP hoặc accuracy là bằng chứng model tốt. Decile được xếp
theo `churn_probability`, nghĩa là xác suất **không mua lại**; lift đo lớp 1, không phải lớp mua lại.

## Hai bảng bàn giao

- `snapshot_evaluation.csv`: khóa khách + `snapshot_timestamp`, split, nhãn, trạng thái nhãn,
  feature và xác suất test. Không gộp nhiều snapshot thành một khách.
- `bi_web_customers.csv`: một dòng mỗi khách có đơn trước **2018-08-31 00:00:00**. Cutoff này
  tương ứng hết ngày 30/08/2018 của bảng RFM/K-Means. Có 96.089 khách, 1.170 đủ điều kiện;
  94.919 khách còn lại không có xác suất. Nhãn thật tại cutoff chưa đủ quan sát nên để trống.
  Cột `kmeans_cluster`, `kmeans_segment` chỉ dùng để mô tả tại cutoff, không dùng làm feature churn.

Mức `cao`/`thap` dùng ngưỡng tạm 0,5, không phải thang rủi ro đã hiệu chỉnh. Cả 1.170 khách đủ
điều kiện hiện đều bị xếp `cao`; bảng chỉ dùng để thử giao diện tích hợp, chưa dùng ra quyết định.
K-Means cần được Tâm xác nhận cùng nguồn và mốc trước khi ghép chính thức.

## Bản cũ theo nhóm khách

Kết quả cũ được giữ trong `outputs/` và model cũ trong `models/` để đối chiếu lịch sử.
Bản đó gồm 1.484 khách duy nhất, 5.920 dòng, nhưng dùng master cũ và quy ước snapshot khác.
Không so sánh trực tiếp điểm giữa hai bản như cùng bộ dữ liệu. Không dùng model cũ để chấm toàn bộ khách.
