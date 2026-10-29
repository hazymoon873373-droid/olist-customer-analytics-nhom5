"""Authenticated analytics screens backed by the group's verified handover."""
from pathlib import Path
import pandas as pd
import streamlit as st
from analytics_data import load_group_data, data_signature, customer_snapshot, filter_orders, kpis, DATA_DIR
from ui import metric_strip, render_chart


@st.cache_data(show_spinner=False)
def cached_data(signature, loader_version=2):
    return load_group_data()


def render_dashboard(tables):
    orders = tables['orders']
    left, right = st.columns([2, 1])
    dates = left.date_input('Khoảng ngày mua hàng', value=(orders.order_purchase_timestamp.min().date(), orders.order_purchase_timestamp.max().date()), key='bi_dates')
    states = right.multiselect('Bang của khách hàng', sorted(orders.customer_state.dropna().unique()), key='bi_states', placeholder='Tất cả các bang')
    if len(dates) != 2:
        st.info('Chọn đủ ngày bắt đầu và ngày kết thúc để xem số liệu.')
        return
    selected = filter_orders(orders, *dates, states)
    k = kpis(selected)
    metric_strip([
        ('GMV sản phẩm · BRL', f"{k['gmv']:,.2f}", 'Đơn đã giao, không gồm cước'),
        ('Đơn hàng', f"{k['orders']:,}", 'Tất cả trạng thái trong bộ lọc'),
        ('Khách hàng', f"{k['customers']:,}", 'customer_unique_id duy nhất'),
        ('Giá trị đơn TB · BRL', f"{k['aov']:,.2f}" if k['aov'] is not None else '—', 'AOV của đơn đã giao'),
    ])
    delivered = selected.loc[selected.order_status.eq('delivered')].copy()
    trend, delivery = st.columns([2, 1], gap='medium')
    with trend:
        st.subheader('Giá trị sản phẩm theo tháng')
        if delivered.empty:
            st.info('Không có đơn đã giao trong phạm vi này.')
        else:
            monthly = delivered.set_index('order_purchase_timestamp').resample('MS').total_products_value.sum().rename('gmv').reset_index()
            render_chart(monthly, 'order_purchase_timestamp', 'gmv', 'Tháng mua', 'BRL', temporal=True)
    with delivery:
        st.subheader('Trải nghiệm giao hàng')
        st.metric('Tỷ lệ đơn giao trễ', f"{k['late_rate']:.2%}" if k['late_rate'] is not None else '—')
        st.metric('Trung vị thời gian giao · ngày', f"{k['median_days']:.2f}" if k['median_days'] is not None else '—')
        st.caption(f"Mẫu số: {k['valid_deliveries']:,} đơn đủ điều kiện KPI giao hàng. Ngày thiếu hoặc thời gian sai không tham gia KPI này.")
    if not delivered.empty:
        left, right = st.columns(2, gap='medium')
        with left:
            st.subheader('10 bang có GMV cao nhất')
            ranked = delivered.groupby('customer_state').total_products_value.sum().nlargest(10).reset_index()
            render_chart(ranked, 'customer_state', 'total_products_value', 'Bang', 'GMV · BRL')
        with right:
            st.subheader('10 danh mục có GMV cao nhất')
            item = tables['items'].loc[tables['items'].order_id.isin(delivered.order_id)]
            ranked = item.groupby('category_english').price.sum().nlargest(10).reset_index()
            render_chart(ranked, 'category_english', 'price', 'Danh mục', 'GMV · BRL')
    st.download_button('Tải các đơn theo bộ lọc · CSV', selected.to_csv(index=False).encode('utf-8-sig'), 'dashboard_orders.csv', key='bi_export')
    with st.expander('Cohort retention · snapshot đến hết tháng 08/2018'):
        retention = tables['retention']
        st.dataframe(retention.style.format('{:.2%}', na_rep='Chưa quan sát'), width='stretch')
        st.caption('Kỳ đã quan sát không mua lại là 0%; ô trống là kỳ tương lai. Snapshot cố định, không đổi theo bộ lọc đơn phía trên.')


