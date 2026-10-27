import argparse
import json
import shutil
import sys
import time
import tracemalloc
from pathlib import Path

import joblib
import matplotlib
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import (
    adjusted_rand_score,
    calinski_harabasz_score,
    davies_bouldin_score,
    silhouette_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, StandardScaler

from prepare_rfm import build_rfm, read_order_master


matplotlib.use("Agg")
import matplotlib.pyplot as plt


if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


FEATURE_COLUMNS = ["recency", "frequency", "monetary"]
RANDOM_STATE = 42
STABILITY_SEEDS = [7, 21, 42, 84, 168]


def make_preprocessor():
    return Pipeline(
        [
            (
                "log1p",
                FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            ),
            ("scaler", StandardScaler()),
        ]
    )


def evaluate_k_values(x_scaled, k_min=2, k_max=10):
    results = []
    sample_size = min(15000, len(x_scaled))

    for k in range(k_min, k_max + 1):
        model = KMeans(
            n_clusters=k,
            random_state=RANDOM_STATE,
            n_init=20,
        )
        labels = model.fit_predict(x_scaled)

        stability_scores = []
        for seed in STABILITY_SEEDS:
            model_seed = KMeans(n_clusters=k, random_state=seed, n_init=10)
            labels_seed = model_seed.fit_predict(x_scaled)
            stability_scores.append(adjusted_rand_score(labels, labels_seed))

        cluster_ratio = pd.Series(labels).value_counts(normalize=True)
        results.append(
            {
                "k": k,
                "inertia": model.inertia_,
                "silhouette": silhouette_score(
                    x_scaled,
                    labels,
                    sample_size=sample_size,
                    random_state=RANDOM_STATE,
                ),
                "davies_bouldin": davies_bouldin_score(x_scaled, labels),
                "calinski_harabasz": calinski_harabasz_score(x_scaled, labels),
                "stability_ari": float(np.mean(stability_scores)),
                "smallest_cluster_pct": cluster_ratio.min() * 100,
                "largest_cluster_pct": cluster_ratio.max() * 100,
            }
        )
        print(f"Đã đánh giá K={k}")

    return pd.DataFrame(results)


def find_elbow(evaluation):
    x = evaluation["k"].to_numpy(dtype=float)
    y = evaluation["inertia"].to_numpy(dtype=float)

    x_norm = (x - x.min()) / (x.max() - x.min())
    y_norm = (y - y.min()) / (y.max() - y.min())
    points = np.column_stack([x_norm, y_norm])

    line_start = points[0]
    line_end = points[-1]
    line = line_end - line_start
    shifted = points - line_start
    distance = np.abs(line[0] * shifted[:, 1] - line[1] * shifted[:, 0])
    distance = distance / np.linalg.norm(line)
    return int(evaluation.iloc[int(np.argmax(distance))]["k"])


def choose_k(evaluation):
    elbow_k = find_elbow(evaluation)
    metric_best_k = int(
        evaluation.sort_values(
            ["silhouette", "davies_bouldin"],
            ascending=[False, True],
        ).iloc[0]["k"]
    )

    elbow_row = evaluation[evaluation["k"].eq(elbow_k)].iloc[0]
    elbow_is_usable = (
        3 <= elbow_k <= 6
        and elbow_row["silhouette"] >= 0.30
        and elbow_row["stability_ari"] >= 0.85
        and elbow_row["smallest_cluster_pct"] >= 2.0
        and elbow_row["largest_cluster_pct"] <= 70.0
    )

    if elbow_is_usable:
        selected_k = elbow_k
        reason = (
            "Chọn điểm elbow vì các cụm ổn định, không có cụm quá nhỏ "
            "và số nhóm phù hợp để xây dựng chính sách khách hàng."
        )
    else:
        valid = evaluation[
            (evaluation["k"].between(3, 6))
            & (evaluation["stability_ari"] >= 0.85)
            & (evaluation["smallest_cluster_pct"] >= 2.0)
        ].copy()
        if valid.empty:
            selected_k = metric_best_k
            reason = "Không có phương án 3-6 cụm đạt điều kiện, chọn K có metric tốt nhất."
        else:
            valid["rank_total"] = (
                valid["silhouette"].rank(ascending=False)
                + valid["davies_bouldin"].rank(ascending=True)
                + valid["calinski_harabasz"].rank(ascending=False)
                + valid["stability_ari"].rank(ascending=False)
            )
            selected_k = int(valid.sort_values("rank_total").iloc[0]["k"])
            reason = "Chọn K cân bằng bốn metric và giữ kích thước cụm đủ để phân tích."

    return selected_k, elbow_k, metric_best_k, reason


def name_four_clusters(profiles):
    remaining = set(profiles.index.astype(int))
    mapping = {}

    loyal_cluster = int(profiles["frequency_mean"].idxmax())
    mapping[loyal_cluster] = "Champions / Loyal (Khách mua lặp lại)"
    remaining.remove(loyal_cluster)

    recent_cluster = int(profiles.loc[list(remaining), "recency_mean"].idxmin())
    mapping[recent_cluster] = "Recent Active (Khách mua gần đây)"
    remaining.remove(recent_cluster)

    at_risk_cluster = int(profiles.loc[list(remaining), "monetary_mean"].idxmax())
    mapping[at_risk_cluster] = "At-Risk High Spenders (Chi tiêu cao, lâu chưa mua)"
    remaining.remove(at_risk_cluster)

    last_cluster = remaining.pop()
    mapping[last_cluster] = "Hibernating Low-Value (Lâu chưa mua, giá trị thấp)"
    return mapping


def build_profiles(rfm):
    profiles = rfm.groupby("cluster").agg(
        customer_count=("customer_unique_id", "size"),
        recency_mean=("recency", "mean"),
        recency_median=("recency", "median"),
        frequency_mean=("frequency", "mean"),
        frequency_median=("frequency", "median"),
        monetary_mean=("monetary", "mean"),
        monetary_median=("monetary", "median"),
    )
    profiles["percentage"] = profiles["customer_count"] / len(rfm) * 100
    return profiles


def save_k_chart(evaluation, selected_k, output_file):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].plot(evaluation["k"], evaluation["inertia"], marker="o")
    axes[0].axvline(selected_k, color="red", linestyle="--", label=f"K={selected_k}")
    axes[0].set_title("Elbow - Inertia")
    axes[0].set_xlabel("Số cụm K")
    axes[0].set_ylabel("Inertia")
    axes[0].legend()

    axes[1].plot(
        evaluation["k"],
        evaluation["silhouette"],
        marker="o",
        color="#f28e2b",
    )
    axes[1].axvline(selected_k, color="red", linestyle="--", label=f"K={selected_k}")
    axes[1].set_title("Silhouette Score")
    axes[1].set_xlabel("Số cụm K")
    axes[1].set_ylabel("Silhouette")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(output_file, dpi=250, bbox_inches="tight")
    plt.close(fig)


