from pathlib import Path
import json
import sys
import tempfile
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from load_orders import load_orders


class LoadOrdersTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.base = Path(self.folder.name)
        self.master = pd.DataFrame([{
            "order_id": "o1", "customer_id": "c1", "customer_unique_id": "u1",
            "order_status": "delivered", "order_purchase_timestamp": "3/1/2018 0:00",
            "customer_state": "SP", "order_products_value": 100, "order_freight_value": 10,
            "total_items_count": 1, "main_payment_type": "credit_card", "max_installments": 2,
            "valid_delay_kpi": False, "delivered_missing_date": True,
            "carrier_before_approval": False, "customer_before_carrier": False,
        }])
        self.clean = pd.DataFrame([{
            "order_id": "o1", "customer_id": "c1", "order_status": "delivered",
            "order_purchase_timestamp": "2018-03-01 00:00:37",
            "order_delivered_customer_date": None, "order_estimated_delivery_date": "2018-03-10",
            "valid_delay_kpi": False, "delivered_missing_date": True,
            "carrier_before_approval": False, "customer_before_carrier": False,
        }])
        self.payments = pd.DataFrame({"order_id": ["o1", "o1"], "payment_sequential": [1, 2]})
        self.customers = pd.DataFrame({"customer_id": ["c1"], "customer_unique_id": ["u1"], "customer_state": ["SP"]})
        self.items = pd.DataFrame({"order_id": ["o1"], "order_item_id": [1], "price": [100], "freight_value": [10]})
        regions = [{"sigla": "SP", "regiao": {"nome": "Sudeste"}}]
        regions += [{"sigla": f"X{i}", "regiao": {"nome": "Teste"}} for i in range(26)]
        (self.base / "ibge.json").write_text(json.dumps(regions), encoding="utf-8")
        self.write_sources()

    def tearDown(self):
        self.folder.cleanup()

    def write_sources(self):
        self.master.to_csv(self.base / "master.csv", sep="\t", encoding="cp1252", index=False)
        self.clean.to_csv(self.base / "clean.csv", index=False)
        self.payments.to_csv(self.base / "payments.csv", index=False)
        self.customers.to_csv(self.base / "customers.csv", index=False)
        self.items.to_csv(self.base / "items.csv", index=False)

    def load(self):
        return load_orders(self.base / "master.csv", self.base / "clean.csv",
                           self.base / "payments.csv", self.base / "ibge.json",
                           self.base / "customers.csv", self.base / "items.csv")

    def test_clean_seconds_missing_delivery_and_aggregated_payment(self):
        result = self.load().iloc[0]
        self.assertEqual(result.order_purchase_timestamp, pd.Timestamp("2018-03-01 00:00:37"))
        self.assertTrue(pd.isna(result.order_delivered_customer_date))
        self.assertFalse(result.valid_delay_kpi)
        self.assertEqual(result.payment_records, 2)
        self.assertEqual(result.total_products_value, 100)
        self.assertEqual(result.region_name, "Sudeste")

    def test_mismatched_flags_rejected(self):
        self.clean.loc[0, "valid_delay_kpi"] = True
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load()

    def test_mismatched_purchase_minute_rejected(self):
        self.clean.loc[0, "order_purchase_timestamp"] = "2018-03-01 00:01:37"
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load()

    def test_duplicate_payment_record_rejected(self):
        self.payments.loc[1, "payment_sequential"] = 1
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load()

    def test_wrong_customer_and_product_totals_are_rejected(self):
        self.customers.loc[0, "customer_unique_id"] = "wrong"
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load()
        self.customers.loc[0, "customer_unique_id"] = "u1"
        self.items.loc[0, "price"] = 101
        self.write_sources()
        with self.assertRaises(ValueError):
            self.load()


if __name__ == "__main__":
    unittest.main()
