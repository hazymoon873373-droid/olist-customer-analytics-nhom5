"""Shared score ranking for evaluation and CSV inference."""
import numpy as np
import pandas as pd


def score_deciles(probability):
    """Decile 1 is highest risk; resolve tied scores by input order."""
    scores = pd.Series(probability)
    if scores.isna().any() or not scores.between(0, 1).all():
        raise ValueError("Invalid churn probability")
    if scores.empty:
        return pd.Series(dtype="int64", index=scores.index)
    rank = scores.rank(ascending=False, method="first")
    return (np.floor((rank - 1) * 10 / len(scores)) + 1).astype(int)
