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
        legacy_model_file = PROJECT_DIR / "models" / "kmeans_rfm_pipeline.pkl"
        metric_file = PROJECT_DIR / "outputs" / "model_metrics.json"

        result = pd.read_csv(result_file)
        bundle = joblib.load(model_file)
        predicted = bundle["pipeline"].predict(result[bundle["feature_columns"]])

        self.assertEqual(len(result), 93358)
        self.assertTrue(result["customer_unique_id"].is_unique)
        self.assertFalse(result[["cluster", "segment"]].isna().any().any())
        self.assertTrue(np.array_equal(predicted, result["cluster"].to_numpy()))

        legacy_bundle = joblib.load(legacy_model_file)
        legacy_predicted = legacy_bundle["pipeline"].predict(
            result[legacy_bundle["feature_columns"]]
        )
        self.assertTrue(np.array_equal(legacy_predicted, result["cluster"].to_numpy()))

        for filename in [
            "Ketqua_KMeans.txt",
            "KMeans_Clusters_2D_PCA.png",
            "KMeans_Elbow_Silhouette.png",
            "KMeans_Recency_vs_Monetary.png",
            "rfm_kmeans_summary.xlsx",
        ]:
            self.assertTrue((PROJECT_DIR / "outputs" / filename).is_file())

        with metric_file.open(encoding="utf-8") as file:
            metrics = json.load(file)
        self.assertEqual(metrics["selected_k"], 4)


if __name__ == "__main__":
    unittest.main()
