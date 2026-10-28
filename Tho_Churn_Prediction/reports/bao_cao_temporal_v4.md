# Báo cáo không mua lại 180 ngày — temporal v4, 29/10/2026

## Phạm vi và nhãn

Một mẫu là customer_unique_id tại T0. Nhãn 0 có mua lại trong [T0,T0+180 ngày), nhãn 1
không mua lại trong cửa sổ đó. Đây là proxy cho đồ án, không phải nhãn churn chính thức
hay kết luận khách bỏ nền tảng vĩnh viễn. Horizon 180 ngày là quy ước nhóm cần giải thích.

Lịch sử gồm đơn delivered đã xác nhận trước T0, valid_delay_kpi=true, giao thực tế không
trước mua; tối thiểu hai đơn và recency không quá 180 ngày. Phạm vi bảo thủ này bỏ nhiều
khách, không suy rộng kết quả cho toàn bộ Olist. Timestamps nguồn chưa xác nhận timezone.
Observation end 31/08/2018 là giả định; đơn lẻ tháng 9–10 không chứng minh đầy đủ theo dõi.

Không coi đơn hủy là mua lại. Trạng thái chưa biết tại mốc ra quyết định có thể làm nhãn
unknown; không tự chuyển unknown thành không mua lại. Giữ nguyên các kiểm tra leakage cũ.

## Tính khả thi validation

Train mỗi fold lấy snapshot từ 10/2016 nhưng chỉ giữ cửa sổ nhãn đã hoàn tất trước T0
validation. Nhãn train dựng với label_known_by=T0 validation; nhãn validation phải biết
trước T0 test 01/03/2018. Kiểm tra từng fold được xuất thành CSV, không chỉ ghi lý thuyết.

| T0 validation | Dòng train | Khách train | Khách train mua lại | Khách validation | Khách validation mua lại |
|---|---:|---:|---:|---:|---:|
| 01/04/2017 | 0 | 0 | 0 | 73 | 0 |
| 01/05/2017 | 2 | 2 | 0 | 111 | 3 |
| 01/06/2017 | 5 | 3 | 0 | 184 | 6 |
| 01/07/2017 | 8 | 3 | 0 | 277 | 11 |
| 01/08/2017 | 23 | 15 | 0 | 345 | 16 |
| 01/09/2017 | 59 | 36 | 0 | 437 | 22 |

Không có fold train đủ hai lớp. Chương trình chặn tuning và giữ RF/0,5 mặc định; đây
là kết quả kiểm tra tính khả thi, không phải tuning thành công. Snapshot 01/04 chỉ hết
180 ngày vào 28/09, nên không được dùng nhãn hoàn chỉnh của nó để train cho đầu tháng 9.

Guard tối thiểu 5 khách khác nhau mỗi lớp là mức thử nghiệm nhỏ, không chứng nhận đủ
độ tin cậy. Nếu có dữ liệu mới đạt guard, code so sánh RF/LR bằng AP lớp mua lại và
chọn ngưỡng theo F1 lớp mua lại trên validation. Không dùng test để chọn hoặc ép đủ lớp.

## Kết quả lịch sử

Refit cấu hình giữ lại trên 1.427 dòng/495 khách ở các snapshot 04–09/2017; có 58 dòng
mua lại, không phải 58 khách độc lập. Test tại 01/03/2018 gồm 944 khách: 48 mua lại và
896 không mua lại. Có 21 khách xuất hiện ở train/test qua thời gian; đây không phải
kiểm định khách hoàn toàn mới. Test đã được xem ở các review trước, không phải holdout
mới chưa từng tiếp xúc. Lần sửa này không chọn mô hình/ngưỡng dựa vào kết quả test đó.

RF/0,5 tiếp tục dự đoán toàn bộ 944 khách không mua lại. Recall mua lại bằng 0; accuracy
94,92% giống baseline đa số về nhãn. ROC-AUC khoảng 0,642; AP mua lại khoảng 0,0806,
so với prevalence mua lại khoảng 0,0508. Xếp hạng còn yếu, chưa chứng minh triển khai
thành công. LR được xuất để so sánh; chưa được chọn chỉ vì một số metric test đã thấy
ở bản trước cao hơn. Không cam kết sửa quy trình sẽ khắc phục được thiếu dữ liệu lịch sử.

