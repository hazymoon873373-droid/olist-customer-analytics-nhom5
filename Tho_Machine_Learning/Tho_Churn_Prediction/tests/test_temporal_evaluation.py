from pathlib import Path
import sys
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "source-code"))
from evaluate_temporal import build_snapshot, score_metrics, score_deciles, make_logistic_pipeline


class TemporalLabelTests(unittest.TestCase):
    def test_deciles_descend_and_preserve_index(self):
        scores = pd.Series([0.1, 0.9, 0.9, 0.4], index=[8, 7, 6, 5])
        result = score_deciles(scores)
        self.assertEqual(result.loc[7], 1)
        self.assertEqual(result.loc[6], 3)
        self.assertEqual(result.loc[8], 8)
        self.assertTrue(result.between(1, 10).all())
        large = score_deciles(pd.Series(range(944), dtype=float) / 944)
        self.assertEqual(int(large.eq(1).sum()), 95)

    def test_logistic_preprocessing_is_inside_pipeline(self):
        pipeline = make_logistic_pipeline()
        self.assertEqual(pipeline.named_steps['model'].class_weight, 'balanced')
        self.assertIn('preprocess', pipeline.named_steps)

    def setUp(self):
        self.t0 = pd.Timestamp("2018-02-01")
        self.end = pd.Timestamp("2018-07-31")
        self.rows = [
            self.order("h1", "c1", "delivered", "2017-12-01", "2017-12-05"),
            self.order("h2", "c1", "delivered", "2018-01-01", "2018-01-05"),
        ]

    def order(self, order_id, customer, status, purchase, delivery=None, valid=True):
        return {
            "order_id": order_id, "customer_unique_id": customer, "order_status": status,
            "order_purchase_timestamp": pd.Timestamp(purchase),
            "order_delivered_customer_date": pd.Timestamp(delivery) if delivery else pd.NaT,
            "valid_delay_kpi": valid, "total_products_value": 100.0,
            "total_freight_value": 10.0, "total_items": 1.0,
            "customer_state": "SP", "region_name": "Sudeste",
        }

    def snapshot(self, extra=None, observation_end="2018-08-31", known_by=None):
        data = pd.DataFrame(self.rows + (extra or []))
        return build_snapshot(data, self.t0, observation_end, label_known_by=known_by).set_index("customer_unique_id")

    def test_return_at_t0_is_inside_and_window_end_is_outside(self):
        at_start = self.order("f1", "c1", "delivered", "2018-02-01", "2018-02-03")
        at_end = self.order("f2", "c1", "delivered", "2018-07-31", "2018-08-02")
        self.assertEqual(self.snapshot([at_start]).loc["c1", "churn_proxy_180d"], 0)
        self.assertEqual(self.snapshot([at_end]).loc["c1", "churn_proxy_180d"], 1)

    def test_insufficient_followup_and_unresolved_order(self):
        self.assertTrue(pd.isna(self.snapshot(observation_end="2018-06-01").loc["c1", "churn_proxy_180d"]))
        pending = self.order("f1", "c1", "shipped", "2018-03-01")
        self.assertEqual(self.snapshot([pending]).loc["c1", "label_status_or_reason"], "unresolved_future_order")
        self.assertTrue(pd.isna(self.snapshot([pending]).loc["c1", "churn_proxy_180d"]))

    def test_knowledge_cutoff_and_unknown_status(self):
        early = self.snapshot(known_by="2018-06-01").loc["c1"]
        self.assertTrue(pd.isna(early.churn_proxy_180d))
        self.assertEqual(early.label_status_or_reason, "insufficient_followup")
        unknown = self.order("f1", "c1", "unrecognized_status", "2018-03-01")
        self.assertTrue(pd.isna(self.snapshot([unknown]).loc["c1", "churn_proxy_180d"]))

    def test_empty_snapshot_preserves_handover_columns(self):
        data = pd.DataFrame(self.rows)
        result = build_snapshot(data, pd.Timestamp("2016-01-01"))
        self.assertTrue(result.empty)
        for column in ["customer_unique_id", "sample_id", "frequency", "churn_proxy_180d"]:
            self.assertIn(column, result.columns)

    def test_canceled_is_not_return_and_delivery_after_knowledge_cutoff_is_unknown(self):
        canceled = self.order("f1", "c1", "canceled", "2018-03-01")
        self.assertEqual(self.snapshot([canceled]).loc["c1", "churn_proxy_180d"], 1)
        late_delivery = self.order("f2", "c1", "delivered", "2018-03-01", "2018-08-01")
        self.assertTrue(pd.isna(self.snapshot([late_delivery], known_by="2018-07-31").loc["c1", "churn_proxy_180d"]))
        self.assertTrue(pd.isna(self.snapshot([canceled], known_by="2018-07-31").loc["c1", "churn_proxy_180d"]))

    def test_future_and_after_t0_delivery_do_not_change_features(self):
        before_but_delivered_later = self.order("h3", "c1", "delivered", "2018-01-31", "2018-02-02")
        future = self.order("f1", "c1", "delivered", "2018-03-01", "2018-03-03")
        first = self.snapshot().loc["c1"]
        second = self.snapshot([before_but_delivered_later, future]).loc["c1"]
        for col in ["frequency", "monetary", "recency", "orders_last_30d"]:
            self.assertEqual(first[col], second[col])

    def test_metrics_handle_single_class(self):
        import numpy as np
        result = score_metrics(np.array([1, 1]), np.array([0.6, 0.7]))
        self.assertIsNone(result["roc_auc_churn_1"])
        self.assertIsNone(result["average_precision_churn_1"])
        self.assertEqual(result["classification_report"]["accuracy"], 1.0)


if __name__ == "__main__":
    unittest.main()