def save_rfm_distribution(rfm, output_file):
    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    colors = ["#4e79a7", "#59a14f", "#e15759"]

    for ax, column, color in zip(axes, FEATURE_COLUMNS, colors):
        sns.histplot(np.log1p(rfm[column]), bins=35, ax=ax, color=color)
        ax.set_title(f"Phân phối log1p({column})")
        ax.set_xlabel(f"log1p({column})")

    fig.tight_layout()
    fig.savefig(output_file, dpi=250, bbox_inches="tight")
    plt.close(fig)


def save_cluster_size(profiles, output_file):
    plot_data = profiles.sort_values("customer_count", ascending=True)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(plot_data["segment"], plot_data["customer_count"], color="#4e79a7")
    ax.set_title("Số khách hàng trong từng cụm")
    ax.set_xlabel("Số khách hàng")
    fig.tight_layout()
    fig.savefig(output_file, dpi=250, bbox_inches="tight")
    plt.close(fig)


def save_profile_heatmap(profiles, output_file):
    profile_values = profiles[["recency_mean", "frequency_mean", "monetary_mean"]]
    profile_scaled = pd.DataFrame(
        StandardScaler().fit_transform(profile_values),
        index=profiles["segment"],
        columns=["Recency", "Frequency", "Monetary"],
    )

    fig, ax = plt.subplots(figsize=(8, 5))
    sns.heatmap(profile_scaled, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
    ax.set_title("Hồ sơ RFM chuẩn hóa theo cụm")
    ax.set_xlabel("")
    ax.set_ylabel("")
    fig.tight_layout()
    fig.savefig(output_file, dpi=250, bbox_inches="tight")
    plt.close(fig)


def save_pca_chart(x_scaled, rfm, output_file):
    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    points = pca.fit_transform(x_scaled)

    sample_size = min(20000, len(rfm))
    rng = np.random.default_rng(RANDOM_STATE)
    sample_index = rng.choice(len(rfm), size=sample_size, replace=False)
    plot_data = pd.DataFrame(
        {
            "PCA 1": points[sample_index, 0],
            "PCA 2": points[sample_index, 1],
            "Phân khúc": rfm.iloc[sample_index]["segment"].to_numpy(),
        }
    )

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=plot_data,
        x="PCA 1",
        y="PCA 2",
        hue="Phân khúc",
        s=18,
        alpha=0.55,
        ax=ax,
    )
    ax.set_title("Phân cụm K-Means trên mặt phẳng PCA")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_file, dpi=250, bbox_inches="tight")
    plt.close(fig)


