# BÀN GIAO PHẦN THU THẬP DỮ LIỆU - NGUYỄN GIA HUY / NHÓM 5

Môn ABDA433708. Đề tài: phân tích khách hàng và dự báo nguy cơ không mua lại trên Olist bằng MongoDB và Machine Learning.

Phần Huy đã thực hiện: **tải Olist từ Kaggle → gọi API IBGE → lưu raw → đếm record → ghi nguồn và mô tả dữ liệu**. Raw đã tải thật qua Internet trong VS Code ngày 20/10/2026 (giờ Việt Nam). Đây là dataset giao dịch lịch sử, không phải đơn hàng mới tại ngày tải.

## 1. Cấu trúc bàn giao

```text
Huy_ThuThap_Olist/
├── source-code/
│   ├── collect_all.py          # Chương trình tổng, chạy một lần đủ 5 yêu cầu
│   ├── data_catalog.py         # Schema và mô tả các trường
│   ├── verify_run.py           # Đọc lại file thực tế, đối chiếu checksum/record
│   └── tests/test_collection.py
├── dataset/
│   ├── latest_success.json     # Đường dẫn tương đối tới bộ dữ liệu được bàn giao
│   └── runs/20261019T171446Z_e35970/
│       ├── raw/olist/          # ZIP gốc và 9 CSV nguyên vẹn
│       ├── raw/ibge/           # Response gốc và JSON bang/vùng Brazil
│       ├── metadata/
│       │   ├── source_manifest.json
│       │   ├── record_counts.csv
│       │   ├── data_dictionary.csv
│       │   └── verification.json
│       ├── logs/collection.log
│       ├── THONG_TIN_DU_LIEU.md
│       └── BIEN_BAN_KIEM_TRA.md
├── .vscode/launch.json         # Cấu hình F5
├── .gitignore
└── README.md                   # Đọc file này trước khi tiếp nhận
```

Hai lần tải cũ, cache Python và báo cáo trùng đã được chuyển ra thư mục lưu trữ bên ngoài gói bàn giao. ZIP gốc và response API được giữ lại vì dùng để đối chiếu tính nguyên vẹn. Các thư mục ẩn là cấu hình chạy/quản lý mã nguồn.

## 2. Kết quả dữ liệu được bàn giao

| Tệp Olist | Record |
|---|---:|
| olist_customers_dataset.csv | 99.441 |
| olist_orders_dataset.csv | 99.441 |
| olist_order_items_dataset.csv | 112.650 |
| olist_order_payments_dataset.csv | 103.886 |
| olist_order_reviews_dataset.csv | 99.224 |
| olist_products_dataset.csv | 32.951 |
| olist_sellers_dataset.csv | 3.095 |
| olist_geolocation_dataset.csv | 1.000.163 |
| product_category_name_translation.csv | 71 |
| **Tổng record Olist** | **1.550.922** |

API IBGE có **27 đơn vị liên bang, 5 vùng lớn**. Liên kết `customer_state = sigla` khớp **99.441/99.441 bản ghi khách hàng**. Tổng 9 CSV là tổng nhiều bảng; không phải 1,55 triệu đơn hoặc khách hàng duy nhất. Dictionary có 58 trường, gồm trường lồng của JSON IBGE.

## 3. Chạy và kiểm tra trên máy thành viên khác

**Mở dữ liệu trên máy Huy:** vào `D:\Big Data\Huy_ThuThap_Olist\dataset\runs\20261019T171446Z_e35970\raw\olist` để xem 9 CSV và ZIP gốc. Dữ liệu API nằm ở thư mục `raw\ibge` cạnh đó.

Nếu Explorer báo **Location is not available** với đường dẫn `Huy_ThuThap_Olist\data\runs`, cửa sổ hoặc liên kết đó đang dùng vị trí trước khi dọn. Đường dẫn hiện tại là `Huy_ThuThap_Olist\dataset\runs`. Đóng thông báo, mở lại thư mục `dataset` ngay trong bộ bàn giao. Không cần tải lại hoặc tạo thêm bản sao dữ liệu.

