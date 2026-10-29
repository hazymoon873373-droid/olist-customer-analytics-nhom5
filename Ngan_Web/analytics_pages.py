"""Authenticated screens backed by the group's verified BI and ML handover."""
from pathlib import Path
import pandas as pd
import streamlit as st
from analytics_data import load_group_data, data_signature, customer_snapshot, filter_orders, kpis
from ui import metric_strip, render_chart, number, section_heading, insight


@st.cache_data(show_spinner=False)
def cached_data(signature, loader_version=2):
    return load_group_data()


def reset_dashboard_filters(start, end):
    st.session_state['bi_dates'] = (start, end)
    st.session_state['bi_states'] = []


def reset_ml_filters():
    st.session_state['ml_search'] = ''
    st.session_state['ml_status'] = []
    st.session_state['ml_clusters'] = []


def render_dashboard(tables):
    orders = tables['orders']
    first, last = orders.order_purchase_timestamp.min().date(), orders.order_purchase_timestamp.max().date()
    with st.container(border=True, key='filter_bar'):
        left, right, action = st.columns([1.3, 1, .55], gap='medium', vertical_alignment='bottom')
        dates = left.date_input('Khoảng ngày mua hàng', value=(first, last), key='bi_dates', format='DD/MM/YYYY')
        states = right.multiselect('Bang của khách hàng', sorted(orders.customer_state.dropna().unique()), key='bi_states', placeholder='Tất cả các bang')
        action.button('Đặt lại bộ lọc', on_click=reset_dashboard_filters, args=(first, last), key='bi_reset', width='stretch')
    if len(dates) != 2:
        st.info('Chọn đủ ngày bắt đầu và ngày kết thúc để xem số liệu.')
        return
    selected = filter_orders(orders, *dates, states)
    k = kpis(selected)
    metric_strip([
        ('GMV sản phẩm · BRL', number(k['gmv'], 2), 'Đơn đã giao · không gồm cước'),
        ('Đơn hàng', number(k['orders']), 'Tất cả trạng thái trong bộ lọc'),
        ('Khách hàng', number(k['customers']), 'Mã khách hàng duy nhất'),
        ('Giá trị đơn trung bình · BRL', number(k['aov'], 2), 'Tính trên các đơn đã giao'),
    ])
    delivered = selected.loc[selected.order_status.eq('delivered')].copy()
    if selected.empty:
        st.info('Không có đơn hàng trong phạm vi đã chọn. Thử đổi ngày hoặc đặt lại bộ lọc.')
    else:
        period = f"{dates[0]:%d/%m/%Y} – {dates[1]:%d/%m/%Y}"
        insight(f"{number(k['orders'])} đơn hàng trong phạm vi phân tích", f"{period} · {number(selected.customer_state.nunique())} bang · Các biểu đồ và file CSV bên dưới cùng áp dụng bộ lọc này.")
    trend, delivery = st.columns([1.9, 1], gap='medium')
    with trend, st.container(border=True, key='gmv_panel'):
        section_heading('Doanh số sản phẩm theo tháng', 'GMV của đơn đã giao · BRL')
        if delivered.empty:
            st.info('Không có đơn đã giao trong phạm vi này.')
        else:
            monthly = delivered.set_index('order_purchase_timestamp').resample('MS').total_products_value.sum().rename('gmv').reset_index()
            render_chart(monthly, 'order_purchase_timestamp', 'gmv', 'Tháng mua', 'BRL', temporal=True, height=220)
    with delivery, st.container(border=True, key='delivery_panel'):
        section_heading('Trải nghiệm giao hàng', 'Chỉ tính các đơn đủ điều kiện KPI')
        st.metric('Tỷ lệ đơn giao trễ', number(k['late_rate'] * 100, 2) + '%' if k['late_rate'] is not None else '—')
        st.metric('Trung vị thời gian giao · ngày', number(k['median_days'], 2))
        st.caption(f"Mẫu số: {number(k['valid_deliveries'])} đơn valid_delay_kpi=true. Loại ngày thiếu hoặc thời gian sai khỏi KPI này.")
    if not delivered.empty:
        left, right = st.columns(2, gap='medium')
        with left, st.container(border=True, key='states_panel'):
            section_heading('Thị trường đóng góp nhiều nhất', '10 bang có GMV sản phẩm cao nhất')
            ranked = delivered.groupby('customer_state').total_products_value.sum().nlargest(10).reset_index()
            render_chart(ranked, 'customer_state', 'total_products_value', 'Bang', 'GMV · BRL', height=235)
        with right, st.container(border=True, key='categories_panel'):
            section_heading('Danh mục được mua nhiều giá trị nhất', '10 danh mục theo GMV sản phẩm, không phải số lượng')
            item = tables['items'].loc[tables['items'].order_id.isin(delivered.order_id)]
            ranked = item.groupby('category_english').price.sum().nlargest(10).reset_index()
            render_chart(ranked, 'category_english', 'price', 'Danh mục', 'GMV · BRL', height=235)
    st.download_button('Tải dữ liệu đang xem · CSV', selected.to_csv(index=False).encode('utf-8-sig'), 'dashboard_orders.csv', key='bi_export')
    with st.expander('Khách hàng quay lại theo tháng · Cohort retention'):
        retention = tables['retention']
        heatmap = retention.rename_axis('CohortMonth').reset_index().melt(id_vars='CohortMonth', var_name='month_index', value_name='retention').dropna()
        heatmap['month_index'] = pd.to_numeric(heatmap['month_index'])
        heatmap = heatmap.loc[heatmap.month_index.gt(0)]
        st.vega_lite_chart(heatmap, {
            'mark': {'type': 'rect', 'cornerRadius': 2},
            'encoding': {
                'x': {'field': 'month_index', 'type': 'ordinal', 'title': 'Tháng kể từ lần mua đầu', 'sort': 'ascending'},
                'y': {'field': 'CohortMonth', 'type': 'ordinal', 'title': 'Tháng mua đầu'},
                'color': {'field': 'retention', 'type': 'quantitative', 'title': 'Tỷ lệ quay lại', 'scale': {'zero': True, 'range': ['#edf5f6', '#1b6c80']}, 'legend': {'format': '.1%'}},
                'tooltip': [{'field': 'CohortMonth', 'title': 'Tháng mua đầu'}, {'field': 'month_index', 'title': 'Tháng tiếp theo'}, {'field': 'retention', 'title': 'Tỷ lệ quay lại', 'format': '.2%'}],
            },
            'height': 400,
            'config': {'font': 'IBM Plex Sans', 'view': {'stroke': None}},
        }, width='stretch', theme=None)
        st.caption('Snapshot đến hết 08/2018, độc lập với bộ lọc đơn phía trên. Bản đồ nhiệt hiển thị từ tháng 1, ẩn tháng 0 luôn là 100%. Kỳ đã quan sát không mua lại là 0%; ô trống là kỳ chưa quan sát. Bảng bên dưới giữ đầy đủ các tháng.')
        st.dataframe(retention.style.format('{:.2%}', na_rep='Chưa quan sát'), width='stretch')


