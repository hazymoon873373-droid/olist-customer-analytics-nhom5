from argparse import ArgumentParser
from pathlib import Path
import hashlib
import json
import sys

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score, classification_report, confusion_matrix,
    precision_recall_curve, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from export_temporal_summary import export_summary

matplotlib.use("Agg")
import matplotlib.pyplot as plt

VERSION = "rf_temporal_v2_provisional"
TEST_T0 = pd.Timestamp("2018-03-01 00:00:00")
BI_T0 = pd.Timestamp("2018-08-31 00:00:00")
OBSERVATION_END = pd.Timestamp("2018-08-31 00:00:00")
HORIZON = pd.Timedelta(days=180)
UNRESOLVED = {"created", "approved", "processing", "invoiced", "shipped"}
NUMERIC = [
    "recency", "frequency", "monetary", "orders_last_30d", "orders_last_90d",
    "orders_last_180d", "spend_last_30d", "spend_last_90d", "spend_last_180d",
    "avg_order_value", "customer_tenure_days", "avg_days_between_orders",
    "avg_items_per_order", "avg_freight_value", "freight_to_product_ratio",
]
CATEGORICAL = ["customer_state", "region_name"]
FEATURES = NUMERIC + CATEGORICAL


def file_hash(path):
    result = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def load_orders(master_path, clean_path):
    columns = [
        "order_id", "customer_unique_id", "order_status", "order_purchase_timestamp",
        "total_products_value", "total_freight_value", "total_items",
        "customer_state", "region_name",
    ]
    clean_columns = [
        "order_id", "order_status", "order_purchase_timestamp",
        "order_delivered_customer_date", "valid_delay_kpi",
    ]
    master = pd.read_csv(master_path, usecols=columns, low_memory=False, na_values=["null"])
    clean = pd.read_csv(clean_path, usecols=clean_columns, low_memory=False, na_values=["null"])
    if master.order_id.duplicated().any() or clean.order_id.duplicated().any():
        raise ValueError("Trùng order_id trong dữ liệu nguồn")
    orders = master.merge(clean, on="order_id", how="left", validate="one_to_one", suffixes=("", "_clean"), indicator=True)
    if not orders["_merge"].eq("both").all():
        raise ValueError("Có đơn không tìm thấy trong bảng sạch")
    if not orders.order_status.eq(orders.order_status_clean).all():
        raise ValueError("Trạng thái đơn giữa hai nguồn không khớp")
    for col in ["order_purchase_timestamp", "order_purchase_timestamp_clean", "order_delivered_customer_date"]:
        orders[col] = pd.to_datetime(orders[col], errors="coerce")
    if not orders.order_purchase_timestamp.equals(orders.order_purchase_timestamp_clean):
        raise ValueError("Thời gian mua giữa hai nguồn không khớp")
    for col in ["total_products_value", "total_freight_value", "total_items"]:
        orders[col] = pd.to_numeric(orders[col], errors="coerce")
    orders["valid_delay_kpi"] = orders.valid_delay_kpi.astype(str).str.lower().eq("true")
    return orders


