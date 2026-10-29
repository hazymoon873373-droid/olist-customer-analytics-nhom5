import math

import pandas as pd
import streamlit as st

from exports import render_excel_export
from pdf_export import render_pdf_export


def reset_customer_filters():
    st.session_state["cus_search"] = ""
    st.session_state["cus_segments"] = []
    st.session_state["cus_states"] = []
    st.session_state["cus_regions"] = []
    st.session_state["cus_reviews"] = []
    st.session_state["cus_missing_review"] = False
    st.session_state["cus_date_enabled"] = False
    st.session_state.pop("cus_dates", None)
    st.session_state["cus_page"] = 1


def render_customers(orders, rfm, user):
    st.subheader("Tra cứu khách hàng")

    st.caption(
        "Phạm vi: khách hàng có trong bảng RFM. "
        "Điều kiện ngày, bang/vùng và điểm đánh giá "
        "phải cùng khớp trên ít nhất một đơn hàng của khách."
    )

    required_orders = {
        "order_id",
        "customer_unique_id",
        "customer_state",
        "region_name",
        "order_purchase_timestamp",
        "review_score",
    }

    required_rfm = {
        "customer_unique_id",
        "segment",
    }

    missing_orders = required_orders - set(orders.columns)
    missing_rfm = required_rfm - set(rfm.columns)

    if missing_orders or missing_rfm:
        st.error(
            "Thiếu cột dữ liệu. "
            f"Bảng đơn hàng: {sorted(missing_orders)}; "
            f"Bảng RFM: {sorted(missing_rfm)}."
        )
        return

    if (
        rfm["customer_unique_id"].isna().any()
        or rfm["customer_unique_id"].duplicated().any()
    ):
        st.error(
            "Bảng RFM có mã khách hàng thiếu hoặc trùng. "
            "Cần kiểm tra trước khi ghép dữ liệu."
        )
        return

    # Chuẩn hóa bản sao, không sửa bảng gốc.
    order_data = orders.copy()

    order_data["order_purchase_timestamp"] = pd.to_datetime(
        order_data["order_purchase_timestamp"],
        errors="coerce",
    )

    order_data["review_score"] = pd.to_numeric(
        order_data["review_score"],
        errors="coerce",
    )

    # ==========================================
    # BỘ LỌC KHÁCH HÀNG
    # ==========================================
    search = st.text_input(
        "Mã khách hàng",
        placeholder="Nhập toàn bộ hoặc một phần mã khách hàng...",
        key="cus_search",
    ).strip()

    segments = st.multiselect(
        "Phân khúc RFM",
        options=sorted(
            rfm["segment"].dropna().unique().tolist()
        ),
        key="cus_segments",
        placeholder="Tất cả phân khúc",
    )

    with st.expander('Bộ lọc nâng cao · Bang, vùng, ngày và đánh giá'):
        col1, col2 = st.columns(2)

        with col1:
            states = st.multiselect(
                "Bang/đặc khu trên đơn hàng",
                options=sorted(
                    order_data["customer_state"]
                    .dropna()
                    .unique()
                    .tolist()
                ),
                key="cus_states",
            )

        with col2:
            regions = st.multiselect(
                "Vùng trên đơn hàng",
                options=sorted(
                    order_data["region_name"]
                    .dropna()
                    .unique()
                    .tolist()
                ),
                key="cus_regions",
            )

        missing_review = st.checkbox(
            "Chỉ tìm khách có đơn chưa có điểm đánh giá",
            key="cus_missing_review",
        )

        reviews = st.multiselect(
            "Điểm đánh giá trên đơn hàng",
            options=sorted(order_data['review_score'].dropna().unique().tolist()),
            disabled=missing_review,
            key="cus_reviews",
        )

        valid_dates = order_data[
            "order_purchase_timestamp"
        ].dropna()

        date_enabled = st.checkbox(
            "Lọc theo ngày đặt hàng",
            disabled=valid_dates.empty,
            key="cus_date_enabled",
        )

        date_range = None

        if date_enabled and not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            date_range = st.date_input(
                "Ngày bắt đầu và ngày kết thúc",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                key="cus_dates",
            )

    st.button(
        "↺ Xóa toàn bộ bộ lọc khách hàng",
        on_click=reset_customer_filters,
        key="cus_reset",
    )

    active_filters = []
    if states:
        active_filters.append('Bang: ' + ', '.join(states))
    if regions:
        active_filters.append('Vùng: ' + ', '.join(regions))
    if missing_review:
        active_filters.append('Có đơn chưa có đánh giá')
    elif reviews:
        active_filters.append('Điểm: ' + ', '.join(map(str, reviews)))
    if date_enabled and date_range is not None and len(date_range) == 2:
        active_filters.append(f'Ngày: {date_range[0]:%d/%m/%Y} – {date_range[1]:%d/%m/%Y}')
    if active_filters:
        st.caption('Đang áp dụng · ' + ' · '.join(active_filters))

    if date_enabled:
        if date_range is None or len(date_range) != 2:
            st.info("Hãy chọn đủ ngày bắt đầu và ngày kết thúc.")
            return

    # ==========================================
    # LỌC CÁC ĐƠN THỎA MÃN ĐỒNG THỜI ĐIỀU KIỆN
    # ==========================================
    matched_orders = order_data.copy()

    if states:
        matched_orders = matched_orders[
            matched_orders["customer_state"].isin(states)
        ]

    if regions:
        matched_orders = matched_orders[
            matched_orders["region_name"].isin(regions)
        ]

    if missing_review:
        matched_orders = matched_orders[
            matched_orders["review_score"].isna()
        ]
    elif reviews:
        matched_orders = matched_orders[
            matched_orders["review_score"].isin(reviews)
        ]

    if date_enabled:
        start = pd.Timestamp(date_range[0])
        end = pd.Timestamp(date_range[1]) + pd.Timedelta(days=1)

        matched_orders = matched_orders[
            (
                matched_orders["order_purchase_timestamp"]
                >= start
            )
            & (
                matched_orders["order_purchase_timestamp"]
                < end
            )
        ]

    # Đếm số đơn phù hợp của mỗi khách.
    # Mỗi mã khách chỉ còn một dòng trước khi ghép.
    counts = (
        matched_orders.dropna(
            subset=["customer_unique_id"]
        )
        .groupby("customer_unique_id")["order_id"]
        .nunique()
        .rename("matched_order_count")
        .reset_index()
    )

    result = rfm.merge(
        counts,
        on="customer_unique_id",
        how="left",
        validate="one_to_one",
    )

    result["matched_order_count"] = (
        result["matched_order_count"]
        .fillna(0)
        .astype(int)
    )

    has_order_filters = bool(
        states
        or regions
        or reviews
        or missing_review
        or date_enabled
    )

    if has_order_filters:
        result = result[
            result["matched_order_count"] > 0
        ]

    # Áp dụng điều kiện ở cấp khách hàng.
    if search:
        result = result[
            result["customer_unique_id"]
            .astype("string")
            .str.contains(
                search,
                case=False,
                regex=False,
                na=False,
            )
        ]

    if segments:
        result = result[
            result["segment"].isin(segments)
        ]

    result = result.sort_values(
        "customer_unique_id"
    ).reset_index(drop=True)

    # ==========================================
    # MÔ TẢ ĐIỀU KIỆN XUẤT BÁO CÁO
    # ==========================================
    date_description = "Không giới hạn"

    if date_enabled:
        date_description = (
            f"{date_range[0].strftime('%d/%m/%Y')} "
            f"đến {date_range[1].strftime('%d/%m/%Y')}"
        )

    if missing_review:
        review_description = "Đơn chưa có điểm đánh giá"
    elif reviews:
        review_description = ", ".join(map(str, reviews))
    else:
        review_description = "Tất cả"

    filters = {
        "Phạm vi khách hàng": "Khách có trong bảng RFM",
        "Mã khách hàng chứa": search or "Không giới hạn",
        "Phân khúc RFM": ", ".join(segments) or "Tất cả",
        "Bang/đặc khu trên đơn": ", ".join(states) or "Tất cả",
        "Vùng trên đơn": ", ".join(regions) or "Tất cả",
        "Ngày đặt hàng": date_description,
        "Điểm đánh giá trên đơn": review_description,
        "Quy tắc lọc": (
            "Khách có ít nhất một đơn cùng thỏa mãn "
            "các điều kiện đơn hàng đã chọn"
            if has_order_filters
            else "Không giới hạn theo điều kiện đơn hàng"
        ),
        "RFM": "Giữ nguyên giá trị trong file nhóm bàn giao",
        "Thứ tự": "Mã khách hàng tăng dần",
    }

    # Đổi bộ lọc sẽ quay về trang 1.
    filter_signature = tuple(filters.items())

    if st.session_state.get("cus_filter_signature") != filter_signature:
        st.session_state["cus_page"] = 1
        st.session_state["cus_filter_signature"] = filter_signature

    st.write(
        f"**Tìm thấy {len(result):,} khách hàng phù hợp.**"
    )

    st.caption(
        "Mỗi khách xuất hiện một dòng. RFM không tính lại "
        "theo bộ lọc ngày. Số đơn phù hợp là chỉ số riêng "
        "được tính từ các đơn đáp ứng bộ lọc hiện tại."
    )

    if result.empty:
        st.info(
            "Không có khách hàng phù hợp. "
            "Hãy thay đổi hoặc xóa bộ lọc."
        )
        return

    # ==========================================
    # PHÂN TRANG
    # ==========================================
    page_size = 50
    total_pages = math.ceil(len(result) / page_size)

    current_page = int(
        st.session_state.get("cus_page", 1)
    )

    st.session_state["cus_page"] = max(
        1,
        min(current_page, total_pages),
    )

    page = st.number_input(
        "Trang hiện tại",
        min_value=1,
        max_value=total_pages,
        step=1,
        key="cus_page",
    )

    start_row = (int(page) - 1) * page_size
    end_row = min(start_row + page_size, len(result))

    labels = {
        "customer_unique_id": "Mã khách hàng",
        "recency": "Recency (ngày)",
        "frequency": "Frequency",
        "monetary": "Monetary (BRL)",
        "first_order": "Đơn đầu tiên",
        "last_order": "Đơn gần nhất",
        "r_score": "Điểm R",
        "f_score": "Điểm F",
        "m_score": "Điểm M",
        "rfm_segment_code": "Mã RFM",
        "segment": "Phân khúc",
        "matched_order_count": "Số đơn phù hợp bộ lọc",
    }

    st.dataframe(
        result.iloc[start_row:end_row].rename(columns=labels)
    )

    st.caption(
        f"Trang {int(page)}/{total_pages} · "
        f"Hiển thị khách {start_row + 1}–{end_row} "
        f"trên tổng {len(result):,} khách."
    )

    # ==========================================
    # XUẤT TOÀN BỘ KẾT QUẢ LỌC
    # ==========================================
    st.markdown("**Xuất báo cáo khách hàng**")

    st.caption(
        "CSV/Excel xuất toàn bộ kết quả, không chỉ trang hiện tại. "
        "PDF hiển thị tối đa 100 khách đầu theo mã tăng dần."
    )

    csv_col, excel_col, pdf_col = st.columns(3)

    with csv_col:
        st.download_button(
            label="Tải CSV",
            data=result.to_csv(
                index=False
            ).encode("utf-8-sig"),
            file_name="khach_hang_da_loc.csv",
            mime="text/csv",
            key="cus_csv",
        )

    with excel_col:
        render_excel_export(
            data=result,
            filters=filters,
            report_name="Khách hàng theo bộ lọc kết hợp",
            username=user["username"],
            file_name="khach_hang_da_loc.xlsx",
            key="cus_excel",
        )

    with pdf_col:
        render_pdf_export(
            data=result,
            filters=filters,
            title="BÁO CÁO KHÁCH HÀNG ĐÃ LỌC",
            username=user["username"],
            columns={
                "customer_unique_id": "Mã khách hàng",
                "recency": "Recency (ngày)",
                "frequency": "Frequency",
                "monetary": "Monetary (BRL)",
                "segment": "Phân khúc",
                "matched_order_count": "Số đơn phù hợp",
            },
            file_name="khach_hang_da_loc.pdf",
            key="cus_pdf",
        )
