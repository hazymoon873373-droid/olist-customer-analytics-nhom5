# Bản code đã áp dụng vá để bàn giao Ngân — 29/10/2026

Thực hiện trên nhánh local `codex/final-handover-20261029`, xuất phát từ main 2b92915. Chưa push hoặc merge vào main.

## Các sửa đã áp dụng

- Thiên: export_packages.py bắt buộc cờ review_before_purchase đúng boolean, loại review trước mua khỏi trung bình, giữ điểm lẻ và null. Test hồi quy nằm tests/test_export_packages.py. Dữ liệu review chi tiết vẫn giữ nguyên cờ, không xóa dòng.
- Tâm: thêm tam_eda, một luồng tạo handover/biểu đồ từ dữ liệu sạch; cờ giao trễ, mốc ngày, review, RFM/cohort đã được đối soát. integration_contract.json ánh xạ file và cột với đầu ra Thọ.
- Bàn giao web: tam_eda/export_ngan.py xuất cấu trúc data/processed, kiểm tra hash, từ chối ghi đè gói có sẵn và không công bố gói dở dang khi lỗi.
- Thọ: giữ nguyên code/model hiện hành; các kiểm thử và lần chạy từ gói sạch Thiên đã xác nhận khớp. Không đổi threshold theo test hoặc sửa nhãn để tạo kết quả đẹp.

## Chạy kiểm tra

Các module dùng requirements riêng; không dùng chung requirements root làm môi trường cho mọi module. Môi trường kiểm tra có pandas 2.3.3, numpy 2.3.4, scikit-learn 1.8.0.

```powershell
python -B -m unittest discover -s tests -p "test_export_packages.py" -v
python -B -m unittest discover -s tam_eda -p "test_*.py" -v
python -B -m unittest discover -s Tho_Shared/tests -v
python -B -m unittest discover -s Tho_RFM_KMeans/tests -v
python -B -m unittest discover -s Tho_Churn_Prediction/tests -v
python -B -m unittest discover -s Tho_Order_Anomaly/tests -v
node tests/test_mongodb_script.js
```

Kỳ vọng lần lượt 6, 18, 7, 7, 26, 9 tests; JavaScript là kiểm tra offline/mô phỏng, không phải bằng chứng Atlas đang có đủ index/đã backup.

## Tạo dữ liệu và gói web

```powershell
python -B tam_eda/run_eda.py
python -B tam_eda/export_ngan.py --output "C:/duong_dan_moi/BanGiao_Ngan"
```

Chọn thư mục output chưa tồn tại. Có thể thêm `--extra-clean "duong_dan/processed"` để đưa geo_by_zip.csv, olist_sellers_clean.csv và audit_report.csv cùng phiên bản vào gói. Các bảng processed bắt buộc cho web đã nằm trong tam_eda/inputs/clean. Giữ Huy_ThuThap_Olist trong bản clone đầy đủ nếu cần chạy lại clean_olist.py từ raw; bộ ZIP code chọn lọc không nhân bản raw này.

Ngân đặt thư mục data cạnh app.py, xem data/integration_contract.json và HANDOVER_MANIFEST.json. Các bảng orders/RFM/chi tiết tương thích schema web hiện tại. ML và Power BI vẫn cần Ngân viết phần tích hợp và kiểm thử trên web thật.

PBIX giữ 5 trang. Khi di chuyển, đổi DataRoot sang thư mục data của gói web (hoặc tam_eda/handover_v3 của repo) rồi Refresh. File nhị phân giữ bản đã kiểm tra native trước đó; lượt vá này không khẳng định đã Refresh ở đường dẫn bản sao mới.

## Giới hạn bắt buộc giữ khi trình bày

RFM 93.358 khách, reference 30/08/2018. BI 96.089 khách, cutoff 31/08/2018; 1.170 được chấm và 94.919 chưa được chấm. Test 944 khách, cutoff 01/03/2018 và horizon 180 ngày. Không ghép test thành điểm BI, không điền xác suất thiếu bằng 0. Khách ngoài snapshot được giữ và đánh dấu ngoài phạm vi.

RF ngưỡng 0,5 dự đoán cả test là không mua lại, recall mua lại bằng 0; temporal validation thiếu điều kiện, observation end còn giả định. Đây là mô hình thử nghiệm, không phải xác suất đã hiệu chuẩn hoặc hệ thống sẵn sàng dùng thực tế. Những giới hạn này không thể sửa bằng đổi CSV hay tune theo test.

Không chạy Mongodb.js lên Atlas trong lượt vá này. Thiên cần giữ log database, index và backup/restore thật để hoàn tất bằng chứng môn học. Không đưa URI có mật khẩu lên Git.
