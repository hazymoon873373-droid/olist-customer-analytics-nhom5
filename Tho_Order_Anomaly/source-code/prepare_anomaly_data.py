from argparse import ArgumentParser
from pathlib import Path
import sys

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "order_id",
    "customer_unique_id",
    "order_status",
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "customer_state",
    "region_name",
    "main_payment_type",
    "total_products_value",
    "total_freight_value",
    "total_items",
    "max_installments",
    "payment_records",
    "delivery_days",
    "delay_days",
]

MODEL_FEATURES = [
    "total_products_value",
    "total_freight_value",
    "freight_to_product_ratio",
    "total_items",
    "max_installments",
    "payment_records",
    "delivery_days",
    "late_days",
]


def load_order_master(input_path):
    data = pd.read_csv(input_path, usecols=REQUIRED_COLUMNS, low_memory=False)
    missing_columns = [
        column for column in REQUIRED_COLUMNS if column not in data.columns
    ]
    if missing_columns:
        raise ValueError(f"Thiếu cột dữ liệu: {missing_columns}")
    return data


def prepare_anomaly_orders(data):
    orders = data[data["order_status"].eq("delivered")].copy()
    orders = orders.drop_duplicates(subset="order_id", keep="last")

    numeric_columns = [
        "total_products_value",
        "total_freight_value",
        "total_items",
        "max_installments",
        "payment_records",
        "delivery_days",
        "delay_days",
    ]
    for column in numeric_columns:
        orders[column] = pd.to_numeric(orders[column], errors="coerce")

    orders["freight_to_product_ratio"] = np.where(
        orders["total_products_value"].gt(0),
        orders["total_freight_value"] / orders["total_products_value"],
        np.nan,
    )
    orders["late_days"] = orders["delay_days"].clip(lower=0)

    first_columns = [
        "order_id",
        "customer_unique_id",
        "order_purchase_timestamp",
        "order_delivered_customer_date",
        "customer_state",
        "region_name",
        "main_payment_type",
    ]
    output = orders[first_columns + MODEL_FEATURES].copy()
    output[MODEL_FEATURES] = output[MODEL_FEATURES].round(4)
    return output.sort_values("order_id").reset_index(drop=True)


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    repo_dir = project_dir.parent
    parser = ArgumentParser(description="Chuẩn bị dữ liệu phát hiện đơn hàng bất thường")
    parser.add_argument(
        "--input",
        type=Path,
        default=repo_dir
        / "Tho_RFM_KMeans"
        / "data"
        / "olist_powerbi_orders_master.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "data" / "order_anomaly_features.csv",
    )
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    orders = load_order_master(args.input)
    result = prepare_anomaly_orders(orders)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")

    print(f"Đã đọc: {len(orders):,} đơn hàng")
    print(f"Đơn delivered dùng cho mô hình: {len(result):,}")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