def build_snapshot(orders, t0, observation_end=OBSERVATION_END, min_orders=2, active_days=180, label_known_by=None):
    t0 = pd.Timestamp(t0)
    end = t0 + HORIZON
    history = orders[
        orders.order_status.eq("delivered") & orders.valid_delay_kpi
        & orders.order_purchase_timestamp.lt(t0)
        & orders.order_delivered_customer_date.lt(t0)
        & orders.order_delivered_customer_date.ge(orders.order_purchase_timestamp)
    ].dropna(subset=["customer_unique_id", "order_id", "order_purchase_timestamp"]).copy()
    if history.empty:
        return pd.DataFrame()
    history = history.sort_values(["customer_unique_id", "order_purchase_timestamp", "order_id"])
    history["days_from_snapshot"] = (t0 - history.order_purchase_timestamp).dt.total_seconds() / 86400
    history["days_between_orders"] = history.groupby("customer_unique_id").order_purchase_timestamp.diff().dt.total_seconds() / 86400
    customers = history.groupby("customer_unique_id").agg(
        last_purchase=("order_purchase_timestamp", "max"),
        first_purchase=("order_purchase_timestamp", "min"),
        frequency=("order_id", "nunique"), monetary=("total_products_value", "sum"),
        avg_items_per_order=("total_items", "mean"), avg_freight_value=("total_freight_value", "mean"),
        total_freight=("total_freight_value", "sum"), avg_days_between_orders=("days_between_orders", "mean"),
    )
    customers["recency"] = (t0 - customers.last_purchase).dt.total_seconds() / 86400
    customers["customer_tenure_days"] = (t0 - customers.first_purchase).dt.total_seconds() / 86400
    customers["avg_order_value"] = customers.monetary / customers.frequency
    customers["freight_to_product_ratio"] = (customers.total_freight / customers.monetary.where(customers.monetary.gt(0)))
    for days in [30, 90, 180]:
        window = history[history.days_from_snapshot.le(days)]
        grouped = window.groupby("customer_unique_id").agg(
            **{f"orders_last_{days}d": ("order_id", "nunique"), f"spend_last_{days}d": ("total_products_value", "sum")}
        )
        customers = customers.join(grouped)
        customers[[f"orders_last_{days}d", f"spend_last_{days}d"]] = customers[[f"orders_last_{days}d", f"spend_last_{days}d"]].fillna(0)
    location = history.drop_duplicates("customer_unique_id", keep="last").set_index("customer_unique_id")[["customer_state", "region_name"]]
    customers = customers.join(location)
    customers = customers[customers.frequency.ge(min_orders)].copy()
    if active_days is not None:
        customers = customers[customers.recency.le(active_days)].copy()

    future = orders[orders.order_purchase_timestamp.ge(t0) & orders.order_purchase_timestamp.lt(end)]
    known_by = min(pd.Timestamp(label_known_by), pd.Timestamp(observation_end)) if label_known_by is not None else pd.Timestamp(observation_end)
    confirmed = (
        future.order_status.eq("delivered")
        & future.order_delivered_customer_date.notna()
        & future.order_delivered_customer_date.ge(future.order_purchase_timestamp)
        & future.order_delivered_customer_date.lt(known_by)
    )
    returned = set(future.loc[confirmed, "customer_unique_id"].dropna())
    pending_mask = future.order_status.isin(UNRESOLVED) | future.order_status.isna()
    pending_mask |= future.order_status.eq("delivered") & ~confirmed
    # Không có thời điểm hủy, nên không thể xác nhận nhãn train đã biết vào T0 test.
    if label_known_by is not None:
        pending_mask |= future.order_status.isin(["canceled", "unavailable"])
    pending = set(future.loc[pending_mask, "customer_unique_id"].dropna())
    customers["churn_proxy_180d"] = pd.Series(pd.NA, index=customers.index, dtype="Int64")
    customers["label_status_or_reason"] = "insufficient_followup"
    if end <= pd.Timestamp(observation_end):
        customers["label_status_or_reason"] = "observed"
        customers["churn_proxy_180d"] = 1
        pending_mask = customers.index.isin(pending) & ~customers.index.isin(returned)
        customers.loc[pending_mask, "churn_proxy_180d"] = pd.NA
        customers.loc[pending_mask, "label_status_or_reason"] = "unresolved_future_order"
        customers.loc[customers.index.isin(returned), "churn_proxy_180d"] = 0
    customers["snapshot_timestamp"] = t0
    customers["prediction_window_end"] = end
    customers = customers.reset_index()
    customers["sample_id"] = customers.customer_unique_id + "_" + t0.strftime("%Y%m%dT%H%M%S")
    return customers


def make_pipeline():
    preprocessor = ColumnTransformer([
        ("numeric", SimpleImputer(strategy="median", add_indicator=True), NUMERIC),
        ("category", Pipeline([
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]), CATEGORICAL),
    ])
    return Pipeline([
        ("preprocess", preprocessor),
        ("model", RandomForestClassifier(n_estimators=100, class_weight="balanced",
                                         random_state=42, n_jobs=-1)),
    ])