def render_customer_ml(tables):
    section_heading('Phân khúc & nguy cơ không mua lại', 'RFM: 30/08/2018 · Snapshot ML: 31/08/2018 · Cửa sổ dự báo: 180 ngày')
    customers = customer_snapshot(tables)
    scored = int(customers.ml_status.eq('Được chấm').sum())
    unscored = int(customers.ml_status.eq('Chưa đủ điều kiện').sum())
    outside = int(customers.ml_status.eq('Ngoài snapshot').sum())
    metric_strip([
        ('Toàn bộ khách hàng', number(len(customers)), 'Tổng thể trong dữ liệu đơn hàng'),
        ('Có điểm mô hình', number(scored), 'Điểm thử nghiệm, chưa hiệu chuẩn'),
        ('Chưa chấm / ngoài snapshot', number(len(customers) - scored), f'{number(unscored)} chưa đủ điều kiện · {number(outside)} ngoài snapshot'),
    ])
    with st.container(border=True, key='coverage_panel'):
        section_heading('Đọc điểm ML đúng phạm vi', f'{number(scored)} trên {number(len(customers))} khách có điểm mô hình')
        st.progress(scored / len(customers), text=f'Độ phủ điểm mô hình: {number(scored / len(customers) * 100, 2)}%')
        st.caption('Khách chưa có điểm được giữ trống; không mặc định là 0% rủi ro. Điểm không phải kết luận khách chắc chắn rời bỏ.')
    with st.container(border=True, key='ml_filters'):
        a, b, c, reset = st.columns([1.4, 1, 1, .5], vertical_alignment='bottom')
        query = a.text_input('Tìm mã khách', key='ml_search', placeholder='Nhập một phần mã khách…').strip()
        status = b.multiselect('Trạng thái chấm điểm', sorted(customers.ml_status.unique()), key='ml_status', placeholder='Tất cả trạng thái')
        clusters = c.multiselect('Cụm K-Means', sorted(customers.kmeans_cluster.dropna().unique()), key='ml_clusters', placeholder='Tất cả cụm')
        reset.button('Đặt lại', on_click=reset_ml_filters, key='ml_reset', width='stretch')
    result = customers
    if query:
        result = result.loc[result.customer_unique_id.str.contains(query, regex=False, case=False)]
    if status:
        result = result.loc[result.ml_status.isin(status)]
    if clusters:
        result = result.loc[result.kmeans_cluster.isin(clusters)]
    result = result.sort_values(['ml_churn_probability', 'customer_unique_id'], ascending=[False, True], na_position='last')
    with st.container(border=True, key='customer_results'):
        section_heading('Danh sách khách hàng', f'{number(len(result))} khách phù hợp · Hiển thị tối đa 200 dòng · CSV chứa toàn bộ kết quả lọc')
        visible = ['customer_unique_id', 'customer_state', 'segment', 'kmeans_segment', 'ml_status', 'ml_churn_probability']
        st.dataframe(result[visible].head(200), hide_index=True, width='stretch', height=350, column_config={
            'customer_unique_id': st.column_config.TextColumn('Mã khách', width='large'),
            'customer_state': 'Bang', 'segment': 'Nhóm RFM', 'kmeans_segment': 'Cụm K-Means',
            'ml_status': 'Trạng thái điểm', 'ml_churn_probability': st.column_config.NumberColumn('Điểm không mua lại', format='%.4f'),
        })
        st.download_button('Tải danh sách khách · CSV', result.to_csv(index=False).encode('utf-8-sig'), 'customers_ml.csv', key='ml_export')
    with st.container(border=True, key='clusters_panel'):
        section_heading('Phân bố cụm khách hàng', '6 nhóm RFM theo quy tắc khác 4 cụm K-Means · Biểu đồ theo kết quả lọc hiện tại')
        grouped = result.groupby('kmeans_segment').size().rename('customers').reset_index()
        if grouped.empty:
            st.info('Không có khách có cụm K-Means trong kết quả lọc này.')
        else:
            render_chart(grouped, 'kmeans_segment', 'customers', 'Cụm', 'Số khách', height=170, tooltip_format=',.0f')
        st.caption('Bộ lọc chỉ chọn kết quả đã tính sẵn, không huấn luyện lại mô hình.')


