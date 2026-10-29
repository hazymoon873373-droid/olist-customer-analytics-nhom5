# Phân tích khách hàng Olist — EDA và Power BI

Môn ABDA433708, nhóm 5. Phần EDA/BI sử dụng dữ liệu sạch Olist, phân tích RFM/cohort và tích hợp kết quả Machine Learning.

## Cấu trúc

| Thành phần | Nội dung |
|---|---|
| POWERBI_Olist_Chot.pbix | Dashboard Power BI 5 trang |
| inputs/clean | 7 bảng sạch, tham chiếu bang/vùng IBGE và RFM reference |
| inputs/ml | Kết quả Machine Learning theo phiên bản của nhóm |
| handover_v3 | Dữ liệu phân tích đã xuất, thống kê/KPI, hợp đồng bàn giao và manifest hash |
| charts | 10 biểu đồ phân tích và phạm vi số liệu |
| design_assets | Nền trang và theme Power BI |
| power_query | Mã truy vấn M và định nghĩa measure/cột tính toán trong model_rules.json |
| Các module Python ở gốc | Nạp, kiểm tra, xử lý dữ liệu, xuất bàn giao và vẽ biểu đồ |
| test_*.py | Kiểm thử quy tắc, dữ liệu và xuất gói web |
| requirements.txt | Phiên bản thư viện cần cài |

inputs là dữ liệu để chạy lại pipeline; handover_v3 là kết quả cho BI/web. Các bản sao phục vụ đầu vào/đầu ra có chủ đích, không xóa chỉ vì trùng tên. Không cần import mọi CSV vào Power BI.

## Cài đặt và chạy

Mở terminal tại thư mục này. Môi trường đã kiểm tra: Python 3.14; dùng môi trường ảo riêng.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B run_eda.py
.\.venv\Scripts\python.exe -B -m unittest discover -s . -p "test_*.py" -v
```

run_eda.py xuất handover_v3 và 10 biểu đồ; --data-only chỉ xuất dữ liệu. Dùng --help để xem tham số đường dẫn. Bộ kiểm thử gồm 18 tests, có kiểm tra dựng lại toàn bộ và đối soát hash. Các script canvas chỉ tạo nền khi chạy trực tiếp.

## Power BI

Mở POWERBI_Olist_Chot.pbix. PBIX được đóng gói từ bản đã Refresh/lưu. Khi mở bản clone này, đặt DataRoot thành đường dẫn tuyệt đối tam_eda/handover_v3 trên máy đang dùng trước khi Refresh.

Khi chuyển sang máy hoặc vị trí khác: Transform data → Edit parameters → đặt DataRoot bằng đường dẫn tuyệt đối của handover_v3 → Close & Apply → Refresh. Python tạo lại CSV khi cần; Power BI không tự chạy pipeline Python.

## Quy tắc phân tích

- Toàn bộ master: 99.441 đơn; 112.650 item. Dữ liệu giữ timestamp đến giây, ZIP dạng text 5 ký tự, giá trị thiếu là null.
- GMV sản phẩm/AOV tính trên delivered; tiền sản phẩm và cước tách riêng. KPI giao trễ chỉ dùng valid_delay_kpi=true: 7.793/95.097 = 8,19479%; median giao hàng 10,271782 ngày. Slicer có thể thay đổi phạm vi KPI.
- Review trước ngày mua theo cờ bị loại khỏi trung bình (64 review); 10 review cùng ngày chưa rõ thứ tự giữ theo quy ước nhóm và cần nêu giới hạn. Không điền review thiếu bằng 0.
- RFM: 93.358 khách delivered, reference 30/08/2018, đơn trước 31/08. Đối soát R/F/M lõi trước khi giữ điểm và 6 nhóm quy tắc trong rfm_reference.csv. K-Means gồm 4 cụm riêng và dùng R/F/M, không dùng điểm RFM quy tắc.
- Cohort: delivered đến hết tháng 08/2018, tuổi tháng 0–23. CSV retention 0–1; kỳ đã quan sát không mua lại là 0, tương lai chưa quan sát là blank.
- Snapshot RFM/ML cố định; bộ lọc ngày không tự tính lại mô hình tại cutoff mới. Biểu đồ review/giao trễ mô tả liên hệ, không chứng minh nhân quả.

## Dữ liệu bàn giao web và kết quả ML

Đọc handover_v3/integration_contract.json để lấy tên file thực, khóa, số dòng và ánh xạ cột từ upstream Thọ sang các cột ml_ của snapshot BI. data_contract.json được giữ nguyên theo phiên bản model gốc.

Snapshot BI cutoff 31/08/2018 có 96.089 khách: 1.170 được chấm, 94.919 chưa được chấm. Test cutoff 01/03/2018 có 944 khách, nhãn không mua lại trong 180 ngày. Không ghép bảng test thành điểm BI và không điền xác suất thiếu thành 0. Decile 1 có churn_probability cao nhất.

Model còn thử nghiệm: RF ngưỡng 0,5 dự đoán cả test là không mua lại; temporal validation chưa đủ điều kiện, observation end còn giả định, xác suất chưa hiệu chuẩn. Xem metrics.json, validation_protocol.json và feature_importance.csv. Average Precision không đồng nhất với PR-AUC hình thang.

Để xuất cấu trúc data/processed cho web, chọn thư mục đích chưa tồn tại và nằm ngoài thư mục dự án:

```powershell
.\.venv\Scripts\python.exe -B export_ngan.py --output "C:/duong_dan_moi/Goi_Web_Olist"
```

Nối bảng khách bằng customer_unique_id; bảng đơn bằng order_id. Không nối đồng thời items/payments/reviews chi tiết rồi cộng tiền để tránh nhân dòng. Web vẫn cần tích hợp và kiểm thử riêng.

## Nguồn

Olist Brazilian E-Commerce, giấy phép CC BY-NC-SA 4.0: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

IBGE States API: https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome

Dữ liệu sạch do nhóm chuẩn hóa từ snapshot Olist; kết quả ML phiên bản temporal_v4_20261029_provisional. Giữ thông tin nguồn và giấy phép khi chia sẻ.
