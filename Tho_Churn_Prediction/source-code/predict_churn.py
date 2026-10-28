"""Score caller-supplied pre-cutoff features with a saved churn pipeline."""
from argparse import ArgumentParser
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd

from prediction_utils import score_deciles

PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = PROJECT_DIR / "outputs/temporal_v3_provisional/random_forest_temporal.joblib"


def model_schema(bundle, model_name):
    features = bundle.get("features") or bundle.get("model_features")
    if not features or "pipeline" not in bundle:
        raise ValueError("Model thiếu pipeline hoặc danh sách feature")
    threshold = float(bundle.get("threshold", 0.5))
    if not np.isfinite(threshold) or not 0 <= threshold <= 1:
        raise ValueError("Ngưỡng model phải nằm trong [0, 1]")
    pipeline = bundle["pipeline"]
    fitted_names = list(getattr(pipeline, "feature_names_in_", features))
    if set(fitted_names) != set(features):
        raise ValueError("Danh sách feature không khớp pipeline đã fit")
    classes = list(pipeline.classes_)
    if set(classes) != {0, 1}:
        raise ValueError("Model phải có nhãn 0=mua lại, 1=không mua lại")
    version = bundle.get("model_version") or bundle.get("metrics", {}).get("version")
    if version is None:
        version = (model_name + "_provisional") if "features" in bundle else "legacy_group_split"
    return list(features), threshold, version, classes.index(1)


def predict_customers(bundle, data, model_name="supplied_model"):
    features, threshold, version, positive_index = model_schema(bundle, model_name)
    required = set(features) | {"frequency", "recency"}
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Thiếu cột feature: {sorted(missing)}")
    output = data.copy()
    frequency = pd.to_numeric(data["frequency"], errors="coerce")
    recency = pd.to_numeric(data["recency"], errors="coerce")
    valid_frequency = np.isfinite(frequency) & frequency.ge(2) & frequency.eq(frequency.round())
    eligible = valid_frequency & np.isfinite(recency) & recency.between(0, 180)
    if "eligibility_status" in data:
        # An explicit exclusion by the feature builder must not be overridden.
        status = data.eligibility_status.astype("string").str.strip()
        eligible &= status.isna() | status.eq("") | status.eq("du_dieu_kien")
    output["eligibility_status"] = np.where(eligible, "du_dieu_kien", "khong_du_dieu_kien")
    output["churn_probability"] = np.nan
    output["repurchase_probability"] = np.nan
    output["predicted_churn"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    output["score_decile"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    output["prediction_threshold"] = np.nan
    output["risk_level"] = pd.Series(pd.NA, index=data.index, dtype="string")
    output["risk_label_status"] = pd.Series(pd.NA, index=data.index, dtype="string")
    output["model_version"] = version
    output["feature_data_status"] = "caller_supplied_pre_cutoff_features"
    if eligible.any():
        inputs = output.loc[eligible, features].copy()
        preprocessor = bundle["pipeline"].named_steps.get("preprocess")
        if preprocessor is None:
            preprocessor = bundle["pipeline"].named_steps.get("preprocessor")
        numeric = bundle.get("numeric_features")
        if numeric is None:
            numeric = next((list(cols) for name, _, cols in preprocessor.transformers_ if name == "numeric"), [])
        for column in numeric:
            values = inputs[column]
            parsed = pd.to_numeric(values, errors="coerce")
            if (values.notna() & parsed.isna()).any() or np.isinf(parsed).any():
                raise ValueError(f"Feature số không hợp lệ: {column}")
            inputs[column] = parsed
        probabilities = bundle["pipeline"].predict_proba(inputs)[:, positive_index]
        probability = pd.Series(probabilities, index=inputs.index)
        prediction = (probability >= threshold).astype(int)
        output.loc[eligible, "churn_probability"] = probability
        output.loc[eligible, "repurchase_probability"] = 1 - probability
        output.loc[eligible, "predicted_churn"] = prediction
        output.loc[eligible, "score_decile"] = score_deciles(probability)
        output.loc[eligible, "prediction_threshold"] = threshold
        output.loc[eligible, "risk_level"] = np.where(prediction.eq(1), "cao", "thap")
        output.loc[eligible, "risk_label_status"] = "tham_khao_chua_hieu_chuan"
    return output


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output", type=Path, default=PROJECT_DIR / "outputs/new_customer_predictions.csv")
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    if args.input.resolve() == args.output.resolve():
        raise ValueError("Đường dẫn output phải khác input để giữ file feature gốc")
    bundle = joblib.load(args.model)
    result = predict_customers(bundle, pd.read_csv(args.input, low_memory=False), args.model.stem)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig", lineterminator="\n")
    count = int(result.eligibility_status.eq("du_dieu_kien").sum())
    print(f"Đã xử lý {len(result):,} dòng; {count:,} dòng đủ điều kiện.")
    print("Kết quả thử nghiệm; người tạo features chịu trách nhiệm nguồn và mốc thời gian trước cutoff.")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
