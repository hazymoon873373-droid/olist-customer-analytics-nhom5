from pathlib import Path
import json
import sys

import joblib
import numpy as np
import pandas as pd

from export_summary import export_summary
from prepare_rfm import MASTER_FILE, build_rfm, read_order_master

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "Tho_Shared"))
from load_orders import DATA_DIR, file_hash, source_metadata


def compare_rfm(left, right):
    keys = ["customer_unique_id", "recency", "frequency", "monetary"]
    if left.customer_unique_id.duplicated().any() or right.customer_unique_id.duplicated().any():
        raise ValueError("Trùng customer_unique_id trong bảng RFM")
    merged = left[keys].merge(right[keys], on="customer_unique_id", how="outer", indicator=True, suffixes=("_new", "_reference"), validate="one_to_one")
    same_keys = int(merged["_merge"].ne("both").sum())
    result = {"customers_new": len(left), "customers_reference": len(right), "unmatched_customers": same_keys}
    for name in ["recency", "frequency", "monetary"]:
        result[f"{name}_mismatches"] = int((merged[f"{name}_new"].round(2) != merged[f"{name}_reference"].round(2)).sum())
    return result


def main():
    project = Path(__file__).resolve().parents[1]
    rfm, reference_date = build_rfm(read_order_master(MASTER_FILE))
    reference_file = DATA_DIR / "rfm_table_tam_20261028.csv"
    reference = pd.read_csv(reference_file, low_memory=False)
    saved = pd.read_csv(project / "outputs" / "rfm_customers_kmeans.csv", low_memory=False)
    comparisons = {"tam": compare_rfm(rfm, reference), "saved_kmeans": compare_rfm(rfm, saved)}
    for values in comparisons.values():
        if values["unmatched_customers"] or any(values[f"{x}_mismatches"] for x in ["recency", "frequency", "monetary"]):
            raise ValueError(f"RFM không khớp: {values}")
    bundle = joblib.load(project / "models" / "rfm_kmeans_pipeline.joblib")
    aligned = saved.merge(rfm, on="customer_unique_id", suffixes=("_saved", ""), validate="one_to_one")
    prediction = bundle["pipeline"].predict(aligned[bundle["feature_columns"]])
    if not np.array_equal(prediction, aligned.kmeans_cluster.to_numpy()):
        raise ValueError("Nhãn K-Means không khớp model đã lưu")
    result = {
        "reference_date": str(reference_date.date()), "source_inputs": source_metadata(),
        "tam_rfm_file": reference_file.name, "tam_rfm_sha256": file_hash(reference_file),
        "comparisons": comparisons, "predictions_checked": len(prediction),
        "result": "R/F/M khớp; giữ model K-Means hiện tại, không train lại",
    }
    output = project / "outputs"
    (output / "rfm_source_check.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    metrics_file = output / "model_metrics.json"
    metrics = json.loads(metrics_file.read_text(encoding="utf-8"))
    metrics["source_validation"] = result
    metrics_file.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    export_summary(output)
    print(json.dumps(comparisons, ensure_ascii=False, indent=2))
    print(f"Đã kiểm tra dự đoán của {len(prediction):,} khách; giữ model K-Means hiện tại")


if __name__ == "__main__":
    main()
