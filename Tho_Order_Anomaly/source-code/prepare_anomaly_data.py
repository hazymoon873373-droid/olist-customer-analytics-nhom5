from argparse import ArgumentParser
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = [
    "order_id",
    "customer_unique_id",
    "order_status",
    "order_purchase_timestamp",
    "customer_state",
    "region_name",
    "main_payment_type",
    "total_products_value",
    "total_freight_value",
    "total_items",
    "max_installments",
    "payment_records",
]

CLEAN_COLUMNS = [
    "order_id", "order_status", "order_purchase_timestamp",
    "order_delivered_customer_date", "order_estimated_delivery_date",
    "valid_delay_kpi", "delivered_missing_date",
    "carrier_before_approval", "customer_before_carrier",
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


def prepare_anomaly_orders(data, clean_orders):
    if data["order_id"].duplicated().any() or clean_orders["order_id"].duplicated().any():
        raise ValueError("order_id bị trùng trong master hoặc bảng đơn sạch")
    clean = clean_orders[CLEAN_COLUMNS].copy()
    orders = data[REQUIRED_COLUMNS].merge(
        clean, on="order_id", how="left", suffixes=("", "_clean"),
        validate="one_to_one", indicator=True,
    )
    if not orders["_merge"].eq("both").all():
        raise ValueError("Có order_id không tìm thấy trong bảng đơn sạch")
    if not orders["order_status"].eq(orders["order_status_clean"]).all():
        raise ValueError("Trạng thái đơn giữa master và bảng sạch không khớp")
    purchase = pd.to_datetime(orders["order_purchase_timestamp"], errors="coerce")
    clean_purchase = pd.to_datetime(orders["order_purchase_timestamp_clean"], errors="coerce")
    if not purchase.equals(clean_purchase):
        raise ValueError("Thời gian mua giữa master và bảng sạch không khớp")
    orders = orders[orders["order_status"].eq("delivered")].copy()

    delivery = pd.to_datetime(orders["order_delivered_customer_date"], errors="coerce")
    estimated = pd.to_datetime(orders["order_estimated_delivery_date"], errors="coerce")
    purchase = pd.to_datetime(orders["order_purchase_timestamp_clean"], errors="coerce")
    valid = orders["valid_delay_kpi"].astype(str).str.lower().eq("true")
    valid &= delivery.notna() & estimated.notna() & purchase.notna()
    orders["valid_delay_kpi"] = valid
    orders["delivery_days"] = ((delivery - purchase).dt.total_seconds() / 86400).where(valid)
    orders["delay_days"] = ((delivery - estimated).dt.total_seconds() / 86400).where(valid)

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
        "valid_delay_kpi",
        "delivered_missing_date",
        "carrier_before_approval",
        "customer_before_carrier",
    ]
    output = orders[first_columns + MODEL_FEATURES].copy()
    output[MODEL_FEATURES] = output[MODEL_FEATURES].round(4)
    return output.sort_values("order_id").reset_index(drop=True)


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    repo_dir = project_dir.parent
    parser = ArgumentParser(description="Chuẩn bị dữ liệu phát hiện đơn hàng bất thường")
    parser.add_argument(
        "--clean-orders", type=Path, required=True,
        help="File olist_orders_clean.csv có cờ valid_delay_kpi",
    )
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
    clean_orders = pd.read_csv(args.clean_orders, low_memory=False, na_values=["null"])
    missing = [column for column in CLEAN_COLUMNS if column not in clean_orders]
    if missing:
        raise ValueError(f"Thiếu cột trong bảng đơn sạch: {missing}")
    result = prepare_anomaly_orders(orders, clean_orders)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")

    def sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    metadata = {
        "master_file": args.input.name,
        "master_sha256": sha256(args.input),
        "master_modified_time_utc": pd.Timestamp(args.input.stat().st_mtime, unit="s", tz="UTC").isoformat(),
        "clean_orders_file": args.clean_orders.name,
        "clean_orders_sha256": sha256(args.clean_orders),
        "clean_orders_modified_time_utc": pd.Timestamp(args.clean_orders.stat().st_mtime, unit="s", tz="UTC").isoformat(),
        "delivered_orders": len(result),
        "invalid_delay_kpi_orders": int((~result["valid_delay_kpi"]).sum()),
        "source_status": "Chờ nhóm xác nhận bản master và dữ liệu sạch chính thức",
    }
    (args.output.parent / "source_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"Đã đọc: {len(orders):,} đơn hàng")
    print(f"Đơn delivered dùng cho mô hình: {len(result):,}")
    print(f"Đơn không đủ điều kiện KPI giao hàng: {(~result['valid_delay_kpi']).sum():,}")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
