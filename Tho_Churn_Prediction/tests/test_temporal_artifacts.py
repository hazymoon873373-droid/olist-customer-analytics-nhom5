from pathlib import Path
import json
import unittest

import joblib
import numpy as np
import pandas as pd


OUTPUT = Path(__file__).resolve().parents[1] / "outputs" / "temporal_v2_provisional"


class TemporalArtifactsTests(unittest.TestCase):
    def test_time_split_and_predictions_match_model(self):
        data = pd.read_csv(OUTPUT / "snapshot_evaluation.csv")
        bundle = joblib.load(OUTPUT / "random_forest_temporal.joblib")
        metrics = json.loads((OUTPUT / "metrics.json").read_text(encoding="utf-8"))
        train = data[data.split.eq("train")]
        test = data[data.split.eq("test")]
        self.assertFalse(data.duplicated(["customer_unique_id", "snapshot_timestamp"]).any())
        self.assertLessEqual(pd.to_datetime(train.prediction_window_end).max(), pd.to_datetime(test.snapshot_timestamp).min())
        self.assertEqual(len(test), metrics["rows"])
        np.testing.assert_allclose(bundle["pipeline"].predict_proba(test[bundle["features"]])[:, 1], test.churn_probability, rtol=1e-10, atol=1e-10)

    def test_bi_has_one_customer_and_no_probability_for_ineligible(self):
        data = pd.read_csv(OUTPUT / "bi_web_customers.csv")
        self.assertTrue(data.customer_unique_id.is_unique)
        self.assertEqual(data.cutoff_timestamp.nunique(), 1)
        excluded = data[data.eligibility_status.eq("khong_du_dieu_kien")]
        self.assertTrue(excluded.churn_probability.isna().all())
        self.assertTrue(excluded.risk_level.isna().all())
        self.assertTrue(data.churn_proxy_180d.isna().all())


if __name__ == "__main__":
    unittest.main()
