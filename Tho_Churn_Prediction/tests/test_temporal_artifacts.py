from pathlib import Path
import json
import unittest

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score


OUTPUT = Path(__file__).resolve().parents[1] / "outputs" / "temporal_v4_provisional"


class TemporalArtifactsTests(unittest.TestCase):
    def test_time_split_and_predictions_match_model(self):
        data = pd.read_csv(OUTPUT / "snapshot_evaluation.csv")
        bundle = joblib.load(OUTPUT / "selected_model.joblib")
        metrics = json.loads((OUTPUT / "metrics.json").read_text(encoding="utf-8"))
        train = data[data.split.eq("train")]
        test = data[data.split.eq("test")]
        self.assertFalse(data.duplicated(["customer_unique_id", "snapshot_timestamp"]).any())
        self.assertLessEqual(pd.to_datetime(train.prediction_window_end).max(), pd.to_datetime(test.snapshot_timestamp).min())
        self.assertEqual(len(test), metrics["rows"])
        np.testing.assert_allclose(bundle["pipeline"].predict_proba(test[bundle["features"]])[:, 1], test.churn_probability, rtol=1e-10, atol=1e-10)
        logistic = joblib.load(OUTPUT / "logistic_regression_temporal.joblib")
        np.testing.assert_allclose(logistic["pipeline"].predict_proba(test[logistic["features"]])[:, 1], test.logistic_churn_probability, rtol=1e-10, atol=1e-10)
        self.assertTrue(test.score_decile.between(1, 10).all())
        self.assertEqual(confusion_matrix(test.churn_proxy_180d, test.predicted_churn, labels=[0, 1]).tolist(), metrics["confusion_matrix_actual_rows_predicted_columns_0_1"])
        self.assertAlmostEqual(roc_auc_score(test.churn_proxy_180d, test.churn_probability), metrics["roc_auc_churn_1"])
        decision = json.loads((OUTPUT / "validation_protocol.json").read_text(encoding="utf-8"))
        self.assertEqual(bundle["model_name"], metrics["selected_model"])
        self.assertEqual(bundle["model_name"], decision["selected_model"])
        self.assertEqual(bundle["threshold"], metrics["threshold"])
        self.assertEqual(bundle["threshold"], decision["threshold"])
        self.assertFalse(decision["test_used_for_selection"])
        np.testing.assert_array_equal(test.predicted_churn, (test.churn_probability >= bundle["threshold"]).astype(int))

    def test_bi_has_one_customer_and_no_probability_for_ineligible(self):
        data = pd.read_csv(OUTPUT / "bi_web_customers.csv")
        self.assertTrue(data.customer_unique_id.is_unique)
        self.assertEqual(data.cutoff_timestamp.nunique(), 1)
        excluded = data[data.eligibility_status.eq("khong_du_dieu_kien")]
        self.assertTrue(excluded.churn_probability.isna().all())
        self.assertTrue(excluded.risk_level.isna().all())
        self.assertTrue(excluded.score_decile.isna().all())
        self.assertTrue(data.loc[data.eligibility_status.eq("du_dieu_kien"), "risk_label_status"].eq("tham_khao_chua_hieu_chuan").all())
        self.assertTrue(data.loc[data.kmeans_cluster.notna(), "kmeans_data_status"].eq("mo_ta_hoi_cuu_trang_thai_cuoi").all())
        self.assertTrue(data.churn_proxy_180d.isna().all())

    def test_bi_probabilities_and_labels_match_selected_model(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source-code'))
        import evaluate_temporal as module
        bundle = joblib.load(OUTPUT / 'selected_model.joblib')
        orders = module.load_orders(module.MASTER_FILE, module.CLEAN_ORDERS_FILE)
        eligible = module.build_snapshot(orders, module.BI_T0)
        expected = bundle['pipeline'].predict_proba(eligible[bundle['features']])[:, list(bundle['pipeline'].classes_).index(1)]
        bi = pd.read_csv(OUTPUT / 'bi_web_customers.csv').set_index('customer_unique_id').loc[eligible.customer_unique_id]
        np.testing.assert_allclose(bi.churn_probability, expected, atol=1e-10)
        np.testing.assert_array_equal(bi.predicted_churn, (expected >= bundle['threshold']).astype(int))
        self.assertTrue(bi.prediction_threshold.eq(bundle['threshold']).all())
        self.assertTrue(bi.model_name.eq(bundle['model_name']).all())

    def test_test_handoff_and_validation_rejection_evidence(self):
        frame = pd.read_csv(OUTPUT / 'test_predictions.csv')
        self.assertTrue(frame.customer_unique_id.is_unique)
        np.testing.assert_array_equal(frame.repurchased_true, 1-frame.churn_proxy_180d)
        self.assertTrue(frame.split.eq('test').all())
        protocol = json.loads((OUTPUT / 'validation_protocol.json').read_text(encoding='utf-8'))
        audit = pd.read_csv(OUTPUT / 'validation_fold_audit.csv')
        if protocol['selection_status'].startswith('blocked'):
            self.assertFalse(audit.usable.any())
            self.assertTrue(pd.read_csv(OUTPUT / 'validation_predictions.csv').empty)
            self.assertEqual(protocol['selected_model'], 'random_forest')


if __name__ == "__main__":
    unittest.main()
