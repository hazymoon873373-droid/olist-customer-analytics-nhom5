from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from anomaly_pages import load_anomalies, filter_anomalies, CONTRACT


class AnomalyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frame, cls.metrics = load_anomalies()

    def test_real_order_scope_and_saved_flags(self):
        self.assertEqual(len(self.frame),96478)
        self.assertTrue(self.frame.order_id.is_unique)
        self.assertEqual(int(self.frame.is_anomaly.sum()),965)
        self.assertEqual(len(filter_anomalies(self.frame)),965)

    def test_filters_keep_empty_scope_and_customer_lookup(self):
        self.assertTrue(filter_anomalies(self.frame,'does-not-exist').empty)
        selected=filter_anomalies(self.frame,states=['SP'])
        self.assertTrue(selected.customer_state.eq('SP').all())
        customer=self.frame.iloc[0].customer_unique_id
        self.assertTrue(filter_anomalies(self.frame,customer).customer_unique_id.eq(customer).all())

    def test_tampered_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder)/'order_anomaly_scores.csv').write_text('order_id\nx\n')
            with self.assertRaisesRegex(ValueError,'đã thay đổi'):
                load_anomalies(folder, CONTRACT)


if __name__=='__main__': unittest.main()
