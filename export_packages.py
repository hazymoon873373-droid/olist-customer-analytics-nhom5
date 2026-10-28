import os
import pandas as pd
from pymongo import MongoClient
from datetime import datetime, timedelta

# 1. Kết nối MongoDB BigData
client = MongoClient("mongodb://localhost:27017/")
db = client["BigData"]

print("=== BẮT ĐẦU TRÍCH XUẤT TẤT CẢ GÓI BÀN GIAO ===")

# Tạo các thư mục lưu trữ
os.makedirs("./handover_tam", exist_ok=True)
os.makedirs("./handover_tho", exist_ok=True)
os.makedirs("./handover_ngan", exist_ok=True)

# ---------------------------------------------------------------------
# PHẦN 1: BÀN GIAO CHO TÂM (BI - Bảng order_summary 1 dòng / order_id)
# ---------------------------------------------------------------------
print("\n[1/3] Đang trích xuất gói bàn giao cho Tâm (BI)...")

# 1.1 Tạo collection order_summary trong MongoDB
pipeline_tam = [
    {
        "$lookup": {
            "from": "olist_order_payments_clean",
            "localField": "order_id",
            "foreignField": "order_id",
            "as": "payments"
        }
    },
    {
        "$lookup": {
            "from": "olist_order_reviews_clean",
            "localField": "order_id",
            "foreignField": "order_id",
            "as": "reviews"
        }
    },
    {
        "$lookup": {
            "from": "olist_order_items_clean",
            "localField": "order_id",
            "foreignField": "order_id",
            "as": "items"
        }
    },
    {
        "$project": {
            "_id": 0,
            "order_id": 1,
            "customer_id": 1,
            "order_status": 1,
            "order_purchase_timestamp": 1,
            "order_delivered_customer_date": 1,
            "order_estimated_delivery_date": 1,
            "delivered_missing_date": 1,
            "valid_delay_kpi": 1,
            "total_payment_value": {"$round": [{"$sum": "$payments.payment_value"}, 2]},
            "total_items_qty": {"$size": "$items"},
            "total_goods_value": {"$round": [{"$sum": "$items.price"}, 2]},
            "total_freight_value": {"$round": [{"$sum": "$items.freight_value"}, 2]},
            "avg_review_score": {"$round": [{"$avg": "$reviews.review_score"}, 1]}
        }
    },
    {"$out": "order_summary"}
]
db.olist_orders_clean.aggregate(pipeline_tam)

# 1.2 Xuất CSV cho Tâm
docs_tam = list(db.order_summary.find({}, {"_id": 0}))
df_tam = pd.DataFrame(docs_tam)
df_tam.to_csv("./handover_tam/order_summary.csv", index=False)

docs_items = list(db.olist_order_items_clean.find({}, {"_id": 0}))
pd.DataFrame(docs_items).to_csv("./handover_tam/olist_order_items_clean.csv", index=False)
print(f" -> [OK] Đã xuất {len(df_tam)} đơn hàng sang './handover_tam/order_summary.csv'")

# ---------------------------------------------------------------------
# PHẦN 2: BÀN GIAO CHO THỌ (ML - Customer Features Cutoff T0)
# ---------------------------------------------------------------------
print("\n[2/3] Đang trích xuất gói bàn giao cho Thọ (ML)...")

T0 = datetime.fromisoformat("2018-03-01T00:00:00")
T_target = T0 + timedelta(days=90)

pipeline_features = [
    {"$match": {"order_purchase_timestamp": {"$lt": T0}}},
    {
        "$lookup": {
            "from": "olist_customers_clean",
            "localField": "customer_id",
            "foreignField": "customer_id",
            "as": "cust"
        }
    },
    {"$unwind": "$cust"},
    {
        "$lookup": {
            "from": "olist_order_payments_clean",
            "localField": "order_id",
            "foreignField": "order_id",
            "as": "payments"
        }
    },
    {
        "$group": {
            "_id": "$cust.customer_unique_id",
            "first_purchase_date": {"$min": "$order_purchase_timestamp"},
            "last_purchase_date": {"$max": "$order_purchase_timestamp"},
            "total_orders_before_T0": {"$sum": 1},
            "total_monetary_before_T0": {"$sum": {"$sum": "$payments.payment_value"}}
        }
    }
]
df_feat = pd.DataFrame(list(db.olist_orders_clean.aggregate(pipeline_features)))

pipeline_target = [
    {"$match": {"order_purchase_timestamp": {"$gte": T0, "$lt": T_target}}},
    {
        "$lookup": {
            "from": "olist_customers_clean",
            "localField": "customer_id",
            "foreignField": "customer_id",
            "as": "cust"
        }
    },
    {"$unwind": "$cust"},
    {"$group": {"_id": "$cust.customer_unique_id"}}
]
repeat_buyers = set(doc["_id"] for doc in db.olist_orders_clean.aggregate(pipeline_target))

df_feat["customer_unique_id"] = df_feat["_id"]
df_feat["recency_days"] = (T0 - pd.to_datetime(df_feat["last_purchase_date"])).dt.days
df_feat["tenure_days"] = (T0 - pd.to_datetime(df_feat["first_purchase_date"])).dt.days
df_feat["target_repurchase_90d"] = df_feat["customer_unique_id"].apply(lambda x: 1 if x in repeat_buyers else 0)

cols = ["customer_unique_id", "tenure_days", "recency_days", "total_orders_before_T0", "total_monetary_before_T0", "target_repurchase_90d"]
df_feat[cols].round(2).to_csv("./handover_tho/customer_features_T0_90d.csv", index=False)

# Xuất bảng địa lý hợp lệ cho Thọ
geo_docs = list(db.geo_by_zip.find({"usable_for_geo": True}, {"_id": 0}))
pd.DataFrame(geo_docs).to_csv("./handover_tho/geo_by_zip_valid.csv", index=False)
print(f" -> [OK] Đã xuất {len(df_feat)} đặc trưng khách hàng sang './handover_tho/customer_features_T0_90d.csv'")

# ---------------------------------------------------------------------
# PHẦN 3: BÀN GIAO CHO NGÂN (EDA - 10 Collection Sạch)
# ---------------------------------------------------------------------
print("\n[3/3] Đang trích xuất gói bàn giao cho Ngân (EDA)...")

collections_ngan = [
    "olist_orders_clean", "olist_customers_clean", "olist_order_items_clean",
    "olist_order_payments_clean", "olist_order_reviews_clean", "olist_products_clean",
    "olist_sellers_clean", "geo_by_zip", "product_category_name_translation_clean"
]

for coll_name in collections_ngan:
    docs = list(db[coll_name].find({}, {"_id": 0}))
    if docs:
        pd.DataFrame(docs).to_csv(f"./handover_ngan/{coll_name}.csv", index=False)

print(" -> [OK] Đã xuất toàn bộ bộ dữ liệu sạch sang './handover_ngan/'")
print("\n=== HOÀN TẤT BÀN GIAO CHO TÂM, THỌ VÀ NGÂN ===")