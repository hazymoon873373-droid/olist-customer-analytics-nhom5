"""Rebuild Tam handover from versioned clean sources; never trains or tunes ML."""
from pathlib import Path
import argparse, json, hashlib, shutil, tempfile, os
import numpy as np
import pandas as pd
from analytics_rules import validate_sources, parse_flags, review_mean, set_delivery_metrics, rfm_core, cohort_tables
from load_data import load_clean_datasets
from integration_contract import write_contract

ROOT = Path(__file__).resolve().parent
def build_into(source, ml, output):
    output.mkdir(parents=True, exist_ok=True)
    tables=load_clean_datasets(source)
    orders,customers,items,payments,reviews,products,translation=[tables[k] for k in ['orders','customers','items','payments','reviews','products','translation']]
    validate_sources(orders,customers,items,payments,reviews,products,translation)
    for c in ['order_purchase_timestamp','order_approved_at','order_delivered_carrier_date',
              'order_delivered_customer_date','order_estimated_delivery_date']:
        orders[c]=pd.to_datetime(orders[c], format='mixed', errors='raise')
    flags=['valid_delay_kpi','delivered_missing_date','carrier_before_approval','customer_before_carrier']
    for c in flags:
        orders[c]=parse_flags(orders[c])
    if orders.order_purchase_timestamp.isna().any() or orders.order_estimated_delivery_date.isna().any():
        raise ValueError('Missing purchase or estimated delivery timestamp')
    customers.customer_zip_code_prefix=customers.customer_zip_code_prefix.str.zfill(5)
    totals=items.groupby('order_id').agg(total_products_value=('price','sum'),
        total_freight_value=('freight_value','sum'),total_items=('order_item_id','size'))
    pay=payments.sort_values(['order_id','payment_value','payment_sequential'],ascending=[True,False,True]).drop_duplicates('order_id').set_index('order_id')
    paytot=payments.groupby('order_id').agg(max_installments=('payment_installments','max'),payment_records=('payment_sequential','size'))
    rv=review_mean(reviews)
    master=orders.merge(customers[['customer_id','customer_unique_id','customer_zip_code_prefix','customer_city','customer_state']],on='customer_id',validate='one_to_one')
    master=master.join(totals,on='order_id').join(pay.payment_type.rename('main_payment_type'),on='order_id').join(paytot,on='order_id').join(rv.rename('review_score'),on='order_id')
    for c in totals:master[c]=master[c].fillna(0)
    master.main_payment_type=master.main_payment_type.fillna('not_defined')
    states=json.loads((source/'ibge_states_raw.json').read_text(encoding='utf8'))
    master['state_name']=master.customer_state.map({s['sigla']:s['nome'] for s in states})
    master['region_name']=master.customer_state.map({s['sigla']:s['regiao']['nome'] for s in states})
    master=set_delivery_metrics(master)
    valid=master.valid_delay_kpi
    master['order_year_month']=master.order_purchase_timestamp.dt.strftime('%Y-%m-01')
    rfm=rfm_core(master)
    # Keep the group's reviewed manual segmentation; verify its core against recomputation.
    ref=pd.read_csv(source/'rfm_reference.csv')
    check=rfm.merge(ref,on='customer_unique_id',suffixes=('','_ref'),validate='one_to_one')
    if not len(check)==len(rfm)==len(ref)==93358:raise ValueError('RFM reference customer scope differs')
    for c in ['recency','frequency','monetary']:
        if not np.allclose(check[c],check[c+'_ref'],atol=1e-6,rtol=0):raise ValueError(f'RFM reference mismatch: {c}')
    rfm=rfm.merge(ref[['customer_unique_id','r_score','f_score','m_score','rfm_segment_code','segment']],on='customer_unique_id',validate='one_to_one')
    master=master.merge(rfm[['customer_unique_id','segment']],on='customer_unique_id',how='left',validate='many_to_one')
    master.segment=master.segment.fillna('Khách chưa phân loại')
    columns=['order_id','customer_id','order_status','order_purchase_timestamp','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date','customer_unique_id','customer_zip_code_prefix','customer_city','customer_state','state_name','region_name','main_payment_type','max_installments','review_score','payment_records','total_products_value','total_freight_value','total_items','segment','delivery_days','delay_days','is_delayed','order_year_month',*flags]
    def save(frame,name):frame.to_csv(output/name,index=False,encoding='utf-8-sig',date_format='%Y-%m-%d %H:%M:%S',lineterminator='\n')
    save(master[columns],'olist_powerbi_orders_master.csv')
    item_master=items.merge(orders[['order_id','order_status','order_purchase_timestamp']],on='order_id',validate='many_to_one').merge(products[['product_id','product_category_name','product_weight_g']],on='product_id',validate='many_to_one').merge(translation,on='product_category_name',how='left',validate='many_to_one')
    item_master['category_english']=item_master.product_category_name_english.fillna('others/unlabeled')
    save(item_master[['order_id','order_item_id','product_id','seller_id','shipping_limit_date','price','freight_value','order_status','order_purchase_timestamp','category_english','product_weight_g']],'olist_powerbi_items_master.csv')
    save(rfm[['customer_unique_id','recency','frequency','monetary','first_order','last_order','r_score','f_score','m_score','rfm_segment_code','segment']],'rfm_table.csv')
    summary=rfm.groupby('segment').agg(customer_count=('customer_unique_id','size'),total_revenue=('monetary','sum'),avg_revenue=('monetary','mean'),avg_recency_days=('recency','mean'),avg_frequency=('frequency','mean')).reset_index()
    summary['customer_pct']=100*summary.customer_count/len(rfm);summary['revenue_pct']=100*summary.total_revenue/rfm.monetary.sum();save(summary,'rfm_segment_summary.csv')
    counts,retention=cohort_tables(master)
    for name,frame in [('cohort_counts_matrix.csv',counts),('cohort_retention_matrix.csv',retention)]:
        frame.index=frame.index.astype(str);frame.index.name='CohortMonth';save(frame.reset_index(),name)
    # Already-reviewed artifacts copied verbatim; selected model/threshold are not changed.
    ml_files=['olist_powerbi_customer_snapshot_temporal_v4.csv','churn_test_predictions_temporal_v4.csv',
              'kmeans_clusters_summary.csv','kmeans_model_evaluation.csv','rfm_kmeans_summary.xlsx',
              'classification_report.csv','confusion_matrix.csv','probability_summary.csv','metrics.json',
              'validation_protocol.json','data_contract.json','feature_importance.csv']
    for name in ml_files:shutil.copyfile(ml/name,output/name)
    primary=master.groupby('main_payment_type').order_id.nunique().rename('order_count').reset_index()
    primary['order_share_pct']=100*primary.order_count/len(master);save(primary,'payment_primary_order_summary.csv')
    trans=payments.groupby('payment_type').agg(transaction_count=('payment_sequential','size'),order_count=('order_id','nunique'),total_payment_value=('payment_value','sum')).reset_index()
    trans['payment_value_share_pct']=100*trans.total_payment_value/trans.total_payment_value.sum();save(trans,'payment_transaction_summary.csv')
    checks={'orders':len(master),'items':len(items),'rfm':len(rfm),'valid_delay':int(valid.sum()),'late':int(master.loc[valid,'is_delayed'].sum()),'missing_review':int(master.review_score.isna().sum()),'missing_estimated':int(master.order_estimated_delivery_date.isna().sum()),'bad_zip':int((~master.customer_zip_code_prefix.str.fullmatch(r'\d{5}')).sum()),'median_delivery_valid':float(master.loc[valid,'delivery_days'].median()),'csat_on_time':float(master.loc[valid & master.is_delayed.eq(False),'review_score'].mean()),'csat_late':float(master.loc[valid & master.is_delayed.eq(True),'review_score'].mean())}
    if (checks['orders'],checks['items'],checks['valid_delay'],checks['late'],checks['missing_estimated'],checks['bad_zip'],checks['missing_review'])!=(99441,112650,95097,7793,0,0,829):
        raise ValueError(f'Snapshot control counts failed: {checks}')
    scope_by_metric={'items':'all source item lines','rfm':'delivered customers before 2018-08-31',
                     'late':'valid_delay_kpi=true','valid_delay':'valid_delay_kpi=true',
                     'median_delivery_valid':'valid_delay_kpi=true',
                     'csat_on_time':'valid_delay_kpi=true; on-time; review available',
                     'csat_late':'valid_delay_kpi=true; late; review available'}
    rows=[{'metric':k,'value':v,'scope':scope_by_metric.get(k,'all source orders')} for k,v in checks.items()]
    delivered=master.loc[master.order_status.eq('delivered')]
    delivered_freq=delivered.groupby('customer_unique_id').order_id.nunique()
    total_gmv=float(delivered.total_products_value.sum())
    gross_value=float((delivered.total_products_value+delivered.total_freight_value).sum())
    business=[('delivered_orders',len(delivered),'delivered orders'),
              ('canceled_orders',int(master.order_status.eq('canceled').sum()),'all source orders; canceled only'),
              ('unavailable_orders',int(master.order_status.eq('unavailable').sum()),'all source orders; unavailable only'),
              ('canceled_rate',float(master.order_status.eq('canceled').mean()),'all source orders; fraction 0..1'),
              ('unique_customers_all_orders',master.customer_unique_id.nunique(),'all source orders; distinct customer_unique_id'),
              ('delivered_customers',len(delivered_freq),'customers with at least one delivered order'),
              ('repeat_delivered_customers',int(delivered_freq.ge(2).sum()),'customers with at least two delivered orders'),
              ('repeat_delivered_customer_rate',float(delivered_freq.ge(2).mean()),'delivered customers; fraction 0..1; historical, not a future label'),
              ('gmv_products_delivered',total_gmv,'delivered orders; BRL; excludes freight'),
              ('gross_value_with_freight_delivered',gross_value,'delivered orders; BRL; includes freight; not accounting profit'),
              ('aov_products_delivered',total_gmv/len(delivered),'delivered orders; BRL per order'),
              ('aov_with_freight_delivered',gross_value/len(delivered),'delivered orders; BRL per order'),
              ('avg_review_score_delivered',float(delivered.review_score.mean()),'delivered orders with review; invalid early reviews excluded'),
              ('late_delivery_rate_valid',checks['late']/checks['valid_delay'],'valid_delay_kpi=true; fraction 0..1')]
    rows.extend({'metric':k,'value':v,'scope':scope} for k,v,scope in business)
    kpi=pd.DataFrame(rows)
    save(kpi,'kpi_summary_tam.csv')
    samples={'delivery_days_valid':master.loc[valid,'delivery_days'],
             'review_score_valid_records':reviews.loc[reviews.review_before_purchase.astype(str).str.lower().eq('false'),'review_score'],
             'item_price':items.price,'freight_value':items.freight_value,'payment_value':payments.payment_value}
    stats=pd.DataFrame({name:values.describe() for name,values in samples.items()}).T
    stats['median']=stats['50%']
    write_contract(output)
    stats['IQR']=stats['75%']-stats['25%'];stats.index.name='variable';save(stats.reset_index(),'descriptive_statistics.csv')
    manifest={'checks':checks,'rfm_reference_date':'2018-08-30','bi_cutoff':'2018-08-31 00:00:00','test_cutoff':'2018-03-01','ml_status':'experimental_not_validated_for_deployment','input_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in source.iterdir() if f.is_file()},'ml_input_sha256':{name:hashlib.sha256((ml/name).read_bytes()).hexdigest() for name in ml_files},'output_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in output.iterdir() if f.is_file() and f.name!='manifest.json'}}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(checks,ensure_ascii=False,indent=2))

