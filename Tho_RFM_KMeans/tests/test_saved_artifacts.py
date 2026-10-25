import json
import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]


class SavedArtifactsTests(unittest.TestCase):
    def test_saved_model_matches_exported_labels(self):
        result_file = PROJECT_DIR / "outputs" / "rfm_customers_kmeans.csv"
        model_file = PROJECT_DIR / "models" / "rfm_kmeans_pipeline.joblib"
        metric_file = PROJECT_DIR / "outputs" / "model_metrics.json"

        result = pd.read_csv(result_file)
        bundle = joblib.load(model_file)
        predicted = bundle["pipeline"].predict(result[bundle["feature_columns"]])

        self.assertEqual(len(result), 93358)
        self.assertTrue(result["customer_unique_id"].is_unique)
        self.assertFalse(result[["cluster", "segment"]].isna().any().any())
        self.assertTrue(np.array_equal(predicted, result["cluster"].to_numpy()))

        with metric_file.open(encoding="utf-8") as file:
            metrics = json.load(file)
        self.assertEqual(metrics["selected_k"], 4)


if __name__ == "__main__":
    unittest.main()
