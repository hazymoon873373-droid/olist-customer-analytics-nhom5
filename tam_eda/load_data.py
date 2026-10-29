"""Load Thiên's versioned clean handover, never a raw/latest-success pointer."""
from pathlib import Path
import pandas as pd

DEFAULT_SOURCE=Path(__file__).resolve().parent/'inputs/clean'
FILES={'orders':'olist_orders_clean.csv','customers':'olist_customers_clean.csv',
       'items':'olist_order_items_clean.csv','payments':'olist_order_payments_clean.csv',
       'reviews':'olist_order_reviews_clean.csv','products':'olist_products_clean.csv',
       'translation':'product_category_name_translation_clean.csv'}

def load_clean_datasets(source=DEFAULT_SOURCE):
    source=Path(source)
    missing=[name for name in FILES.values() if not (source/name).is_file()]
    if missing:raise FileNotFoundError('Missing clean inputs: '+', '.join(missing))
    return {key:pd.read_csv(source/name,na_values=['null'],low_memory=False,
              dtype={'customer_zip_code_prefix':str}) for key,name in FILES.items()}

if __name__=='__main__':
    for name,frame in load_clean_datasets().items():print(name,len(frame))
