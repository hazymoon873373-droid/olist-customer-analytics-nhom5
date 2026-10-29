# Website Olist — Nhóm 5

Ứng dụng Streamlit dùng dữ liệu sạch của Thiên, bộ BI của Tâm và kết quả ML của Thọ. Phần dữ liệu lịch sử chỉ đọc; tài khoản, ghi chú, ưu tiên và chiến dịch được lưu riêng trong SQLite.

## Chạy trên Windows

Tại thư mục gốc bản clone dự án:

```powershell
cd Ngan_Web
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe database.py
.\.venv\Scripts\python.exe -m streamlit run app.py
```

Lệnh database.py yêu cầu tự đặt mật khẩu ít nhất 10 ký tự cho hai tài khoản admin và analyst. Không có mật khẩu mặc định. Tài khoản đã có được giữ nguyên. Các lần mở sau chỉ cần chạy lệnh Streamlit. Truy cập http://localhost:8501; dừng bằng Ctrl+C tại terminal. Môi trường đã kiểm thử: Python 3.14 trên Windows.

Chạy từ Ngan_Web để Streamlit đọc cấu hình theme trong .streamlit/config.toml. Font IBM Plex Sans có sẵn trong assets/fonts, dùng được cả khi không có Internet; giấy phép OFL đi kèm.

## Dữ liệu cần giữ cạnh mã nguồn

| Nguồn | Đường dẫn mặc định từ Ngan_Web | Chức năng |
|---|---|---|
| Tâm + kết quả Thọ tích hợp | ../tam_eda/handover_v3 | Dashboard, bảng đơn/RFM, snapshot ML, metrics, cohort và hợp đồng dữ liệu |
| Thiên | ../Thien_ETL_MongoDB/processed | Hồ sơ, địa chỉ, đơn, sản phẩm, thanh toán và đánh giá chi tiết |
| Power BI | ../tam_eda/POWERBI_Olist_Chot.pbix | Tải báo cáo Power BI gốc 5 trang |
| SQLite | storage/olist_app.db | Tài khoản, chăm sóc, chiến dịch và nhật ký |

Clone toàn bộ repository hoặc giữ các thư mục trên cùng cấu trúc. Không cần nhân bản raw hay tải lại Kaggle. Chỉ có Ngan_Web mà thiếu dữ liệu thì ứng dụng sẽ báo thiếu file.

Có thể đổi đường dẫn trước khi chạy:

```powershell
$env:OLIST_DATA_DIR = 'D:\DuLieuNhom\handover_v3'
$env:OLIST_CLEAN_DIR = 'D:\DuLieuNhom\processed'
$env:OLIST_DB_PATH = 'D:\DuLieuRieng\olist_app.db'
```

Bộ BI được đối chiếu checksum, số dòng, cột và khóa với manifest/integration_contract. Các CSV sạch ở trang chi tiết phải đúng checksum nguồn mà Tâm đã dùng dựng BI. Khi tái tạo dữ liệu, cần bàn giao đồng bộ CSV và manifest; không sửa checksum để bỏ qua lỗi. Khóa cache gồm dấu thời gian và kích thước file, cùng phiên bản mã đọc dữ liệu.

## Các màn hình

1. **Dashboard tương tác:** lọc ngày mua và bang; GMV/AOV chỉ trên đơn delivered, không gồm cước. Tỷ lệ trễ và trung vị giao hàng chỉ dùng valid_delay_kpi=true. Ngày kết thúc được tính hết ngày. CSV xuất toàn bộ kết quả lọc. Cohort trong mục mở rộng là snapshot cố định, không thay đổi theo bộ lọc này.
2. **Khách hàng & ML:** tra mã khách, lọc trạng thái chấm điểm/cụm K-Means, xem tối đa 200 dòng và xuất toàn bộ kết quả lọc. Thanh độ phủ mô tả toàn bộ khách, biểu đồ phân cụm mô tả kết quả sau lọc.
3. **Đánh giá mô hình:** đọc kết quả test lịch sử, decile, ma trận nhầm lẫn và feature importance. Dữ liệu test tách khỏi snapshot khách hàng BI.
4. **Power BI:** tải PBIX để mở bằng Power BI Desktop; đặt DataRoot thành đường dẫn handover_v3 trên máy nhận trước Refresh. Dashboard web có biểu đồ tương tác thực tế; PBIX không tự được nhúng trực tuyến.
5. **Tra cứu & Chăm sóc:** tìm đơn, khách RFM, hồ sơ chi tiết, ghi chú/nhãn, khách ưu tiên và chiến dịch. Màn hình chi tiết nối RFM/ML theo customer_unique_id; không cộng lặp đơn khi xem nhiều item/thanh toán/review.

