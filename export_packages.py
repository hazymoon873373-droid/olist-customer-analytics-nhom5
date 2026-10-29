"""Export clean MongoDB collections without changing the database.

The ML team creates its own 180-day labels from these clean tables. This
export deliberately does not create an independent, incompatible target.
"""
from argparse import ArgumentParser
import json
import os
from pathlib import Path

import pandas as pd

COLLECTIONS = [
    "olist_orders_clean", "olist_customers_clean", "olist_order_items_clean",
    "olist_order_payments_clean", "olist_order_reviews_clean", "olist_products_clean",
    "olist_sellers_clean", "geo_by_zip", "product_category_name_translation_clean",
]


def build_order_summary(orders, customers, items, payments, reviews):
    """Return one row per order; child tables are aggregated before joining."""
    for frame, key, label in [(orders, "order_id", "orders"),
                               (customers, "customer_id", "customers")]:
        if frame[key].isna().any() or frame[key].duplicated().any():
            raise ValueError(f"Missing or duplicate {key} in {label}")
    for frame, columns in [(items, ["order_id", "order_item_id"]),
                            (payments, ["order_id", "payment_sequential"])]:
        if frame[columns].isna().any().any() or frame.duplicated(columns).any():
            raise ValueError(f"Missing or duplicate key: {columns}")
    items = items.copy()
    payments = payments.copy()
    reviews = reviews.copy()
    if 'review_before_purchase' not in reviews.columns:
        raise ValueError('Clean reviews require review_before_purchase; export refused')
    review_flags=reviews['review_before_purchase'].astype('string').str.strip().str.lower()
    if not review_flags.isin(['true','false']).all():
        raise ValueError('Invalid or missing review_before_purchase flag')
    reviews=reviews.loc[review_flags.eq('false')].copy()
    for frame, cols in [(items, ["price", "freight_value"]),
                        (payments, ["payment_value", "payment_installments"]), (reviews, ["review_score"])]:
        for col in cols:
            frame[col] = pd.to_numeric(frame[col], errors="raise")
    item_totals = items.groupby("order_id").agg(
        total_items_qty=("order_item_id", "size"),
        total_goods_value=("price", lambda s: s.sum(min_count=1)),
        total_freight_value=("freight_value", lambda s: s.sum(min_count=1)),
    )
    pay_totals = payments.groupby("order_id").payment_value.sum(min_count=1).rename("total_payment_value")
    pay_detail = payments.groupby("order_id").agg(max_installments=("payment_installments", "max"))
    main_payment = (payments.sort_values(["order_id", "payment_value", "payment_sequential"], ascending=[True, False, True])
                    .drop_duplicates("order_id").set_index("order_id").payment_type.rename("main_payment_type"))
    review_avg = reviews.groupby("order_id").review_score.mean().rename("avg_review_score")
    result = orders.merge(customers[["customer_id", "customer_unique_id", "customer_state"]], on="customer_id", how="left", validate="many_to_one")
    if result.customer_unique_id.isna().any():
        raise ValueError("An order has no customer_unique_id")
    for totals in (item_totals, pay_totals, pay_detail, main_payment, review_avg):
        result = result.join(totals, on="order_id", validate="one_to_one")
    result["order_products_value"] = result.total_goods_value
    result["order_freight_value"] = result.total_freight_value
    result["total_items_count"] = result.total_items_qty
    return result


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--db", default="BigData")
    parser.add_argument("--output-dir", type=Path, default=Path("handover"))
    args = parser.parse_args()
    uri = os.environ.get("MONGODB_URI", "mongodb://localhost:27017/")
    from pymongo import MongoClient
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[args.db]
    names = set(db.list_collection_names())
    missing = set(COLLECTIONS) - names
    if missing:
        raise ValueError(f"Missing collections in {args.db}: {sorted(missing)}")
    frames = {}
    for name in COLLECTIONS:
        rows = list(db[name].find({}, {"_id": 0}))
        if not rows:
            raise ValueError(f"Empty collection: {name}")
        frames[name] = pd.DataFrame(rows).replace({"null": None, "": None})
    summary = build_order_summary(*(frames[n] for n in COLLECTIONS[:5]))
    for role in ("tam", "tho", "ngan"):
        dest = args.output_dir / role
        dest.mkdir(parents=True, exist_ok=True)
        for name, frame in frames.items():
            frame.to_csv(dest / f"{name}.csv", index=False, encoding="utf-8-sig")
        summary.to_csv(dest / "order_summary.csv", index=False, encoding="utf-8-sig")
    manifest = {"database": args.db, "order_summary_rows": len(summary),
                "collection_counts": {k: len(v) for k, v in frames.items()},
                "ml_labels": "not generated; use Tho's 180-day pipeline"}
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    client.close()


if __name__ == "__main__":
    main()
