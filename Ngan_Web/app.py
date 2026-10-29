from pathlib import Path

import pandas as pd
import streamlit as st

from auth import require_login, render_account_menu
from campaigns import render_campaigns
from customer_care import render_customer_care
from customer_detail import render_customer_detail
from customers import render_customers
from exports import render_excel_export
from pdf_export import render_pdf_export
from analytics_data import DATA_DIR
from analytics_pages import render_analytics, cached_data
from analytics_data import data_signature
from ui import load_style, page_header, metric_strip


# ==============================================
# 1. CẤU HÌNH TRANG
# ==============================================
st.set_page_config(
    page_title="Olist | Phân tích khách hàng",
    page_icon=str(Path(__file__).resolve().parent / "assets/olist-mark.svg"),
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent

ORDERS_PATH = DATA_DIR / "olist_powerbi_orders_master.csv"
RFM_PATH = DATA_DIR / "rfm_table.csv"
CSS_PATH = BASE_DIR / "style.css"


# ==============================================
# 2. GIAO DIỆN VÀ ĐĂNG NHẬP
# ==============================================
load_style()

current_user = require_login()
workspace = st.sidebar.radio('Không gian làm việc',['Dashboard & Machine Learning','Tra cứu & Chăm sóc'],key='workspace', format_func=lambda value: {'Dashboard & Machine Learning':'Tổng quan & phân tích', 'Tra cứu & Chăm sóc':'Khách hàng & chăm sóc'}[value])
render_account_menu(current_user)
if workspace == 'Dashboard & Machine Learning':
    page_header('Phân tích khách hàng Olist', 'Khám phá doanh số, hành vi mua sắm và cơ hội giữ chân khách hàng.')
    render_analytics()
    st.stop()


# ==============================================
# 3. BANNER
# ==============================================
page_header('Khách hàng & chăm sóc', 'Từ lịch sử mua hàng đến ghi chú, ưu tiên và chiến dịch giữ chân.')


# ==============================================
# 4. KIỂM TRA FILE DỮ LIỆU
# ==============================================
missing_files = [
    path.name
    for path in [ORDERS_PATH, RFM_PATH]
    if not path.is_file()
]

if missing_files:
    st.error(
        "Chưa tìm thấy file trong bộ dữ liệu BI: "
        + ", ".join(missing_files)
    )

    st.info(
        "Giữ thư mục tam_eda/handover_v3 cạnh Ngan_Web hoặc đặt OLIST_DATA_DIR theo hướng dẫn."
    )

    st.stop()


# ==============================================
# 5. ĐỌC VÀ KIỂM TRA DỮ LIỆU
# ==============================================
def load_data():
    tables = cached_data(data_signature())
    return tables['orders'], tables['rfm']


try:
    with st.spinner("Đang đọc dữ liệu..."):
        orders, rfm = load_data()
except Exception as error:
    st.error(f"Không đọc được dữ liệu: {error}")
    st.stop()


# ==============================================
# 6. HÀM HỖ TRỢ
# ==============================================
def format_number(value):
    return f"{value:,}".replace(",", ".")


def reset_order_filters():
    st.session_state["order_search"] = ""
    st.session_state["order_states"] = []
    st.session_state["order_statuses"] = []
    st.session_state["order_date_enabled"] = False
    st.session_state.pop("order_date_range", None)
    st.session_state["order_reviews"] = []
    st.session_state["order_missing_reviews"] = False


# Danh sách khách hàng dùng cho ghi chú và chiến dịch.
customer_ids = (
    orders["customer_unique_id"]
    .dropna()
    .unique()
    .tolist()
)


# ==============================================
# 7. TỔNG QUAN
# ==============================================
metric_strip([
    ('Tổng số đơn hàng', format_number(orders['order_id'].nunique()), 'Toàn bộ dữ liệu tổng hợp'),
    ('Khách hàng duy nhất', format_number(orders['customer_unique_id'].nunique()), 'Trong bảng đơn hàng'),
    ('Khách hàng có RFM', format_number(rfm['customer_unique_id'].nunique()), 'Snapshot RFM đã bàn giao'),
])
st.caption('Các chỉ số mô tả toàn bộ dữ liệu. Kết quả theo bộ lọc được hiển thị trong từng tab bên dưới.')



# ==============================================
# 8. ĐIỀU HƯỚNG
# ==============================================
(
    tab_orders,
    tab_customers,
    tab_detail,
    tab_care,
    tab_campaigns,
) = st.tabs(
    [
        "Tra cứu đơn hàng",
        "Khách hàng RFM",
        "Chi tiết khách hàng",
        "Chăm sóc khách hàng",
        "Chiến dịch giữ chân",
    ]
)


# ==============================================
# 9. TRA CỨU ĐƠN HÀNG
# ==============================================
with tab_orders:
    st.subheader("Khám phá đơn hàng")

    st.caption(
        "Kết hợp mã đơn, bang/đặc khu, trạng thái, "
        "ngày đặt hàng và điểm đánh giá."
    )

    with st.container(border=True, key='order_search_panel'):
        search_col, reset_col = st.columns([4, 1], vertical_alignment='bottom')
        with search_col:
            search_order = st.text_input(
                "Mã đơn hàng",
                placeholder="Nhập toàn bộ hoặc một phần order_id...",
                key="order_search",
            ).strip()
        with reset_col:
            st.button('Đặt lại bộ lọc', on_click=reset_order_filters, key='reset_orders', width='stretch')
    with st.expander('Bộ lọc nâng cao · Bang, trạng thái, ngày và đánh giá'):
        state_options = sorted(
            orders["customer_state"]
            .dropna()
            .unique()
            .tolist()
        )

        status_options = sorted(
            orders["order_status"]
            .dropna()
            .unique()
            .tolist()
        )

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:
            selected_states = st.multiselect(
                "Bang/đặc khu của khách hàng",
                options=state_options,
                help="Để trống để xem tất cả.",
                key="order_states",
            placeholder="Tất cả các bang",
            )

        with filter_col2:
            selected_statuses = st.multiselect(
                "Trạng thái đơn hàng",
                options=status_options,
                help="Để trống để xem tất cả.",
                key="order_statuses",
            placeholder="Tất cả trạng thái",
            )

        # ------------------------------------------
        # Bộ lọc thời gian
        # ------------------------------------------
        valid_dates = orders[
            "order_purchase_timestamp"
        ].dropna()

        selected_dates = None
        date_filter_ready = True

        if not valid_dates.empty:
            min_date = valid_dates.min().date()
            max_date = valid_dates.max().date()

            enable_date_filter = st.checkbox(
                "Lọc theo ngày đặt hàng",
                key="order_date_enabled",
            )

            if enable_date_filter:
                selected_dates = st.date_input(
                    "Ngày bắt đầu và ngày kết thúc",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date,
                    key="order_date_range",
                )

                date_filter_ready = (
                    isinstance(selected_dates, (tuple, list))
                    and len(selected_dates) == 2
                )

                if date_filter_ready:
                    date_filter_ready = (
                        selected_dates[0] <= selected_dates[1]
                    )
        else:
            st.info(
                "Không có ngày đặt hàng hợp lệ để lọc thời gian."
            )

        # ------------------------------------------
        # Bộ lọc đánh giá
        # ------------------------------------------
        only_missing_reviews = st.checkbox(
            "Chỉ xem đơn chưa có điểm đánh giá",
            key="order_missing_reviews",
        )

        selected_reviews = st.multiselect(
            "Điểm đánh giá",
            options=sorted(orders.review_score.dropna().unique().tolist()),
            help="Để trống để không giới hạn điểm.",
            key="order_reviews",
        placeholder="Tất cả điểm đánh giá",
            disabled=only_missing_reviews,
        )

    active_filters = []
    if selected_states:
        active_filters.append('Bang: ' + ', '.join(selected_states))
    if selected_statuses:
        active_filters.append('Trạng thái: ' + ', '.join(selected_statuses))
    if selected_dates is not None and date_filter_ready:
        active_filters.append(f'Ngày: {selected_dates[0]:%d/%m/%Y} – {selected_dates[1]:%d/%m/%Y}')
    if only_missing_reviews:
        active_filters.append('Chưa có đánh giá')
    elif selected_reviews:
        active_filters.append('Điểm: ' + ', '.join(map(str, selected_reviews)))
    if active_filters:
        st.caption('Đang áp dụng · ' + ' · '.join(active_filters))

    # ------------------------------------------
    # Áp dụng điều kiện
    # ------------------------------------------
    filtered_orders = orders.copy()

    if search_order:
        filtered_orders = filtered_orders.loc[
            filtered_orders["order_id"].str.contains(
                search_order,
                case=False,
                regex=False,
                na=False,
            )
        ]

    if selected_states:
        filtered_orders = filtered_orders.loc[
            filtered_orders["customer_state"].isin(
                selected_states
            )
        ]

    if selected_statuses:
        filtered_orders = filtered_orders.loc[
            filtered_orders["order_status"].isin(
                selected_statuses
            )
        ]

    if selected_dates is not None and date_filter_ready:
        start_date, end_date = selected_dates

        start_time = pd.Timestamp(start_date)
        end_time = (
            pd.Timestamp(end_date)
            + pd.Timedelta(days=1)
        )

        filtered_orders = filtered_orders.loc[
            (
                filtered_orders["order_purchase_timestamp"]
                >= start_time
            )
            & (
                filtered_orders["order_purchase_timestamp"]
                < end_time
            )
        ]

    if only_missing_reviews:
        filtered_orders = filtered_orders.loc[
            filtered_orders["review_score"].isna()
        ]
    elif selected_reviews:
        filtered_orders = filtered_orders.loc[
            filtered_orders["review_score"].isin(
                selected_reviews
            )
        ]

    # ------------------------------------------
    # Hiển thị kết quả
    # ------------------------------------------
    if not date_filter_ready:
        st.info(
            "Hãy chọn đủ ngày bắt đầu và ngày kết thúc hợp lệ "
            "để xem hoặc xuất kết quả."
        )

    elif filtered_orders.empty:
        st.write("**Kết quả: 0 đơn hàng phù hợp.**")
        st.info(
            "Hãy đổi điều kiện hoặc bấm Xóa bộ lọc đơn hàng."
        )

    else:
        st.markdown(
            f"**Kết quả: {format_number(len(filtered_orders))} "
            "đơn hàng phù hợp.**"
        )

        display_columns = [
            "order_id",
            "order_purchase_timestamp",
            "order_status",
            "customer_unique_id",
            "customer_city",
            "customer_state",
            "region_name",
            "total_products_value",
            "total_freight_value",
            "review_score",
        ]

        display_columns = [
            column
            for column in display_columns
            if column in filtered_orders.columns
        ]

        column_labels = {
            "order_id": "Mã đơn hàng",
            "order_purchase_timestamp": "Thời điểm đặt",
            "order_status": "Trạng thái",
            "customer_unique_id": "Mã khách hàng",
            "customer_city": "Thành phố",
            "customer_state": "Bang/đặc khu",
            "region_name": "Vùng",
            "total_products_value": "Giá trị hàng hóa (BRL)",
            "total_freight_value": "Phí vận chuyển (BRL)",
            "review_score": "Điểm đánh giá",
        }

        st.dataframe(
            filtered_orders[display_columns]
            .head(100)
            .rename(columns=column_labels),
            width="stretch",
            hide_index=True,
        )

        st.caption(
            "Bảng xem trước tối đa 100 dòng. "
            "CSV/Excel chứa toàn bộ kết quả sau lọc; "
            "PDF trình bày tối đa 100 dòng đầu."
        )

        # --------------------------------------
        # Thông tin bộ lọc cho báo cáo
        # --------------------------------------
        date_description = "Không giới hạn"

        if selected_dates is not None and date_filter_ready:
            date_description = (
                f"{selected_dates[0].strftime('%d/%m/%Y')} "
                f"đến {selected_dates[1].strftime('%d/%m/%Y')}"
            )

        if only_missing_reviews:
            review_description = (
                "Chỉ đơn chưa có điểm đánh giá"
            )
        elif selected_reviews:
            review_description = ", ".join(
                str(score) for score in selected_reviews
            )
        else:
            review_description = "Tất cả"

        order_filters = {
            "Mã đơn chứa": (
                search_order or "Không giới hạn"
            ),
            "Bang/đặc khu": (
                ", ".join(selected_states)
                if selected_states
                else "Tất cả"
            ),
            "Trạng thái đơn": (
                ", ".join(selected_statuses)
                if selected_statuses
                else "Tất cả"
            ),
            "Ngày đặt hàng": date_description,
            "Điểm đánh giá": review_description,
        }

        # --------------------------------------
        # Xuất CSV / Excel / PDF
        # --------------------------------------
        st.markdown("**Xuất báo cáo**")

        csv_col, excel_col, pdf_col = st.columns(3)

        with csv_col:
            st.download_button(
                label="Tải CSV",
                data=filtered_orders.to_csv(
                    index=False
                ).encode("utf-8-sig"),
                file_name="don_hang_da_loc.csv",
                mime="text/csv",
                key="download_orders",
            )

        with excel_col:
            render_excel_export(
                data=filtered_orders,
                filters=order_filters,
                report_name="Danh sách đơn hàng đã lọc",
                username=current_user["username"],
                file_name="don_hang_da_loc.xlsx",
                key="orders_excel",
            )

        with pdf_col:
            render_pdf_export(
                data=filtered_orders,
                filters=order_filters,
                title="BÁO CÁO ĐƠN HÀNG ĐÃ LỌC",
                username=current_user["username"],
                columns={
                    "order_id": "Mã đơn hàng",
                    "order_purchase_timestamp": "Ngày đặt",
                    "order_status": "Trạng thái",
                    "customer_state": "Bang",
                    "total_products_value": (
                        "Giá trị hàng hóa (BRL)"
                    ),
                    "review_score": "Điểm đánh giá",
                },
                file_name="bao_cao_don_hang.pdf",
                key="orders_pdf",
            )


# ==============================================
# 10. KHÁCH HÀNG VÀ BỘ LỌC KẾT HỢP
# ==============================================
with tab_customers:
    st.caption(
        "Phân khúc hiện tại lấy từ bảng RFM của nhóm. "
        "Đây chưa phải kết quả K-Means hoặc xác suất "
        "không mua lại."
    )

    render_customers(
        orders=orders,
        rfm=rfm,
        user=current_user,
    )


# ==============================================
# 11. CHI TIẾT KHÁCH HÀNG
# ==============================================
with tab_detail:
    st.caption(
        "Copy mã customer_unique_id từ danh sách khách hàng "
        "rồi dán vào ô tra cứu. Màn hình này hiển thị toàn bộ "
        "lịch sử của khách trong bộ processed, độc lập với "
        "bộ lọc ở các tab khác."
    )

    render_customer_detail()


# ==============================================
# 12. CHĂM SÓC KHÁCH HÀNG
# ==============================================
with tab_care:
    render_customer_care(
        current_user,
        customer_ids,
    )


# ==============================================
# 13. CHIẾN DỊCH GIỮ CHÂN
# ==============================================
with tab_campaigns:
    render_campaigns(
        user=current_user,
        customer_ids=customer_ids,
    )


# ==============================================
# 14. CHÂN TRANG
# ==============================================
footer_html = (
    '<div class="app-footer">'
    '<strong>Olist Customer Analytics</strong>'
    '<br>'
    'Đồ án phân tích dữ liệu lớn · Dữ liệu Brazil 2016–2018'
    '</div>'
)

st.markdown(footer_html, unsafe_allow_html=True)
