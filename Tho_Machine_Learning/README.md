# Machine Learning cho phân tích khách hàng Olist

Môn ABDA433708 — nhóm 5. Phần này đặt trong Tho_Machine_Learning của repository chung. Giữ nguyên cấu trúc 4 thư mục con:

| Thư mục | Vai trò |
|---|---|
| Tho_Shared | Loader chung, dữ liệu sạch và master/RFM tham chiếu để tái lập kết quả |
| Tho_RFM_KMeans | RFM và phân cụm K-Means; model, biểu đồ và báo cáo kết quả |
| Tho_Churn_Prediction | Dự báo proxy không mua lại 180 ngày, đánh giá theo thời gian và snapshot BI |
| Tho_Order_Anomaly | Isolation Forest phát hiện đơn hàng bất thường |

Không đổi tên 4 thư mục vì các module import và tìm dữ liệu theo cấu trúc này. Chạy các lệnh bên dưới từ thư mục Tho_Machine_Learning (cd Tho_Machine_Learning từ gốc repo). Tham khảo README và requirements riêng trong từng phần.

## Cài đặt và kiểm thử

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r Tho_Churn_Prediction/requirements.txt
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s Tho_Shared/tests -v
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s Tho_RFM_KMeans/tests -v
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s Tho_Churn_Prediction/tests -v
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s Tho_Order_Anomaly/tests -v
```

Loader nhận cả tên cột master ETL và master BI cuối của Tâm; từ chối dữ liệu khi hai tên cột cùng tồn tại nhưng giá trị mâu thuẫn. Đơn không có item có thể giữ tổng bằng 0 hoặc null theo hợp đồng nguồn. Không bỏ các kiểm tra khóa/cờ/ngày/tổng tiền.

## Chạy và dữ liệu

K-Means: dùng lệnh verify_rfm.py trong README của phần tương ứng để đối soát và giữ model; chỉ train khi có lý do thay snapshot. Churn có thể chạy run_all.py --output-dir với thư mục kiểm tra riêng; giữ nguyên outputs/temporal_v4_provisional là phiên bản kết quả hiện hành. Model mặc định là selected_model.joblib; candidate RF/LR cần giữ để so sánh và chạy kiểm thử.

Các master, CSV sạch và RFM reference trong Tho_Shared/data là đầu vào tái lập kết quả, không phải file rác. reports/ và Ketqua_*.txt là báo cáo/kết quả nghiệp vụ của đồ án; metrics, data_contract, validation_fold_audit, source_metadata và rfm_source_check là dữ liệu đánh giá/nguồn do pipeline tạo. Giữ các kết quả này để kiểm chứng thuật toán, số liệu và nguồn dữ liệu.

## Mốc thời gian và giới hạn

RFM reference 30/08/2018 có 93.358 khách; K-Means 4 cụm khác 6 nhóm RFM quy tắc của Tâm. Churn test cutoff 01/03/2018, horizon 180 ngày, 944 khách; BI cutoff 31/08/2018, 96.089 khách, 1.170 được chấm. Không ghép điểm test vào snapshot BI; xác suất chưa được chấm giữ null.

RF/0,5 dự đoán cả test là không mua lại, recall lớp mua lại bằng 0; validation theo thời gian không đủ hai lớp và observation end còn giả định. Xem báo cáo temporal_v4, metrics.json và validation_protocol.json để trình bày trung thực. Không tune theo test đã xem; xác suất chưa hiệu chuẩn. Isolation Forest không có nhãn thật nên không dùng accuracy/F1 và không kết luận đơn bất thường là gian lận.

Nguồn Olist Brazilian E-Commerce (CC BY-NC-SA 4.0): https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce . Dữ liệu sạch và IBGE là snapshot chung của nhóm.
