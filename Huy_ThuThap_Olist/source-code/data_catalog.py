"""Schema và mô tả dữ liệu thô dùng cho chương trình thu thập của Huy.

Kiểu dữ liệu là kiểu đề xuất khi ETL. CSV gốc vẫn giữ nguyên chuỗi, kể cả mã ZIP.
"""

KAGGLE_PAGE = "https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce"
KAGGLE_URL = "https://www.kaggle.com/api/v1/datasets/download/olistbr/brazilian-ecommerce"
IBGE_DOCS = "https://servicodados.ibge.gov.br/api/docs/localidades"
IBGE_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados?orderBy=nome"

# field = (tên cột giữ nguyên theo nguồn, kiểu đề xuất, ý nghĩa)
CATALOG = {
    "olist_customers_dataset.csv": {
        "expected_records": 99441,
        "description": "Bản ghi khách hàng gắn với đơn hàng, địa chỉ ở mức thành phố/bang.",
        "key": "customer_id; customer_unique_id nhận diện khách qua nhiều đơn",
        "fields": [
            ("customer_id", "string", "Mã khách gắn với từng đơn; nối orders.customer_id"),
            ("customer_unique_id", "string", "Mã cùng một khách qua nhiều đơn; dùng phân tích mua lại"),
            ("customer_zip_code_prefix", "string(5)", "Tiền tố mã bưu chính; giữ số 0 đầu"),
            ("customer_city", "string", "Thành phố khách hàng theo nguồn"),
            ("customer_state", "string(2)", "Mã bang Brazil; nối IBGE.sigla"),
        ],
    },
    "olist_orders_dataset.csv": {
        "expected_records": 99441,
        "description": "Đơn hàng, trạng thái và các thời điểm mua, duyệt, giao, dự kiến giao.",
        "key": "order_id; nối customers bằng customer_id",
        "fields": [
            ("order_id", "string", "Mã đơn hàng"),
            ("customer_id", "string", "Nối customers.customer_id"),
            ("order_status", "string", "Trạng thái đơn; trạng thái cuối có thể biết sau mốc ML"),
            ("order_purchase_timestamp", "datetime", "Thời điểm đặt hàng theo nguồn; không tự gán UTC"),
            ("order_approved_at", "datetime?", "Thời điểm thanh toán được duyệt"),
            ("order_delivered_carrier_date", "datetime?", "Thời điểm bàn giao cho đơn vị vận chuyển"),
            ("order_delivered_customer_date", "datetime?", "Thời điểm giao cho khách"),
            ("order_estimated_delivery_date", "datetime?", "Ngày giao dự kiến"),
        ],
    },
    "olist_order_items_dataset.csv": {
        "expected_records": 112650,
        "description": "Chi tiết hàng hóa trong đơn; giá và phí vận chuyển bằng BRL.",
        "key": "Khóa ghép (order_id, order_item_id)",
        "fields": [
            ("order_id", "string", "Nối orders.order_id"),
            ("order_item_id", "integer", "Số thứ tự item trong đơn, không phải số lượng mua"),
            ("product_id", "string", "Nối products.product_id"),
            ("seller_id", "string", "Nối sellers.seller_id"),
            ("shipping_limit_date", "datetime", "Hạn bàn giao hàng cho đơn vị vận chuyển"),
            ("price", "decimal", "Giá item bằng BRL"),
            ("freight_value", "decimal", "Phí vận chuyển item bằng BRL"),
        ],
    },
    "olist_order_payments_dataset.csv": {
        "expected_records": 103886,
        "description": "Thanh toán; một đơn có thể có nhiều phương thức hoặc dòng thanh toán.",
        "key": "Khóa ứng viên (order_id, payment_sequential), cần kiểm định ở bước ETL",
        "fields": [
            ("order_id", "string", "Nối orders.order_id"),
            ("payment_sequential", "integer", "Thứ tự bản ghi thanh toán trong đơn"),
            ("payment_type", "string", "Phương thức thanh toán"),
            ("payment_installments", "integer", "Số kỳ trả góp"),
            ("payment_value", "decimal", "Giá trị thanh toán bằng BRL"),
        ],
    },
    "olist_order_reviews_dataset.csv": {
        "expected_records": 99224,
        "description": "Đánh giá đơn hàng; bình luận có thể chứa dấu phẩy, dấu nháy và xuống dòng.",
        "key": "review_id/order_id cần kiểm định; không giả định quan hệ 1-1",
        "fields": [
            ("review_id", "string", "Mã review theo nguồn; không mặc định duy nhất"),
            ("order_id", "string", "Nối orders.order_id"),
            ("review_score", "integer", "Điểm đánh giá từ 1 đến 5"),
            ("review_comment_title", "string?", "Tiêu đề bình luận, có thể thiếu"),
            ("review_comment_message", "string?", "Nội dung bình luận, có thể thiếu hoặc nhiều dòng"),
            ("review_creation_date", "datetime", "Ngày tạo khảo sát đánh giá"),
            ("review_answer_timestamp", "datetime", "Thời điểm khách gửi đánh giá"),
        ],
    },
    "olist_products_dataset.csv": {
        "expected_records": 32951,
        "description": "Thông tin danh mục, kích thước, trọng lượng và độ dài mô tả sản phẩm.",
        "key": "product_id",
        "fields": [
            ("product_id", "string", "Mã sản phẩm"),
            ("product_category_name", "string?", "Danh mục tiếng Bồ Đào Nha"),
            ("product_name_lenght", "integer?", "Độ dài tên; giữ nguyên lỗi chính tả lenght từ nguồn"),
            ("product_description_lenght", "integer?", "Độ dài mô tả; giữ tên cột gốc"),
            ("product_photos_qty", "integer?", "Số ảnh sản phẩm"),
            ("product_weight_g", "decimal?", "Trọng lượng gram"),
            ("product_length_cm", "decimal?", "Chiều dài cm"),
            ("product_height_cm", "decimal?", "Chiều cao cm"),
            ("product_width_cm", "decimal?", "Chiều rộng cm"),
        ],
    },
    "olist_sellers_dataset.csv": {
        "expected_records": 3095,
        "description": "Người bán và vị trí ở mức tiền tố bưu chính, thành phố, bang.",
        "key": "seller_id",
        "fields": [
            ("seller_id", "string", "Mã người bán"),
            ("seller_zip_code_prefix", "string(5)", "Tiền tố mã bưu chính người bán"),
            ("seller_city", "string", "Thành phố người bán"),
            ("seller_state", "string(2)", "Mã bang người bán; nối IBGE.sigla"),
        ],
    },
    "olist_geolocation_dataset.csv": {
        "expected_records": 1000163,
        "description": "Tọa độ địa lý theo tiền tố bưu chính; nhiều tọa độ có thể cùng tiền tố.",
        "key": "Không mặc định zip_code_prefix là khóa duy nhất",
        "fields": [
            ("geolocation_zip_code_prefix", "string(5)", "Tiền tố mã bưu chính để liên kết vị trí"),
            ("geolocation_lat", "float", "Vĩ độ"),
            ("geolocation_lng", "float", "Kinh độ"),
            ("geolocation_city", "string", "Thành phố theo nguồn"),
            ("geolocation_state", "string(2)", "Mã bang của tọa độ"),
        ],
    },
    "product_category_name_translation.csv": {
        "expected_records": 71,
        "description": "Bảng dịch tên danh mục sản phẩm sang tiếng Anh.",
        "key": "product_category_name",
        "fields": [
            ("product_category_name", "string", "Danh mục tiếng Bồ Đào Nha; nối products"),
            ("product_category_name_english", "string", "Tên danh mục tiếng Anh"),
        ],
    },
}

IBGE_FIELDS = [
    ("id", "integer", "Mã đơn vị liên bang do IBGE cung cấp"),
    ("sigla", "string(2)", "Mã bang; nối customer_state/seller_state"),
    ("nome", "string", "Tên bang hoặc đặc khu liên bang"),
    ("regiao.id", "integer", "Mã vùng lớn của Brazil"),
    ("regiao.sigla", "string", "Viết tắt vùng"),
    ("regiao.nome", "string", "Tên vùng để phân tích BI theo địa lý"),
]