Sao chép **toàn bộ thư mục Huy_ThuThap_Olist**, giữ cấu trúc thư mục. Cần Python **3.10+**; mã nguồn chỉ dùng thư viện chuẩn, không cần cài pip. Đường dẫn dữ liệu trong `latest_success.json` là tương đối nên có thể chuyển sang ổ đĩa khác.

Mở terminal tại thư mục Huy_ThuThap_Olist và chạy:

```powershell
# Kiểm tra bộ dữ liệu đã nhận, không tải lại:
python -B source-code/verify_run.py

# Kiểm tra mã nguồn:
python -B -m unittest discover -s source-code/tests -v

# Tải mới cả Kaggle và API IBGE:
python -B source-code/collect_all.py
```

Trong VS Code: mở **cả thư mục Huy_ThuThap_Olist**, chọn interpreter Python 3.10+, chọn cấu hình **Huy - Thu thap Olist + API IBGE (chay tat ca)** rồi nhấn **F5**. Cần extension Python và Python Debugger của Microsoft. Kết quả hiện ở Debug Console.

Mỗi lần tải mới tạo một run riêng và cập nhật `dataset/latest_success.json`. Bộ bàn giao hiện chỉ giữ một run. Không cần tải lại để bắt đầu ETL/BI/ML. Khi có thêm run, chọn đúng run mới bằng pointer; không ghép lẫn các lần tải.

Nếu chủ động dùng ZIP đã có để demo khi Kaggle không truy cập được:

```powershell
python -B source-code/collect_all.py --local-zip "dataset/runs/20261019T171446Z_e35970/raw/olist/brazilian-ecommerce.zip"
```

Chế độ này ghi rõ `local_zip_explicit`, vẫn gọi IBGE trực tiếp. `verify_run.py` đánh dấu tiêu chí tải mới Kaggle chưa đạt đối với run dùng ZIP cục bộ; đây là phân biệt chủ ý về bằng chứng nguồn.

## 4. Hướng dẫn bàn giao cho từng bạn

| Người nhận | Nhận gì | Công việc tiếp theo |
|---|---|---|
| **Thiên** | Toàn bộ raw, metadata, thông tin dữ liệu | Làm sạch, chuẩn hóa, kiểm tra khóa và quan hệ, ETL, thiết kế/import MongoDB, indexes, backup/restore |
| **Thọ** | Dictionary, sơ đồ liên kết dưới đây; sau đó nhận processed từ Thiên | Tạo đặc trưng trước T0, nhãn no_repeat_proxy sau T0, K-Means, supervised ML và đánh giá |
| **Tâm** | Dictionary, bảng số bản ghi, IBGE; sau đó nhận processed và kết quả ML | EDA, KPI, dashboard theo bang/vùng và insight |
| **Ngân** | Schema, khóa liên kết; sau đó nhận MongoDB/API từ Thiên và kết quả ML từ Thọ | Website, phân quyền, CRUD, lọc và xuất báo cáo |
| **Huy** | Giữ code và bằng chứng nguồn | Giải thích phương pháp thu thập, theo dõi bàn giao và kiểm tra tích hợp |

Ví dụ tìm đúng raw bằng Python sau khi sao chép thư mục:

```python
import json
from pathlib import Path

project = Path.cwd()  # chạy tại thư mục Huy_ThuThap_Olist
dataset = project / "dataset"
pointer = json.loads((dataset / "latest_success.json").read_text(encoding="utf-8"))
run = dataset / pointer["run_path"]
olist_raw = run / "raw" / "olist"
ibge_raw = run / "raw" / "ibge" / "ibge_states_raw.json"
```

## 5. Khóa, quan hệ và lưu ý ETL/ML

