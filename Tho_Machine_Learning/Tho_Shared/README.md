# Dữ liệu đầu vào chung cho phần học máy

`data/olist_powerbi_orders_master_20261028.csv` là master nhóm cung cấp ngày 28/10/2026;
file dùng tab, mã cp1252 và thời gian đến phút. `data/olist_orders_clean.csv` và
`data/olist_order_payments_clean.csv`, `data/olist_customers_clean.csv` và
`data/olist_order_items_clean.csv` là bảng sạch trong thư mục `processed` của nhóm.
`data/ibge_states_raw.json` là snapshot IBGE trong bộ thu thập của Huy.
`data/rfm_table_tam_20261028.csv` là bản sao của bảng RFM do Tâm cung cấp, dùng để đối soát
với RFM tính từ master mới.

`load_orders.py` kiểm tra `order_id`, trạng thái, thời gian mua đến phút và các cờ chất lượng
giữa master và bảng đơn sạch. Code cũng đối chiếu định danh khách, bang và các tổng sản phẩm/cước
với bảng khách và item sạch. Sau khi khớp, code dùng timestamp đầy đủ từ bảng sạch, đổi tên
các cột giá trị để tương thích model, đếm bản ghi thanh toán và ghép vùng theo IBGE.
Các file CSV giữ nguyên nội dung nguồn, không sửa dữ liệu gốc. SHA-256 các nguồn được ghi
trong kết quả của từng phần.

Bộ đọc cũng nhận master CSV cuối của Tâm với các tên `total_products_value`,
`total_freight_value`, `total_items`, bên cạnh tên cũ/ETL. Nếu cả hai cách đặt tên
cùng xuất hiện nhưng khác giá trị, chương trình dừng. Đơn không có item được phép
biểu diễn tổng bằng 0 hoặc null; tổng khác 0 khi không có item bị từ chối.

Cột `Delivery_Status` trong master ghi “On-time” cả với đơn không đủ điều kiện KPI.
Pipeline học máy không dùng cột này; dùng cờ `valid_delay_kpi` và ngày gốc trong bảng sạch.

Mốc đầy đủ dữ liệu tương lai và thời điểm chốt trạng thái đơn vẫn cần nhóm xác nhận để kết quả
gán nhãn 180 ngày được coi là chính thức.
