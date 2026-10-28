import importlib.util
from pathlib import Path
import unittest

import pandas as pd

spec = importlib.util.spec_from_file_location('export_packages', Path(__file__).resolve().parents[1] / 'export_packages.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.orders = pd.DataFrame([{'order_id':'o1','customer_id':'c1','valid_delay_kpi':False,'order_delivered_customer_date':None}])
        self.customers = pd.DataFrame([{'customer_id':'c1','customer_unique_id':'u1','customer_state':'SP'}])
        self.items = pd.DataFrame([{'order_id':'o1','order_item_id':1,'price':10,'freight_value':2}, {'order_id':'o1','order_item_id':2,'price':20,'freight_value':3}])
        self.payments = pd.DataFrame([{'order_id':'o1','payment_sequential':1,'payment_value':15,'payment_installments':1,'payment_type':'voucher'}, {'order_id':'o1','payment_sequential':2,'payment_value':20,'payment_installments':3,'payment_type':'credit_card'}])
        self.reviews = pd.DataFrame([{'order_id':'o1','review_score':'3'}, {'order_id':'o1','review_score':'5'}])

    def test_no_cross_product_and_missing_date_preserved(self):
        result = module.build_order_summary(self.orders, self.customers, self.items, self.payments, self.reviews)
        self.assertEqual(len(result), 1)
        row = result.iloc[0]
        self.assertEqual(row.customer_unique_id, 'u1')
        self.assertEqual(row.total_goods_value, 30)
        self.assertEqual(row.total_freight_value, 5)
        self.assertEqual(row.total_payment_value, 35)
        self.assertEqual(row.avg_review_score, 4)
        self.assertEqual(row.max_installments, 3)
        self.assertEqual(row.main_payment_type, 'credit_card')
        self.assertTrue(pd.isna(row.order_delivered_customer_date))

    def test_duplicate_items_are_rejected(self):
        items = pd.concat([self.items, self.items.iloc[[0]]], ignore_index=True)
        with self.assertRaises(ValueError):
            module.build_order_summary(self.orders, self.customers, items, self.payments, self.reviews)


if __name__ == '__main__':
    unittest.main()
