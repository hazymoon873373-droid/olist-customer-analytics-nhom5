"""Matured-label validation only. Test labels are never accepted by selection."""
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, f1_score
from prediction_utils import positive_probability, validate_threshold


def audit_fold(train, validation, validation_t0, decision_time, min_unique_per_class=5):
    validation_t0, decision_time = pd.Timestamp(validation_t0), pd.Timestamp(decision_time)
    if len(train) and (pd.to_datetime(train.prediction_window_end).gt(validation_t0).any()
                       or pd.to_datetime(train.snapshot_timestamp).ge(validation_t0).any()):
        raise ValueError('train labels/features are not available before validation')
    if len(validation) and (pd.to_datetime(validation.prediction_window_end).gt(decision_time).any()
                            or not pd.to_datetime(validation.snapshot_timestamp).eq(validation_t0).all()):
        raise ValueError('validation labels are not available at selection time')
    result = {'validation_t0': str(validation_t0), 'selection_known_by': str(decision_time),
              'train_rows': len(train), 'validation_rows': len(validation)}
    counts = []
    for name, frame in [('train', train), ('validation', validation)]:
        result[name + '_customers'] = int(frame.customer_unique_id.nunique())
        for label, tag in [(0, 'return'), (1, 'no_repurchase')]:
            count = int(frame.loc[frame.churn_proxy_180d.eq(label), 'customer_unique_id'].nunique())
            result[f'{name}_{tag}_customers'] = count
            counts.append(count)
    result['usable'] = bool(min(counts) >= min_unique_per_class)
    result['reason'] = 'usable' if result['usable'] else 'insufficient_distinct_customers_in_class'
    result['min_unique_per_class'] = min_unique_per_class
    return result


def select_configuration(folds, factories, features, decision_time, min_unique_per_class=5):
    """Select AP-return model, then F1-return threshold, using validation alone.

    Five distinct customers per class is a declared pilot guard, not a claim of
    statistical adequacy. Infeasible folds are recorded without fitting models.
    """
    audits, predictions = [], []
    for t0, train, validation in folds:
        audit = audit_fold(train, validation, t0, decision_time, min_unique_per_class)
        audits.append(audit)
        if not audit['usable']:
            continue
        for name, factory in factories.items():
            model = factory()
            model.fit(train[features], train.churn_proxy_180d.astype(int))
            probability = positive_probability(model, validation[features])
            for row, p in zip(validation.to_dict('records'), probability):
                predictions.append({'model': name, 'validation_t0': str(t0),
                    'customer_unique_id': row['customer_unique_id'], 'sample_id': row['sample_id'],
                    'actual': int(row['churn_proxy_180d']), 'churn_probability': float(p)})
    columns = ['model', 'validation_t0', 'customer_unique_id', 'sample_id', 'actual', 'churn_probability']
    results = pd.DataFrame(predictions, columns=columns)
    decision = {'selection_status': 'blocked_insufficient_temporal_validation',
        'selected_model': 'random_forest', 'threshold': .5,
        'selection_metric': 'average_precision_repurchase_0',
        'threshold_metric': 'f1_repurchase_0', 'decision_time': str(decision_time),
        'min_unique_per_class': min_unique_per_class,
        'candidate_threshold_grid': [float(round(x, 2)) for x in np.arange(.05, 1, .05)],
        'candidate_results': {}, 'test_used_for_selection': False,
        'test_previously_reviewed': True,
        'reason': 'No eligible two-class temporal validation; retain documented RF/0.5 baseline, do not tune on test.'}
    ranked = []
    for name in factories:
        frame = results[results.model.eq(name)]
        if frame.empty:
            continue
        y, p = frame.actual.to_numpy(), frame.churn_probability.to_numpy()
        ap = float(average_precision_score(1-y, 1-p))
        thresholds = []
        for threshold in decision['candidate_threshold_grid']:
            score = float(f1_score(y, (p >= threshold).astype(int), pos_label=0, zero_division=0))
            thresholds.append((score, -abs(threshold-.5), -threshold, threshold))
        best = max(thresholds)
        decision['candidate_results'][name] = {'validation_ap_repurchase_0': ap,
            'validation_f1_repurchase_0': best[0], 'threshold': best[3], 'rows': len(frame)}
        ranked.append((ap, best[0], -list(factories).index(name), name, best[3]))
    if ranked:
        _, _, _, name, threshold = max(ranked)
        decision.update(selection_status='selected_on_temporal_validation', selected_model=name,
                        threshold=validate_threshold(threshold), reason='Selected on matured temporal validation only; test remains an already-reviewed historical benchmark.')
    return decision, pd.DataFrame(audits), results


def probability_summary(y, probability, split, model, threshold):
    y, probability = np.asarray(y), np.asarray(probability)
    threshold = validate_threshold(threshold)
    records = []
    for label in ['all', '0', '1']:
        p = probability if label == 'all' else probability[y == int(label)]
        records.append({'split': split, 'model': model, 'actual_class': label,
            'count': len(p), 'threshold': threshold,
            'min': float(p.min()) if len(p) else None,
            'q25': float(np.quantile(p, .25)) if len(p) else None,
            'median': float(np.median(p)) if len(p) else None,
            'q75': float(np.quantile(p, .75)) if len(p) else None,
            'max': float(p.max()) if len(p) else None,
            'predicted_return': int((p < threshold).sum()),
            'predicted_no_repurchase': int((p >= threshold).sum())})
    return pd.DataFrame(records)
