from pathlib import Path
import sys,unittest,json,hashlib,tempfile
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pandas as pd
from analytics_data import load_group_data,customer_snapshot,kpis,filter_orders,flags,DATA_DIR

class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.tables=load_group_data()
    def test_real_counts_and_missing_probability(self):
        customers=customer_snapshot(self.tables)
        self.assertEqual(len(customers),96096)
        self.assertTrue(customers.customer_unique_id.is_unique)
        self.assertEqual(customers.ml_status.eq('Được chấm').sum(),1170)
        self.assertEqual(customers.ml_status.eq('Chưa đủ điều kiện').sum(),94919)
        self.assertEqual(customers.ml_status.eq('Ngoài snapshot').sum(),7)
        self.assertTrue(customers.loc[customers.ml_status.ne('Được chấm'),'ml_churn_probability'].isna().all())
    def test_delivery_and_revenue_scope(self):
        k=kpis(self.tables['orders'])
        self.assertEqual(k['valid_deliveries'],95097)
        self.assertAlmostEqual(k['late_rate'],7793/95097)
        self.assertAlmostEqual(k['median_days'],10.2717824074)
        delivered=self.tables['items'].query("order_status=='delivered'")
        self.assertAlmostEqual(k['gmv'],delivered.price.sum(),places=6)
    def test_end_day_included_and_empty_scope(self):
        sample=pd.DataFrame({'order_purchase_timestamp':pd.to_datetime(['2018-08-01 23:59','2018-08-02 00:00']),'customer_state':['SP','RJ']})
        self.assertEqual(len(filter_orders(sample,'2018-08-01','2018-08-01')),1)
        self.assertIsNone(kpis(self.tables['orders'].iloc[:0])['late_rate'])
    def test_bad_flags_rejected(self):
        with self.assertRaises(ValueError):flags(pd.Series(['false','unknown']))
        self.assertEqual(flags(pd.Series([' TRUE ','false'])).tolist(),[True,False])
    def test_tampered_file_rejected_before_use(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            for name in ['integration_contract.json','manifest.json']:
                (root/name).write_bytes((DATA_DIR/name).read_bytes())
            (root/'olist_powerbi_orders_master.csv').write_text('order_id\nx\n')
            with patch('analytics_data.DATA_DIR',root),self.assertRaisesRegex(ValueError,'Dữ liệu đã thay đổi'):
                load_group_data()
    def test_manifest_matching_but_wrong_schema_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'integration_contract.json').write_bytes((DATA_DIR/'integration_contract.json').read_bytes())
            payload=b'order_id\nx\n'
            (root/'olist_powerbi_orders_master.csv').write_bytes(payload)
            manifest=json.loads((DATA_DIR/'manifest.json').read_text())
            manifest['output_sha256']['olist_powerbi_orders_master.csv']=hashlib.sha256(payload).hexdigest()
            (root/'manifest.json').write_text(json.dumps(manifest))
            with patch('analytics_data.DATA_DIR',root),self.assertRaisesRegex(ValueError,'Thiếu cột'):
                load_group_data()

if __name__=='__main__':unittest.main()
