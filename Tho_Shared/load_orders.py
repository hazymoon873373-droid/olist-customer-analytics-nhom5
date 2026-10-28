from pathlib import Path
import hashlib
import json

import numpy as np
import pandas as pd


DATA_DIR = Path(__file__).resolve().parent / "data"
MASTER_FILE = DATA_DIR / "olist_powerbi_orders_master_20261028.csv"
CLEAN_ORDERS_FILE = DATA_DIR / "olist_orders_clean.csv"
PAYMENTS_FILE = DATA_DIR / "olist_order_payments_clean.csv"
CUSTOMERS_FILE = DATA_DIR / "olist_customers_clean.csv"
ITEMS_FILE = DATA_DIR / "olist_order_items_clean.csv"
IBGE_FILE = DATA_DIR / "ibge_states_raw.json"

QUALITY_FLAGS = [
    "valid_delay_kpi", "delivered_missing_date",
    "carrier_before_approval", "customer_before_carrier",
]
MASTER_COLUMNS = [
    "order_id", "customer_id", "customer_unique_id", "order_status",
    "order_purchase_timestamp", "customer_state", "order_products_value",
    "order_freight_value", "total_items_count", "main_payment_type",
    "max_installments", *QUALITY_FLAGS,
]
CLEAN_COLUMNS = [
    "order_id", "customer_id", "order_status", "order_purchase_timestamp",
    "order_delivered_customer_date", "order_estimated_delivery_date", *QUALITY_FLAGS,
]


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def boolean_flags(data, columns):
    for column in columns:
        text = data[column].astype(str).str.strip().str.lower()
        if not text.isin(["true", "false"]).all():
            raise ValueError(f"Cờ {column} có giá trị thiếu hoặc không hợp lệ")
        data[column] = text.eq("true")
    return data


