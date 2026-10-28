from argparse import ArgumentParser
from pathlib import Path
import sys

import joblib
import pandas as pd


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    parser = ArgumentParser(description="Dự đoán churn từ file feature khách hàng")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--model",
        type=Path,
        default=project_dir / "models" / "random_forest_churn_pipeline.joblib",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "outputs" / "new_customer_predictions.csv",
    )
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    bundle = joblib.load(args.model)
    data = pd.read_csv(args.input)
    missing_columns = set(bundle["model_features"]) - set(data.columns)
    if missing_columns:
        raise ValueError(f"Thiếu cột feature: {sorted(missing_columns)}")

    output = data.copy()
    frequency = pd.to_numeric(output["frequency"], errors="coerce")
    recency = pd.to_numeric(output["recency"], errors="coerce")
    eligible = frequency.ge(2) & recency.between(0, 180)
    output["eligibility_status"] = "khong_du_dieu_kien"
    output.loc[eligible, "eligibility_status"] = "du_dieu_kien"
    output["churn_probability"] = float("nan")
    output["predicted_churn"] = pd.Series(pd.NA, index=output.index, dtype="Int64")
    output["prediction_threshold"] = float("nan")
    if eligible.any():
        churn_probability = bundle["pipeline"].predict_proba(output.loc[eligible, bundle["model_features"]])[:, 1]
        output.loc[eligible, "churn_probability"] = churn_probability
        output.loc[eligible, "predicted_churn"] = (churn_probability >= bundle["threshold"]).astype(int)
        output.loc[eligible, "prediction_threshold"] = bundle["threshold"]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Đã dự đoán {len(output):,} khách hàng")
    print("Lưu ý: model cũ dùng để đối chiếu, không dùng tích hợp chính thức.")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
