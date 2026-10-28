from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd


SOURCE_DIR = Path(__file__).resolve().parents[1] / "source-code"
sys.path.insert(0, str(SOURCE_DIR))

from prepare_anomaly_data import MODEL_FEATURES, prepare_anomaly_orders


class TestPrepareAnomalyData(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame(
            {
                "order_id": ["o1", "o2", "o3"],
                "customer_unique_id": ["c1", "c2", "c3"],
                "order_status": ["delivered", "canceled", "delivered"],
                "order_purchase_timestamp": ["2024-01-01"] * 3,
                "order_delivered_customer_date": ["2024-01-10"] * 3,
                "customer_state": ["SP", "RJ", "MG"],
                "region_name": ["Sudeste"] * 3,
                "main_payment_type": ["credit_card"] * 3,
                "total_products_value": [100, 50, 0],
                "total_freight_value": [20, 10, 15],
                "total_items": [1, 1, 2],
                "max_installments": [2, 1, 1],
                "payment_records": [1, 1, 1],
                "delivery_days": [9, 9, 15],
                "delay_days": [-3, 2, 5],
            }
        )

    def test_only_delivered_orders_are_kept(self):
        result = prepare_anomaly_orders(self.data)
        self.assertEqual(set(result["order_id"]), {"o1", "o3"})

    def test_derived_features(self):
        result = prepare_anomaly_orders(self.data).set_index("order_id")
        self.assertEqual(result.loc["o1", "late_days"], 0)
        self.assertEqual(result.loc["o3", "late_days"], 5)
        self.assertAlmostEqual(result.loc["o1", "freight_to_product_ratio"], 0.2)
        self.assertTrue(np.isnan(result.loc["o3", "freight_to_product_ratio"]))

    def test_model_features_are_available(self):
        result = prepare_anomaly_orders(self.data)
        self.assertTrue(set(MODEL_FEATURES).issubset(result.columns))


if __name__ == "__main__":
    unittest.main()