def render_evaluation(tables):
    m = tables['metrics']
    section_heading('Mô hình hoạt động đến đâu?', f"{number(len(tables['ml_test']))} khách trên tập test lịch sử · Cutoff: 01/03/2018 · Cửa sổ 180 ngày")
    st.warning('RF tại ngưỡng 0,5 dự đoán toàn bộ test là không mua lại; recall mua lại bằng 0. Temporal validation chưa đủ điều kiện. Không điều chỉnh mô hình theo tập test đã xem.')
    metric_strip([
        ('ROC-AUC · không mua lại', number(m['roc_auc_churn_1'], 4), 'Khả năng phân biệt trên tập test'),
        ('AP · mua lại', number(m['average_precision_repurchase_0'], 4), 'Average Precision cho nhóm mua lại'),
        ('Top-decile lift · không mua lại', number(m['top_decile_lift_churn_1'], 4), '10% có điểm không mua lại cao nhất'),
    ])
    test = tables['ml_test']
    deciles = test.groupby('score_decile').agg(customers=('customer_unique_id', 'size'), repurchased=('repurchased_true', 'sum'), avg_churn_score=('churn_probability', 'mean'))
    left, right = st.columns(2)
    with left, st.container(border=True, key='decile_panel'):
        section_heading('Khách mua lại theo nhóm điểm', 'Số khách thực tế mua lại trong từng decile trên tập test')
        plot = deciles.reset_index()
        plot['decile_label'] = 'Decile ' + plot.score_decile.astype(str)
        render_chart(plot, 'decile_label', 'repurchased', 'Nhóm điểm', 'Khách có mua lại', height=220, value_format=',.0f', tooltip_format=',.0f', category_sort=plot.decile_label.tolist())
    with right, st.container(border=True, key='confusion_panel'):
        section_heading('Ma trận nhầm lẫn', 'Hàng: thực tế · Cột: dự đoán · Đơn vị: khách hàng')
        matrix = tables['confusion'].set_index(tables['confusion'].columns[0])
        tp = int(matrix.loc['actual_return_0', 'predicted_return_0'])
        fn = int(matrix.loc['actual_return_0', 'predicted_no_repurchase_1'])
        fp = int(matrix.loc['actual_no_repurchase_1', 'predicted_return_0'])
        tn = int(matrix.loc['actual_no_repurchase_1', 'predicted_no_repurchase_1'])
        st.markdown(f'<table class="confusion-table"><thead><tr><th scope="col">Thực tế / Dự đoán</th><th scope="col">Mua lại</th><th scope="col">Không mua lại</th></tr></thead><tbody><tr><th scope="row">Mua lại</th><td>{number(tp)}</td><td class="matrix-miss">{number(fn)}</td></tr><tr><th scope="row">Không mua lại</th><td>{number(fp)}</td><td class="matrix-correct">{number(tn)}</td></tr></tbody></table>', unsafe_allow_html=True)
        st.caption(f'{number(tp + fn)} khách thực tế mua lại; mô hình nhận diện {number(tp)} khách tại ngưỡng 0,5.')
    with st.expander('Xem bảng chi tiết theo decile'):
        st.dataframe(deciles, width='stretch', column_config={'score_decile':'Decile', 'customers':'Số khách', 'repurchased':'Có mua lại', 'avg_churn_score':st.column_config.NumberColumn('Điểm TB',format='%.4f')})
    with st.container(border=True, key='importance_panel'):
        section_heading('Điều gì ảnh hưởng đến mô hình?', '15 đặc trưng quan trọng nhất · Tỷ trọng quan trọng, không phải mức tác động nhân quả')
        render_chart(tables['importance'].head(15), 'feature', 'importance', 'Đặc trưng', 'Mức độ quan trọng', height=360, value_format='.0%', tooltip_format='.2%')
    with st.expander('Cách đọc và giới hạn đánh giá'):
        st.write('AP là Average Precision. Lift xếp theo churn_probability. Observation end còn giả định; train_in_sample không phải đánh giá độc lập. Feature importance không chứng minh quan hệ nhân quả. Tập test lịch sử tách khỏi snapshot khách hàng BI.')


