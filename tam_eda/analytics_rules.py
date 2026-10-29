"""Business rules shared by the handover builder and exploratory analysis."""
import numpy as np
import pandas as pd

def require_keys(frame, columns, label):
    if frame[columns].isna().any().any():raise ValueError(f'{label}: missing key {columns}')
    if frame.duplicated(columns).any():raise ValueError(f'{label}: duplicate key {columns}')

def parse_flags(series):
    text=series.astype('string').str.strip().str.lower()
    if not text.isin(['true','false']).all():raise ValueError('Invalid or missing boolean flag')
    return text.eq('true').astype(bool)

def filter_dates(frame, start_date=None, end_date=None):
    out=frame.copy()
    timestamps=pd.to_datetime(out.order_purchase_timestamp,format='mixed',errors='raise')
    if start_date is not None:out=out.loc[timestamps.ge(pd.Timestamp(start_date))]
    if end_date is not None:
        end=pd.Timestamp(end_date)
        if end!=end.normalize():raise ValueError('end_date must be a calendar date')
        out=out.loc[timestamps.loc[out.index].lt(end+pd.Timedelta(days=1))]
    return out

def apply_multidimensional_filter(orders,items,payments,start_date=None,end_date=None,
                                 states=None,categories=None,payment_types=None,order_status='delivered'):
    """Select orders; category item output contains selected categories only.

    Order totals remain whole-basket amounts. This exploratory view never
    overwrites the fixed RFM/ML snapshots or redefines their cutoff.
    """
    out=filter_dates(orders,start_date,end_date)
    selected=items.copy()
    if order_status is not None:out=out.loc[out.order_status.eq(order_status)]
    if states:out=out.loc[out.customer_state.isin([s.upper() for s in states])]
    if categories:
        selected=selected.loc[selected.category_english.isin(categories)]
        out=out.loc[out.order_id.isin(selected.order_id)]
    if payment_types:
        ids=payments.loc[payments.payment_type.isin(payment_types),'order_id']
        out=out.loc[out.order_id.isin(ids)]
    return out.copy(),selected.loc[selected.order_id.isin(out.order_id)].copy()

def review_mean(reviews):
    values=pd.to_numeric(reviews.review_score,errors='raise')
    if not values.between(1,5).all():raise ValueError('Review score must be 1..5')
    valid=~parse_flags(reviews.review_before_purchase)
    return reviews.assign(review_score=values).loc[valid].groupby('order_id').review_score.mean()

def set_delivery_metrics(frame):
    out=frame.copy();valid=parse_flags(out.valid_delay_kpi)
    out['delivery_days']=(out.order_delivered_customer_date-out.order_purchase_timestamp).dt.total_seconds()/86400
    out['delay_days']=(out.order_delivered_customer_date-out.order_estimated_delivery_date).dt.total_seconds()/86400
    if out.loc[valid,['delivery_days','delay_days']].isna().any().any() or out.loc[valid,'delivery_days'].lt(0).any():
        raise ValueError('Valid delivery flag conflicts with delivery dates')
    out['is_delayed']=pd.Series(pd.NA,index=out.index,dtype='boolean')
    out.loc[valid,'is_delayed']=out.loc[valid,'delay_days'].gt(0)
    return out

def rfm_core(master, reference_date='2018-08-30'):
    require_keys(master,['order_id'],'orders')
    ref=pd.Timestamp(reference_date).normalize()
    d=master.loc[master.order_status.eq('delivered') & master.order_purchase_timestamp.lt(ref+pd.Timedelta(days=1))]
    r=d.groupby('customer_unique_id').agg(frequency=('order_id','nunique'),monetary=('total_products_value','sum'),first_order=('order_purchase_timestamp','min'),last_order=('order_purchase_timestamp','max')).reset_index()
    r['recency']=(ref-r.last_order.dt.normalize()).dt.days
    return r

def cohort_tables(orders, observation_month='2018-08'):
    end=pd.Period(observation_month,freq='M')
    d=orders.loc[orders.order_status.eq('delivered') & orders.order_purchase_timestamp.lt((end+1).start_time),['customer_unique_id','order_purchase_timestamp']].copy()
    if d.empty:raise ValueError('No delivered orders for cohort')
    d['month']=d.order_purchase_timestamp.dt.to_period('M');d['first']=d.groupby('customer_unique_id').month.transform('min')
    d['age']=(d.month.dt.year-d['first'].dt.year)*12+d.month.dt.month-d['first'].dt.month
    counts=d.groupby(['first','age']).customer_unique_id.nunique().unstack(fill_value=0).reindex(columns=range(24),fill_value=0).astype(float)
    for month in counts.index:
        for age in counts:
            if month+age>end:counts.loc[month,age]=np.nan
    retention=counts.div(counts[0],axis=0).round(4)
    for frame in [counts,retention]:frame.index=frame.index.astype(str);frame.index.name='CohortMonth'
    return counts,retention

def validate_sources(orders,customers,items,payments,reviews,products,translation):
    for frame,keys,label in [(orders,['order_id'],'orders'),(customers,['customer_id'],'customers'),
        (items,['order_id','order_item_id'],'items'),(payments,['order_id','payment_sequential'],'payments'),
        (reviews,['review_id','order_id'],'reviews'),(products,['product_id'],'products'),
        (translation,['product_category_name'],'translation')]:require_keys(frame,keys,label)
    if not orders.customer_id.isin(customers.customer_id).all():raise ValueError('Order has missing customer')
    if customers.customer_unique_id.isna().any():raise ValueError('Missing customer_unique_id')
    for frame in [items,payments,reviews]:
        if not frame.order_id.isin(orders.order_id).all():raise ValueError('Orphan order reference')
    if not items.product_id.isin(products.product_id).all():raise ValueError('Orphan product reference')
    for frame,cols in [(items,['price','freight_value']),(payments,['payment_value'])]:
        for col in cols:
            n=pd.to_numeric(frame[col],errors='raise')
            if not np.isfinite(n).all() or n.lt(0).any():raise ValueError(f'Invalid economic value {col}')
