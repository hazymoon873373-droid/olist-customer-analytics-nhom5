# Sao lưu và khôi phục MongoDB

Sao lưu database sạch đã chốt, khôi phục vào database kiểm thử riêng và đối chiếu dữ liệu. Cài MongoDB Database Tools và MongoDB Community Server trên máy đích. Không đưa mật khẩu hoặc URI có thông tin đăng nhập vào Git.

1. Tạo thư mục `C:\mongodb_backup` và thiết lập biến môi trường `MONGODB_URI` bằng chuỗi kết nối được cấp riêng. Không chia sẻ giá trị biến này.
2. Thay `TEN_DATABASE_SACH` bằng database nguồn thực tế rồi chạy trong PowerShell:

   ```powershell
   mongodump --uri="$env:MONGODB_URI" --db=TEN_DATABASE_SACH --gzip --archive="C:\mongodb_backup\olist_backup.gz"
   ```

3. Kiểm tra mã thoát, kích thước file và log. Khôi phục sang database kiểm thử trên MongoDB local, thay `TEN_DATABASE_SACH` cho đúng nguồn:

   ```powershell
   mongorestore --uri="mongodb://localhost:27017/" --gzip --archive="C:\mongodb_backup\olist_backup.gz" --nsFrom="TEN_DATABASE_SACH.*" --nsTo="olist_restore_test.*"
   ```

4. Chọn `olist_restore_test` trong Compass. Đối chiếu số document, danh sách indexes, `valid_delay_kpi`, khóa nối và kết quả query với nguồn. Các số 99.441 orders, 112.650 items, 19.015 geo_by_zip và 95.097 đơn hợp lệ chỉ áp dụng cho snapshot đã chốt. Lưu log backup, restore và kết quả đối soát.

Không dùng `--drop` trên database nhóm đang sử dụng. Nếu thông tin đăng nhập đã bị lộ, chủ tài khoản cần đổi/thu hồi ngay và phối hợp xử lý lịch sử Git. Thay tài liệu hiện tại không xóa credential khỏi commit cũ.
