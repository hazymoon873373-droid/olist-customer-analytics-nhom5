from pathlib import Path
import json
import sys
import unittest

import joblib
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]
SOURCE_DIR = PROJECT_DIR / "source-code"
sys.path.insert(0, str(SOURCE_DIR))

from train_isolation_forest import MODEL_FEATURES


class TestModelArtifacts(unittest.TestCase):
    def test_model_bundle(self):
        model_path = PROJECT_DIR / "models" / "isolation_forest_order_pipeline.joblib"
        bundle = joblib.load(model_path)
        self.assertEqual(bundle["algorithm"], "Isolation Forest")
        self.assertEqual(bundle["model_features"], MODEL_FEATURES)

    def test_output_count_matches_metrics(self):
        metrics_path = PROJECT_DIR / "outputs" / "model_metrics.json"
        anomaly_path = PROJECT_DIR / "outputs" / "anomalous_orders.csv"
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        anomalies = pd.read_csv(anomaly_path)
        self.assertEqual(len(anomalies), metrics["anomaly_orders"])
        self.assertGreater(metrics["seed_7_42_jaccard"], 0.7)

    def test_anomaly_scores_are_sorted(self):
        data = pd.read_csv(PROJECT_DIR / "outputs" / "anomalous_orders.csv")
        self.assertTrue(data["anomaly_score"].is_monotonic_decreasing)
        self.assertTrue(data["is_anomaly"].eq(1).all())


if __name__ == "__main__":
    unittest.main()
