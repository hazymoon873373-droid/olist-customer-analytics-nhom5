"""Shared data contract and KPI rules for the authenticated web application."""
from pathlib import Path
import os,json,hashlib
import pandas as pd

ROOT=Path(__file__).resolve().parent
DATA_DIR=Path(os.environ.get('OLIST_DATA_DIR',ROOT.parent/'tam_eda/handover_v3')).resolve()
CLEAN_DIR=Path(os.environ.get('OLIST_CLEAN_DIR',ROOT.parent/'Thien_ETL_MongoDB/processed')).resolve()

def flags(series):
    text=series.astype('string').str.strip().str.lower()
    if not text.isin(['true','false']).all():raise ValueError('Cờ dữ liệu không hợp lệ')
    return text.eq('true').astype(bool)

def data_signature():
    files=[Path(__file__),*[p for p in sorted(DATA_DIR.glob('*')) if p.is_file()]]
    return tuple((str(p),p.stat().st_mtime_ns,p.stat().st_size) for p in files)

def load_group_data():
    contract=json.loads((DATA_DIR/'integration_contract.json').read_text(encoding='utf8'))
    manifest=json.loads((DATA_DIR/'manifest.json').read_text(encoding='utf8'))
    tables={}
    for role,spec in contract['datasets'].items():
        path=DATA_DIR/spec['file']
        if path.parent.resolve()!=DATA_DIR:raise ValueError('Đường dẫn dữ liệu không hợp lệ')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['output_sha256'][path.name]:raise ValueError('Dữ liệu đã thay đổi: '+path.name)
        frame=pd.read_csv(path,low_memory=False,dtype={'customer_zip_code_prefix':'string'})
        missing=set(spec['columns'])-set(frame.columns)
        if missing:raise ValueError('Thiếu cột '+role+': '+', '.join(sorted(missing)))
        if frame.duplicated(spec['key']).any() or frame[spec['key']].isna().any().any():raise ValueError('Trùng/thiếu khóa '+role)
        if len(frame)!=spec['rows']:raise ValueError('Sai số dòng '+role)
        tables[role]=frame
    tables['orders'].order_purchase_timestamp=pd.to_datetime(tables['orders'].order_purchase_timestamp,format='mixed')
    tables['orders'].valid_delay_kpi=flags(tables['orders'].valid_delay_kpi)
    tables['orders']['is_delayed']=tables['orders']['is_delayed'].astype('string').str.lower().map({'true':True,'false':False}).astype('boolean')
    bi=tables['ml_bi'];bi.ml_scored=flags(bi.ml_scored)
    if bi.loc[~bi.ml_scored,'ml_churn_probability'].notna().any():raise ValueError('Khách chưa chấm có xác suất')
    p=bi.loc[bi.ml_scored,'ml_churn_probability']
    if not p.between(0,1).all():raise ValueError('Xác suất ngoài phạm vi')
    for name in ['metrics.json','feature_importance.csv','cohort_retention_matrix.csv','confusion_matrix.csv']:
        path=DATA_DIR/name
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['output_sha256'][name]:raise ValueError('Dữ liệu đã thay đổi: '+name)
    tables['metrics']=json.loads((DATA_DIR/'metrics.json').read_text(encoding='utf8'))
    tables['importance']=pd.read_csv(DATA_DIR/'feature_importance.csv')
    tables['retention']=pd.read_csv(DATA_DIR/'cohort_retention_matrix.csv').set_index('CohortMonth')
    tables['confusion']=pd.read_csv(DATA_DIR/'confusion_matrix.csv')
    return tables

def customer_snapshot(tables):
    base=tables['orders'].sort_values(['order_purchase_timestamp','order_id']).drop_duplicates('customer_unique_id',keep='last')[['customer_unique_id','customer_state','region_name']]
    base=base.merge(tables['rfm'][['customer_unique_id','segment']],on='customer_unique_id',how='left',validate='one_to_one')
    bi=tables['ml_bi'];cols=['customer_unique_id','ml_scored','kmeans_cluster','kmeans_segment',*[c for c in bi if c.startswith('ml_') and c!='ml_scored']]
    result=base.merge(bi[cols],on='customer_unique_id',how='left',validate='one_to_one',indicator=True)
    result['ml_status']='Chưa đủ điều kiện'
    result.loc[result._merge.eq('left_only'),'ml_status']='Ngoài snapshot'
    result.loc[result.ml_scored.eq(True),'ml_status']='Được chấm'
    return result.drop(columns='_merge')

def filter_orders(orders,start=None,end=None,states=None):
    result=orders
    if start is not None:result=result.loc[result.order_purchase_timestamp.ge(pd.Timestamp(start))]
    if end is not None:result=result.loc[result.order_purchase_timestamp.lt(pd.Timestamp(end)+pd.Timedelta(days=1))]
    if states:result=result.loc[result.customer_state.isin(states)]
    return result.copy()

def kpis(orders):
    delivered=orders.loc[orders.order_status.eq('delivered')]
    valid=orders.loc[orders.valid_delay_kpi]
    return {'orders':len(orders),'customers':orders.customer_unique_id.nunique(),'gmv':float(delivered.total_products_value.sum()),
            'aov':float(delivered.total_products_value.mean()) if len(delivered) else None,'valid_deliveries':len(valid),
            'late_rate':float(valid.is_delayed.mean()) if len(valid) else None,'median_days':float(valid.delivery_days.median()) if len(valid) else None}
