import sys
import unittest
from pathlib import Path

import pandas as pd


SOURCE_DIR = Path(__file__).resolve().parents[1] / "source-code"
sys.path.insert(0, str(SOURCE_DIR))

from prepare_rfm import build_rfm


class PrepareRFMTests(unittest.TestCase):
    def test_only_delivered_orders_are_used(self):
        orders = pd.DataFrame(
            [
                ["o1", "c1", "delivered", "2024-01-01", 100.0],
                ["o2", "c1", "canceled", "2024-01-05", 999.0],
                ["o3", "c2", "delivered", "2024-01-03", 50.0],
            ],
            columns=[
                "order_id",
                "customer_unique_id",
                "order_status",
                "order_purchase_timestamp",
                "total_products_value",
            ],
        )

        rfm, reference_date = build_rfm(orders)
        customer_1 = rfm.set_index("customer_unique_id").loc["c1"]

        self.assertEqual(reference_date, pd.Timestamp("2024-01-04"))
        self.assertEqual(customer_1["frequency"], 1)
        self.assertEqual(customer_1["monetary"], 100.0)
        self.assertEqual(customer_1["recency"], 3)

    def test_frequency_counts_unique_orders(self):
        orders = pd.DataFrame(
            [
                ["o1", "c1", "delivered", "2024-01-01", 10.0],
                ["o1", "c1", "delivered", "2024-01-01", 10.0],
                ["o2", "c1", "delivered", "2024-01-02", 20.0],
            ],
            columns=[
                "order_id",
                "customer_unique_id",
                "order_status",
                "order_purchase_timestamp",
                "total_products_value",
            ],
        )

        rfm, _ = build_rfm(orders)
        self.assertEqual(rfm.loc[0, "frequency"], 2)
        self.assertEqual(rfm.loc[0, "monetary"], 30.0)


if __name__ == "__main__":
    unittest.main()
