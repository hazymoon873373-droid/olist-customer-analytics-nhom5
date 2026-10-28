# RFM và K-Means

Phần này phân khúc khách hàng Olist bằng ba biến Recency, Frequency và Monetary. Dữ liệu đầu vào là `olist_powerbi_orders_master.csv`.

## Quy tắc tính RFM

- Chỉ lấy đơn có trạng thái `delivered`.
- Khách hàng được xác định bằng `customer_unique_id`.
- Recency: số ngày từ lần mua cuối đến ngày 30/08/2018.
- Frequency: số đơn hàng khác nhau của khách hàng.
- Monetary: tổng `total_products_value`, không cộng phí vận chuyển.
- Dùng toàn bộ lịch sử đơn delivered đến hết ngày 30/08/2018.
- Không dùng `valid_delay_kpi` để loại đơn khỏi bảng RFM.

Sau khi lọc còn 93.358 khách hàng. Ba biến RFM được biến đổi `log1p`, chuẩn hóa bằng `StandardScaler` rồi mới đưa vào K-Means.

## Cài thư viện

```powershell
python -m pip install -r Tho_RFM_KMeans/requirements.txt
```

## Chạy lại toàn bộ

Đặt `olist_powerbi_orders_master.csv` trong `Tho_RFM_KMeans/data/`, sau đó chạy:

```powershell
python -B Tho_RFM_KMeans/source-code/train_kmeans.py
```

Có thể dùng tên file tương thích với phiên bản cũ:

```powershell
python -B Tho_RFM_KMeans/source-code/kmeans_rfm.py
```

Hoặc truyền đường dẫn trực tiếp:

```powershell
python -B Tho_RFM_KMeans/source-code/train_kmeans.py `
  --input "D:\duong-dan\olist_powerbi_orders_master.csv"
```

Chạy test:

```powershell
python -B -m unittest discover -s Tho_RFM_KMeans/tests -v
```

Gán cụm cho bảng RFM mới:

```powershell
python -B Tho_RFM_KMeans/source-code/predict_cluster.py `
  --input "duong-dan\rfm_moi.csv" `
  --output "duong-dan\ket_qua_gan_cum.csv"
```

## Kết quả chính

- K theo Silhouette tốt nhất: 2.
- K tại điểm elbow: 4.
- K được chọn: 4.
- Silhouette: 0,3918.
- Davies-Bouldin: 0,7591.
- Calinski-Harabasz: 73.516,9960.
- Độ ổn định trung bình ARI: 0,9992.

K=2 có Silhouette cao nhưng một cụm chiếm khoảng 97% khách hàng. K=4 tách được bốn nhóm có ý nghĩa sử dụng rõ hơn và vẫn ổn định qua nhiều lần khởi tạo.

## Thư mục kết quả

```text
Tho_RFM_KMeans/
├── source-code/       # Code tạo RFM, train và dự đoán
├── tests/             # Kiểm tra công thức và pipeline
├── models/            # Pipeline log1p + scaler + K-Means
├── outputs/           # CSV, metric và biểu đồ
├── reports/           # Các bước thực hiện và nội dung báo cáo
└── data/              # Dữ liệu đầu vào local, không commit
```

Model lưu cả bước `log1p` và chuẩn hóa. Khi dự đoán chỉ cần đưa vào ba cột `recency`, `frequency`, `monetary`, không xử lý lại bằng tay.

Các file mang tên giống phiên bản cũ gồm `Ketqua_KMeans.txt`, `rfm_kmeans_summary.xlsx`, ba biểu đồ `KMeans_*.png` và `kmeans_rfm_pipeline.pkl`. Nhóm có thể thay trực tiếp thư mục kết quả cũ mà không cần đổi tên file.