def score_metrics(y, probability, threshold=0.5):
    prediction = (probability >= threshold).astype(int)
    report = classification_report(y, prediction, labels=[0, 1], output_dict=True, zero_division=0)
    order = np.argsort(-probability, kind="stable")
    top_n = max(1, int(np.ceil(len(y) * 0.1)))
    prevalence = float(np.mean(y))
    metrics = {
        "rows": len(y), "return_0": int((y == 0).sum()), "no_repurchase_1": int((y == 1).sum()),
        "threshold": threshold, "classification_report": report,
        "confusion_matrix_actual_rows_predicted_columns_0_1": confusion_matrix(y, prediction, labels=[0, 1]).tolist(),
        "top_decile_ranked_by": "churn_probability", "top_decile_count": top_n,
        "top_decile_lift_churn_1": float(np.mean(y[order[:top_n]]) / prevalence) if prevalence else None,
    }
    if len(np.unique(y)) == 2:
        metrics["roc_auc_churn_1"] = float(roc_auc_score(y, probability))
        metrics["average_precision_churn_1"] = float(average_precision_score(y, probability))
        metrics["average_precision_repurchase_0"] = float(average_precision_score(1 - y, 1 - probability))
    else:
        metrics["roc_auc_churn_1"] = None
        metrics["average_precision_churn_1"] = None
        metrics["average_precision_repurchase_0"] = None
    return metrics


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    root = Path(__file__).resolve().parents[1]
    parser = ArgumentParser(description="Đánh giá Random Forest theo thời gian")
    parser.add_argument("--master", type=Path, default=root.parent / "Tho_RFM_KMeans/data/olist_powerbi_orders_master.csv")
    parser.add_argument("--clean-orders", type=Path, required=True)
    parser.add_argument("--observation-end", default=str(OBSERVATION_END))
    args = parser.parse_args()
    observation_end = pd.Timestamp(args.observation_end)
    if observation_end < BI_T0:
        raise ValueError("Mốc dữ liệu quan sát phải đến ít nhất cutoff BI 2018-08-31")
    orders = load_orders(args.master, args.clean_orders)
    snapshots = list(pd.date_range("2017-04-01", "2017-09-01", freq="MS")) + [TEST_T0]
    frames = [build_snapshot(orders, t0, observation_end, label_known_by=TEST_T0 if t0 < TEST_T0 else None) for t0 in snapshots]
    data = pd.concat(frames, ignore_index=True)
    if data.duplicated(["customer_unique_id", "snapshot_timestamp"]).any():
        raise ValueError("Trùng khóa customer_unique_id và snapshot_timestamp")
    data["split"] = np.where(data.snapshot_timestamp.eq(TEST_T0), "test", "train")
    data.loc[data.churn_proxy_180d.isna(), "split"] = "not_evaluated"
    train = data[data.split.eq("train")].copy()
    test = data[data.split.eq("test")].copy()
    if train.empty or test.empty or train.prediction_window_end.max() > TEST_T0:
        raise ValueError("Không đủ dữ liệu hoặc cửa sổ nhãn train kết thúc sau T0 test")
    if train.churn_proxy_180d.nunique() < 2:
        raise ValueError("Train không có đủ hai lớp")

    model = make_pipeline()
    model.fit(train[FEATURES], train.churn_proxy_180d.astype(int))
    prob = model.predict_proba(test[FEATURES])[:, 1]
    data["churn_probability"] = np.nan
    data["predicted_churn"] = pd.Series(pd.NA, index=data.index, dtype="Int64")
    data.loc[test.index, "churn_probability"] = prob
    data.loc[test.index, "predicted_churn"] = (prob >= 0.5).astype(int)
    metrics = score_metrics(test.churn_proxy_180d.astype(int).to_numpy(), prob)
    metrics.update({
        "version": VERSION, "source_status": "Tạm thời: chờ xác nhận dữ liệu và mốc theo dõi",
        "master_sha256": file_hash(args.master), "clean_orders_sha256": file_hash(args.clean_orders),
        "master_modified_time_utc": pd.Timestamp(args.master.stat().st_mtime, unit="s", tz="UTC").isoformat(),
        "clean_orders_modified_time_utc": pd.Timestamp(args.clean_orders.stat().st_mtime, unit="s", tz="UTC").isoformat(),
        "observation_end_exclusive": str(observation_end), "test_t0": str(TEST_T0),
        "train_max_label_end": str(train.prediction_window_end.max()),
        "train_rows": len(train), "train_customers": train.customer_unique_id.nunique(),
        "train_return_0": int(train.churn_proxy_180d.eq(0).sum()), "train_no_repurchase_1": int(train.churn_proxy_180d.eq(1).sum()),
        "test_customers": test.customer_unique_id.nunique(), "unevaluated_rows": int(data.split.eq("not_evaluated").sum()),
        "train_test_customer_overlap": len(set(train.customer_unique_id) & set(test.customer_unique_id)),
        "selection": "Dùng tham số mặc định RandomForest, class_weight=balanced, threshold 0.5; không tối ưu bằng test; chưa có CV theo thời gian do lịch sử ngắn.",
    })
    out = root / "outputs" / "temporal_v2_provisional"
    out.mkdir(parents=True, exist_ok=True)
    eval_cols = ["sample_id", "customer_unique_id", "snapshot_timestamp", "prediction_window_end", "churn_proxy_180d", "label_status_or_reason", "split", "churn_probability", "predicted_churn"] + FEATURES
    data[eval_cols].to_csv(out / "snapshot_evaluation.csv", index=False, encoding="utf-8-sig")
    (out / "metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    pd.DataFrame(metrics["classification_report"]).transpose().to_csv(out / "classification_report.csv", encoding="utf-8-sig")
    pd.DataFrame(metrics["confusion_matrix_actual_rows_predicted_columns_0_1"], index=["actual_return_0", "actual_no_repurchase_1"], columns=["predicted_return_0", "predicted_no_repurchase_1"]).to_csv(out / "confusion_matrix.csv", encoding="utf-8-sig")
    joblib.dump({"pipeline": model, "features": FEATURES, "model_version": VERSION, "threshold": 0.5, "metrics": metrics}, out / "random_forest_temporal.joblib", compress=3)
    features = model.named_steps["preprocess"].get_feature_names_out()
    pd.DataFrame({"feature": features, "importance": model.named_steps["model"].feature_importances_}).sort_values("importance", ascending=False).to_csv(out / "feature_importance.csv", index=False, encoding="utf-8-sig")
    if len(np.unique(test.churn_proxy_180d.astype(int))) == 2:
        precision, recall, thresholds = precision_recall_curve(test.churn_proxy_180d.astype(int), prob, pos_label=1)
        pd.DataFrame({"precision_churn_1": precision, "recall_churn_1": recall, "threshold": np.r_[thresholds, np.nan]}).to_csv(out / "precision_recall_churn_1.csv", index=False, encoding="utf-8-sig")

    charts = out / "charts"
    charts.mkdir(exist_ok=True)
    fig, ax = plt.subplots(figsize=(6, 5))
    matrix = np.array(metrics["confusion_matrix_actual_rows_predicted_columns_0_1"])
    im = ax.imshow(matrix, cmap="Blues")
    for row in range(2):
        for col in range(2):
            ax.text(col, row, str(matrix[row, col]), ha="center", va="center", color="white" if matrix[row, col] > matrix.max() / 2 else "black")
    ax.set_xticks([0, 1], ["Mua lại", "Không mua lại"])
    ax.set_yticks([0, 1], ["Mua lại", "Không mua lại"])
    ax.set_xlabel("Dự đoán")
    ax.set_ylabel("Thực tế")
    ax.set_title("Confusion matrix - test theo thời gian")
    fig.colorbar(im, ax=ax)
    fig.tight_layout()
    fig.savefig(charts / "confusion_matrix.png", dpi=160)
    plt.close(fig)
    if len(np.unique(test.churn_proxy_180d.astype(int))) == 2:
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.plot(recall, precision, color="#2A9D8F", label=f"AP lớp 1 = {metrics['average_precision_churn_1']:.3f}")
        ax.set_xlabel("Recall - không mua lại (1)")
        ax.set_ylabel("Precision - không mua lại (1)")
        ax.set_title("Precision-recall theo thời gian")
        ax.legend()
        fig.tight_layout()
        fig.savefig(charts / "precision_recall_churn_1.png", dpi=160)
        plt.close(fig)
    importance = pd.read_csv(out / "feature_importance.csv").head(15).sort_values("importance")
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(importance.feature, importance.importance, color="#457B9D")
    ax.set_title("15 feature quan trọng - Random Forest")
    fig.tight_layout()
    fig.savefig(charts / "feature_importance.png", dpi=160)
    plt.close(fig)

    counts = []
    scope_totals = []
    for minimum, active in [(1, None), (2, 180)]:
        total_customers = set()
        totals = {"rows": 0, "return_0": 0, "no_repurchase_1": 0, "unknown": 0}
        for t0 in snapshots:
            frame = build_snapshot(orders, t0, observation_end, minimum, active, TEST_T0 if t0 < TEST_T0 else None)
            counts.append({"scope": "at_least_1_delivered" if minimum == 1 else "at_least_2_active_180d", "snapshot_timestamp": t0, "rows": len(frame), "customers": frame.customer_unique_id.nunique(), "return_0": int(frame.churn_proxy_180d.eq(0).sum()), "no_repurchase_1": int(frame.churn_proxy_180d.eq(1).sum()), "unknown": int(frame.churn_proxy_180d.isna().sum())})
            total_customers.update(frame.customer_unique_id)
            totals["rows"] += len(frame)
            totals["return_0"] += int(frame.churn_proxy_180d.eq(0).sum())
            totals["no_repurchase_1"] += int(frame.churn_proxy_180d.eq(1).sum())
            totals["unknown"] += int(frame.churn_proxy_180d.isna().sum())
        scope_totals.append({"scope": "at_least_1_delivered" if minimum == 1 else "at_least_2_active_180d", "unique_customers": len(total_customers), **totals})
    pd.DataFrame(counts).to_csv(out / "scope_comparison.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(scope_totals).to_csv(out / "scope_totals.csv", index=False, encoding="utf-8-sig")

    eligible = build_snapshot(orders, BI_T0, observation_end)
    eligible["churn_probability"] = model.predict_proba(eligible[FEATURES])[:, 1]
    eligible["risk_level"] = np.where(eligible.churn_probability.ge(0.5), "cao", "thap")
    eligible["eligibility_status"] = "du_dieu_kien"
    universe = orders.loc[orders.order_purchase_timestamp.lt(BI_T0), ["customer_unique_id"]].dropna().drop_duplicates()
    bi = universe.merge(eligible[["customer_unique_id", "churn_probability", "risk_level", "eligibility_status"]], on="customer_unique_id", how="left", validate="one_to_one")
    bi["eligibility_status"] = bi.eligibility_status.fillna("khong_du_dieu_kien")
    kmeans_path = root.parent / "Tho_RFM_KMeans/outputs/rfm_customers_kmeans.csv"
    kmeans = pd.read_csv(kmeans_path, usecols=["customer_unique_id", "kmeans_cluster", "kmeans_segment"])
    bi = bi.merge(kmeans, on="customer_unique_id", how="left", validate="one_to_one")
    bi["cutoff_timestamp"] = BI_T0
    bi["model_version"] = VERSION
    bi["source_version"] = file_hash(args.master)[:12] + "-" + file_hash(args.clean_orders)[:12]
    bi["churn_proxy_180d"] = pd.NA
    bi["label_status_or_reason"] = "insufficient_followup"
    bi.to_csv(out / "bi_web_customers.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(metrics, ensure_ascii=False, indent=2))
    print(f"BI/web: {len(bi):,} khách; đủ điều kiện: {len(eligible):,}")
    export_summary(out)


if __name__ == "__main__":
    main()