CSV/Excel ở các màn hình tra cứu chứa toàn bộ kết quả lọc; bảng được phân trang để dễ xem. PDF là báo cáo tóm tắt tối đa 100 dòng đầu, ghi rõ giới hạn và tổng số kết quả trên file. Font tiếng Việt được đóng gói sẵn.

## Phân quyền và lưu trữ

| Thao tác | Admin | Analyst |
|---|---|---|
| Tra cứu, lọc, xem dashboard/ML, tải báo cáo | Có | Có |
| Xem ghi chú, danh sách ưu tiên và chiến dịch | Có | Có |
| Thêm/sửa/xóa mềm ghi chú, ưu tiên, chiến dịch và thành viên | Có | Không |
| Xem nhật ký và danh sách tài khoản | Có | Không |

Mật khẩu băm bằng Argon2. Quyền được kiểm tra lại ở hàm thao tác SQLite và trong giao dịch ghi, không chỉ ẩn nút. Xóa mềm giữ dữ liệu và nhật ký; thêm lại khách ưu tiên đã xóa sẽ khôi phục bản ghi. Mức ưu tiên do Admin chọn độc lập với điểm ML. Các chiến dịch chỉ lưu kế hoạch và thành viên; không tự gửi tin nhắn cho khách.

SQLite cần thư mục có quyền ghi. storage bị loại khỏi Git; không đưa tài khoản, mật khẩu hoặc database làm việc vào repo công khai. Sao lưu file SQLite khi ứng dụng đã dừng. Mỗi máy có SQLite riêng; nếu triển khai một máy chủ, mọi người cần dùng cùng ứng dụng trên máy chủ đó để chia sẻ dữ liệu chăm sóc. Phiên đăng nhập kết thúc khi đăng xuất; tải lại tab có thể yêu cầu đăng nhập lại.

## Mốc thời gian và giới hạn ML

- Tổng thể: 99.441 đơn, 112.650 item, 96.096 khách trong bảng đơn.
- RFM quy tắc: 93.358 khách, reference 30/08/2018, 6 nhóm; khác 4 cụm K-Means.
- Snapshot BI/ML cutoff 31/08/2018: 96.089 khách; 1.170 được chấm và 94.919 chưa đủ điều kiện. 7 khách trong tổng thể nằm ngoài snapshot. Điểm thiếu giữ null, không thay bằng 0.
- Test lịch sử cutoff 01/03/2018, cửa sổ 180 ngày: 944 khách. RF ở ngưỡng 0,5 dự đoán toàn bộ là không mua lại; recall mua lại bằng 0. AP mua lại khoảng 0,0806, ROC-AUC khoảng 0,6420. Temporal validation chưa đủ điều kiện; observation end còn giả định.
- Điểm ML là kết quả thử nghiệm chưa hiệu chuẩn. Không trình bày là dự đoán chính xác khách chắc chắn rời bỏ; feature importance không chứng minh nhân quả. Bộ lọc web không huấn luyện lại mô hình.

## Kiểm thử

Từ Ngan_Web:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Bộ kiểm thử kiểm tra số lượng/khóa khách, phạm vi KPI/GMV, null điểm ML, ngày kết thúc, dữ liệu bị sửa hoặc sai cấu trúc, quyền Admin/Analyst, thao tác chăm sóc/chiến dịch và xuất Excel/PDF. AppTest chạy đăng nhập thực bằng tài khoản tạm, chuyển màn hình, lọc rỗng và đăng xuất. Database kiểm thử nằm trong thư mục tạm; không dùng tài khoản thật. Kiểm thử web không thay thế minh chứng MongoDB thật của phần Thiên.

## Demo khi báo cáo

Đăng nhập Admin → dashboard toàn bộ → lọc một bang, đối chiếu KPI và tải CSV → xem độ phủ ML và trạng thái chưa chấm → xem hạn chế trên tập test → chuyển Tra cứu & Chăm sóc → tra một khách thật → tạo ghi chú/ưu tiên/chiến dịch → xuất Excel/PDF → đăng xuất, vào Analyst để chứng minh không được sửa. Dùng dữ liệu chăm sóc minh họa do nhóm tự tạo, phân biệt với lịch sử Olist.

Nguồn dữ liệu Olist/IBGE được ghi trong phần thu thập của Huy. Website chạy local để demo; việc push Git chưa phải triển khai website công khai. Triển khai và cơ chế truy cập từ ngoài máy cần cấu hình riêng.
