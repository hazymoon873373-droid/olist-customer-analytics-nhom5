# Dự đoán không mua lại trong 180 ngày — đánh giá theo thời gian

## Cơ sở chọn 180 ngày

Zeinali, Ramezani Asli và Khalili (2026) nghiên cứu trên dữ liệu Olist, sử dụng ngưỡng 180 ngày
để định nghĩa khách không còn hoạt động và mô tả thiết kế dự đoán với T0 trước cửa sổ nhãn.
Tác giả báo cáo khoảng 88% khoảng cách mua lặp lại được khảo sát nằm trong 180 ngày. Đây là kết quả
của bài nghiên cứu, không phải số liệu nhóm đã tự tính trên dữ liệu đang dùng. Ngưỡng có thể thay đổi
theo đặc điểm khách hàng và ngành hàng; không khẳng định khách rời bỏ vĩnh viễn sau 180 ngày.

Zeinali, M., Ramezani Asli, L., & Khalili, M. A. (2026). *Integrating Business Intelligence and CRM
Systems With a Machine Learning Approach for Predictive Customer Retention in E-Commerce*.
The Scientific World Journal, 2026, 1946904. <https://doi.org/10.1155/tswj/1946904>

## Nguồn dữ liệu và giới hạn

Bản `rf_temporal_v3_20261028_provisional` dùng master nhóm cập nhật ngày 28/10/2026, bảng đơn sạch,
bảng thanh toán sạch và snapshot vùng IBGE trong `Tho_Shared/data/`. Code đối chiếu mã đơn, trạng thái,
thời gian mua theo phút và bốn cờ chất lượng giữa master và bảng sạch. Thời gian mua, giao và dự kiến
được lấy từ bảng sạch có độ chính xác đến giây, không dùng 8 ngày giao đã được điền trong master cũ.
Tên, phiên bản và SHA-256 các file được lưu trong `outputs/temporal_v3_provisional/metrics.json`.

Mốc kết thúc quan sát **2018-08-31 00:00:00** đang là giả định, không bao gồm thời điểm đó.
Nhóm cần xác nhận dữ liệu đầy đủ và thời điểm chốt trạng thái đơn để xem nhãn là chính thức.
Nguồn không ghi timezone, vì vậy timestamp giữ nguyên không gắn timezone. Chưa có lịch sử thay đổi
trạng thái/hủy và thời điểm ghi nhận đầy đủ cho từng trường; việc dùng trạng thái cuối để gán nhãn
vẫn có giới hạn. Giá trị sản phẩm, số sản phẩm, cước và địa điểm được giả định đã biết khi đơn giao.

## Quy ước mẫu và nhãn

Một mẫu là một khách tại T0, không gộp các snapshot khác nhau. Feature chỉ dùng dữ liệu trước T0;
khách cần ít nhất 2 đơn delivered đủ điều kiện đã giao trước T0 và có mua trong 180 ngày trước T0.
Để thận trọng, phiên bản churn còn yêu cầu đơn lịch sử đạt `valid_delay_kpi`. Quy tắc này làm hẹp
phạm vi model và không dùng để loại đơn khỏi RFM gốc của Tâm. Monetary chỉ tính tiền sản phẩm.

Trong `[T0, T0 + 180 ngày)`, nhãn `0` là có đơn mua lại delivered được xác nhận; nhãn `1` là
không quan sát được đơn mua lại hợp lệ. Nếu chưa đủ 180 ngày hoặc còn đơn có kết quả chưa rõ, nhãn
chưa xác định. Đơn hủy trong cửa sổ train được đánh dấu chưa rõ nếu không chứng minh được khi nào hủy.
Không dùng cụm K-Means tại tháng 08/2018 làm feature cho các snapshot trước đó.

## Dữ liệu và chia tập

Theo giả định dữ liệu đủ quan sát đến cutoff nêu trên, train dùng các snapshot đầu tháng từ
01/04 đến 01/09/2017: **1.427 mẫu của 495 khách**, gồm 58 mẫu mua lại và 1.369 mẫu không mua lại.
Nhãn train kết thúc muộn nhất ngày **28/02/2018 00:00:00**, trước T0 test **01/03/2018 00:00:00**.
Test gồm **944 khách: 48 mua lại, 896 không mua lại**. Có 21 khách xuất hiện ở cả train và test;
đây là đánh giá theo thời gian, không phải đánh giá riêng khách hoàn toàn mới.

Trên 7 snapshot của phép thử, phạm vi từ 1 đơn gồm 51.885 khách duy nhất và 120.776 dòng; phạm vi
2 đơn, hoạt động 180 ngày gồm 1.418 khách duy nhất và 2.371 dòng. Số này theo phiên bản v3,
khác với 1.484 khách trong kết quả chia theo nhóm khách phiên bản cũ.

