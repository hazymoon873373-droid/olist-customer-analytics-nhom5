from pathlib import Path
import hashlib
import json

import pandas as pd
import streamlit as st


from analytics_data import CLEAN_DIR as DATA_DIR, DATA_DIR as BI_DIR

FILES = {
    "customers": "olist_customers_clean.csv",
    "orders": "olist_orders_clean.csv",
    "items": "olist_order_items_clean.csv",
    "payments": "olist_order_payments_clean.csv",
    "reviews": "olist_order_reviews_clean.csv",
}

REQUIRED = {
    "customers": [
        "customer_id", "customer_unique_id",
        "customer_city", "customer_state",
        "customer_zip_code_prefix",
    ],
    "orders": [
        "order_id", "customer_id",
        "order_status", "order_purchase_timestamp",
    ],
    "items": [
        "order_id", "order_item_id",
        "product_id", "price", "freight_value",
    ],
    "payments": [
        "order_id", "payment_type",
        "payment_installments", "payment_value",
    ],
    "reviews": [
        "order_id", "review_score",
        "review_comment_title", "review_comment_message",
    ],
}

LABELS = {
    "customer_city": "Thành phố",
    "customer_state": "Bang",
    "customer_zip_code_prefix": "Mã bưu chính",
    "order_id": "Mã đơn hàng",
    "order_status": "Trạng thái",
    "order_purchase_timestamp": "Ngày đặt hàng",
    "order_delivered_customer_date": "Ngày nhận hàng",
    "order_estimated_delivery_date": "Ngày giao dự kiến",
    "order_item_id": "STT sản phẩm trong đơn",
    "product_id": "Mã sản phẩm",
    "seller_id": "Mã người bán",
    "price": "Giá sản phẩm (BRL)",
    "freight_value": "Phí vận chuyển (BRL)",
    "payment_sequential": "STT thanh toán",
    "payment_type": "Phương thức thanh toán",
    "payment_installments": "Số kỳ trả góp",
    "payment_value": "Giá trị thanh toán (BRL)",
    "review_score": "Điểm đánh giá",
    "review_comment_title": "Tiêu đề",
    "review_comment_message": "Nội dung phản hồi",
    "review_creation_date": "Ngày tạo đánh giá",
    "review_time_status": "Trạng thái thời gian đánh giá",
    "valid_delay_kpi": "Đủ điều kiện KPI giao hàng",
    "delivered_missing_date": "Đã giao nhưng thiếu ngày nhận",
    "carrier_before_approval": "Vận chuyển trước duyệt đơn",
    "customer_before_carrier": "Nhận hàng trước vận chuyển",
}


@st.cache_data(show_spinner=False)
def load_tables(signatures, expected_hashes):
    tables = {}
    hashes = dict(expected_hashes)

    for name, path, modified_time, file_size in signatures:
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != hashes[Path(path).name]:
            raise ValueError(f'{Path(path).name} khác phiên bản dữ liệu sạch đã dùng dựng BI.')
        # Giữ nguyên mã định danh và số 0 đầu mã bưu chính.
        frame = pd.read_csv(path, dtype="string")

        missing_columns = [
            column
            for column in REQUIRED[name]
            if column not in frame.columns
        ]

        if missing_columns:
            raise ValueError(
                f"{Path(path).name} thiếu cột: "
                + ", ".join(missing_columns)
            )

        tables[name] = frame

    # Kiểm tra khóa để tránh hiển thị đơn hàng bị trùng.
    for name, key in [
        ("customers", "customer_id"),
        ("orders", "order_id"),
    ]:
        frame = tables[name]

        if frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError(
                f"Bảng {name}: {key} có giá trị thiếu hoặc trùng."
            )

    tables["orders"]["order_purchase_timestamp"] = pd.to_datetime(
        tables["orders"]["order_purchase_timestamp"],
        errors="coerce",
    )

    for table_name, columns in {
        "items": ["price", "freight_value"],
        "payments": ["payment_value"],
        "reviews": ["review_score"],
    }.items():
        for column in columns:
            tables[table_name][column] = pd.to_numeric(
                tables[table_name][column],
                errors="coerce",
            )

    return tables


