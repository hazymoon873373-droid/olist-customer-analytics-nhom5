from argparse import ArgumentParser
from pathlib import Path
import sys

import numpy as np
import pandas as pd


PREDICTION_DAYS = 180
ACTIVE_DAYS = 180
MIN_ORDERS = 2

REQUIRED_COLUMNS = [
    "order_id",
    "customer_unique_id",
    "order_status",
    "order_purchase_timestamp",
    "order_delivered_customer_date",
    "total_products_value",
    "total_freight_value",
    "total_items",
    "max_installments",
    "customer_state",
    "region_name",
]


def load_order_master(input_path):
    df = pd.read_csv(input_path, usecols=REQUIRED_COLUMNS, low_memory=False)
    df["order_purchase_timestamp"] = pd.to_datetime(
        df["order_purchase_timestamp"], errors="coerce"
    )
    df["order_delivered_customer_date"] = pd.to_datetime(
        df["order_delivered_customer_date"], errors="coerce"
    )

    numeric_columns = [
        "total_products_value",
        "total_freight_value",
        "total_items",
        "max_installments",
    ]
    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    return df.drop_duplicates(subset="order_id", keep="last")


def get_monthly_snapshots(orders):
    delivered = orders[orders["order_status"].eq("delivered")]
    first_date = delivered["order_purchase_timestamp"].min()
    last_date = delivered["order_purchase_timestamp"].max()

    first_allowed = first_date + pd.Timedelta(days=ACTIVE_DAYS)
    last_allowed = last_date - pd.Timedelta(days=PREDICTION_DAYS)
    first_month = first_allowed.to_period("M").to_timestamp() + pd.offsets.MonthBegin(1)
    last_month = last_allowed.to_period("M").to_timestamp()

    month_starts = pd.date_range(first_month, last_month, freq="MS")
    return [date + pd.Timedelta(days=1) - pd.Timedelta(seconds=1) for date in month_starts]


def build_customer_snapshot(
    orders,
    snapshot_date,
    prediction_days=PREDICTION_DAYS,
    active_days=ACTIVE_DAYS,
    min_orders=MIN_ORDERS,
):
    prediction_end = snapshot_date + pd.Timedelta(days=prediction_days)
    delivered = orders[orders["order_status"].eq("delivered")].copy()
    history = delivered[
        delivered["order_purchase_timestamp"].le(snapshot_date)
        & delivered["order_delivered_customer_date"].le(snapshot_date)
    ].copy()
    history = history.dropna(
        subset=["customer_unique_id", "order_purchase_timestamp"]
    )
    if history.empty:
        return pd.DataFrame()

    history = history.sort_values(
        ["customer_unique_id", "order_purchase_timestamp", "order_id"]
    )
    history["days_from_snapshot"] = (
        snapshot_date - history["order_purchase_timestamp"]
    ).dt.total_seconds() / 86400
    history["days_between_orders"] = (
        history.groupby("customer_unique_id")["order_purchase_timestamp"]
        .diff()
        .dt.total_seconds()
        / 86400
    )

    customer = history.groupby("customer_unique_id").agg(
        last_purchase_date=("order_purchase_timestamp", "max"),
        first_purchase_date=("order_purchase_timestamp", "min"),
        frequency=("order_id", "nunique"),
        monetary=("total_products_value", "sum"),
        avg_items_per_order=("total_items", "mean"),
        avg_freight_value=("total_freight_value", "mean"),
        total_freight_value=("total_freight_value", "sum"),
        avg_installments=("max_installments", "mean"),
        avg_days_between_orders=("days_between_orders", "mean"),
    )

    customer["recency"] = (
        snapshot_date - customer["last_purchase_date"]
    ).dt.total_seconds() / 86400
    customer["customer_tenure_days"] = (
        snapshot_date - customer["first_purchase_date"]
    ).dt.total_seconds() / 86400
    customer["avg_order_value"] = customer["monetary"] / customer["frequency"]
    customer["freight_to_product_ratio"] = np.where(
        customer["monetary"].gt(0),
        customer["total_freight_value"] / customer["monetary"],
        np.nan,
    )

    for days in (30, 90, 180):
        window = history[history["days_from_snapshot"].lt(days)]
        summary = window.groupby("customer_unique_id").agg(
            **{
                f"orders_last_{days}d": ("order_id", "nunique"),
                f"spend_last_{days}d": ("total_products_value", "sum"),
            }
        )
        customer = customer.join(summary, how="left")

    window_columns = [
        "orders_last_30d",
        "orders_last_90d",
        "orders_last_180d",
        "spend_last_30d",
        "spend_last_90d",
        "spend_last_180d",
    ]
    customer[window_columns] = customer[window_columns].fillna(0)

    latest_location = (
        history.drop_duplicates("customer_unique_id", keep="last")
        .set_index("customer_unique_id")[["customer_state", "region_name"]]
    )
    customer = customer.join(latest_location, how="left")
    customer = customer[
        customer["frequency"].ge(min_orders) & customer["recency"].le(active_days)
    ].copy()
    if customer.empty:
        return pd.DataFrame()

    future = delivered[
        delivered["order_purchase_timestamp"].gt(snapshot_date)
        & delivered["order_purchase_timestamp"].le(prediction_end)
    ]
    returning_customers = set(future["customer_unique_id"].dropna())
    customer["churn_proxy_180d"] = (
        ~customer.index.to_series().isin(returning_customers)
    ).astype(int)
    customer["snapshot_date"] = snapshot_date.normalize()
    customer["prediction_window_end"] = prediction_end.normalize()

    output_columns = [
        "snapshot_date",
        "prediction_window_end",
        "recency",
        "frequency",
        "monetary",
        "orders_last_30d",
        "orders_last_90d",
        "orders_last_180d",
        "spend_last_30d",
        "spend_last_90d",
        "spend_last_180d",
        "avg_order_value",
        "customer_tenure_days",
        "avg_days_between_orders",
        "avg_items_per_order",
        "avg_freight_value",
        "freight_to_product_ratio",
        "avg_installments",
        "customer_state",
        "region_name",
        "churn_proxy_180d",
    ]
    customer = customer[output_columns].reset_index()
    customer["sample_id"] = (
        customer["customer_unique_id"]
        + "_"
        + customer["snapshot_date"].dt.strftime("%Y%m%d")
    )
    return customer


