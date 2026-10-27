import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.pipeline import Pipeline


SOURCE_DIR = Path(__file__).resolve().parents[1] / "source-code"
sys.path.insert(0, str(SOURCE_DIR))

from train_kmeans import make_preprocessor, name_four_clusters


class KMeansPipelineTests(unittest.TestCase):
    def test_preprocessor_handles_zero_values(self):
        rfm = pd.DataFrame(
            {
                "recency": [1, 20, 100],
                "frequency": [1, 2, 4],
                "monetary": [0.0, 50.0, 500.0],
            }
        )
        transformed = make_preprocessor().fit_transform(rfm)

        self.assertEqual(transformed.shape, (3, 3))
        self.assertTrue(np.isfinite(transformed).all())

    def test_model_pipeline_predicts_from_raw_rfm(self):
        rfm = pd.DataFrame(
            {
                "recency": [1, 5, 100, 120, 250, 300],
                "frequency": [5, 4, 2, 2, 1, 1],
                "monetary": [500, 450, 200, 180, 20, 10],
            }
        )
        pipeline = Pipeline(
            [
                ("preprocessor", make_preprocessor()),
                ("kmeans", KMeans(n_clusters=3, random_state=42, n_init=10)),
            ]
        )
        pipeline.fit(rfm)
        labels = pipeline.predict(rfm)

        self.assertEqual(len(labels), len(rfm))

    def test_four_cluster_names_are_unique(self):
        profiles = pd.DataFrame(
            {
                "frequency_mean": [1.0, 1.1, 3.0, 1.0],
                "recency_mean": [300.0, 250.0, 100.0, 30.0],
                "monetary_mean": [30.0, 300.0, 250.0, 100.0],
            },
            index=[0, 1, 2, 3],
        )
        mapping = name_four_clusters(profiles)

        self.assertEqual(len(mapping), 4)
        self.assertEqual(len(set(mapping.values())), 4)


if __name__ == "__main__":
    unittest.main()
