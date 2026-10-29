"""Describe packaged BI/web names separately from Tho's upstream names."""
import json
from pathlib import Path
import pandas as pd

BI_COLUMN_MAP={
    'churn_probability':'ml_churn_probability','score_decile':'ml_score_decile',
    'risk_level':'ml_risk_level','eligibility_status':'ml_eligibility_status',
    'cutoff_timestamp':'ml_snapshot_cutoff','model_version':'ml_model_version',
    'model_name':'ml_model_name','prediction_threshold':'ml_prediction_threshold',
    'repurchase_probability':'ml_repurchase_probability','predicted_churn':'ml_predicted_churn',
    'eligibility_reason':'ml_eligibility_reason','model_quality_status':'ml_quality_status',
    'risk_label_status':'ml_risk_label_status','source_version':'ml_source_version',
    'churn_proxy_180d':'ml_churn_proxy_180d','label_status_or_reason':'ml_label_status_or_reason',
    'kmeans_cluster':'kmeans_cluster','kmeans_segment':'kmeans_segment','kmeans_data_status':'kmeans_data_status',
}

def write_contract(output):
    output=Path(output)
    specifications={
        'orders':('olist_powerbi_orders_master.csv',['order_id'],'all statuses; one order'),
        'items':('olist_powerbi_items_master.csv',['order_id','order_item_id'],'one item line; do not sum order totals after joining'),
        'rfm':('rfm_table.csv',['customer_unique_id'],'delivered customers before 2018-08-31; manual segmentation'),
        'ml_test':('churn_test_predictions_temporal_v4.csv',['customer_unique_id'],'historical test only; not current BI customer scores'),
        'ml_bi':('olist_powerbi_customer_snapshot_temporal_v4.csv',['customer_unique_id'],'fixed BI snapshot; preserve unscored nulls'),
    }
    datasets={}
    for role,(filename,key,scope) in specifications.items():
        frame=pd.read_csv(output/filename,low_memory=False)
        if frame[key].isna().any().any() or frame.duplicated(key).any():
            raise ValueError(f'Invalid integration key: {role}')
        datasets[role]={'file':filename,'key':key,'rows':len(frame),'columns':list(frame.columns),'scope':scope}
    contract={
        'version':'group_bi_web_handover_20261029','path_base':'directory containing this JSON',
        'datasets':datasets,'upstream_model_contract':'data_contract.json',
        'upstream_contract_note':'Preserved Tho contract uses upstream filenames; consumers of this package must use datasets above.',
        'upstream_filename_map':{'test_predictions.csv':datasets['ml_test']['file'],'bi_web_customers.csv':datasets['ml_bi']['file']},
        'upstream_bi_column_map':BI_COLUMN_MAP,
        'cutoffs':{'rfm_reference_date':'2018-08-30','bi_cutoff_exclusive':'2018-08-31 00:00:00','ml_test_cutoff':'2018-03-01 00:00:00','horizon_days':180},
        'null_probability':'not scored or outside snapshot; never zero risk',
        'snapshot_join':'customer_unique_id; one-to-one between customer tables; many-to-one when joining to orders',
        'test_join':'Do not use historical test scores as BI customer scores.',
        'manual_rfm_vs_kmeans':'Manual RFM has 6 labels; K-Means has 4 clusters and uses R/F/M, not manual scores.',
        'quality_status':'experimental_not_validated_for_deployment',
        'powerbi':'PBIX desktop artifact; configure DataRoot after moving; web integration must be tested separately.',
    }
    (output/'integration_contract.json').write_text(json.dumps(contract,ensure_ascii=False,indent=2),encoding='utf8')
    return contract
