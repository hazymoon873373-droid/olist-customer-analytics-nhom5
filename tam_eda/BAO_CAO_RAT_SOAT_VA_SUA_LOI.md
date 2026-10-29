# Rà soát toàn bộ code Tâm và kết quả xử lý

Ngày 29/10/2026. Đầu vào: tam_eda (.zip trong Downloads.
SHA256 ZIP gốc: 670d397b05fe8213137d61c22e777ec34b658a0d1fcf3b5a851adf5dac2388b0.

Đã đọc 8/8 Python, kiểm tra cú pháp, lần theo nguồn–biến đổi–xuất–vẽ, đối chiếu bộ sạch Thiên và kết quả Thọ. Cả 8 file qua kiểm tra cú pháp; lỗi nằm ở logic, đường dẫn, nhiều writer và việc code không đồng nhất với dữ liệu xuất sẵn. Tâm có xử lý, biểu đồ, RFM/cohort và thiết kế thực tế; không phải chỉ sườn.

## Mảng 1 — Nguồn dữ liệu và đường dẫn

**Lỗi:** eda_analysis_pipeline.py:22–23, run_eda.py:19–20 mặc định ổ D; load_data.py còn nhánh raw/latest-success; script khác dùng D:/Dữ liệu sạch hoặc D:/Huy_ThuThap_Olist. Tên CSV giữa các luồng khác nhau. Máy đủ file có thể chạy một nhánh, máy khác lỗi hoặc đọc phiên bản khác.

**Đã sửa:** load_data.py chỉ đọc tên chuẩn từ inputs/clean; không fallback raw. Mặc định theo vị trí script, đổi được qua CLI. Thiếu file báo rõ. IBGE và RFM reference ghim cùng phiên bản, có hash.

## Mảng 2 — Thời gian và giao trễ

**Lỗi 2.1:** rfm_cohort_analysis.py:65–66, eda_analysis_pipeline.py:142–143 dùng timestamp <= end_date, biến ngày cuối kỳ thành 00:00:00. Đã tái hiện với đơn lúc 14:00 ngày cuối.

**Sửa:** Cận trên mở < ngày kết thúc + 1 ngày. Tách bộ lọc khám phá với snapshot RFM đã chốt.

**Lỗi 2.2:** eda_analysis_pipeline.py:175, run_eda.py:168 biến so sánh ngày thiếu thành False; mẫu số KPI có thể gồm đơn không đủ điều kiện. apply_leader_feedback.py đã thêm cờ nhưng không khiến các entrypoint khác đồng nhất.

**Sửa:** Cờ boolean được kiểm tra chặt; chỉ gán is_delayed cho valid_delay_kpi=true; ngoài phạm vi giữ null. Giữ timestamp đến giây, tính chênh lệch theo giây rồi đổi ngày. Cờ true nhưng thiếu ngày sẽ báo lỗi. Không xóa đơn bất thường để làm đẹp KPI.

**Kiểm chứng:** Test ngày cuối, ngày thiếu, cờ xung đột; đối soát 5 timestamp toàn bộ master với nguồn. Kết quả 95.097 đơn hợp lệ, 7.793 trễ, median 10,271782 ngày.

## Mảng 3 — Review, khóa, tiền và KPI

**Lỗi 3.1:** eda_analysis_pipeline.py:155, export_rfm_pipeline_chuan.py:36 tính review chưa loại cờ trước mua. run_eda.py:170 nối review chi tiết có thể nhân dòng cấp đơn.

**Sửa:** Loại 64 review trước mua trước khi tính điểm. Giữ 10 cùng ngày chưa rõ thứ tự theo quy ước nhóm; cần ghi rõ giới hạn này. Trung bình theo đơn, giữ điểm lẻ; thiếu giữ null. Items/payments tổng hợp về order trước khi nối. Kiểm tra khóa chính/ngoại, giá trị kinh tế và cờ; không âm thầm bỏ dòng.

**Lỗi 3.2:** Quy tắc thanh toán chính và CSV KPI không thống nhất giữa các writer.

**Sửa:** Thanh toán chính chọn giao dịch giá trị lớn nhất, hòa chọn sequential nhỏ nhất. Bảng giao dịch thanh toán riêng giữ giá trị thực từng phương thức. KPI xuất số thật kèm scope: GMV/AOV delivered, canceled và unavailable riêng, repeat historical delivered, giao trễ hợp lệ. Thống kê có count/mean/median/min/max/std và quartile/IQR.

**Kiểm chứng:** Review 1 và 5 điểm, review 1 bị cờ: code cũ cho 3, bản sửa cho 5. Test giữ trung bình 4,5 khi hai review hợp lệ. Master có 829 đơn thiếu điểm, không điền 0. Test tiền đối soát GMV/gross/AOV từ item delivered độc lập.

## Mảng 4 — RFM, cohort, lọc đa chiều

**Lỗi 4.1:** rfm_cohort_analysis.py:105–112 reference động và chênh timestamp có giờ. apply_leader_feedback.py:135–137 và export_rfm_pipeline_chuan.py:100–102 dùng thang F khác rfm_cohort_analysis.py. Nhiều cách chia nhóm, qcut kém bền với dữ liệu nhỏ/nhiều điểm trùng; chạy lần lượt có thể đổi nhãn Thọ nhận.

**Sửa:** Một RFM lõi, reference 30/08/2018, mua trước 31/08, recency theo ngày. Đối soát từng khách với rfm_reference.csv trước khi dùng điểm/6 nhãn đã duyệt. Không đổi thang điểm, không huấn luyện lại K-Means. Nếu đổi snapshot khách, phải duyệt reference mới; code hiện tại chủ động dừng.

**Lỗi 4.2:** rfm_cohort_analysis.py:216 xuất 0–100 trong khi hợp đồng Power BI dùng 0–1; biểu diễn tháng trống giữa các luồng khác nhau.

**Sửa:** Cohort khách duy nhất delivered, tuổi tháng 0–23; đã quan sát nhưng không mua lại = 0, tương lai = null. CSV 0–1; biểu đồ đổi phần trăm lúc vẽ. Tháng 0 = 100%.

**Lỗi 4.3:** rfm_cohort_analysis.py:75–78 chọn đơn có danh mục nhưng vẫn trả mọi item trong giỏ.

**Sửa:** Item trả về chỉ đúng danh mục; đồng bộ bang/thời gian/phương thức/trạng thái qua order_id. Tổng giá trị cấp đơn vẫn toàn giỏ và được ghi rõ. Không ghi đè RFM cố định bằng tập lọc.

**Kiểm chứng:** Test recency lúc 23:59 và cutoff; observed-zero/future-null; lọc kết hợp với đơn nhiều danh mục. RFM 93.358 khách khớp lõi reference.

## Mảng 5 — Một luồng chạy và bàn giao an toàn

**Lỗi:** apply_leader_feedback.py, export_rfm_pipeline_chuan.py, run_eda.py xử lý/ghi file ở top-level; import có thể gây I/O. Nhiều writer ghi cùng tên nhưng schema/quy tắc khác. ZIP có .bak_20261029, chưa có bộ kiểm thử/dependency lock đầy đủ.

**Sửa:** run_eda.py là điểm chạy chính; build_handover.py xuất CSV duy nhất; analytics_rules.py quy tắc chung; renderer chỉ đọc và vẽ. Ba writer cũ được hợp nhất, không mang chúng vào gói chạy mới. Main guard cho mọi module. Canvas chuyển sang CLI, chỉ vẽ khi chạy trực tiếp. Giữ theme/nền thực tế của Tâm.

Xuất staging trước, thành công mới thay bộ handover; có rollback. Lỗi nguồn không phá bản đang dùng. requirements ghim dependency; manifest hash input sạch, ML, output. ZIP gốc giữ nguyên; không sửa/push Git trong lượt này.

**Kiểm chứng:** Test lỗi nguồn không thay đầu ra cũ; dựng lại toàn bộ ở thư mục tạm và so hash từng file. CLI chính tạo lại dữ liệu và 10 PNG. Hai canvas đã chạy thử output riêng thành công. Log kiểm thử thực tế nằm audit/final_tests.log.

## Mảng 6 — Thiên → Tâm → Thọ/Ngân và Power BI

Nguồn nghiệp vụ dùng bộ sạch Thiên. 944 khách test của ZIP Tâm mới khớp Thọ v4 ở các cột số kiểm tra; không quy lỗi ML cho Tâm hoặc tự tune theo test. Artifact ML trong gói mới được sao chép nguyên và có hash.

Mốc cần ghi đúng:
- RFM reference 30/08/2018, mua trước 31/08.
- Snapshot BI cutoff 31/08/2018: 96.089 khách, 1.170 được chấm/94.919 chưa được chấm.
- ML test cutoff 01/03/2018, horizon 180 ngày: 944 khách.

Các mốc khác nhau do mục đích khác nhau. Không ép mọi bảng cùng số khách/cutoff. Snapshot phân khúc cố định không tự thành dự báo thời gian thực theo slicer.

PBIX gói mới dùng DataRoot trỏ handover_v3 mới, quan hệ ngày đã sửa và 5 trang. Đã bỏ 3 truy vấn chẩn đoán Errors in... cũ sau khi xác nhận không được partition/truy vấn khác tham chiếu; chúng còn gọi những cột thuộc schema cũ. Truy vấn M ở power_query. Bằng chứng Refresh/DAX ở powerbi_runtime_checks.json; kết quả cuối/hash PBIX ở KET_QUA_KIEM_TRA.json. Ngân lấy bảng theo khóa/phạm vi ghi trong README, tránh join nhiều bảng chi tiết rồi cộng tiền.

## Kết luận và giới hạn

Các lỗi code tái hiện được đã có quy tắc sửa, kiểm thử hồi quy, và một luồng chạy thay thế thống nhất. Dùng nguyên thư mục theo README; không chạy writer cũ lên đầu ra mới. Kiểm kê 8 code gốc, kiểm tra CSV và bằng chứng nằm trong audit; manifest đối soát dữ liệu.

ML vẫn thử nghiệm: RF ngưỡng 0,5 phân loại cả 944 khách test là không mua lại; temporal validation bị chặn; observation end còn giả định. Đây là giới hạn model/dataset, không che bằng sửa CSV hoặc chọn ngưỡng theo test. Bản sửa hoàn thiện code EDA/BI và tích hợp, không chứng nhận ML đủ triển khai thực tế hoặc cam kết điểm đồ án.