def load_orders(master_path=MASTER_FILE, clean_orders_path=CLEAN_ORDERS_FILE,
                payments_path=PAYMENTS_FILE, ibge_path=IBGE_FILE,
                customers_path=CUSTOMERS_FILE, items_path=ITEMS_FILE):
    # Legacy BI master is tab/CP1252; Thien's handover is comma/UTF-8 BOM.
    with Path(master_path).open("rb") as file:
        header = file.readline()
    sep, encoding = ("\t", "cp1252") if b"\t" in header else (",", "utf-8-sig")
    master = pd.read_csv(master_path, sep=sep, encoding=encoding, usecols=MASTER_COLUMNS,
                         low_memory=False, na_values=["null"])
    clean = pd.read_csv(clean_orders_path, usecols=CLEAN_COLUMNS, low_memory=False, na_values=["null"])
    payments = pd.read_csv(payments_path, usecols=["order_id", "payment_sequential"], low_memory=False)
    customers = pd.read_csv(customers_path, usecols=["customer_id", "customer_unique_id", "customer_state"], low_memory=False, na_values=["null"])
    items = pd.read_csv(items_path, usecols=["order_id", "order_item_id", "price", "freight_value"], low_memory=False, na_values=["null"])
    if master.order_id.isna().any() or clean.order_id.isna().any():
        raise ValueError("Thiếu order_id trong master hoặc bảng đơn sạch")
    if master.order_id.duplicated().any() or clean.order_id.duplicated().any():
        raise ValueError("Trùng order_id trong master hoặc bảng đơn sạch")
    if payments.duplicated(["order_id", "payment_sequential"]).any():
        raise ValueError("Trùng khóa bản ghi thanh toán")
    if customers.customer_id.duplicated().any() or items.duplicated(["order_id", "order_item_id"]).any():
        raise ValueError("Trùng khóa khách hàng hoặc sản phẩm trong dữ liệu sạch")
    master = boolean_flags(master, QUALITY_FLAGS)
    clean = boolean_flags(clean, QUALITY_FLAGS)
    joined = master.merge(clean, on="order_id", how="outer", suffixes=("_master", "_clean"),
                          indicator=True, validate="one_to_one")
    if not joined["_merge"].eq("both").all():
        raise ValueError("Hai nguồn không có cùng tập order_id")
    for column in ["customer_id", "order_status", *QUALITY_FLAGS]:
        if not joined[f"{column}_master"].equals(joined[f"{column}_clean"]):
            raise ValueError(f"Cột {column} giữa master và bảng sạch không khớp")

    master_purchase = pd.to_datetime(joined.order_purchase_timestamp_master, format="mixed", errors="coerce")
    clean_purchase = pd.to_datetime(joined.order_purchase_timestamp_clean, format="mixed", errors="coerce")
    if master_purchase.isna().any() or clean_purchase.isna().any():
        raise ValueError("Thiếu hoặc sai ngày mua")
    matches = master_purchase.eq(clean_purchase) | master_purchase.eq(clean_purchase.dt.floor("min"))
    if not matches.all():
        raise ValueError("Ngày mua master không khớp bảng sạch (giây hoặc phút)")

    checked_customers = joined.merge(customers, left_on="customer_id_clean", right_on="customer_id",
                                    how="left", validate="many_to_one", suffixes=("_master", "_clean"), indicator="customer_join")
    if not checked_customers.customer_join.eq("both").all():
        raise ValueError("Có đơn thiếu khách hàng trong bảng sạch")
    for column in ["customer_unique_id", "customer_state"]:
        if not checked_customers[f"{column}_master"].equals(checked_customers[f"{column}_clean"]):
            raise ValueError(f"Cột {column} không khớp bảng khách sạch")

    totals = items.groupby("order_id").agg(
        product=("price", "sum"), freight=("freight_value", "sum"), items=("order_item_id", "count")
    )
    checked_items = master.join(totals, on="order_id")
    for master_column, clean_column in [("order_products_value", "product"), ("order_freight_value", "freight"), ("total_items_count", "items")]:
        a = pd.to_numeric(checked_items[master_column], errors="coerce").to_numpy(dtype=float)
        b = pd.to_numeric(checked_items[clean_column], errors="coerce").to_numpy(dtype=float)
        if not np.isclose(a, b, atol=1e-6, rtol=0, equal_nan=True).all():
            raise ValueError(f"Cột {master_column} không khớp tổng hợp bảng item sạch")

    regions = json.loads(Path(ibge_path).read_text(encoding="utf-8"))
    region_map = {row["sigla"]: row["regiao"]["nome"] for row in regions}
    if len(region_map) != 27:
        raise ValueError("Bảng vùng IBGE không có đủ 27 bang")
    joined["region_name"] = joined.customer_state.map(region_map)
    if joined.region_name.isna().any():
        raise ValueError("Có bang không tìm thấy trong bảng IBGE")
    payment_counts = payments.groupby("order_id").size().rename("payment_records")
    joined = joined.join(payment_counts, on="order_id")

    joined = joined.rename(columns={
        "customer_id_clean": "customer_id", "order_status_clean": "order_status",
        "order_purchase_timestamp_clean": "order_purchase_timestamp",
        "order_products_value": "total_products_value",
        "order_freight_value": "total_freight_value",
        "total_items_count": "total_items",
        **{f"{col}_clean": col for col in QUALITY_FLAGS},
    })
    joined["order_purchase_timestamp"] = clean_purchase
    for column in ["order_delivered_customer_date", "order_estimated_delivery_date"]:
        joined[column] = pd.to_datetime(joined[column], format="mixed", errors="coerce")
    for column in ["total_products_value", "total_freight_value", "total_items", "max_installments", "payment_records"]:
        joined[column] = pd.to_numeric(joined[column], errors="coerce")
    keep = [
        "order_id", "customer_id", "customer_unique_id", "order_status",
        "order_purchase_timestamp", "order_delivered_customer_date", "order_estimated_delivery_date",
        "customer_state", "region_name", "main_payment_type", "total_products_value",
        "total_freight_value", "total_items", "max_installments", "payment_records", *QUALITY_FLAGS,
    ]
    return joined[keep].copy()


def source_metadata(master_path=MASTER_FILE, clean_orders_path=CLEAN_ORDERS_FILE,
                    payments_path=PAYMENTS_FILE, ibge_path=IBGE_FILE,
                    customers_path=CUSTOMERS_FILE, items_path=ITEMS_FILE):
    paths = {
        "master": Path(master_path), "clean_orders": Path(clean_orders_path),
        "clean_payments": Path(payments_path), "ibge_states": Path(ibge_path),
        "clean_customers": Path(customers_path), "clean_items": Path(items_path),
    }
    return {
        name: {"file": path.name, "sha256": file_hash(path)}
        for name, path in paths.items()
    }
