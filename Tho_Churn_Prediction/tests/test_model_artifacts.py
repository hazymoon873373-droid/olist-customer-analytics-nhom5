import unittest
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


PROJECT_DIR = Path(__file__).resolve().parents[1]


class ModelArtifactTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = joblib.load(
            PROJECT_DIR / "models" / "random_forest_churn_pipeline.joblib"
        )
        cls.dataset = pd.read_csv(PROJECT_DIR / "data" / "customer_churn_180d.csv")
        cls.predictions = pd.read_csv(
            PROJECT_DIR / "outputs" / "test_predictions.csv"
        )
        cls.split_table = pd.read_csv(
            PROJECT_DIR / "outputs" / "train_test_split.csv"
        )

    def test_model_does_not_use_identifier_or_target(self):
        features = set(self.bundle["model_features"])
        self.assertNotIn("customer_unique_id", features)
        self.assertNotIn("churn_proxy_180d", features)
        self.assertNotIn("snapshot_date", features)
        self.assertNotIn("prediction_window_end", features)

    def test_exported_probabilities_match_saved_model(self):
        sample = self.predictions.head(25)
        source = self.dataset.set_index("sample_id").loc[sample["sample_id"]]
        probability = self.bundle["pipeline"].predict_proba(
            source[self.bundle["model_features"]]
        )[:, 1]
        np.testing.assert_allclose(
            probability,
            sample["churn_probability"].to_numpy(),
            rtol=1e-7,
            atol=1e-9,
        )

    def test_exported_labels_use_saved_threshold(self):
        expected = (
            self.predictions["churn_probability"] >= self.bundle["threshold"]
        ).astype(int)
        pd.testing.assert_series_equal(
            expected.reset_index(drop=True),
            self.predictions["predicted_churn"].reset_index(drop=True),
            check_names=False,
        )

    def test_customer_does_not_appear_in_both_sets(self):
        train_customers = set(
            self.split_table.loc[
                self.split_table["split"].eq("train"), "customer_unique_id"
            ]
        )
        test_customers = set(
            self.split_table.loc[
                self.split_table["split"].eq("test"), "customer_unique_id"
            ]
        )
        self.assertFalse(train_customers & test_customers)

    def test_split_is_close_to_80_20(self):
        test_rate = self.split_table["split"].eq("test").mean()
        self.assertGreater(test_rate, 0.17)
        self.assertLess(test_rate, 0.23)


if __name__ == "__main__":
    unittest.main()
