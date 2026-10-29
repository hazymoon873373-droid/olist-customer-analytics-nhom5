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
        self.assertFalse(result[["kmeans_cluster", "kmeans_segment"]].isna().any().any())
        self.assertTrue(np.array_equal(predicted, result["kmeans_cluster"].to_numpy()))

        for filename in [
            "Ketqua_KMeans.txt",
            "charts/05_kmeans_pca.png",
            "charts/01_k_evaluation.png",
            "charts/06_recency_monetary.png",
            "rfm_kmeans_summary.xlsx",
        ]:
            self.assertTrue((PROJECT_DIR / "outputs" / filename).is_file())

        with metric_file.open(encoding="utf-8") as file:
            metrics = json.load(file)
        self.assertEqual(metrics["selected_k"], 4)


if __name__ == "__main__":
    unittest.main()
