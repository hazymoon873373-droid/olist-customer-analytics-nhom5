import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd


SOURCE_DIR = Path(__file__).resolve().parents[1] / "source-code"
sys.path.insert(0, str(SOURCE_DIR))

from prepare_churn_data import build_customer_churn_table


class PrepareChurnDataTest(unittest.TestCase):
    def setUp(self):
        self.snapshot = pd.Timestamp("2018-03-02 23:59:59")
        self.end_date = pd.Timestamp("2018-08-29 23:59:59")

    def make_order(
        self,
        order_id,
        customer_id,
        purchase_date,
        delivered_date,
        status="delivered",
        product_value=100.0,
        freight_value=20.0,
        items=1,
        installments=1,
    ):
        return {
            "order_id": order_id,
            "customer_unique_id": customer_id,
            "order_status": status,
            "order_purchase_timestamp": pd.Timestamp(purchase_date),
            "order_delivered_customer_date": (
                pd.Timestamp(delivered_date) if delivered_date else pd.NaT
            ),
            "total_products_value": product_value,
            "total_freight_value": freight_value,
            "total_items": items,
            "max_installments": installments,
            "customer_state": "SP",
            "region_name": "Sudeste",
        }

    def test_future_delivered_order_marks_customer_as_returning(self):
        orders = pd.DataFrame(
            [
                self.make_order("h1", "c1", "2018-01-01", "2018-01-05"),
                self.make_order("f1", "c1", "2018-08-29", "2018-09-02"),
            ]
        )
        result = build_customer_churn_table(orders, self.snapshot, self.end_date)
        self.assertEqual(result.loc[0, "churn_proxy_180d"], 0)

    def test_cancelled_and_late_orders_do_not_count_as_return(self):
        orders = pd.DataFrame(
            [
                self.make_order("h1", "c1", "2018-01-01", "2018-01-05"),
                self.make_order(
                    "f1", "c1", "2018-04-01", None, status="canceled"
                ),
                self.make_order("f2", "c1", "2018-08-30", "2018-09-02"),
            ]
        )
        result = build_customer_churn_table(orders, self.snapshot, self.end_date)
        self.assertEqual(result.loc[0, "churn_proxy_180d"], 1)

    def test_order_delivered_after_snapshot_is_not_used_as_history(self):
        orders = pd.DataFrame(
            [
                self.make_order("h1", "c1", "2018-01-01", "2018-01-05"),
                self.make_order("h2", "c2", "2018-02-20", "2018-03-10"),
            ]
        )
        result = build_customer_churn_table(orders, self.snapshot, self.end_date)
        self.assertEqual(result["customer_unique_id"].tolist(), ["c1"])

    def test_customer_features_are_calculated_from_history_only(self):
        orders = pd.DataFrame(
            [
                self.make_order(
                    "h1", "c1", "2018-01-01", "2018-01-05", product_value=100
                ),
                self.make_order(
                    "h2", "c1", "2018-02-01", "2018-02-05", product_value=200
                ),
                self.make_order(
                    "f1", "c1", "2018-04-01", "2018-04-05", product_value=999
                ),
            ]
        )
        result = build_customer_churn_table(orders, self.snapshot, self.end_date)
        row = result.iloc[0]
        self.assertEqual(row["frequency"], 2)
        self.assertEqual(row["monetary"], 300)
        self.assertEqual(row["avg_order_value"], 150)
        self.assertAlmostEqual(row["avg_days_between_orders"], 31)

    def test_single_order_customer_keeps_missing_order_gap(self):
        orders = pd.DataFrame(
            [self.make_order("h1", "c1", "2018-01-01", "2018-01-05")]
        )
        result = build_customer_churn_table(orders, self.snapshot, self.end_date)
        self.assertTrue(np.isnan(result.loc[0, "avg_days_between_orders"]))


if __name__ == "__main__":
    unittest.main()
