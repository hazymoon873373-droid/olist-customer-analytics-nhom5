# BIÊN BẢN KIỂM TRA DỮ LIỆU THU THẬP

- Run: `20261019T171446Z_e35970`
- Kiểm tra lúc: 2026-10-30T21:23:28.885115+07:00 (UTC+7)
- Kết quả kỹ thuật: ĐẠT

| Kiểm tra | Kết quả | Bằng chứng |
|---|---|---|
| Thư mục dữ liệu đang mở tồn tại | ĐẠT | dataset/runs/20261019T171446Z_e35970 |
| Đường dẫn bàn giao tương đối trỏ đúng dữ liệu | ĐẠT | dataset/latest_success.json -> runs/20261019T171446Z_e35970 |
| F5 trỏ đúng mã nguồn sau khi dọn | ĐẠT | source-code/collect_all.py |
| Có ZIP Olist nguồn để tái lập | ĐẠT | tải mới từ Kaggle |
| Nguồn địa lý có 27 UF và provenance | ĐẠT | https_api; endpoint=https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome; snapshot=n/a |
| Trạng thái chạy hoàn tất | ĐẠT | Run 20261019T171446Z_e35970; kết thúc 2026-10-19T17:14:57.198059+00:00 |
| ZIP gốc khớp checksum đã ghi | ĐẠT | 967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784 |
| Raw CSV: olist_customers_dataset.csv | ĐẠT | 99,441 record, 9,033,957 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_orders_dataset.csv | ĐẠT | 99,441 record, 17,654,914 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_order_items_dataset.csv | ĐẠT | 112,650 record, 15,438,671 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_order_payments_dataset.csv | ĐẠT | 103,886 record, 5,777,138 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_order_reviews_dataset.csv | ĐẠT | 99,224 record, 14,451,670 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_products_dataset.csv | ĐẠT | 32,951 record, 2,379,446 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_sellers_dataset.csv | ĐẠT | 3,095 record, 174,703 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: olist_geolocation_dataset.csv | ĐẠT | 1,000,163 record, 61,273,883 byte; CSV nguyên vẹn so với ZIP và manifest |
| Raw CSV: product_category_name_translation.csv | ĐẠT | 71 record, 2,613 byte; CSV nguyên vẹn so với ZIP và manifest |
| Lưu dữ liệu API địa lý và provenance nguyên vẹn | ĐẠT | 27 record; 2,446 byte JSON; response trực tiếp khớp HTTP receipt |
| Nguồn phụ ghép được với Olist | ĐẠT | Khớp 99,441/99,441 bản ghi khách hàng |
| Bảng đếm khớp file thực tế | ĐẠT | 10 tệp dữ liệu trên 2 nguồn |
| Có mô tả đầy đủ các trường | ĐẠT | 58 trường có tên, kiểu đề xuất và ý nghĩa |
| Có nhật ký và báo cáo | ĐẠT | Có log đầy đủ 5 bước và thông tin dữ liệu |

## Đối chiếu phạm vi

Đường dẫn hiện tại: `dataset/runs/` trong thư mục Huy_ThuThap_Olist. Các cửa sổ, liên kết hoặc log cũ trỏ tới `data/runs/` cần mở lại ở đường dẫn hiện tại. Không cần tải lại dữ liệu để khắc phục thông báo Location is not available.

Đã lưu 9 CSV Olist và dữ liệu IBGE; lượt chạy này đã gọi API trực tiếp.

Đối chiếu LabF: có 2 nguồn, có chương trình thu thập, dữ liệu trên 5.000 record. Phần lưu DBMS, làm sạch, thiết kế MongoDB và phân tích/ML cần nhóm tiếp tục thực hiện theo phân công.

Tài liệu crawl của thầy Khải minh họa Scrapy/HTML và lưu MongoDB Atlas. Chương trình hiện tại thu thập qua HTTPS (ZIP/JSON API); chưa cài spider Scrapy, chưa đẩy dữ liệu lên Atlas. Nếu áp dụng nguyên yêu cầu bài thực hành trong PDF thì cần làm thêm các phần đó và đúng website của bài lab. Theo phạm vi đồ án đã chia, Huy bàn giao raw và hồ sơ nguồn cho Thiên làm ETL/MongoDB.

Dữ liệu là lần thu thập mới từ Internet của dataset lịch sử; nội dung đơn hàng vẫn thuộc kỳ dữ liệu Olist công bố. Kết quả kiểm tra kỹ thuật không thay thế đánh giá cuối cùng của giảng viên.
