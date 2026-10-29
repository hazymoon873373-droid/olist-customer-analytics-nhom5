# Làm sạch và quản lý dữ liệu Olist bằng MongoDB

Môn ABDA433708 — nhóm 5, phần ETL/MongoDB.

## Nội dung

- clean_olist.py: làm sạch dữ liệu, giữ cờ chất lượng và tạo geo_by_zip.
- processed/: 9 bảng Olist sạch, geo_by_zip, audit_report.csv và manifest hash.
- Mongodb.js: kiểm tra điều kiện đầu vào, chuyển kiểu BSON và tạo index.
- mongodb/inspect_collections.js: kiểm tra database ở chế độ đọc.
- export_packages.py: xuất dữ liệu sạch và order_summary cho BI/ML/web; review trước mua bị loại khỏi trung bình, dữ liệu chi tiết giữ nguyên cờ.
- tests/: 6 kiểm thử Python cho export và kiểm thử JavaScript offline/mô phỏng.
- HUONG_DAN_BAN_GIAO.md, HUONG_DAN_BACKUP_RESTORE.md: quy trình sử dụng MongoDB và sao lưu.

## Cài đặt và chạy lại ETL

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B clean_olist.py --raw_dir "DUONG_DAN_9_CSV_OLIST_THO" --output_dir processed
```

Nguồn raw nằm trong phần thu thập Huy của repository chung: ../Huy_ThuThap_Olist/dataset/runs/20261019T171446Z_e35970/raw/olist. Bộ này không nhân bản thêm ZIP/raw; processed đã có sẵn để sử dụng và đối chiếu. Chạy các lệnh tại thư mục Thien_ETL_MongoDB. processed được giữ cùng phần Thiên để nộp và đối soát.

## Kiểm thử

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_export_packages.py" -v
node tests/test_mongodb_script.js
```

JavaScript test là offline; chạy trên database thật và backup/restore cần kiểm tra riêng, không suy ra từ mock.

## MongoDB và bàn giao

Import các CSV sạch vào database đã chọn, kiểm tra CONFIG.dbName rồi chạy Mongodb.js theo hướng dẫn. Không lưu URI có mật khẩu trong code. Export dùng MONGODB_URI qua biến môi trường, mặc định MongoDB local; ví dụ python export_packages.py --db BigData --output-dir handover.

Orders 99.441; items 112.650; geo_by_zip 19.015. KPI giao trễ chỉ dùng 95.097 đơn valid_delay_kpi=true. Không tự lấp ngày thiếu, không xóa đơn bất thường để làm đẹp KPI. Timestamp nguồn chưa xác nhận timezone. Review cùng ngày chưa rõ thứ tự giữ cờ để giải thích giới hạn.

audit_report.csv là kết quả kiểm định dữ liệu do pipeline tạo, thuộc sản phẩm ETL; không phải báo cáo rà soát nội bộ. Manifest dùng đối soát file. Không đưa dữ liệu tài khoản hoặc backup có credentials lên repo công khai.

Nguồn: Olist Brazilian E-Commerce (CC BY-NC-SA 4.0), https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce . API IBGE trong phần thu thập của nhóm là nguồn tham chiếu địa lý.