def save_recency_monetary_chart(rfm, output_file):
    sample_size = min(25000, len(rfm))
    plot_data = rfm.sample(sample_size, random_state=RANDOM_STATE)

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.scatterplot(
        data=plot_data,
        x="recency",
        y="monetary",
        hue="segment",
        s=18,
        alpha=0.55,
        ax=ax,
    )
    ax.set_yscale("log")
    ax.set_title("Recency và Monetary theo phân khúc")
    ax.set_xlabel("Recency (ngày)")
    ax.set_ylabel("Monetary (BRL, thang log)")
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(output_file, dpi=250, bbox_inches="tight")
    plt.close(fig)


def save_text_result(metrics, profiles, output_file):
    display_columns = [
        "segment",
        "customer_count",
        "percentage",
        "recency_mean",
        "frequency_mean",
        "monetary_mean",
    ]
    profile_text = profiles[display_columns].round(2).to_string()

    content = (
        "KẾT QUẢ HUẤN LUYỆN MÔ HÌNH PHÂN CỤM KHÁCH HÀNG K-MEANS\n\n"
        f"- Số khách hàng: {metrics['customer_count']:,}\n"
        f"- Ngày tham chiếu RFM: {metrics['reference_date']}\n"
        f"- Số cụm K được chọn: {metrics['selected_k']}\n"
        f"- K theo Silhouette tốt nhất: {metrics['metric_best_k']}\n"
        f"- K tại điểm Elbow: {metrics['elbow_k']}\n"
        f"- Inertia (WCSS): {metrics['inertia']:.2f}\n"
        f"- Silhouette Score: {metrics['silhouette']:.4f}\n"
        f"- Davies-Bouldin Index: {metrics['davies_bouldin']:.4f}\n"
        f"- Calinski-Harabasz Score: {metrics['calinski_harabasz']:.2f}\n"
        f"- Stability ARI: {metrics['stability_ari']:.4f}\n"
        f"- Thời gian huấn luyện: {metrics['train_time_seconds']:.4f}s\n"
        f"- RAM tiêu thụ đỉnh: {metrics['peak_memory_mb']:.2f} MB\n\n"
        "LÝ DO CHỌN K\n"
        f"{metrics['selection_reason']}\n\n"
        "BẢNG ĐẶC TRƯNG PHÂN CỤM\n"
        f"{profile_text}\n"
    )
    output_file.write_text(content, encoding="utf-8")


