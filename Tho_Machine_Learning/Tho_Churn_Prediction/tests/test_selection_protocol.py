from pathlib import Path
import sys
import unittest
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source-code'))
from temporal_selection import audit_fold, select_configuration, probability_summary
from prediction_utils import positive_probability, validate_threshold


def frame(t0, end, y=(0, 1)):
    return pd.DataFrame({'customer_unique_id': [f'c{i}' for i in range(len(y))],
        'snapshot_timestamp': pd.Timestamp(t0), 'prediction_window_end': pd.Timestamp(end),
        'churn_proxy_180d': list(y), 'x': np.arange(len(y)),
        'sample_id': [f'c{i}_{t0}' for i in range(len(y))]})


class ProtocolTests(unittest.TestCase):
    def test_unmatured_train_and_validation_are_rejected(self):
        train = frame('2017-04-01', '2017-09-28')
        val = frame('2017-09-01', '2018-02-28')
        with self.assertRaisesRegex(ValueError, 'train'):
            audit_fold(train, val, pd.Timestamp('2017-09-01'), pd.Timestamp('2018-03-01'), 1)
        with self.assertRaisesRegex(ValueError, 'validation'):
            audit_fold(frame('2017-01-01', '2017-06-30'), val,
                       pd.Timestamp('2017-09-01'), pd.Timestamp('2018-02-01'), 1)

    def test_single_class_training_blocks_tuning_without_fit(self):
        train = frame('2017-01-01', '2017-06-30', (1, 1))
        val = frame('2017-09-01', '2018-02-28')
        def forbidden():
            raise AssertionError('Must not fit when validation is infeasible')
        decision, audit, results = select_configuration(
            [(pd.Timestamp('2017-09-01'), train, val)], {'random_forest': forbidden},
            ['x'], pd.Timestamp('2018-03-01'), min_unique_per_class=1)
        self.assertEqual(decision['selection_status'], 'blocked_insufficient_temporal_validation')
        self.assertEqual(decision['selected_model'], 'random_forest')
        self.assertEqual(decision['threshold'], .5)
        self.assertEqual(audit.iloc[0].train_return_customers, 0)
        self.assertTrue(results.empty)

    def test_fit_uses_only_train_and_selects_from_validation(self):
        train = frame('2017-01-01', '2017-06-30')
        val = frame('2017-09-01', '2018-02-28')
        fitted = []
        class Fake:
            classes_ = np.array([0, 1])
            def fit(self, x, y):
                fitted.append(x.copy()); return self
            def predict_proba(self, x):
                return np.array([[.8, .2], [.2, .8]])
        decision, audit, results = select_configuration(
            [(pd.Timestamp('2017-09-01'), train, val)], {'random_forest': Fake},
            ['x'], pd.Timestamp('2018-03-01'), min_unique_per_class=1)
        self.assertTrue(audit.iloc[0].usable)
        self.assertEqual(len(fitted), 1)
        pd.testing.assert_frame_equal(fitted[0], train[['x']])
        self.assertEqual(decision['selection_status'], 'selected_on_temporal_validation')
        self.assertEqual(decision['selection_metric'], 'average_precision_repurchase_0')

    def test_count_customers_instead_of_repeated_snapshot_rows(self):
        train = pd.concat([frame('2017-01-01', '2017-06-30')] * 10)
        val = frame('2017-09-01', '2018-02-28')
        report = audit_fold(train, val, pd.Timestamp('2017-09-01'), pd.Timestamp('2018-03-01'), 2)
        self.assertEqual(report['train_return_customers'], 1)
        self.assertFalse(report['usable'])

    def test_positive_probability_uses_class_identity_and_validates(self):
        class Reversed:
            classes_ = np.array([1, 0])
            def predict_proba(self, x): return np.array([[.7, .3]])
        np.testing.assert_allclose(positive_probability(Reversed(), [[1]]), [.7])
        for value in [-.1, 1.1, np.nan, np.inf]:
            with self.assertRaises(ValueError): validate_threshold(value)

    def test_probability_diagnostics_include_actual_groups(self):
        report = probability_summary(np.array([0, 1]), np.array([.2, .9]), 'test', 'rf', .5)
        self.assertEqual(set(report.actual_class), {'all', '0', '1'})
        self.assertEqual(report.loc[report.actual_class.eq('all'), 'predicted_return'].iloc[0], 1)

    def test_constant_baseline_has_no_top_decile_ranking_advantage(self):
        from evaluate_temporal import score_metrics
        result = score_metrics(np.array([0, 1, 1, 1]), np.ones(4))
        self.assertEqual(result['top_decile_lift_churn_1'], 1.0)
        self.assertTrue(result['all_scores_equal'])


if __name__ == '__main__':
    unittest.main()
