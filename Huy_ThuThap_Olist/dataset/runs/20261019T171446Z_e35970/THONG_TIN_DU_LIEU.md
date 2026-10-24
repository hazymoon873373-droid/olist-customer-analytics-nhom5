# KẾT QUẢ THU THẬP DỮ LIỆU - NGUYỄN GIA HUY / NHÓM 5

- Trạng thái: **SUCCESS**
- Run ID: `20261019T171446Z_e35970`
- Thời gian bắt đầu (UTC): 2026-10-19T17:14:46.163177+00:00
- Thời gian kết thúc (UTC): 2026-10-19T17:14:57.198059+00:00
- Olist: **9 CSV / 1,550,922 bản ghi**
- IBGE API: **27 bản ghi**; trạng thái: success
- Tổng bản ghi trên các tệp nguồn: **1,550,949**

Tổng trên là tổng các bảng, không phải số đơn hàng hoặc khách hàng duy nhất.

## Nguồn và phương thức

- Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Phương thức Olist: `https_kaggle_download`.
- Giấy phép dataset Olist: CC BY-NC-SA 4.0; giữ ghi công và tuân thủ điều kiện của nguồn.
- IBGE: https://servicodados.ibge.gov.br/api/docs/localidades
- Endpoint: https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome
- IBGE được dùng để bổ sung nhãn bang/vùng cho BI; không suy diễn GDP/dân số lịch sử.
- Chưa xác minh số phiên bản Kaggle; mỗi tệp được định danh bằng SHA-256 và thời điểm tải.

## Số lượng và mô tả dữ liệu raw

| Tệp | Record | Cột | Mô tả |
|---|---:|---:|---|
| olist_customers_dataset.csv | 99,441 | 5 | Bản ghi khách hàng gắn với đơn hàng, địa chỉ ở mức thành phố/bang. |
| olist_orders_dataset.csv | 99,441 | 8 | Đơn hàng, trạng thái và các thời điểm mua, duyệt, giao, dự kiến giao. |
| olist_order_items_dataset.csv | 112,650 | 7 | Chi tiết hàng hóa trong đơn; giá và phí vận chuyển bằng BRL. |
| olist_order_payments_dataset.csv | 103,886 | 5 | Thanh toán; một đơn có thể có nhiều phương thức hoặc dòng thanh toán. |
| olist_order_reviews_dataset.csv | 99,224 | 7 | Đánh giá đơn hàng; bình luận có thể chứa dấu phẩy, dấu nháy và xuống dòng. |
| olist_products_dataset.csv | 32,951 | 9 | Thông tin danh mục, kích thước, trọng lượng và độ dài mô tả sản phẩm. |
| olist_sellers_dataset.csv | 3,095 | 4 | Người bán và vị trí ở mức tiền tố bưu chính, thành phố, bang. |
| olist_geolocation_dataset.csv | 1,000,163 | 5 | Tọa độ địa lý theo tiền tố bưu chính; nhiều tọa độ có thể cùng tiền tố. |
| product_category_name_translation.csv | 71 | 2 | Bảng dịch tên danh mục sản phẩm sang tiếng Anh. |
| ibge_states_raw.json | 27 | 6 | 27 đơn vị liên bang Brazil, gồm bang/đặc khu và 5 vùng lớn |

## Khả năng liên kết nguồn

`Olist.customer_state = IBGE.sigla`
Khớp 99,441/99,441 bản ghi khách hàng (100.0%).
Mã bang chưa khớp: []

## Tệp bằng chứng

- `raw/olist/brazilian-ecommerce.zip`: tệp ZIP gốc (nếu tải thành công).
- `raw/olist/*.csv`: 9 CSV nguyên bản, không làm sạch hoặc đổi tên cột.
- `raw/ibge/ibge_response.bin`: response body gốc; có thể được mã hóa gzip.
- `raw/ibge/ibge_states_raw.json`: JSON sau giải mã truyền tải, giữ nguyên nội dung.
- `metadata/source_manifest.json`: nguồn, mô tả, checksum, thời điểm, HTTP receipt.
- `metadata/record_counts.csv`: số record từng tệp.
- `metadata/data_dictionary.csv`: ý nghĩa và kiểu đề xuất cho từng trường.
- `logs/collection.log`: nhật ký chạy.

## Lưu ý khi bàn giao

- Đếm CSV bằng parser vì review có nội dung nhiều dòng.
- Giá tiền là BRL; mã bưu chính cần giữ dạng chuỗi.
- Nhận diện khách mua lại bằng customer_unique_id, liên kết đơn qua customer_id.
- Thiên tiếp nhận raw để làm sạch/ETL/MongoDB; Thọ phụ trách nhãn và ML; Tâm phụ trách BI.
- Không cộng lại giá trị sau các phép join 1-n nếu chưa tổng hợp về đúng cấp đơn hàng.
- Dữ liệu IBGE được lấy ở thời điểm chạy hiện tại, dùng làm bảng tham chiếu địa lý.