def train_kmeans(order_master_file, output_dir, model_dir, k_min=2, k_max=10, final_k=None):
    output_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)
    chart_dir = output_dir / "charts"
    chart_dir.mkdir(parents=True, exist_ok=True)

    order_master = read_order_master(order_master_file)
    rfm, reference_date = build_rfm(order_master)
    rfm.to_csv(
        output_dir / "rfm_rebuilt.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )

    preprocessor = make_preprocessor()
    x_scaled = preprocessor.fit_transform(rfm[FEATURE_COLUMNS])
    evaluation = evaluate_k_values(x_scaled, k_min=k_min, k_max=k_max)
    auto_k, elbow_k, metric_best_k, reason = choose_k(evaluation)
    selected_k = final_k if final_k is not None else auto_k

    if selected_k < k_min or selected_k > k_max:
        raise ValueError(f"K cuối phải nằm trong khoảng {k_min}-{k_max}")

    model_pipeline = Pipeline(
        [
            (
                "log1p",
                FunctionTransformer(np.log1p, feature_names_out="one-to-one"),
            ),
            ("scaler", StandardScaler()),
            (
                "kmeans",
                KMeans(
                    n_clusters=selected_k,
                    random_state=RANDOM_STATE,
                    n_init=30,
                ),
            ),
        ]
    )

    tracemalloc.start()
    start_time = time.perf_counter()
    rfm["cluster"] = model_pipeline.fit_predict(rfm[FEATURE_COLUMNS])
    train_time = time.perf_counter() - start_time
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    profiles = build_profiles(rfm)
    if selected_k == 4:
        cluster_mapping = name_four_clusters(profiles)
    else:
        cluster_mapping = {int(cluster): f"Cluster {cluster}" for cluster in profiles.index}

    rfm["segment"] = rfm["cluster"].map(cluster_mapping)
    profiles["segment"] = profiles.index.map(cluster_mapping)

    selected_row = evaluation[evaluation["k"].eq(selected_k)].iloc[0]
    metrics = {
        "customer_count": int(len(rfm)),
        "reference_date": reference_date.date().isoformat(),
        "selected_k": int(selected_k),
        "elbow_k": int(elbow_k),
        "metric_best_k": int(metric_best_k),
        "selection_reason": reason,
        "silhouette": float(selected_row["silhouette"]),
        "davies_bouldin": float(selected_row["davies_bouldin"]),
        "calinski_harabasz": float(selected_row["calinski_harabasz"]),
        "stability_ari": float(selected_row["stability_ari"]),
        "inertia": float(selected_row["inertia"]),
        "train_time_seconds": train_time,
        "peak_memory_mb": peak_memory / (1024 * 1024),
        "input_rule": "Chỉ lấy đơn delivered; Monetary là tổng total_products_value.",
    }

    evaluation.to_csv(
        output_dir / "k_evaluation.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    profiles.reset_index().to_csv(
        output_dir / "cluster_profiles.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    rfm.to_csv(
        output_dir / "rfm_customers_kmeans.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )
    with (output_dir / "model_metrics.json").open(
        "w", encoding="utf-8", newline="\n"
    ) as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)

    model_bundle = {
        "pipeline": model_pipeline,
        "feature_columns": FEATURE_COLUMNS,
        "cluster_mapping": cluster_mapping,
        "reference_date": reference_date,
        "selected_k": selected_k,
    }
    joblib.dump(model_bundle, model_dir / "rfm_kmeans_pipeline.joblib")
    joblib.dump(model_bundle, model_dir / "kmeans_rfm_pipeline.pkl")

    final_scaled = model_pipeline[:-1].transform(rfm[FEATURE_COLUMNS])
    k_chart = chart_dir / "01_k_evaluation.png"
    pca_chart = chart_dir / "05_kmeans_pca.png"
    rm_chart = chart_dir / "06_recency_monetary.png"

    save_k_chart(evaluation, selected_k, k_chart)
    save_rfm_distribution(rfm, chart_dir / "02_rfm_distribution.png")
    save_cluster_size(profiles, chart_dir / "03_cluster_size.png")
    save_profile_heatmap(profiles, chart_dir / "04_cluster_profile_heatmap.png")
    save_pca_chart(final_scaled, rfm, pca_chart)
    save_recency_monetary_chart(rfm, rm_chart)

    save_text_result(metrics, profiles, output_dir / "Ketqua_KMeans.txt")
    shutil.copy2(k_chart, output_dir / "KMeans_Elbow_Silhouette.png")
    shutil.copy2(pca_chart, output_dir / "KMeans_Clusters_2D_PCA.png")
    shutil.copy2(rm_chart, output_dir / "KMeans_Recency_vs_Monetary.png")

    print("\nKẾT QUẢ K-MEANS")
    print(f"Số khách hàng: {len(rfm):,}")
    print(f"K theo metric tốt nhất: {metric_best_k}")
    print(f"K tại điểm elbow: {elbow_k}")
    print(f"K được chọn: {selected_k}")
    print(f"Silhouette: {metrics['silhouette']:.4f}")
    print(f"Davies-Bouldin: {metrics['davies_bouldin']:.4f}")
    print(f"Stability ARI: {metrics['stability_ari']:.4f}")
    print("\nHồ sơ cụm:")
    print(
        profiles[
            [
                "segment",
                "customer_count",
                "percentage",
                "recency_mean",
                "frequency_mean",
                "monetary_mean",
            ]
        ].round(2)
    )

    return rfm, evaluation, profiles, metrics


def main():
    project_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Huấn luyện K-Means trên dữ liệu RFM")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "data" / "olist_powerbi_orders_master.csv",
    )
    parser.add_argument("--output-dir", type=Path, default=project_dir / "outputs")
    parser.add_argument("--model-dir", type=Path, default=project_dir / "models")
    parser.add_argument("--k-min", type=int, default=2)
    parser.add_argument("--k-max", type=int, default=10)
    parser.add_argument("--final-k", type=int, default=None)
    args = parser.parse_args()

    train_kmeans(
        order_master_file=args.input,
        output_dir=args.output_dir,
        model_dir=args.model_dir,
        k_min=args.k_min,
        k_max=args.k_max,
        final_k=args.final_k,
    )


if __name__ == "__main__":
    main()
