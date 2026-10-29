"""Render exploratory charts from the single validated handover; never overwrites its CSVs."""
from pathlib import Path
import json,textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

def render_charts(handover, output):
    handover,output=Path(handover),Path(output);output.mkdir(parents=True,exist_ok=True)
    orders=pd.read_csv(handover/'olist_powerbi_orders_master.csv',low_memory=False)
    items=pd.read_csv(handover/'olist_powerbi_items_master.csv',low_memory=False)
    orders.order_purchase_timestamp=pd.to_datetime(orders.order_purchase_timestamp,format='mixed')
    delivered=orders[orders.order_status.eq('delivered')].copy()
    entries=[]
    def finish(fig,name,scope):
        fig.tight_layout();fig.savefig(output/name,dpi=150);plt.close(fig)
        entries.append({'file':name,'scope':scope})
    def bars(series,name,title,scope,xlabel='BRL'):
        series=series.sort_values().tail(10)
        fig,ax=plt.subplots(figsize=(11,5));ax.barh([textwrap.fill(str(v),30) for v in series.index],series.values,color='#2874A6')
        ax.set(title=title,xlabel=xlabel);finish(fig,name,scope)
    delivered['month']=delivered.order_purchase_timestamp.dt.to_period('M').astype(str)
    monthly=delivered.groupby('month').agg(gmv=('total_products_value','sum'),orders=('order_id','nunique'))
    fig,ax=plt.subplots(figsize=(12,5));ax.plot(monthly.index,monthly.gmv,marker='o');ax.tick_params(axis='x',rotation=60)
    ax.set(title='Giá trị sản phẩm theo tháng — đơn delivered',ylabel='BRL',xlabel='Tháng mua')
    finish(fig,'chart1_revenue_over_time.png','Delivered orders; product value excludes freight')
    bars(delivered.groupby('state_name').total_products_value.sum(),'chart2_revenue_by_state.png','Top 10 bang — giá trị sản phẩm delivered','Delivered orders')
    bars(items.loc[items.order_status.eq('delivered')].groupby('category_english').price.sum(),'chart3_revenue_by_category.png','Top 10 danh mục — đơn delivered','Delivered item lines; sum price')
    payment=pd.read_csv(handover/'payment_transaction_summary.csv').set_index('payment_type')
    bars(payment.total_payment_value,'chart4_revenue_by_payment.png','Giá trị thanh toán thực tế theo phương thức','All payment transactions; not accounting revenue')
    fig,ax=plt.subplots(figsize=(11,5));ax.hist(np.log1p(delivered.total_products_value),bins=40,color='#2874A6')
    ax.set(title='Phân bố giá trị sản phẩm mỗi đơn delivered',xlabel='log(1 + giá trị sản phẩm BRL)',ylabel='Số đơn')
    finish(fig,'chart5_order_value_histogram.png','All delivered orders, log transformed axis; no outlier deletion')
    valid=orders[orders.valid_delay_kpi & orders.review_score.notna()].copy()
    stats=valid.groupby('is_delayed').review_score.agg(['mean','count'])
    fig,ax=plt.subplots(figsize=(8,5));labels=['Đúng hạn','Trễ'];means=[stats.loc[False,'mean'],stats.loc[True,'mean']]
    ax.bar(labels,means,color=['#2874A6','#D35400']);ax.set(ylim=(0,5),ylabel='Điểm review',title='Review và giao trễ — mối liên hệ, không suy ra nhân quả')
    for x,val in enumerate(means):ax.text(x,val+.08,f'{val:.2f}',ha='center')
    finish(fig,'chart6_delivery_delay_vs_review.png','valid_delay_kpi=true; reviewed orders only; mean per order')
    summary=pd.read_csv(handover/'rfm_segment_summary.csv').set_index('segment')
    bars(summary.customer_count,'chart7_customer_segments.png','Phân nhóm RFM theo quy tắc — snapshot 30/08/2018','93358 delivered customers; manual segments, not K-Means',xlabel='Số khách')
    ret=pd.read_csv(handover/'cohort_retention_matrix.csv').set_index('CohortMonth')
    fig,ax=plt.subplots(figsize=(12,8));cmap=plt.get_cmap('Blues').copy();cmap.set_bad('#D3D3D3')
    im=ax.imshow(np.ma.masked_invalid(ret.to_numpy()*100),aspect='auto',cmap=cmap,vmin=0,vmax=100)
    ax.set_yticks(range(len(ret)),ret.index,fontsize=8);ax.set_xticks(range(24),range(24),fontsize=8)
    ax.set(title='Cohort retention — xám: chưa quan sát; trắng: 0%',xlabel='Số tháng từ tháng mua đầu',ylabel='Tháng mua đầu')
    fig.colorbar(im,ax=ax,label='Retention (%)');finish(fig,'chart8_cohort_retention_heatmap.png','Delivered customers; 0..23; future null and observed zero distinct')
    test=pd.read_csv(handover/'churn_test_predictions_temporal_v4.csv')
    fig,ax=plt.subplots(figsize=(10,5))
    for actual,label in [(1,'Có mua lại'),(0,'Không mua lại')]:
        ax.hist(test.loc[test.repurchased_true.eq(actual),'churn_probability'],bins=np.linspace(0,1,21),alpha=.55,label=label)
    ax.axvline(.5,color='black',linestyle='--',label='Ngưỡng 0,5');ax.legend();ax.set(title='Phân bố điểm RF — test lịch sử, chưa hiệu chuẩn',xlabel='Điểm không mua lại',ylabel='Số khách')
    finish(fig,'chart9_ml_probability_test.png','944 historical test customers; no train_in_sample pooling')
    km=pd.read_csv(handover/'kmeans_clusters_summary.csv').set_index('Cụm (Cluster)')
    bars(km['Số lượng khách (Count)'],'chart10_kmeans_clusters.png','4 cụm K-Means — khác 6 nhóm RFM quy tắc','93358 delivered customers; frozen model snapshot',xlabel='Số khách')
    (output/'chart_manifest.json').write_text(json.dumps(entries,ensure_ascii=False,indent=2),encoding='utf8')
    return entries

if __name__=='__main__':
    import argparse
    root=Path(__file__).resolve().parent;parser=argparse.ArgumentParser()
    parser.add_argument('--handover',type=Path,default=root/'handover_v3');parser.add_argument('--output',type=Path,default=root/'charts')
    args=parser.parse_args();render_charts(args.handover,args.output)
