# Olist Customer Analytics — Nhóm 5

ABDA433708: phân tích khách hàng, phân khúc RFM và nguy cơ không mua lại trong 180 ngày bằng MongoDB, Power BI và Machine Learning.

## Các phần bài làm trên main

| Thành viên | Thư mục | Nội dung |
|---|---|---|
| Tâm | [tam_eda](tam_eda/README.md) | Code EDA/BI, dữ liệu phân tích, biểu đồ, Power BI 5 trang và bộ xuất web |
| Thiên | [Thien_ETL_MongoDB](Thien_ETL_MongoDB/README.md) | Code ETL/MongoDB, dữ liệu sạch, index và export |
| Thọ | [Tho_Machine_Learning](Tho_Machine_Learning/README.md) | RFM/K-Means, proxy không mua lại 180 ngày, Isolation Forest và loader chung |
| Huy | [Huy_ThuThap_Olist](Huy_ThuThap_Olist/README.md) | Thu thập Olist/IBGE, snapshot raw và thông tin nguồn |

Website Ngân đang ở nhánh [codex/ngan-web-bao-cao](https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5/tree/codex/ngan-web-bao-cao). Dữ liệu bàn giao đã có, việc tích hợp ML/dashboard và nghiệm thu web được thực hiện riêng. Các bản code thay thế nằm trong lịch sử Git; dùng các thư mục hiện hành ở trên.

## Chạy từ bản clone mới

```powershell
git clone https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5.git
cd olist-customer-analytics-nhom5
```

Mỗi phần có README và môi trường thư viện riêng. Không dùng requirements của một phần để suy ra đã cài đủ cho toàn bộ dự án.

- Tâm: cd tam_eda, cài requirements.txt, chạy python -B run_eda.py. Mở POWERBI_Olist_Chot.pbix và đặt DataRoot về handover_v3 của bản clone trước Refresh. Xuất web bằng export_ngan.py với output là thư mục mới nằm ngoài dự án.
- Thiên: cd Thien_ETL_MongoDB, cài requirements.txt; clean_olist.py đọc raw từ ../Huy_ThuThap_Olist/dataset/runs/20261019T171446Z_e35970/raw/olist. CSV sạch có sẵn trong processed. Kiểm tra CONFIG.dbName trước khi chạy Mongodb.js trên database thật; MONGODB_URI đi qua biến môi trường, không đưa mật khẩu vào Git.
- Thọ: cd Tho_Machine_Learning; cài requirements của module cần chạy. Giữ 4 thư mục con cạnh nhau. Kết quả churn hiện hành duy nhất nằm Tho_Churn_Prediction/outputs/temporal_v4_provisional.
- Huy: python -X utf8 -B Huy_ThuThap_Olist/source-code/verify_run.py từ gốc repo để kiểm tra snapshot; không cần tải lại dữ liệu để sử dụng bản đã chốt.

## Kiểm thử

```powershell
python -B -m unittest discover -s tam_eda -p "test_*.py" -v
python -B -m unittest discover -s Thien_ETL_MongoDB/tests -p "test_*.py" -v
node Thien_ETL_MongoDB/tests/test_mongodb_script.js
python -B -m unittest discover -s Tho_Machine_Learning/Tho_Shared/tests -v
python -B -m unittest discover -s Tho_Machine_Learning/Tho_RFM_KMeans/tests -v
python -B -m unittest discover -s Tho_Machine_Learning/Tho_Churn_Prediction/tests -v
python -B -m unittest discover -s Tho_Machine_Learning/Tho_Order_Anomaly/tests -v
python -B -m unittest discover -s Huy_ThuThap_Olist/source-code/tests -v
```

Kiểm thử JavaScript là offline/mô phỏng; không thay bằng chứng database, index và backup/restore thật. Code không tự triển khai website khi push Git.

## Phạm vi và giới hạn

99.441 đơn, 112.650 item. RFM reference 30/08/2018 có 93.358 khách. ML test cutoff 01/03/2018, horizon 180 ngày, 944 khách. Snapshot BI cutoff 31/08/2018 có 96.089 khách, 1.170 được chấm và 94.919 chưa được chấm. Đọc integration_contract.json trong tam_eda/handover_v3 trước khi nối bảng; không gán xác suất thiếu thành 0, không ghép điểm test thành điểm BI.

RF/0,5 dự đoán cả test là không mua lại, recall mua lại bằng 0; temporal validation chưa đủ điều kiện, observation end còn giả định và xác suất chưa hiệu chuẩn. Đây là mô hình thử nghiệm của đồ án. Báo cáo kết quả thuật toán và giới hạn vẫn giữ trong phần Thọ. 4 cụm K-Means khác 6 nhóm RFM theo quy tắc; đơn bất thường không đồng nghĩa gian lận.

Nguồn: [Olist Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), CC BY-NC-SA 4.0; [API IBGE](https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome). Giữ thông tin nguồn và giấy phép khi chia sẻ. File nguồn/dữ liệu có chủ đích phục vụ tái lập kết quả; không xóa chỉ vì trùng tên ở hai bước đầu vào/đầu ra.
