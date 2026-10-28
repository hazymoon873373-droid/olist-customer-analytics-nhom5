from argparse import ArgumentParser
from pathlib import Path
import sys

import joblib
import pandas as pd

from train_isolation_forest import add_anomaly_reasons


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    parser = ArgumentParser(description="Chấm điểm bất thường cho dữ liệu đơn hàng")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--model",
        type=Path,
        default=project_dir / "models" / "isolation_forest_order_pipeline.joblib",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=project_dir / "outputs" / "new_order_anomaly_scores.csv",
    )
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    bundle = joblib.load(args.model)
    data = pd.read_csv(args.input, low_memory=False)
    features = bundle["model_features"]
    missing_columns = [column for column in features if column not in data]
    if missing_columns:
        raise ValueError(f"Thiếu feature: {missing_columns}")
    if "valid_delay_kpi" not in data:
        raise ValueError("Thiếu cờ valid_delay_kpi; hãy chuẩn bị dữ liệu từ bảng đơn sạch")
    valid = data["valid_delay_kpi"].astype(str).str.lower().eq("true")
    data.loc[~valid, ["delivery_days", "late_days"]] = float("nan")

    pipeline = bundle["pipeline"]
    prediction = pipeline.predict(data[features])
    result = data.copy()
    result["anomaly_score"] = -pipeline.decision_function(data[features])
    result["is_anomaly"] = (prediction == -1).astype(int)
    result = add_anomaly_reasons(result, bundle["reason_thresholds"])
    result = result.sort_values("anomaly_score", ascending=False)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False, encoding="utf-8-sig")
    print(f"Đã chấm điểm {len(result):,} đơn hàng")
    print(f"Đã lưu: {args.output}")


if __name__ == "__main__":
    main()
