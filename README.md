# Olist Customer Analytics — Nhóm 5

Môn ABDA433708. Phân tích khách hàng và nguy cơ không mua lại trên Olist bằng MongoDB và Machine Learning.

## Phân nhánh

| Nhánh | Người phụ trách | Nội dung |
|---|---|---|
| main | Huy điều phối | Bản tích hợp chung đã thống nhất |
| codex/huy-thu-thap | Huy | Thu thập Kaggle, API IBGE, dữ liệu thô, metadata và giám sát |
| codex/thien-etl-mongodb | Thiên | Làm sạch, kiểm định, MongoDB |
| codex/tam-bi | Tâm | EDA, KPI và Power BI |
| codex/tho-machine-learning | Thọ | RFM, K-Means, mô hình nguy cơ không mua lại |
| codex/ngan-web-bao-cao | Ngân | Website, khai thác dữ liệu và báo cáo theo phân công nhóm |

Các nhánh ban đầu cùng chứa gói thu thập của Huy. Thành viên làm trên nhánh của mình rồi mở Pull Request vào main để nhóm kiểm tra trước khi hợp nhất. Chưa đưa sản phẩm của Thiên, Tâm, Thọ hoặc Ngân vào đợt push này.

## Phần đã bàn giao

Thư mục `Huy_ThuThap_Olist/` chứa code Python, cấu hình VS Code, snapshot dữ liệu thô, ZIP nguồn, phản hồi API, metadata, log và báo cáo kiểm tra. Đọc README trong thư mục đó để xem chi tiết nguồn và giới hạn dữ liệu.

Snapshot: `20261019T171446Z_e35970`. Có 9 CSV Olist (99.441 đơn hàng) và JSON IBGE (27 đơn vị liên bang). Các số lượng cộng giữa nhiều bảng không phải số khách hàng duy nhất.

Nhánh `codex/tho-machine-learning` có thêm thư mục `Tho_RFM_KMeans/`. Phần này tạo lại bảng RFM từ order master, đánh giá K từ 2 đến 10 và huấn luyện K-Means với K=4. Model, bảng gán nhãn, biểu đồ và nội dung báo cáo được lưu cùng thư mục.

Nhánh này cũng có thư mục `Tho_Churn_Prediction/`. Phần supervised learning tạo nhãn churn proxy 180 ngày theo rolling snapshot cho khách đã có ít nhất hai đơn, huấn luyện Random Forest, xuất model, dự đoán test, biểu đồ và báo cáo. Feature chỉ dùng thông tin có trước từng snapshot.

Thư mục `Tho_Order_Anomaly/` dùng Isolation Forest để khảo sát các đơn hàng đã giao có đặc điểm bất thường. Phần này có Pipeline, model, CSV chấm điểm, biểu đồ, Excel tổng hợp và nội dung báo cáo.

## Bắt đầu

```powershell
git clone https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5.git
cd olist-customer-analytics-nhom5
git switch codex/huy-thu-thap
cd Huy_ThuThap_Olist
python -B source-code/verify_run.py
python -B -m unittest discover -s source-code/tests -v
```

Thay tên nhánh bằng nhánh được phân công. Python 3.10+; phần thu thập chỉ dùng thư viện chuẩn. Mở riêng `Huy_ThuThap_Olist` trong VS Code để sử dụng cấu hình F5. Lệnh thu thập mới: `python -B source-code/collect_all.py`.

Chỉ snapshot bàn giao được theo dõi bằng Git; run mới được bỏ qua để tránh vô tình đưa thêm nhiều bản dữ liệu vào lịch sử. Dùng thư mục riêng cho sản phẩm từng thành viên, giữ raw nguyên vẹn. Không commit mật khẩu, token, URI MongoDB có thông tin đăng nhập hoặc `.env`.

## Nguồn và phạm vi

- Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce — ghi công Olist, CC BY-NC-SA 4.0 theo hồ sơ nguồn.
- IBGE: https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome — tham chiếu địa lý tại thời điểm thu thập.
- Giữ các điều kiện nguồn khi sử dụng/chia sẻ dữ liệu. Không áp dụng giấy phép mã nguồn mới cho dữ liệu bên thứ ba.
- Nhãn không mua lại là proxy, không phải churn chính thức. Features ML chỉ dùng thông tin đã biết trước T0.
- Kiểm tra phần Huy: 7 tests và 21 kiểm tra dữ liệu đạt; chưa chứng nhận phần MongoDB, BI, ML hoặc toàn bộ đồ án.

Repo riêng tư: chủ repo cần cấp quyền GitHub cho từng thành viên để họ clone/push; tạo nhánh không tự cấp quyền truy cập.