Random Forest dùng tham số mặc định, `class_weight=balanced` và ngưỡng 0,5 cố định. Tiền xử lý nằm
trong Pipeline fit trên train; không chọn model hoặc ngưỡng bằng test. Chưa thực hiện GridSearchCV
theo thời gian vì lịch sử train ngắn so với khoảng cách cần thiết để quan sát nhãn 180 ngày.

## Kết quả test

Đã bổ sung Logistic Regression và baseline luôn dự đoán không mua lại trên cùng tập test thời gian.
Ngưỡng 0,5 được cố định trước, không chọn theo kết quả test. Logistic Regression nhận diện 27/48
mẫu mua lại (recall 0,5625), nhưng chỉ 27/375 dự đoán mua lại là đúng (precision 0,0720);
ROC-AUC là 0,6254. Random Forest có ROC-AUC 0,6420 nhưng tại ngưỡng 0,5 không nhận diện được mẫu
mua lại nào. Baseline đa số có accuracy 0,9492. So sánh đầy đủ trong `baseline_comparison.json`.
Chưa có căn cứ chọn mô hình này cho quyết định chăm sóc thực tế; tập test chỉ có 48 mẫu mua lại,
thời điểm kết thúc quan sát và nhãn vẫn cần nhóm xác nhận.

`score_decile` xếp theo xác suất không mua lại giảm dần, 1 là nhóm điểm cao nhất; nếu điểm trùng,
thứ tự xuất ổn định quyết định thứ hạng. Tập BI có decile trong nhóm đủ điều kiện tại cutoff;
decile trong bảng đánh giá được tính riêng trên tập test. Hai bảng không dùng cùng mẫu số.

| Chỉ số | Kết quả |
|---|---:|
| Accuracy | 0,9492 |
| ROC-AUC lớp không mua lại (1) | 0,6420 |
| AP lớp không mua lại (1) | 0,9666 |
| AP lớp mua lại (0) | 0,0806 |
| Macro Precision / Recall / F1 | 0,4746 / 0,5000 / 0,4870 |
| Weighted Precision / Recall / F1 | 0,9009 / 0,9492 / 0,9244 |
| Precision / Recall / F1 lớp mua lại (0) | 0 / 0 / 0 |
| Precision / Recall / F1 lớp không mua lại (1) | 0,9492 / 1,0000 / 0,9739 |
| Top Decile Lift lớp không mua lại | 1,0314 |

Confusion matrix, hàng là thực tế và cột là dự đoán theo thứ tự mua lại (0), không mua lại (1):
`[[0, 48], [0, 896]]`. Tất cả mẫu test được dự đoán là không mua lại; accuracy và weighted F1 cao
do lớp không mua lại chiếm đa số, không cho thấy model nhận diện tốt khách mua lại.

Decile xếp giảm dần theo **xác suất không mua lại**, lift đo lớp `1`. Đường PR được xuất riêng cho
hai lớp; đường lớp mua lại dùng `1 - churn_probability`. Feature importance phản ánh mức đóng góp
của feature trong model, không khẳng định quan hệ nhân quả.

## Bàn giao và ứng dụng

- `snapshot_evaluation.csv`: khách + snapshot, split, nhãn và trạng thái nhãn; xác suất có trên tập test.
- `bi_web_customers.csv`: một dòng mỗi khách tại **2018-08-31 00:00:00**, tương ứng hết ngày
  30/08/2018 của RFM. Gồm 96.089 khách, trong đó 1.170 đủ điều kiện; 94.919 khách còn lại không
  được gán xác suất. Nhãn thật sau cutoff để trống vì chưa đủ dữ liệu tương lai trong phép thử.
- `kmeans_cluster` và `kmeans_segment` mô tả RFM hồi cứu đến cutoff theo trạng thái đơn cuối cùng,
  không dùng làm feature churn. Trạng thái delivered có thể được xác nhận sau cutoff; vì vậy không
  coi các cụm này là thông tin chắc chắn đã có tại thời điểm dự đoán. Cột `kmeans_data_status`
  đánh dấu cách hiểu này để nhóm lưu ý khi tích hợp.
- Mức rủi ro `cao`/`thap` là ngưỡng thử 0,5, có thêm cờ `tham_khao_chua_hieu_chuan`.
  Model hiện xếp toàn bộ khách đủ điều kiện vào mức cao; chỉ dùng bảng để thử tích hợp, không
  dùng trực tiếp cho quyết định chăm sóc.

Bản chia nhóm khách trước đây và temporal v2 được lưu trong lịch sử Git để đối chiếu, dùng nguồn và
quy ước khác nhau; không xem điểm các bản là kết quả cùng một phép thử. Mô hình chưa đủ cơ sở để
khẳng định hiệu quả dự báo thực tế hoặc chốt mốc theo dõi 180 ngày.