```text
customers.customer_id  ← orders.customer_id
orders.order_id        ← order_items.order_id / order_payments.order_id / order_reviews.order_id
products.product_id    ← order_items.product_id
sellers.seller_id      ← order_items.seller_id
products.product_category_name → translation.product_category_name
customers.customer_state / sellers.seller_state → IBGE.sigla
customer_zip_code_prefix / seller_zip_code_prefix → geolocation_zip_code_prefix
```

- Phân tích mua lại dùng `customer_unique_id`; `customer_id` dùng liên kết đơn với bản ghi khách hàng. Không nhầm 99.441 dòng customers thành 99.441 khách duy nhất.
- Khóa item là `(order_id, order_item_id)`. Không mặc định `review_id` hoặc `order_id` là duy nhất trong bảng review; Thiên phải kiểm tra trước thiết kế.
- Giữ mã ZIP dạng chuỗi để không mất số 0 đầu. Giá tiền là BRL. Thời gian đơn hàng theo nguồn không có timezone; không tự gán UTC. Timestamp thu thập trong manifest dùng UTC.
- Review có ô chứa xuống dòng; dùng CSV parser để đọc, không đếm bằng số dòng văn bản.
- Có dữ liệu thiếu trong nguồn: 2.965 dòng orders thiếu ngày giao khách; 610 dòng products thiếu danh mục; nhiều review thiếu bình luận. Bảng geolocation có thể nhiều tọa độ trên cùng tiền tố ZIP; cần tổng hợp trước khi join. Đây là đầu vào cho Thiên làm sạch, không phải mất dữ liệu do tải.
- Chuẩn hóa và tạo bảng processed riêng; giữ raw nguyên vẹn. Cẩn thận phép join một-nhiều làm nhân doanh thu.
- IBGE lấy tại thời điểm thu thập, dùng làm tham chiếu địa lý; không suy diễn GDP/dân số năm 2016–2018.
- Thọ phải chọn T0 và đủ cửa sổ theo dõi; mọi feature chỉ dùng thông tin đã biết trước T0. Nhãn không mua lại là proxy lịch sử, không phải churn chính thức.

## 6. Nguồn và phạm vi hoàn thành

- Olist: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce
- Endpoint tải: https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce
- Tài liệu API IBGE: https://servicodados.ibge.gov.br/api/docs/localidades
- Endpoint: https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome
- Olist: CC BY-NC-SA 4.0; giữ ghi công và tuân thủ điều kiện nguồn. IBGE: giữ ghi nguồn, chưa khẳng định mã giấy phép riêng cho endpoint.
- Có HTTP receipt, thời điểm tải, SHA-256, mô tả bảng/trường, kiểm tra schema, số record và độ phủ mã bang. Chưa xác minh số phiên bản Kaggle; dùng checksum định danh file.
- Log giữ nguyên đường dẫn tại thời điểm tải ban đầu trước khi dọn thư mục. Đường dẫn hiện tại lấy từ `dataset/latest_success.json`; việc chuyển thư mục không thay đổi byte dữ liệu raw.

**Phạm vi đã hoàn thành:** 5 yêu cầu thu thập của Huy. Bộ dữ liệu đủ để bàn giao cho các thành viên tiếp tục. **Công việc tiếp theo của nhóm:** làm sạch, thiết kế/lưu MongoDB, BI, ML và web theo phân công. Tài liệu crawl của thầy Khải minh họa Scrapy/HTML và MongoDB Atlas; chương trình này thu thập ZIP/API bằng HTTPS. Nếu giảng viên yêu cầu riêng spider Scrapy hoặc Atlas trong bài thực hành, đó là yêu cầu bổ sung ngoài chương trình thu thập hiện tại.

Điểm giảng viên chấm còn phụ thuộc triển khai, tích hợp và vấn đáp; biên bản kiểm tra xác nhận đầu ra kỹ thuật.