def render_customer_ml(tables):
    st.subheader('Phân khúc & nguy cơ không mua lại')
    st.caption('RFM: 30/08/2018 · Snapshot ML: 31/08/2018 · Cửa sổ dự báo: 180 ngày')
    customers = customer_snapshot(tables)
    scored = int(customers.ml_status.eq('Được chấm').sum())
    a, b, c = st.columns(3)
    a.metric('Toàn bộ khách', f'{len(customers):,}')
    b.metric('Có điểm mô hình', f'{scored:,}')
    c.metric('Chưa chấm / ngoài snapshot', f'{len(customers) - scored:,}')
    st.progress(scored / len(customers), text=f'Độ phủ điểm mô hình: {scored / len(customers):.2%} khách trong toàn bộ dữ liệu')
    st.warning('Điểm ML thử nghiệm, chưa hiệu chuẩn. Khách chưa có điểm được giữ trống; không mặc định là 0% rủi ro. Không kết luận khách chắc chắn rời bỏ.')
    a, b, c = st.columns([2, 1, 1])
    query = a.text_input('Tìm mã khách', key='ml_search').strip()
    status = b.multiselect('Trạng thái chấm điểm', sorted(customers.ml_status.unique()), key='ml_status')
    clusters = c.multiselect('Cụm K-Means', sorted(customers.kmeans_cluster.dropna().unique()), key='ml_clusters')
    result = customers
    if query:
        result = result.loc[result.customer_unique_id.str.contains(query, regex=False, case=False)]
    if status:
        result = result.loc[result.ml_status.isin(status)]
    if clusters:
        result = result.loc[result.kmeans_cluster.isin(clusters)]
    result = result.sort_values(['ml_churn_probability', 'customer_unique_id'], ascending=[False, True], na_position='last')
    st.caption(f'{len(result):,} khách phù hợp · Hiển thị tối đa 200 dòng · Xuất CSV bao gồm toàn bộ kết quả lọc')
    visible = ['customer_unique_id', 'customer_state', 'segment', 'kmeans_segment', 'ml_status', 'ml_churn_probability']
    st.dataframe(result[visible].head(200), hide_index=True, width='stretch', column_config={
        'customer_unique_id': st.column_config.TextColumn('Mã khách', width='large'),
        'customer_state': 'Bang', 'segment': 'Nhóm RFM', 'kmeans_segment': 'Cụm K-Means',
        'ml_status': 'Trạng thái điểm', 'ml_churn_probability': st.column_config.NumberColumn('Điểm không mua lại', format='%.4f'),
    })
    st.download_button('Tải toàn bộ khách theo bộ lọc · CSV', result.to_csv(index=False).encode('utf-8-sig'), 'customers_ml.csv', key='ml_export')
    st.subheader('Phân bố cụm trong kết quả lọc')
    grouped = result.groupby('kmeans_segment').size().rename('customers').reset_index()
    if grouped.empty:
        st.info('Không có khách có cụm K-Means trong kết quả lọc này.')
    else:
        render_chart(grouped, 'kmeans_segment', 'customers', 'Cụm', 'Số khách')
    st.caption('6 nhóm RFM theo quy tắc khác 4 cụm K-Means. Bộ lọc chỉ chọn dữ liệu đã tính sẵn, không huấn luyện lại mô hình.')


def render_evaluation(tables):
    m = tables['metrics']
    st.subheader('Đánh giá test lịch sử')
    st.caption(f"{len(tables['ml_test']):,} khách · Cutoff: 01/03/2018 · Horizon: 180 ngày · Không dùng snapshot BI để tính test")
    st.warning('RF / ngưỡng 0,5 dự đoán toàn bộ test là không mua lại. Recall mua lại bằng 0; temporal validation chưa đủ điều kiện. Không điều chỉnh mô hình theo tập test đã xem.')
    a, b, c = st.columns(3)
    a.metric('ROC-AUC · không mua lại', f"{m['roc_auc_churn_1']:.4f}")
    b.metric('AP · mua lại', f"{m['average_precision_repurchase_0']:.4f}")
    c.metric('Top-decile lift · không mua lại', f"{m['top_decile_lift_churn_1']:.4f}")
    st.caption('AP là Average Precision. Lift xếp theo churn_probability. Observation end còn giả định; train_in_sample không phải đánh giá độc lập.')
    left, right = st.columns(2)
    with left:
        st.subheader('Kết quả theo decile')
        test = tables['ml_test']
        st.dataframe(test.groupby('score_decile').agg(customers=('customer_unique_id', 'size'), repurchased=('repurchased_true', 'sum'), avg_churn_score=('churn_probability', 'mean')), width='stretch')
    with right:
        st.subheader('Ma trận nhầm lẫn')
        st.dataframe(tables['confusion'], hide_index=True, width='stretch')
    st.subheader('15 đặc trưng quan trọng nhất')
    render_chart(tables['importance'].head(15), 'feature', 'importance', 'Đặc trưng', 'Importance', height=320)
    st.caption('Feature importance mô tả mô hình, không chứng minh quan hệ nhân quả.')


def render_powerbi():
    st.subheader('Báo cáo Power BI · 5 trang')
    st.write('Báo cáo gốc của Tâm và dashboard web sử dụng cùng bộ dữ liệu BI đã chốt. Tải file để mở bằng Power BI Desktop.')
    pbix = Path(__file__).resolve().parents[1] / 'tam_eda/POWERBI_Olist_Chot.pbix'
    if pbix.is_file():
        st.download_button('Tải báo cáo Power BI', pbix.read_bytes(), pbix.name, key='pbix_download')
    else:
        st.info('Chưa có file PBIX trong bản cài này. Dashboard web vẫn hoạt động với bộ dữ liệu bàn giao.')
    st.caption('Trước Refresh trên máy nhận, đặt DataRoot về thư mục handover_v3. File PBIX không tự trở thành báo cáo nhúng trực tuyến khi push Git.')


def render_analytics():
    try:
        with st.spinner('Đang đối soát và đọc dữ liệu BI/ML…'):
            tables = cached_data(data_signature())
    except (OSError, ValueError, KeyError) as error:
        st.error(f'Không thể nạp bộ dữ liệu BI/ML: {error}')
        if st.button('Thử đọc lại dữ liệu'):
            cached_data.clear()
            st.rerun()
        return
    dashboard, ml, evaluation, powerbi = st.tabs(['Dashboard tương tác', 'Khách hàng & ML', 'Đánh giá mô hình', 'Power BI'])
    with dashboard:
        render_dashboard(tables)
    with ml:
        render_customer_ml(tables)
    with evaluation:
        render_evaluation(tables)
    with powerbi:
        render_powerbi()
