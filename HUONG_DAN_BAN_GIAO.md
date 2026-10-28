# Bàn giao dữ liệu sạch

Chạy `clean_olist.py` từ dữ liệu raw và import bộ CSV sạch vào database đã chọn. Trong Compass/mongosh chọn cùng database trong `CONFIG.dbName` của `Mongodb.js`, sau đó chạy script. Script dừng trước khi cập nhật nếu thiếu collection, sai số bản ghi đã chốt, giá trị chuyển kiểu không hợp lệ hoặc ZIP thiếu/sai. Bản gốc không có timezone; không diễn giải timestamps lưu trong BSON là múi giờ Brazil đã xác nhận.

Export không ghi hoặc thay collection trong MongoDB. Cài `pandas` và `pymongo`, đặt `MONGODB_URI` qua biến môi trường nếu dùng Atlas (không commit URI), rồi chạy:

```powershell
python export_packages.py --db BigData --output-dir handover
```

Nếu không đặt `MONGODB_URI`, chương trình dùng MongoDB local. Thay tên database theo thực tế. Chương trình xuất CSV sạch, `order_summary.csv` một dòng mỗi order, và manifest đếm bản ghi cho Tâm, Thọ và Ngân. Các bảng con được cộng riêng trước khi join, giữ cờ và ngày thiếu. Tiền hàng, cước và thanh toán là các cột riêng.

Thọ tạo nhãn 180 ngày bằng pipeline ML của mình; gói này không phát sinh nhãn 90 ngày. Tài liệu backup/restore nằm ở `HUONG_DAN_BACKUP_RESTORE.md`. Phải chạy thực tế và đối soát counts, kiểu BSON, query và backup/restore trên database nhóm trước khi bàn giao.

Thọ có thể chạy `python -B Tho_Churn_Prediction/source-code/run_all.py --handover-dir "duong-dan/handover/tho"` từ repository của Thọ. `main_payment_type` chọn phương thức có số tiền thanh toán lớn nhất, nếu bằng nhau ưu tiên `payment_sequential` nhỏ nhất; đây là quy tắc mô tả, không phải tổng doanh thu. File bàn giao là CSV UTF-8 BOM, phân tách bằng dấu phẩy. `order_summary.csv` giữ cột thời gian và cờ gốc, đồng thời có các cột tên tương thích với pipeline của Thọ.
