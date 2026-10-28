# Dữ liệu dùng cho anomaly detection

File đầu vào được dùng chung từ:

`../../Tho_RFM_KMeans/data/olist_powerbi_orders_master.csv`

Chạy `prepare_anomaly_data.py` sẽ tạo `order_anomaly_features.csv` trong thư mục này.
Chỉ các đơn có trạng thái `delivered` được giữ lại để khảo sát bất thường sau giao hàng.