def display_table(frame, columns, empty_message):
    if frame.empty:
        st.info(empty_message)
        return

    available = [
        column for column in columns
        if column in frame.columns
    ]

    st.dataframe(
        frame[available].rename(columns=LABELS),
        hide_index=True,
        width="stretch",
    )


def render_customer_detail():
    st.subheader("Chi tiết khách hàng")
    st.caption(
        "Xem dữ liệu lịch sử từ bộ processed của Thiên. "
        "Thông tin tại đây chỉ được tra cứu, không chỉnh sửa."
    )

    missing_files = [
        filename
        for filename in FILES.values()
        if not (DATA_DIR / filename).is_file()
    ]

    if missing_files:
        st.error(
            "Thiếu file dữ liệu sạch: "
            + ", ".join(missing_files)
        )
        return

    try:
        signatures = tuple(
            (
                name,
                str(DATA_DIR / filename),
                (DATA_DIR / filename).stat().st_mtime_ns,
                (DATA_DIR / filename).stat().st_size,
            )
            for name, filename in FILES.items()
        )

        with st.spinner("Đang đọc dữ liệu khách hàng..."):
            manifest = json.loads((BI_DIR / 'manifest.json').read_text(encoding='utf8'))
            expected_hashes = tuple((filename, manifest['input_sha256'][filename]) for filename in FILES.values())
            tables = load_tables(signatures, expected_hashes)

    except Exception as exc:
        st.error(f"Không thể đọc dữ liệu: {exc}")
        return

    with st.form("detail_search_form"):
        entered_id = st.text_input(
            "Mã khách hàng — customer_unique_id",
            placeholder="Dán đầy đủ mã từ danh sách khách hàng",
        )

        submitted = st.form_submit_button("Tra cứu")

    if submitted:
        st.session_state["detail_customer_id"] = entered_id.strip()

    selected_customer = st.session_state.get(
        "detail_customer_id", ""
    )

    if not selected_customer:
        st.info("Nhập mã khách hàng rồi bấm Tra cứu.")
        return

    customers = tables["customers"]

    profile = customers.loc[
        customers["customer_unique_id"]
        .eq(selected_customer)
        .fillna(False)
    ].copy()

    if profile.empty:
        st.warning("Không tìm thấy khách hàng có mã này.")
        return

    st.write("**Mã khách hàng:**", selected_customer)

    # Join on the person key, not the per-order customer_id. Never fill an absent score with zero.
    from analytics_pages import cached_data
    from analytics_data import data_signature
    group = cached_data(data_signature())
    ml = group['ml_bi'].loc[group['ml_bi'].customer_unique_id.eq(selected_customer)]
    rfm = group['rfm'].loc[group['rfm'].customer_unique_id.eq(selected_customer)]
    with st.expander('Phân khúc và kết quả ML của khách'):
        st.write('**Nhóm RFM:**', rfm.iloc[0]['segment'] if len(rfm) else 'Chưa có phân khúc RFM')
        if ml.empty:
            st.info('Khách ngoài snapshot ML 31/08/2018; chưa có điểm mô hình.')
        else:
            record = ml.iloc[0]
            segment = record['kmeans_segment']
            st.write('**Cụm K-Means:**', segment if pd.notna(segment) else 'Chưa có cụm')
            if record['ml_scored']:
                st.metric('Điểm không mua lại trong 180 ngày', f"{record['ml_churn_probability']:.4f}")
            else:
                st.info('Chưa đủ điều kiện chấm điểm. Lý do: ' + str(record['ml_eligibility_reason']))
        st.caption('Kết quả thử nghiệm, chưa hiệu chuẩn; điểm mô hình không phải mức ưu tiên chăm sóc do Admin chọn.')

    geo_columns = [
        "customer_city",
        "customer_state",
        "customer_zip_code_prefix",
    ]

    st.write("**Thông tin địa lý theo lịch sử mua hàng**")

    display_table(
        profile[geo_columns].drop_duplicates(),
        geo_columns,
        "Chưa có thông tin địa lý.",
    )

    st.caption(
        "Một khách hàng có thể có nhiều địa chỉ trong các lần mua."
    )

    # Một customer_unique_id có thể ứng với nhiều customer_id.
    customer_ids = profile["customer_id"].dropna().unique()

    orders = tables["orders"].loc[
        tables["orders"]["customer_id"].isin(customer_ids)
    ].copy()

    orders = orders.sort_values(
        ["order_purchase_timestamp", "order_id"],
        ascending=[False, True],
        na_position="last",
    )

    if orders.empty:
        st.info("Chưa có đơn hàng liên kết với khách hàng này.")
        return

    col1, col2 = st.columns(2)

    col1.metric(
        "Tổng số đơn trong lịch sử",
        orders["order_id"].nunique(),
    )

    col2.metric(
        "Số đơn đã giao",
        orders.loc[
            orders["order_status"].eq("delivered"),
            "order_id",
        ].nunique(),
    )

    st.write("**Lịch sử đơn hàng**")

    display_table(
        orders,
        [
            "order_id",
            "order_purchase_timestamp",
            "order_status",
            "order_delivered_customer_date",
            "order_estimated_delivery_date",
            "valid_delay_kpi",
            "delivered_missing_date",
            "carrier_before_approval",
            "customer_before_carrier",
        ],
        "Chưa có đơn hàng.",
    )

    st.caption('Chỉ đơn valid_delay_kpi=true mới dùng tính tỷ lệ trễ và thời gian giao. Các đơn khác vẫn giữ để tra cứu lịch sử.')

    order_options = orders["order_id"].dropna().tolist()

    # Đặt lại lựa chọn đơn khi đổi khách hàng.
    if st.session_state.get("detail_order_id") not in order_options:
        st.session_state.pop("detail_order_id", None)

    selected_order = st.selectbox(
        "Chọn đơn hàng để xem sản phẩm, thanh toán và đánh giá",
        options=order_options,
        key="detail_order_id",
    )

    # Lọc riêng từng bảng, tránh nhân bản dòng khi nối nhiều bảng.
    order_details = {}

    for name in ["items", "payments", "reviews"]:
        frame = tables[name]
        order_details[name] = frame.loc[
            frame["order_id"].eq(selected_order).fillna(False)
        ].copy()

    st.write("**Sản phẩm trong đơn**")

    display_table(
        order_details["items"],
        [
            "order_item_id",
            "product_id",
            "seller_id",
            "price",
            "freight_value",
        ],
        "Đơn này chưa có dữ liệu sản phẩm.",
    )

    st.write("**Thông tin thanh toán**")

    payments = order_details["payments"]

    display_table(
        payments,
        [
            "payment_sequential",
            "payment_type",
            "payment_installments",
            "payment_value",
        ],
        "Đơn này chưa có dữ liệu thanh toán.",
    )

    if not payments.empty:
        total_payment = payments["payment_value"].sum(min_count=1)

        if pd.notna(total_payment):
            st.metric(
                "Tổng thanh toán ghi nhận của đơn (BRL)",
                f"{total_payment:,.2f}",
            )

        st.caption(
            "Tổng các bản ghi thanh toán của đơn, "
            "không phải doanh thu thuần sau hoàn tiền."
        )

    st.write("**Đánh giá và phản hồi**")

    display_table(
        order_details["reviews"],
        [
            "review_score",
            "review_comment_title",
            "review_comment_message",
            "review_creation_date",
            "review_time_status",
        ],
        "Đơn này chưa có đánh giá.",
    )
