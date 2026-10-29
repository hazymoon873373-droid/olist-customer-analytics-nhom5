# Bộ code và dữ liệu bàn giao Tâm — 29/10/2026

Mở `POWERBI_Olist_Chot.pbix`. Báo cáo giữ 5 trang chính, đã bỏ Page 1 bổ sung theo yêu cầu Huy. Xem `BAO_CAO_RAT_SOAT_VA_SUA_LOI.md` để biết từng nhóm lỗi và bằng chứng kiểm tra.

## Chạy lại toàn bộ

Mở terminal tại thư mục này; dùng Python 3.11 trở lên (bản này đã kiểm tra bằng Python 3.14).

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B run_eda.py
.\.venv\Scripts\python.exe -B -m unittest discover -s . -p "test_*.py" -v
```

`run_eda.py` là lệnh chính: kiểm tra đầu vào, tính và đối soát số liệu, xuất `handover_v3`, rồi tạo 10 PNG trong `charts`. Dùng `--data-only` nếu chỉ cần CSV. `--source`, `--ml`, `--output`, `--charts` cho phép đổi đường dẫn; xem `--help`.

Code mặc định dùng đường dẫn theo vị trí script, không cần thư mục cũ trên ổ D. Đầu vào sạch Thiên và kết quả ML Thọ được đóng gói theo phiên bản. Nếu thiếu file/sai khóa/sai cờ/sai số kiểm soát, pipeline báo lỗi và không thay bộ bàn giao đang dùng. Đây là code cho snapshot Olist đã chốt của nhóm, không phải chương trình huấn luyện ML cho mọi dữ liệu mới.

## Thành phần

| File/thư mục | Công việc |
|---|---|
| load_data.py | Đọc 7 bảng sạch chuẩn olist_*_clean.csv; không tự chuyển sang raw |
| analytics_rules.py | Quy tắc khóa, cờ, review, giao trễ, ngày lọc, RFM, cohort, lọc đa chiều |
| build_handover.py | Một nơi tính/xuất CSV; có staging/rollback và manifest SHA256 |
| integration_contract.py | Xuất hợp đồng file/schema/khóa và ánh xạ cột ML để bàn giao web |
| eda_analysis_pipeline.py | Vẽ 10 biểu đồ; không ghi đè CSV nghiệp vụ |
| run_eda.py | Điểm chạy chính |
| generate_canvas_bg.py, generate_canvas_page5.py | Tạo nền trang khi chạy trực tiếp; không ghi file lúc import |
| test_rules.py, test_handover.py | Kiểm thử hồi quy và đối soát toàn bộ lần dựng lại |
| inputs/clean | Dữ liệu sạch Thiên, IBGE, RFM reference đã duyệt |
| inputs/ml | Artifact Thọ v4; giữ nguyên nội dung, không fit/tune lại |
| handover_v3 | CSV/JSON/XLSX cho Power BI và Ngân |
| charts | 10 biểu đồ và chart_manifest.json ghi phạm vi |
| design_assets | Nền Power BI và theme giữ lại từ sản phẩm Tâm |
| power_query | Truy vấn M và tham số DataRoot của PBIX đã sửa |
| audit | Kiểm kê nguồn, tái hiện lỗi, đối chiếu dữ liệu, log kiểm thử |

Ba writer cũ `apply_leader_feedback.py`, `export_rfm_pipeline_chuan.py`, `rfm_cohort_analysis.py` được hợp nhất vào module trên. Không chạy chúng lên bộ mới: chúng từng dùng quy tắc khác nhau và ghi đè cùng tên đầu ra. ZIP gốc vẫn giữ nguyên trong Downloads để đối chiếu.

## Power BI trên máy khác

Mở PBIX → **Transform data → Edit parameters** → đổi `DataRoot` thành đường dẫn tuyệt đối của `handover_v3` vừa giải nén → **Close & Apply** → **Refresh**. Chạy code trước nếu cần tạo lại CSV. Power BI không tự chạy Python pipeline hay huấn luyện lại mô hình.

Đây là bản sao trong gói gửi Tâm/Ngân. PBIX giữ nguyên nhị phân đã kiểm tra native; tham số đang lưu đường dẫn bản Tam_Chot_Code_20261029 ban đầu. Cần đổi DataRoot sang thư mục bản sao này trước khi Refresh nếu dùng bản sao, không nhầm việc mở được cache với đã đọc dữ liệu tại vị trí mới.

Gói hiện có 18 kiểm thử đạt. Người tích hợp đọc `handover_v3/integration_contract.json` để lấy tên file thực, khóa và ánh xạ `churn_probability → ml_churn_probability` cùng các cột khác. `data_contract.json` là hợp đồng gốc Thọ, dùng tên file upstream; giữ để truy nguồn, không dùng các tên upstream đó để tìm file trong thư mục Tâm. Bảng test chỉ đánh giá lịch sử, snapshot BI mới phục vụ danh sách khách tại cutoff BI.

Quan hệ ngày active dùng Calendar.Date → orders.OrderDate (phần ngày, một chiều). Timestamp giữ đến giây, ZIP text 5 ký tự. Loại 64 review trước ngày mua; 10 review cùng ngày chưa rõ thứ tự được giữ theo quy ước nhóm, chưa chứng minh được thứ tự thời gian.

## Phạm vi cần giải thích khi báo cáo

- Orders 99.441, items 112.650. KPI giao trễ chỉ dùng 95.097 đơn valid_delay_kpi=true, có 7.793 trễ, tỷ lệ 8,19479%, median giao hàng 10,271782 ngày. Không coi đơn thiếu ngày giao là đúng hạn.
- GMV sản phẩm và AOV dùng đơn delivered; GMV sản phẩm không cộng cước. Canceled và unavailable tách riêng. KPI tỷ lệ trong CSV là 0–1; customer_pct/revenue_pct trong summary là 0–100, tên và scope ghi rõ.
- RFM 93.358 khách delivered mua trước 31/08/2018; reference 30/08/2018, recency theo ngày. Tính lại R/F/M lõi và đối soát rfm_reference.csv trước khi giữ điểm/6 nhóm quy tắc đã duyệt. Reference là đầu vào có chủ đích, không phải tự chấm lại cho tập khách khác. K-Means có 4 cụm riêng.
- Cohort delivered đến hết tháng 08/2018, tuổi tháng 0–23. Kỳ đã quan sát không mua lại là 0; tương lai blank. CSV retention là 0–1, biểu đồ hiển thị phần trăm.
- ML test cutoff 01/03/2018, 944 khách. Snapshot BI cutoff 31/08/2018 có 96.089 khách: 1.170 được chấm, 94.919 chưa được chấm. Xác suất thiếu không phải 0%. Khác mốc là khác phạm vi, không buộc mọi bảng có cùng cutoff.
- RFM/ML và summary phân cụm là snapshot cố định. Bộ lọc ngày đơn không tự tính RFM ở cutoff mới, không tạo dự báo thời gian thực. Hàm lọc đa chiều trả item đúng danh mục; tổng giá trị cấp đơn vẫn là toàn giỏ.

ML còn thử nghiệm: RF ngưỡng 0,5 phân loại cả 944 khách test là không mua lại; temporal validation chưa đủ điều kiện, observation end còn giả định. Sửa tích hợp không xác nhận chất lượng mô hình. Xem metrics.json, validation_protocol.json, data_contract.json.

Ngân dùng customer_unique_id cho bảng khách và order_id cho bảng đơn. Không nối items/payments/reviews chi tiết cùng lúc rồi cộng tiền vì nhân dòng. Đối soát bằng manifest.json, kpi_summary_tam.csv và chart_manifest.json.

Nguồn: Olist Kaggle (CC BY-NC-SA 4.0), IBGE; sạch Thiên theo repo main 2b92915; Thọ temporal_v4_20261029_provisional. Giữ ghi công trong báo cáo.
API sửa model: https://learn.microsoft.com/en-us/analysis-services/tom/introduction-to-the-tabular-object-model-tom-in-analysis-services-amo



Xuất cấu trúc web sẵn cho Ngân: `python -B tam_eda/export_ngan.py --output "duong_dan_thu_muc_moi"` từ gốc repo. Xem BAN_GIAO_NGAN.md ở gốc repo. Script không ghi đè output đã tồn tại.
