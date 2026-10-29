"""Shared score ranking for evaluation and CSV inference."""
import numpy as np
import pandas as pd


def validate_threshold(value):
    value = float(value)
    if not np.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Prediction threshold must be finite and within [0, 1]')
    return value


def positive_probability(model, features):
    classes = list(model.classes_)
    if set(classes) != {0, 1}:
        raise ValueError('Expected classes 0=repurchase and 1=no repurchase')
    values = np.asarray(model.predict_proba(features))[:, classes.index(1)]
    if not np.isfinite(values).all() or ((values < 0) | (values > 1)).any():
        raise ValueError('Invalid churn probability')
    return values


def score_deciles(probability):
    """Decile 1 is highest risk; resolve tied scores by input order."""
    scores = pd.Series(probability)
    if scores.isna().any() or not scores.between(0, 1).all():
        raise ValueError("Invalid churn probability")
    if scores.empty:
        return pd.Series(dtype="int64", index=scores.index)
    rank = scores.rank(ascending=False, method="first")
    return (np.floor((rank - 1) * 10 / len(scores)) + 1).astype(int)