def build_rolling_churn_table(orders, snapshot_dates=None):
    if snapshot_dates is None:
        snapshot_dates = get_monthly_snapshots(orders)

    snapshots = []
    for snapshot_date in snapshot_dates:
        snapshot = build_customer_snapshot(orders, pd.Timestamp(snapshot_date))
        if not snapshot.empty:
            snapshots.append(snapshot)

    if not snapshots:
        raise ValueError("Không tạo được mẫu customer-snapshot hợp lệ")

    result = pd.concat(snapshots, ignore_index=True)
    first_columns = [
        "sample_id",
        "customer_unique_id",
        "snapshot_date",
        "prediction_window_end",
    ]
    remaining_columns = [column for column in result.columns if column not in first_columns]
    result = result[first_columns + remaining_columns]

    round_columns = [
        column
        for column in result.select_dtypes(include="number").columns
        if column != "churn_proxy_180d"
    ]
    result[round_columns] = result[round_columns].round(4)
    return result.sort_values(["snapshot_date", "customer_unique_id"]).reset_index(
        drop=True
    )


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    repo_dir = project_dir.parent
    parser = ArgumentParser(description="Tạo dữ liệu churn theo nhiều snapshot")
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
        default=project_dir / "data" / "customer_churn_180d.csv",
    )
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    if not args.input.exists():
        raise FileNotFoundError(f"Không tìm thấy file đầu vào: {args.input}")

    orders = load_order_master(args.input)
    churn_table = build_rolling_churn_table(orders)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    churn_table.to_csv(
        args.output,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )

    label_count = churn_table["churn_proxy_180d"].value_counts().sort_index()
    print("=" * 60)
    print("TẠO DỮ LIỆU CHURN THEO NHIỀU SNAPSHOT")
    print(f"Số snapshot: {churn_table['snapshot_date'].nunique():,}")
    print(f"Số khách hàng: {churn_table['customer_unique_id'].nunique():,}")
    print(f"Số mẫu customer-snapshot: {len(churn_table):,}")
    print(f"Quay lại (0): {label_count.get(0, 0):,}")
    print(f"Churn proxy (1): {label_count.get(1, 0):,}")
    print(f"Tỷ lệ churn: {churn_table['churn_proxy_180d'].mean():.2%}")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
