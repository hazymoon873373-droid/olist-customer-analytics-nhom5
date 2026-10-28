# Phát hiện đơn hàng bất thường bằng Isolation Forest

Phần này khảo sát các đơn hàng có đặc điểm khác nhiều so với phần lớn dữ liệu Olist.
Mô hình dùng **Isolation Forest** và chỉ xét các đơn có trạng thái `delivered`.

## Kết quả chính

- Số đơn được chấm điểm: **96.478**.
- Số đơn được gắn cờ bất thường: **965**.
- Tỷ lệ bất thường: **1,00%**.
- Độ giống nhau giữa kết quả seed 42 và seed 7 (Jaccard): **0,8021**.
- Phí vận chuyển và thời gian giao hàng của nhóm bất thường cao hơn rõ so với nhóm còn lại.

Kết quả này dùng để khoanh vùng đơn cần xem thêm, không khẳng định đơn đó là gian lận.
Dữ liệu không có nhãn bất thường thực tế nên không tính accuracy, precision, recall hoặc F1.

## Các feature sử dụng

```text
total_products_value
total_freight_value
freight_to_product_ratio
total_items
max_installments
payment_records
delivery_days
late_days
```

`late_days` chỉ lấy phần giao trễ: đơn giao sớm hoặc đúng hạn có giá trị bằng 0.

## Cách chạy

Từ thư mục gốc repository:

```bash
pip install -r Tho_Order_Anomaly/requirements.txt
python Tho_Order_Anomaly/source-code/run_all.py
```

Chạy kiểm thử:

```bash
python -m unittest discover -s Tho_Order_Anomaly/tests -v
```

Chấm điểm lại một file đã có đủ 8 feature:

```bash
python Tho_Order_Anomaly/source-code/predict_anomaly.py --input duong_dan_file.csv
```

## Thư mục quan trọng

- `data/`: bảng feature sau khi lọc đơn delivered.
- `models/`: Pipeline tiền xử lý và Isolation Forest đã huấn luyện.
- `outputs/`: CSV gán nhãn, bảng tổng hợp, biểu đồ và file Excel.
- `reports/`: quy trình thực hiện và nội dung có thể dùng cho báo cáo.
- `source-code/`: code chuẩn bị dữ liệu, huấn luyện và dự đoán.
- `tests/`: kiểm tra dữ liệu và file kết quả.
