import sys
import unittest
from pathlib import Path

import pandas as pd


SOURCE_DIR = Path(__file__).resolve().parents[1] / "source-code"
sys.path.insert(0, str(SOURCE_DIR))

from prepare_churn_data import build_customer_snapshot, build_rolling_churn_table


class PrepareChurnDataTest(unittest.TestCase):
    def make_order(
        self,
        order_id,
        customer_id,
        purchase_date,
        delivered_date,
        status="delivered",
        product_value=100.0,
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
            "total_freight_value": 20.0,
            "total_items": 1,
            "max_installments": 1,
            "customer_state": "SP",
            "region_name": "Sudeste",
        }

    def build_orders(self, future_status="delivered", future_date="2018-04-01"):
        return pd.DataFrame(
            [
                self.make_order("h1", "c1", "2017-12-01", "2017-12-05", product_value=100),
                self.make_order("h2", "c1", "2018-02-01", "2018-02-05", product_value=200),
                self.make_order(
                    "f1", "c1", future_date, "2018-04-05", status=future_status
                ),
            ]
        )

    def test_customer_needs_two_historical_orders(self):
        orders = pd.DataFrame(
            [self.make_order("h1", "c1", "2018-02-01", "2018-02-05")]
        )
        result = build_customer_snapshot(
            orders, pd.Timestamp("2018-03-01 23:59:59")
        )
        self.assertTrue(result.empty)

    def test_inactive_customer_is_not_in_snapshot(self):
        orders = pd.DataFrame(
            [
                self.make_order("h1", "c1", "2016-01-01", "2016-01-05"),
                self.make_order("h2", "c1", "2016-02-01", "2016-02-05"),
            ]
        )
        result = build_customer_snapshot(
            orders, pd.Timestamp("2018-03-01 23:59:59")
        )
        self.assertTrue(result.empty)

    def test_future_delivered_order_marks_customer_as_returning(self):
        result = build_customer_snapshot(
            self.build_orders(), pd.Timestamp("2018-03-01 23:59:59")
        )
        self.assertEqual(result.loc[0, "churn_proxy_180d"], 0)

    def test_cancelled_order_does_not_count_as_return(self):
        result = build_customer_snapshot(
            self.build_orders(future_status="canceled"),
            pd.Timestamp("2018-03-01 23:59:59"),
        )
        self.assertEqual(result.loc[0, "churn_proxy_180d"], 1)

    def test_order_delivered_after_snapshot_is_not_history(self):
        orders = pd.DataFrame(
            [
                self.make_order("h1", "c1", "2018-01-01", "2018-01-05"),
                self.make_order("h2", "c1", "2018-02-01", "2018-03-10"),
            ]
        )
        result = build_customer_snapshot(
            orders, pd.Timestamp("2018-03-01 23:59:59")
        )
        self.assertTrue(result.empty)

    def test_features_use_history_before_snapshot(self):
        result = build_customer_snapshot(
            self.build_orders(), pd.Timestamp("2018-03-01 23:59:59")
        )
        row = result.iloc[0]
        self.assertEqual(row["frequency"], 2)
        self.assertEqual(row["monetary"], 300)
        self.assertEqual(row["avg_order_value"], 150)
        self.assertEqual(row["orders_last_90d"], 1)

    def test_rolling_table_has_one_sample_per_customer_snapshot(self):
        orders = self.build_orders(future_date="2018-06-01")
        snapshots = [
            pd.Timestamp("2018-02-10 23:59:59"),
            pd.Timestamp("2018-03-01 23:59:59"),
        ]
        result = build_rolling_churn_table(orders, snapshot_dates=snapshots)
        self.assertEqual(result["sample_id"].nunique(), len(result))
        self.assertEqual(result["snapshot_date"].nunique(), 2)


if __name__ == "__main__":
    unittest.main()
