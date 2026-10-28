# Olist Customer Analytics nhóm 5

Môn ABDA433708. Phân tích khách hàng, phân khúc RFM và nguy cơ không mua lại trong 180 ngày trên Olist bằng MongoDB và Machine Learning.

## Cấu trúc và phiên bản sử dụng

| Phần | Điểm bắt đầu |
|---|---|
| Thu thập và bằng chứng nguồn của Huy | `Huy_ThuThap_Olist/README.md` |
| Làm sạch và MongoDB của Thiên | `HUONG_DAN_BAN_GIAO.md`, `clean_olist.py`, `Mongodb.js` |
| Dữ liệu sạch chung của ML | `Tho_Shared/README.md` |
| RFM và K-Means | `Tho_RFM_KMeans/README.md` |
| Dự đoán không mua lại | `Tho_Churn_Prediction/README.md` |
| Phát hiện đơn bất thường | `Tho_Order_Anomaly/README.md` |
| Website của Ngân | Nhánh `codex/ngan-web-bao-cao`, đọc `HUONG_DAN_WEB.md` trên nhánh đó |
| BI của Tâm | Nhánh `codex/tam-bi`; bản RFM đã nhận được lưu trong `Tho_Shared/data/` |

`main` là bản sử dụng chung của phần thu thập, ETL/MongoDB và ML đã tích hợp. Website vẫn có nhánh riêng và hướng dẫn dữ liệu riêng; việc dọn mã nguồn không thay thế công việc tích hợp dashboard và ML vào web. Không dùng code cũ còn nằm ở commit trước làm bản đang chạy.

## Chạy từ một bản clone mới

```powershell
git clone https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5.git
cd olist-customer-analytics-nhom5
```

Phần thu thập chỉ cần Python 3.10+ và thư viện chuẩn:

```powershell
python -X utf8 -B Huy_ThuThap_Olist/source-code/verify_run.py
```

Phần ML dùng môi trường riêng theo requirements của từng mô-đun. Ví dụ churn:

```powershell
python -m venv .venv-ml
.\.venv-ml\Scripts\python.exe -m pip install -r Tho_Churn_Prediction/requirements.txt
.\.venv-ml\Scripts\python.exe -B Tho_Churn_Prediction/source-code/run_all.py
.\.venv-ml\Scripts\python.exe -B -m unittest discover -s Tho_Churn_Prediction/tests -v
```

Kiểm tra và giữ K-Means hiện tại: `python -B Tho_RFM_KMeans/source-code/verify_rfm.py`. Isolation Forest: `python -B Tho_Order_Anomaly/source-code/run_all.py` sau khi cài requirements tương ứng. Mỗi bộ test chạy riêng theo thư mục mô-đun.

ETL/MongoDB dùng `requirements.txt` ở gốc; đọc `HUONG_DAN_BAN_GIAO.md` và `HUONG_DAN_BACKUP_RESTORE.md`. Script MongoDB có cập nhật dữ liệu/index; kiểm tra đúng database và bản sao lưu trước khi chạy. Code test giả lập không thay thế kiểm thử trên server thật.

## Dữ liệu và giới hạn

- Snapshot raw của Huy chứa 9 CSV, ZIP nguồn và phản hồi API IBGE; giữ raw nguyên vẹn để đối chiếu, không nhầm tổng nhiều bảng thành số đơn hoặc số khách duy nhất.
- Dữ liệu sử dụng hiện tại của ML nằm trong `Tho_Shared/data/`. Kết quả churn nằm duy nhất trong `Tho_Churn_Prediction/outputs/temporal_v3_provisional/`.
- Raw Olist: [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), ghi công Olist theo hồ sơ nguồn, CC BY-NC-SA 4.0. [API IBGE](https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome) làm tham chiếu địa lý.
- Nhãn không mua lại là proxy lịch sử. Mốc kết thúc quan sát cần nhóm xác nhận. Các điểm ML và mức rủi ro đang là kết quả thử nghiệm, không phải kết luận chắc chắn về khách hàng.
- Các phiên bản đã bỏ khỏi gói chạy vẫn xem được trong [snapshot trước khi dọn](https://github.com/hazymoon873373-droid/olist-customer-analytics-nhom5/tree/89faa7f8e3909211543a897710e7168f65a0ff87). Không rewrite lịch sử Git để dọn file thông thường.
- Repo công khai cho phép xem/clone; quyền push vẫn do chủ repo cấp. Không commit mật khẩu, token, URI có thông tin đăng nhập hoặc dữ liệu tài khoản ứng dụng.
