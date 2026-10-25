import argparse
import sys
from pathlib import Path

import joblib
import pandas as pd


if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def predict_clusters(model_file, input_file, output_file):
    bundle = joblib.load(model_file)
    df = pd.read_csv(input_file)
    feature_columns = bundle["feature_columns"]

    missing_columns = [col for col in feature_columns if col not in df.columns]
    if missing_columns:
        raise ValueError(f"Thiếu cột đầu vào: {missing_columns}")

    df["cluster"] = bundle["pipeline"].predict(df[feature_columns])
    df["segment"] = df["cluster"].map(bundle["cluster_mapping"])

    output_file.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(f"Đã gán cụm cho {len(df):,} khách hàng")
    print(f"Đã lưu: {output_file}")


def main():
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Gán cụm bằng model K-Means đã lưu")
    parser.add_argument(
        "--model",
        type=Path,
        default=project_dir / "models" / "rfm_kmeans_pipeline.joblib",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    predict_clusters(args.model, args.input, args.output)


if __name__ == "__main__":
    main()