def render_powerbi():
    with st.container(border=True, key='powerbi_file_panel'):
        st.markdown('<div class="report-file"><span class="file-extension">PBIX</span><div><h3>Báo cáo Power BI · 5 trang</h3><p>Tổng quan, khách hàng, sản phẩm, giao hàng và phân khúc.</p><p>Báo cáo của Tâm dùng cùng bộ dữ liệu BI đã chốt trên website.</p></div></div>', unsafe_allow_html=True)
        pbix = Path(__file__).resolve().parents[1] / 'tam_eda/POWERBI_Olist_Chot.pbix'
        if not pbix.is_file():
            st.error('Chưa tìm thấy file báo cáo Power BI trong bộ bàn giao.')
            return
        st.download_button('Tải báo cáo Power BI (.pbix)', pbix.read_bytes(), pbix.name, mime='application/octet-stream', key='pbix_download')
        st.caption(f"{pbix.name} · {number(pbix.stat().st_size / 1_000_000, 1)} MB · Mở bằng Power BI Desktop")
    with st.expander('Hướng dẫn mở báo cáo trên máy nhận'):
        st.write('1. Tải file PBIX và mở bằng Power BI Desktop.\n2. Xem 5 trang báo cáo từ dữ liệu đã lưu trong file.\n3. Trước Refresh, đặt tham số DataRoot về thư mục handover_v3 trong bộ bàn giao.')


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