probability_summary ghi min/quartile/median/max và số dự đoán mỗi lớp cho RF/LR trên
train_in_sample và test_historical. Train không phải đánh giá độc lập. Validation CSV
có header nhưng không có dòng vì mọi fold bị loại. Biểu đồ phân bố hai lớp thật có
đường ngưỡng; không che giấu việc dự đoán cùng lớp.

Decile 1 xếp nguy cơ không mua lại cao nhất. Điểm hòa dùng thứ tự ổn định và báo số hòa
ở biên. Baseline có điểm hoàn toàn bằng nhau không có khả năng xếp hạng: ghi lift kỳ
vọng 1 thay vì lấy lợi thế ngẫu nhiên từ thứ tự dòng.

## Bàn giao

Model, metric, ngưỡng, nhãn dự đoán và BI lấy cùng selected_model. Bundle và data_contract
lưu danh tính/phiên bản, ngưỡng và trạng thái chất lượng. Test có repurchased_true =
1 - churn_proxy_180d; nhãn tương lai của BI để trống.

Snapshot BI 31/08/2018 00:00 có 96.089 khách: 1.170 được chấm, 94.919 không đủ điều kiện.
Không gán xác suất 0 cho nhóm chưa chấm. RF hiện xếp toàn bộ khách đủ điều kiện vào nhóm
cao; không tạo giả ba mức thấp/vừa/cao. Chỉ dùng để thử tích hợp, chưa dùng quyết định
chăm sóc. Không đổi ngưỡng hoặc bỏ khách chỉ để dashboard có đủ màu.

K-Means ghép vào BI là mô tả hồi cứu theo trạng thái cuối dataset, có thể có xác nhận
giao sau cutoff, không dùng làm features supervised. Isolation Forest đánh dấu đơn
bất thường, không mặc nhiên xác nhận gian lận. Hai mô-đun đó và các bảng raw/clean giữ nguyên.

## Tám việc đã xử lý

1. Giữ v3 trong lịch sử Git; v4 là đầu ra hiện hành duy nhất.
2. Thêm thống kê và biểu đồ phân bố xác suất theo lớp thật.
3. Audit validation có nhãn trưởng thành đúng thời gian; chặn tuning khi không khả thi.
4. So sánh candidate và baseline cùng test, công bố hỗ trợ lớp thiểu số và giới hạn.
5. Dùng ngưỡng cấu hình chung xuyên metric, bundle, inference và BI.
6. Thống nhất model bàn giao, tách test có nhãn khỏi BI chưa có nhãn.
7. Thêm test maturity, thiếu lớp, đếm khách độc lập, threshold, class probability,
   artifact/BI và baseline điểm bằng nhau; giữ các kiểm thử leakage hiện có.
8. Tạo lại model, CSV/JSON, Excel, biểu đồ và tài liệu.

Để tối ưu/kiểm định mạnh hơn cần thêm lịch sử hoặc thiết kế nghiên cứu khác được thống
nhất trước. Không tự đổi 180 thành 90 ngày hoặc nới phạm vi chỉ để tăng điểm. Trạng thái
chất lượng tiếp tục là experimental_not_validated_for_deployment.

## Kiểm chứng lần bàn giao

Đã chạy lại pipeline đầy đủ và 49 kiểm thử: 26 churn, 7 nạp dữ liệu chung, 7 K-Means,
9 phát hiện bất thường; tất cả đạt. Kiểm tra mutation đảo điều kiện đủ hỗ trợ lớp bị
test phát hiện, sau đó khôi phục và chạy lại 7 test protocol đạt. Excel đọc được đủ
7 sheet, biểu đồ phân bố xác suất được kiểm tra trực quan. Không có kiểm định mới
trên khách hàng thực tế; các kết quả trên chỉ xác nhận hành vi chương trình và
đối soát artifact, không chứng minh mô hình đủ chất lượng triển khai.