def build(source, ml, output):
    source,ml,output=Path(source).resolve(),Path(ml).resolve(),Path(output).resolve()
    if output==ROOT.resolve() or source.is_relative_to(output) or ml.is_relative_to(output):
        raise ValueError('Output must be a dedicated folder, not project/input root')
    if output.exists() and any(output.iterdir()) and not (output/'manifest.json').exists():
        raise ValueError('Refuse to replace a non-handover directory')
    output.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.tam_stage_',dir=output.parent))
    previous=Path(tempfile.mkdtemp(prefix='.tam_previous_',dir=output.parent));previous.rmdir()
    published=False
    try:
        build_into(source,ml,stage)
        if output.exists():os.replace(output,previous)
        try:
            os.replace(stage,output)
            published=True
        except BaseException:
            if previous.exists():os.replace(previous,output)
            raise
    finally:
        for folder in ([stage,previous] if published else [stage]):
            if folder.exists():
                if folder.resolve().parent!=output.parent or not folder.name.startswith(('.tam_stage_','.tam_previous_')):
                    raise RuntimeError('Unsafe temporary directory cleanup')
                shutil.rmtree(folder)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--source',type=Path,default=ROOT/'inputs/clean');parser.add_argument('--ml',type=Path,default=ROOT/'inputs/ml');parser.add_argument('--output',type=Path,default=ROOT/'handover_v3');a=parser.parse_args();build(a.source,a.ml,a.output)
