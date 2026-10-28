from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import joblib
import numpy as np
import pandas as pd

PROJECT = Path(__file__).resolve().parents[1]
SOURCE = PROJECT / "source-code"
sys.path.insert(0, str(SOURCE))
from predict_churn import DEFAULT_MODEL, predict_customers


class PredictChurnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = joblib.load(DEFAULT_MODEL)
        cls.evaluation = pd.read_csv(DEFAULT_MODEL.parent / "snapshot_evaluation.csv")
        cls.test = cls.evaluation[cls.evaluation.split.eq("test")].copy()

    def test_temporal_predictions_match_all_saved_test_rows(self):
        result = predict_customers(self.bundle, self.test)
        np.testing.assert_allclose(result.churn_probability, self.test.churn_probability, atol=1e-10)
        np.testing.assert_allclose(result.repurchase_probability, 1 - result.churn_probability)
        self.assertTrue(result.model_version.eq(self.bundle["model_version"]).all())
        self.assertEqual(int(result.score_decile.eq(1).sum()), 95)

    def test_legacy_bundle_is_supported_explicitly(self):
        # Verify the old bundle schema without keeping obsolete artifacts.
        bundle = {"pipeline": self.bundle["pipeline"], "model_features": self.bundle["features"], "threshold": self.bundle["threshold"]}
        data = self.test.head(10)
        result = predict_customers(bundle, data)
        np.testing.assert_allclose(result.churn_probability, bundle["pipeline"].predict_proba(data[bundle["model_features"]])[:, 1])
        self.assertTrue(result.model_version.eq("legacy_group_split").all())

    def test_logistic_bundle_and_explicit_exclusion(self):
        bundle = joblib.load(DEFAULT_MODEL.parent / "logistic_regression_temporal.joblib")
        data = self.test.head(3).copy()
        data["eligibility_status"] = ["du_dieu_kien", "khong_du_dieu_kien", "du_dieu_kien"]
        data.loc[data.index[2], "frequency"] = 1
        result = predict_customers(bundle, data, "logistic_regression_temporal")
        expected = bundle["pipeline"].predict_proba(data.iloc[[0]][bundle["features"]])[0, 1]
        self.assertAlmostEqual(result.iloc[0].churn_probability, expected)
        for name in ["churn_probability", "predicted_churn", "prediction_threshold", "score_decile", "risk_level"]:
            self.assertTrue(result.iloc[1:][name].isna().all())

    def test_invalid_features_and_empty_input(self):
        with self.assertRaisesRegex(ValueError, "Thiếu cột"):
            predict_customers(self.bundle, self.test.drop(columns="monetary"))
        for value in ["broken", float("inf")]:
            data = self.test.head(1).copy().astype({"monetary": "object"})
            data.loc[data.index[0], "monetary"] = value
            with self.assertRaisesRegex(ValueError, "monetary"):
                predict_customers(self.bundle, data)
        empty = predict_customers(self.bundle, self.test.head(0))
        self.assertEqual(len(empty), 0)
        data = self.test.head(2).copy()
        data["frequency"] = [float("inf"), 2.5]
        self.assertTrue(predict_customers(self.bundle, data).churn_probability.isna().all())

    def test_cli_default_and_protect_input_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            input_file, output_file = path / "features.csv", path / "predictions.csv"
            sample = self.test.head(8)
            sample.to_csv(input_file, index=False, encoding="utf-8-sig")
            command = [sys.executable, "-X", "utf8", "-B", str(SOURCE / "predict_churn.py"), "--input", str(input_file), "--output", str(output_file)]
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(completed.returncode, 0, completed.stderr)
            result = pd.read_csv(output_file)
            np.testing.assert_allclose(result.churn_probability, sample.churn_probability, atol=1e-10)
            before = input_file.read_bytes()
            command[-1] = str(input_file)
            rejected = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
            self.assertNotEqual(rejected.returncode, 0)
            self.assertEqual(before, input_file.read_bytes())


if __name__ == "__main__":
    unittest.main()
