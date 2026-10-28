import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd


if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


REQUIRED_COLUMNS = [
    "order_id",
    "customer_unique_id",
    "order_status",
    "order_purchase_timestamp",
    "total_products_value",
]

RFM_REFERENCE_DATE = pd.Timestamp("2018-08-30")


def read_order_master(input_file):
    df = pd.read_csv(input_file, low_memory=False)
    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Thiếu cột trong order master: {missing_columns}")
    return df


def add_rfm_scores(rfm):
    # Recency càng nhỏ càng tốt, Monetary càng lớn càng tốt.
    recency_rank = rfm["recency"].rank(method="average", pct=True)
    monetary_rank = rfm["monetary"].rank(method="average", pct=True)

    rfm["r_score"] = (5 - np.ceil(recency_rank * 4)).clip(1, 4).astype(int)
    rfm["m_score"] = np.ceil(monetary_rank * 4).clip(1, 4).astype(int)

    frequency = rfm["frequency"]
    rfm["f_score"] = np.select(
        [frequency <= 1, frequency == 2, frequency == 3, frequency >= 4],
        [1, 2, 3, 4],
        default=1,
    ).astype(int)

    rfm["rfm_score"] = (
        rfm["r_score"].astype(str)
        + rfm["f_score"].astype(str)
        + rfm["m_score"].astype(str)
    )
    return rfm


def build_rfm(order_master, reference_date=RFM_REFERENCE_DATE):
    reference_date = pd.Timestamp(reference_date).normalize()
    df = order_master[REQUIRED_COLUMNS].copy()
    df = df[df["order_status"].eq("delivered")]

    df["order_purchase_timestamp"] = pd.to_datetime(
        df["order_purchase_timestamp"], errors="coerce"
    )
    df["total_products_value"] = pd.to_numeric(
        df["total_products_value"], errors="coerce"
    )

    df = df.dropna(
        subset=[
            "order_id",
            "customer_unique_id",
            "order_purchase_timestamp",
            "total_products_value",
        ]
    )
    df = df[
        df["order_purchase_timestamp"]
        < reference_date + pd.Timedelta(days=1)
    ]
    if df.empty:
        raise ValueError("Không còn đơn delivered hợp lệ để tính RFM")

    df = df.sort_values("order_purchase_timestamp").drop_duplicates("order_id", keep="last")

    rfm = (
        df.groupby("customer_unique_id", as_index=False)
        .agg(
            first_order=("order_purchase_timestamp", "min"),
            last_order=("order_purchase_timestamp", "max"),
            frequency=("order_id", "nunique"),
            monetary=("total_products_value", "sum"),
        )
        .sort_values("customer_unique_id")
        .reset_index(drop=True)
    )

    rfm.insert(
        1,
        "recency",
        (reference_date - rfm["last_order"].dt.normalize()).dt.days.astype(int),
    )
    rfm["frequency"] = rfm["frequency"].astype(int)
    rfm["monetary"] = rfm["monetary"].round(2)
    rfm = add_rfm_scores(rfm)

    return rfm, reference_date


def main():
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Tạo bảng RFM từ order master")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "data" / "olist_powerbi_orders_master.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "data" / "rfm_rebuilt.csv",
    )
    args = parser.parse_args()

    order_master = read_order_master(args.input)
    rfm, reference_date = build_rfm(order_master)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    rfm.to_csv(
        args.output,
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )

    print(f"Số đơn trong order master: {len(order_master):,}")
    print(f"Số khách hàng trong bảng RFM: {len(rfm):,}")
    print(f"Ngày tham chiếu: {reference_date.date()}")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
