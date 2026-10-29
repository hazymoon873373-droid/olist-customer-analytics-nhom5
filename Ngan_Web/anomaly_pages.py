"""Review the saved Isolation Forest results; never treat flags as confirmed fraud."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import streamlit as st

from analytics_data import filter_orders
from ui import metric_strip, number, section_heading, render_chart

ROOT = Path(__file__).resolve().parent
ANOMALY_DIR = ROOT.parent / 'Tho_Machine_Learning/Tho_Order_Anomaly/outputs'
CONTRACT = ROOT / 'anomaly_contract.json'
REASONS = {
    'Nhieu_san_pham': 'Nhiều sản phẩm',
    'Gia_tri_san_pham_cao': 'Giá trị sản phẩm cao',
    'Phi_van_chuyen_cao': 'Phí vận chuyển cao',
    'Ty_le_phi_van_chuyen_cao': 'Tỷ lệ phí vận chuyển cao',
    'Nhieu_ky_tra_gop': 'Nhiều kỳ trả góp',
    'Nhieu_ban_ghi_thanh_toan': 'Nhiều bản ghi thanh toán',
    'Thoi_gian_giao_hang_dai': 'Thời gian giao hàng dài',
    'Giao_hang_tre_nhieu': 'Giao hàng trễ nhiều',
}


def load_anomalies(directory=ANOMALY_DIR, contract_path=CONTRACT):
    contract = json.loads(Path(contract_path).read_text(encoding='utf8'))
    directory = Path(directory)
    for filename, expected in contract['sha256'].items():
        path = directory / filename
        if path.parent.resolve() != directory.resolve():
            raise ValueError('Đường dẫn kết quả bất thường không hợp lệ.')
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('Kết quả Isolation Forest đã thay đổi: ' + filename)
    frame = pd.read_csv(directory/'order_anomaly_scores.csv', low_memory=False)
    required = {'order_id','customer_unique_id','order_purchase_timestamp','customer_state',
                'anomaly_score','is_anomaly','anomaly_reason','total_products_value',
                'total_freight_value','valid_delay_kpi'}
    if required - set(frame):
        raise ValueError('Thiếu cột kết quả đơn hàng bất thường.')
    if frame.order_id.isna().any() or not frame.order_id.is_unique:
        raise ValueError('Mã đơn bất thường thiếu hoặc trùng.')
    if not frame.is_anomaly.isin([0,1]).all() or not np.isfinite(frame.anomaly_score).all():
        raise ValueError('Cờ hoặc điểm bất thường không hợp lệ.')
    metrics = json.loads((directory/'model_metrics.json').read_text(encoding='utf8'))
    if (len(frame) != metrics['total_orders'] or int(frame.is_anomaly.sum()) != metrics['anomaly_orders']
            or len(frame) != contract['rows'] or int(frame.is_anomaly.sum()) != contract['flagged_rows']):
        raise ValueError('Số đơn không khớp hợp đồng Isolation Forest.')
    frame.order_purchase_timestamp = pd.to_datetime(frame.order_purchase_timestamp, errors='raise')
    return frame, metrics


@st.cache_data(show_spinner=False)
def cached_anomalies(signature):
    return load_anomalies()


def filter_anomalies(frame, query='', states=None, flagged_only=True, start=None, end=None):
    result = filter_orders(frame, start, end, states)
    if flagged_only:
        result = result.loc[result.is_anomaly.eq(1)]
    if query.strip():
        query = query.strip()
        result = result.loc[result.order_id.str.contains(query, case=False, regex=False)
                            | result.customer_unique_id.str.contains(query, case=False, regex=False)]
    return result.sort_values(['anomaly_score','order_id'], ascending=[False,True]).copy()


def render_anomalies(tables):
    section_heading('Đơn hàng cần kiểm tra', 'Kết quả Isolation Forest của Thọ · Một dòng cho mỗi đơn đã giao')
    try:
        files = [CONTRACT, ANOMALY_DIR/'order_anomaly_scores.csv', ANOMALY_DIR/'model_metrics.json']
        frame, metrics = cached_anomalies(tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in files))
        known = tables['orders'].set_index('order_id')
        linked = known.reindex(frame.order_id)
        if linked.customer_unique_id.isna().any() or linked.customer_unique_id.tolist() != frame.customer_unique_id.tolist():
            raise ValueError('Đơn bất thường không khớp bộ dữ liệu BI hiện hành.')
    except (OSError, ValueError, KeyError) as error:
        st.error(f'Không đọc được kết quả bất thường: {error}')
        return
    metric_strip([
        ('Đơn hàng được khảo sát', number(len(frame)), 'Chỉ các đơn đã giao'),
        ('Đơn được gắn cờ', number(metrics['anomaly_orders']), 'Cần kiểm tra thêm về nghiệp vụ'),
        ('Tỷ lệ được gắn cờ', number(metrics['anomaly_rate'] * 100, 2) + '%', 'Toàn bộ snapshot Isolation Forest'),
    ])
    st.caption('Điểm càng cao càng khác biệt so với phần lớn dữ liệu. Không có nhãn bất thường thật; cờ này không xác nhận lỗi hoặc gian lận. Tỷ lệ khoảng 1% chịu ảnh hưởng của contamination=0,01.')
    with st.container(border=True, key='anomaly_filters'):
        left, right = st.columns([2,1])
        query = left.text_input('Tìm đơn hoặc khách hàng', key='anomaly_search', placeholder='Nhập mã đơn hoặc mã khách…')
        states = right.multiselect('Bang của đơn khảo sát', sorted(frame.customer_state.dropna().unique()), key='anomaly_states', placeholder='Tất cả các bang')
        flagged = st.checkbox('Chỉ xem đơn được gắn cờ bất thường', value=True, key='anomaly_flagged')
    result = filter_anomalies(frame, query, states, flagged)
    with st.container(border=True, key='anomaly_results'):
        section_heading('Danh sách đối chiếu', f'{number(len(result))} đơn phù hợp · Hiển thị tối đa 200 dòng · CSV chứa toàn bộ kết quả lọc')
        columns = ['order_id','customer_unique_id','order_purchase_timestamp','customer_state',
                   'total_products_value','total_freight_value','anomaly_score','is_anomaly','anomaly_reason','valid_delay_kpi']
        st.dataframe(result[columns].head(200), hide_index=True, width='stretch', column_config={
            'order_id':'Mã đơn','customer_unique_id':'Mã khách','order_purchase_timestamp':'Ngày mua',
            'customer_state':'Bang','total_products_value':'Tiền hàng · BRL','total_freight_value':'Cước · BRL',
            'anomaly_score':st.column_config.NumberColumn('Điểm bất thường',format='%.4f'),
            'is_anomaly':'Cờ bất thường','anomaly_reason':'Dấu hiệu theo quy tắc','valid_delay_kpi':'Hợp lệ KPI giao hàng',
        })
        st.download_button('Tải đơn khảo sát đang lọc · CSV',result.to_csv(index=False).encode('utf-8-sig'),
                           'olist_anomaly_filtered.csv',key='anomaly_export')
    if result.empty:
        st.info('Không có đơn phù hợp. Thử đổi mã tìm kiếm, bang hoặc bỏ điều kiện chỉ xem đơn được gắn cờ.')
    else:
        reasons = result.anomaly_reason.dropna().str.split(';').explode().str.strip()
        reasons = reasons.loc[reasons.ne('')].map(lambda value: REASONS.get(value,value))
        if not reasons.empty:
            with st.container(border=True, key='anomaly_reasons'):
                section_heading('Dấu hiệu cần kiểm tra', 'Một đơn có thể có nhiều dấu hiệu; tổng số dấu hiệu có thể lớn hơn số đơn')
                counts = reasons.value_counts().head(8).rename_axis('reason').reset_index(name='orders')
                render_chart(counts,'reason','orders','Dấu hiệu','Số đơn',height=220,tooltip_format=',.0f')
