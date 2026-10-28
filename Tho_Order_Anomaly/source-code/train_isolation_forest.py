from argparse import ArgumentParser
from pathlib import Path
import json
import sys

import joblib
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, RobustScaler


matplotlib.use("Agg")
import matplotlib.pyplot as plt


RANDOM_STATE = 42
CONTAMINATION = 0.01

LOG_FEATURES = [
    "total_products_value",
    "total_freight_value",
    "freight_to_product_ratio",
    "total_items",
]

OTHER_FEATURES = [
    "max_installments",
    "payment_records",
    "delivery_days",
    "late_days",
]

MODEL_FEATURES = LOG_FEATURES + OTHER_FEATURES

REASON_NAMES = {
    "total_products_value": "Gia_tri_san_pham_cao",
    "total_freight_value": "Phi_van_chuyen_cao",
    "freight_to_product_ratio": "Ty_le_phi_van_chuyen_cao",
    "total_items": "Nhieu_san_pham",
    "max_installments": "So_ky_tra_gop_cao",
    "payment_records": "Nhieu_ban_ghi_thanh_toan",
    "delivery_days": "Thoi_gian_giao_hang_dai",
    "late_days": "Giao_hang_tre_nhieu",
}


def build_pipeline(random_state=RANDOM_STATE):
    log_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "log",
                FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            ),
            ("scaler", RobustScaler()),
        ]
    )
    other_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", RobustScaler()),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("log_features", log_pipeline, LOG_FEATURES),
            ("other_features", other_pipeline, OTHER_FEATURES),
        ],
        verbose_feature_names_out=False,
    )
    model = IsolationForest(
        n_estimators=200,
        max_samples=4096,
        contamination=CONTAMINATION,
        random_state=random_state,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def get_reason_thresholds(data):
    return {
        column: float(data[column].quantile(0.99)) for column in MODEL_FEATURES
    }


def add_anomaly_reasons(scored_data, thresholds):
    result = scored_data.copy()

    def make_reason(row):
        reasons = [
            REASON_NAMES[column]
            for column in MODEL_FEATURES
            if pd.notna(row[column]) and row[column] >= thresholds[column]
        ]
        if row["is_anomaly"] == 1 and not reasons:
            reasons.append("Ket_hop_nhieu_dac_trung")
        return "; ".join(reasons)

    result["anomaly_reason"] = result.apply(make_reason, axis=1)
    return result


def make_feature_profile(scored_data):
    normal = scored_data[scored_data["is_anomaly"].eq(0)]
    anomaly = scored_data[scored_data["is_anomaly"].eq(1)]
    rows = []
    for column in MODEL_FEATURES:
        normal_median = float(normal[column].median())
        anomaly_median = float(anomaly[column].median())
        ratio = anomaly_median / normal_median if normal_median != 0 else np.nan
        rows.append(
            {
                "feature": column,
                "normal_median": normal_median,
                "anomaly_median": anomaly_median,
                "anomaly_to_normal_ratio": ratio,
            }
        )
    return pd.DataFrame(rows).round(4)


def count_reasons(anomalies):
    reasons = anomalies["anomaly_reason"].str.split("; ").explode()
    return (
        reasons.value_counts()
        .rename_axis("reason")
        .reset_index(name="order_count")
    )


def save_charts(scored_data, profile, reason_count, chart_dir):
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    counts = scored_data["is_anomaly"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(
        ["Bình thường", "Bất thường"],
        [counts.get(0, 0), counts.get(1, 0)],
        color=["#2A9D8F", "#E76F51"],
    )
    ax.bar_label(bars, fmt="{:,.0f}")
    ax.set_title("Phân bố kết quả Isolation Forest")
    ax.set_ylabel("Số đơn hàng")
    fig.tight_layout()
    fig.savefig(chart_dir / "01_anomaly_distribution.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(scored_data["anomaly_score"], bins=50, color="#457B9D")
    cutoff = scored_data.loc[
        scored_data["is_anomaly"].eq(1), "anomaly_score"
    ].min()
    ax.axvline(cutoff, color="#E76F51", linestyle="--", label="Ngưỡng bất thường")
    ax.set_title("Phân bố điểm bất thường")
    ax.set_xlabel("Anomaly score (cao hơn = bất thường hơn)")
    ax.set_ylabel("Số đơn hàng")
    ax.legend()
    fig.tight_layout()
    fig.savefig(chart_dir / "02_anomaly_score_distribution.png", dpi=160)
    plt.close(fig)

    normal_sample = scored_data[scored_data["is_anomaly"].eq(0)].sample(
        n=min(5000, counts.get(0, 0)), random_state=RANDOM_STATE
    )
    plot_data = pd.concat(
        [normal_sample, scored_data[scored_data["is_anomaly"].eq(1)]]
    )
    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(
        data=plot_data,
        x="delivery_days",
        y="late_days",
        hue="is_anomaly",
        palette={0: "#8ECAE6", 1: "#D62828"},
        alpha=0.65,
        s=28,
        ax=ax,
    )
    ax.set_title("Thời gian giao hàng và số ngày giao trễ")
    ax.set_xlabel("Thời gian giao hàng (ngày)")
    ax.set_ylabel("Số ngày giao trễ")
    ax.legend(title="Bất thường")
    fig.tight_layout()
    fig.savefig(chart_dir / "03_delivery_delay_scatter.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 6))
    sns.scatterplot(
        data=plot_data,
        x="total_products_value",
        y="freight_to_product_ratio",
        hue="is_anomaly",
        palette={0: "#8ECAE6", 1: "#D62828"},
        alpha=0.65,
        s=28,
        ax=ax,
    )
    ax.set_xscale("log")
    ax.set_yscale("symlog", linthresh=0.01)
    ax.set_title("Giá trị sản phẩm và tỷ lệ phí vận chuyển")
    ax.set_xlabel("Giá trị sản phẩm - thang log")
    ax.set_ylabel("Phí vận chuyển / giá trị sản phẩm")
    ax.legend(title="Bất thường")
    fig.tight_layout()
    fig.savefig(chart_dir / "04_freight_product_scatter.png", dpi=160)
    plt.close(fig)

    reason_plot = reason_count.sort_values("order_count")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(reason_plot["reason"], reason_plot["order_count"], color="#F4A261")
    ax.set_title("Các dấu hiệu thường gặp trong đơn bất thường")
    ax.set_xlabel("Số đơn hàng")
    fig.tight_layout()
    fig.savefig(chart_dir / "05_anomaly_reasons.png", dpi=160)
    plt.close(fig)

    profile_plot = profile.copy()
    profile_plot["anomaly_to_normal_ratio"] = profile_plot[
        "anomaly_to_normal_ratio"
    ].fillna(1)
    profile_plot = profile_plot.sort_values("anomaly_to_normal_ratio")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(
        profile_plot["feature"],
        profile_plot["anomaly_to_normal_ratio"],
        color="#264653",
    )
    ax.axvline(1, color="gray", linestyle="--")
    ax.set_title("Trung vị nhóm bất thường so với nhóm bình thường")
    ax.set_xlabel("Tỷ lệ trung vị bất thường / bình thường")
    fig.tight_layout()
    fig.savefig(chart_dir / "06_feature_profile.png", dpi=160)
    plt.close(fig)


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    parser = ArgumentParser(description="Huấn luyện Isolation Forest")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "data" / "order_anomaly_features.csv",
    )
    parser.add_argument("--project-dir", type=Path, default=project_dir)
    return parser.parse_args()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    project_dir = args.project_dir.resolve()
    model_dir = project_dir / "models"
    output_dir = project_dir / "outputs"
    chart_dir = output_dir / "charts"
    model_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(args.input, low_memory=False)
    missing_columns = [column for column in MODEL_FEATURES if column not in data]
    if missing_columns:
        raise ValueError(f"Thiếu feature: {missing_columns}")

    pipeline = build_pipeline()
    prediction = pipeline.fit_predict(data[MODEL_FEATURES])
    scored_data = data.copy()
    scored_data["anomaly_score"] = -pipeline.decision_function(
        data[MODEL_FEATURES]
    )
    scored_data["is_anomaly"] = (prediction == -1).astype(int)

    thresholds = get_reason_thresholds(data)
    scored_data = add_anomaly_reasons(scored_data, thresholds)
    scored_data = scored_data.sort_values("anomaly_score", ascending=False)
    anomalies = scored_data[scored_data["is_anomaly"].eq(1)].copy()

    second_pipeline = build_pipeline(random_state=7)
    second_prediction = second_pipeline.fit_predict(data[MODEL_FEATURES])
    first_set = set(data.index[prediction == -1])
    second_set = set(data.index[second_prediction == -1])
    seed_jaccard = len(first_set & second_set) / len(first_set | second_set)

    profile = make_feature_profile(scored_data)
    reason_count = count_reasons(anomalies)

    scored_data.to_csv(
        output_dir / "order_anomaly_scores.csv", index=False, encoding="utf-8-sig"
    )
    anomalies.to_csv(
        output_dir / "anomalous_orders.csv", index=False, encoding="utf-8-sig"
    )
    profile.to_csv(
        output_dir / "anomaly_feature_profile.csv",
        index=False,
        encoding="utf-8-sig",
    )
    reason_count.to_csv(
        output_dir / "anomaly_reason_counts.csv",
        index=False,
        encoding="utf-8-sig",
    )

    metrics = {
        "algorithm": "Isolation Forest",
        "data_scope": "delivered orders",
        "total_orders": int(len(scored_data)),
        "anomaly_orders": int(len(anomalies)),
        "normal_orders": int(len(scored_data) - len(anomalies)),
        "anomaly_rate": float(len(anomalies) / len(scored_data)),
        "contamination": CONTAMINATION,
        "random_state": RANDOM_STATE,
        "n_estimators": 200,
        "max_samples": 4096,
        "seed_7_42_jaccard": float(seed_jaccard),
        "score_note": "anomaly_score càng cao thì đơn hàng càng bất thường",
    }
    with open(output_dir / "model_metrics.json", "w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)

    bundle = {
        "pipeline": pipeline,
        "model_features": MODEL_FEATURES,
        "reason_thresholds": thresholds,
        "contamination": CONTAMINATION,
        "algorithm": "Isolation Forest",
    }
    joblib.dump(bundle, model_dir / "isolation_forest_order_pipeline.joblib")
    save_charts(scored_data, profile, reason_count, chart_dir)

    result_lines = [
        "KẾT QUẢ ISOLATION FOREST - PHÁT HIỆN ĐƠN HÀNG BẤT THƯỜNG",
        "=" * 62,
        f"Tổng số đơn delivered: {len(scored_data):,}",
        f"Số đơn bất thường: {len(anomalies):,}",
        f"Tỷ lệ bất thường: {len(anomalies) / len(scored_data):.2%}",
        f"Jaccard giữa seed 42 và seed 7: {seed_jaccard:.4f}",
        "",
        "Lưu ý: dữ liệu không có nhãn bất thường thực tế, vì vậy không dùng accuracy/F1.",
        "Điểm càng cao cho biết đơn hàng càng khác biệt so với phần lớn dữ liệu.",
    ]
    (output_dir / "Ketqua_IsolationForest.txt").write_text(
        "\n".join(result_lines), encoding="utf-8"
    )

    print(f"Đã huấn luyện trên {len(scored_data):,} đơn hàng")
    print(f"Phát hiện {len(anomalies):,} đơn bất thường")
    print(f"Tỷ lệ bất thường: {len(anomalies) / len(scored_data):.2%}")
    print(f"Jaccard seed 42 và 7: {seed_jaccard:.4f}")
    print(f"Đã lưu model: {model_dir / 'isolation_forest_order_pipeline.joblib'}")


if __name__ == "__main__":
    main()
