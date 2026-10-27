from argparse import ArgumentParser
from pathlib import Path
import json
import sys
import time
import tracemalloc

import joblib
import matplotlib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
    make_scorer,
)
from sklearn.model_selection import (
    GridSearchCV,
    StratifiedKFold,
    cross_val_predict,
    train_test_split,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder


matplotlib.use("Agg")
import matplotlib.pyplot as plt


RANDOM_STATE = 42
TARGET_COLUMN = "churn_proxy_180d"

NUMERIC_FEATURES = [
    "recency",
    "frequency",
    "monetary",
    "orders_last_30d",
    "orders_last_90d",
    "orders_last_180d",
    "spend_last_30d",
    "spend_last_90d",
    "spend_last_180d",
    "avg_order_value",
    "customer_tenure_days",
    "avg_days_between_orders",
    "avg_items_per_order",
    "avg_freight_value",
    "freight_to_product_ratio",
    "avg_installments",
]

CATEGORICAL_FEATURES = ["customer_state", "region_name"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_pipeline():
    numeric_pipeline = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(strategy="median", add_indicator=True),
            )
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            (
                "onehot",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
            ),
        ]
    )
    preprocessor = ColumnTransformer(
        [
            ("numeric", numeric_pipeline, NUMERIC_FEATURES),
            ("categorical", categorical_pipeline, CATEGORICAL_FEATURES),
        ],
        verbose_feature_names_out=False,
    )

    model = RandomForestClassifier(
        random_state=RANDOM_STATE,
        class_weight="balanced",
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", preprocessor), ("model", model)])


def select_threshold(y_true, churn_probability):
    candidates = np.arange(0.05, 0.951, 0.01)
    scores = []
    for threshold in candidates:
        prediction = (churn_probability >= threshold).astype(int)
        scores.append(f1_score(y_true, prediction, average="macro"))

    best_score = max(scores)
    best_indexes = np.flatnonzero(np.isclose(scores, best_score))
    best_index = min(best_indexes, key=lambda index: abs(candidates[index] - 0.5))
    return float(candidates[best_index]), float(scores[best_index])


def calculate_metrics(y_true, y_pred, churn_probability):
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted")),
        "return_precision": float(
            precision_score(y_true, y_pred, pos_label=0, zero_division=0)
        ),
        "return_recall": float(
            recall_score(y_true, y_pred, pos_label=0, zero_division=0)
        ),
        "return_f1": float(f1_score(y_true, y_pred, pos_label=0, zero_division=0)),
        "churn_precision": float(
            precision_score(y_true, y_pred, pos_label=1, zero_division=0)
        ),
        "churn_recall": float(
            recall_score(y_true, y_pred, pos_label=1, zero_division=0)
        ),
        "churn_f1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, churn_probability)),
        "return_average_precision": float(
            average_precision_score((y_true == 0).astype(int), 1 - churn_probability)
        ),
    }


def make_classification_report_table(y_true, y_pred):
    report = classification_report(
        y_true,
        y_pred,
        labels=[0, 1],
        target_names=["Quay_lai_0", "Churn_1"],
        output_dict=True,
        zero_division=0,
    )
    rows = []
    for label in ["Quay_lai_0", "Churn_1", "macro avg", "weighted avg"]:
        rows.append({"class": label, **report[label]})
    rows.insert(
        2,
        {
            "class": "accuracy",
            "precision": np.nan,
            "recall": np.nan,
            "f1-score": report["accuracy"],
            "support": len(y_true),
        },
    )
    return pd.DataFrame(rows)


def save_charts(
    y_test,
    y_pred,
    churn_probability,
    feature_importance,
    dataset,
    chart_dir,
):
    chart_dir.mkdir(parents=True, exist_ok=True)
    plt.style.use("seaborn-v0_8-whitegrid")

    label_count = dataset[TARGET_COLUMN].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(
        ["Quay lại (0)", "Churn proxy (1)"],
        [label_count.get(0, 0), label_count.get(1, 0)],
        color=["#2A9D8F", "#E76F51"],
    )
    ax.bar_label(bars, fmt="{:,.0f}")
    ax.set_title("Phân bố nhãn churn 180 ngày")
    ax.set_ylabel("Số khách hàng")
    fig.tight_layout()
    fig.savefig(chart_dir / "01_class_distribution.png", dpi=160)
    plt.close(fig)

    matrix = confusion_matrix(y_test, y_pred, labels=[0, 1])
    fig, ax = plt.subplots(figsize=(6, 5))
    image = ax.imshow(matrix, cmap="Blues")
    color_limit = matrix.max() / 2
    for row in range(2):
        for column in range(2):
            text_color = "white" if matrix[row, column] > color_limit else "#222222"
            ax.text(
                column,
                row,
                f"{matrix[row, column]:,}",
                ha="center",
                va="center",
                color=text_color,
            )
    ax.set_xticks([0, 1], ["Quay lại", "Churn"])
    ax.set_yticks([0, 1], ["Quay lại", "Churn"])
    ax.set_xlabel("Dự đoán")
    ax.set_ylabel("Thực tế")
    ax.set_title("Confusion matrix trên tập test")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    fig.savefig(chart_dir / "02_confusion_matrix.png", dpi=160)
    plt.close(fig)

    fpr, tpr, _ = roc_curve(y_test, churn_probability)
    auc_value = roc_auc_score(y_test, churn_probability)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(fpr, tpr, color="#264653", linewidth=2, label=f"AUC = {auc_value:.4f}")
    ax.plot([0, 1], [0, 1], "--", color="gray")
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title("ROC curve - lớp churn")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(chart_dir / "03_roc_curve.png", dpi=160)
    plt.close(fig)

    return_true = (y_test == 0).astype(int)
    return_probability = 1 - churn_probability
    precision, recall, _ = precision_recall_curve(return_true, return_probability)
    average_precision = average_precision_score(return_true, return_probability)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.plot(
        recall,
        precision,
        color="#2A9D8F",
        linewidth=2,
        label=f"Average precision = {average_precision:.4f}",
    )
    ax.set_xlabel("Recall")
    ax.set_ylabel("Precision")
    ax.set_title("Precision-Recall curve - lớp khách quay lại")
    ax.legend(loc="lower right")
    fig.tight_layout()
    fig.savefig(chart_dir / "04_precision_recall_return.png", dpi=160)
    plt.close(fig)

    top_features = feature_importance.head(15).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh(top_features["feature"], top_features["importance"], color="#457B9D")
    ax.set_xlabel("Mức độ quan trọng")
    ax.set_title("15 feature quan trọng nhất")
    fig.tight_layout()
    fig.savefig(chart_dir / "05_feature_importance.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(
        churn_probability[y_test.to_numpy() == 0],
        bins=20,
        alpha=0.75,
        label="Quay lại (0)",
        color="#2A9D8F",
    )
    ax.hist(
        churn_probability[y_test.to_numpy() == 1],
        bins=20,
        alpha=0.55,
        label="Churn (1)",
        color="#E76F51",
    )
    ax.set_xlabel("Xác suất churn")
    ax.set_ylabel("Số khách hàng")
    ax.set_title("Phân bố xác suất dự đoán trên tập test")
    ax.legend()
    fig.tight_layout()
    fig.savefig(chart_dir / "06_probability_distribution.png", dpi=160)
    plt.close(fig)


def parse_args():
    project_dir = Path(__file__).resolve().parents[1]
    parser = ArgumentParser(description="Huấn luyện Random Forest dự đoán churn")
    parser.add_argument(
        "--input",
        type=Path,
        default=project_dir / "data" / "customer_churn_180d.csv",
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

    data = pd.read_csv(args.input)
    missing_columns = set(MODEL_FEATURES + [TARGET_COLUMN, "customer_unique_id"]) - set(
        data.columns
    )
    if missing_columns:
        raise ValueError(f"Thiếu cột: {sorted(missing_columns)}")

    train_data, test_data = train_test_split(
        data,
        test_size=0.2,
        random_state=RANDOM_STATE,
        stratify=data[TARGET_COLUMN],
    )
    X_train = train_data[MODEL_FEATURES]
    y_train = train_data[TARGET_COLUMN].astype(int)
    X_test = test_data[MODEL_FEATURES]
    y_test = test_data[TARGET_COLUMN].astype(int)

    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=RANDOM_STATE)
    scoring = {
        "macro_f1": "f1_macro",
        "balanced_accuracy": "balanced_accuracy",
        "return_f1": make_scorer(f1_score, pos_label=0, zero_division=0),
        "roc_auc": "roc_auc",
    }
    param_grid = {
        "model__n_estimators": [250, 400],
        "model__max_depth": [8, None],
        "model__min_samples_leaf": [1, 5],
        "model__min_samples_split": [2],
        "model__max_features": ["sqrt"],
        "model__criterion": ["gini"],
        "model__class_weight": ["balanced"],
    }

    print("=" * 60)
    print("HUẤN LUYỆN RANDOM FOREST")
    print(f"Train: {len(train_data):,} | Test: {len(test_data):,}")
    print("Đang chạy GridSearchCV 3-fold trên tập train...")

    tracemalloc.start()
    start_time = time.perf_counter()
    grid_search = GridSearchCV(
        estimator=build_pipeline(),
        param_grid=param_grid,
        scoring=scoring,
        refit="macro_f1",
        cv=cv,
        n_jobs=1,
        return_train_score=False,
        verbose=1,
    )
    grid_search.fit(X_train, y_train)

    best_pipeline = grid_search.best_estimator_
    oof_probability = cross_val_predict(
        best_pipeline,
        X_train,
        y_train,
        cv=cv,
        method="predict_proba",
        n_jobs=1,
    )[:, 1]
    threshold, oof_macro_f1 = select_threshold(y_train, oof_probability)

    best_pipeline.fit(X_train, y_train)
    test_probability = best_pipeline.predict_proba(X_test)[:, 1]
    test_prediction = (test_probability >= threshold).astype(int)
    elapsed_seconds = time.perf_counter() - start_time
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    test_metrics = calculate_metrics(y_test, test_prediction, test_probability)
    baseline_prediction = np.ones(len(y_test), dtype=int)
    baseline_metrics = calculate_metrics(y_test, baseline_prediction, test_probability)

    report_table = make_classification_report_table(y_test, test_prediction)
    report_table.to_csv(
        output_dir / "classification_report.csv",
        index=False,
        encoding="utf-8-sig",
        lineterminator="\n",
    )

    matrix = confusion_matrix(y_test, test_prediction, labels=[0, 1])
    matrix_table = pd.DataFrame(
        matrix,
        index=["actual_return_0", "actual_churn_1"],
        columns=["predicted_return_0", "predicted_churn_1"],
    )
    matrix_table.to_csv(
        output_dir / "confusion_matrix.csv", encoding="utf-8-sig"
    )

    feature_names = best_pipeline.named_steps["preprocessor"].get_feature_names_out()
    importance_values = best_pipeline.named_steps["model"].feature_importances_
    feature_importance = pd.DataFrame(
        {"feature": feature_names, "importance": importance_values}
    ).sort_values("importance", ascending=False)
    feature_importance.to_csv(
        output_dir / "feature_importance.csv", index=False, encoding="utf-8-sig"
    )

    cv_results = pd.DataFrame(grid_search.cv_results_)
    cv_columns = [
        "rank_test_macro_f1",
        "mean_test_macro_f1",
        "std_test_macro_f1",
        "mean_test_balanced_accuracy",
        "mean_test_roc_auc",
        "mean_fit_time",
        "param_model__n_estimators",
        "param_model__max_depth",
        "param_model__min_samples_leaf",
    ]
    cv_results[cv_columns].sort_values("rank_test_macro_f1").to_csv(
        output_dir / "cross_validation_results.csv",
        index=False,
        encoding="utf-8-sig",
    )

    predictions = test_data[["customer_unique_id", TARGET_COLUMN]].copy()
    predictions["churn_probability"] = test_probability
    predictions["predicted_churn"] = test_prediction
    predictions["prediction_threshold"] = threshold
    predictions = predictions.rename(columns={TARGET_COLUMN: "actual_churn"})
    predictions.to_csv(
        output_dir / "test_predictions.csv", index=False, encoding="utf-8-sig"
    )

    best_params = {
        key.replace("model__", ""): value for key, value in grid_search.best_params_.items()
    }
    metrics = {
        "model": "RandomForestClassifier",
        "label_definition": "1 = không có đơn delivered trong 180 ngày sau snapshot; 0 = có quay lại mua",
        "snapshot_date": "2018-03-02",
        "prediction_window_end": "2018-08-29",
        "random_state": RANDOM_STATE,
        "train_rows": int(len(train_data)),
        "test_rows": int(len(test_data)),
        "train_churn_rate": float(y_train.mean()),
        "test_churn_rate": float(y_test.mean()),
        "best_parameters": best_params,
        "cv_best_macro_f1_at_default_threshold": float(grid_search.best_score_),
        "selected_threshold": threshold,
        "oof_macro_f1_at_selected_threshold": oof_macro_f1,
        "test_metrics": test_metrics,
        "all_churn_baseline": {
            key: baseline_metrics[key]
            for key in ["accuracy", "balanced_accuracy", "macro_f1"]
        },
        "training_seconds": float(elapsed_seconds),
        "peak_memory_mb": float(peak_memory / (1024**2)),
    }
    with (output_dir / "model_metrics.json").open("w", encoding="utf-8") as file:
        json.dump(metrics, file, ensure_ascii=False, indent=2)

    model_bundle = {
        "pipeline": best_pipeline,
        "threshold": threshold,
        "model_features": MODEL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "label_mapping": {0: "quay_lai", 1: "churn_proxy_180d"},
        "snapshot_date": "2018-03-02",
        "prediction_window_end": "2018-08-29",
    }
    joblib.dump(
        model_bundle,
        model_dir / "random_forest_churn_pipeline.joblib",
        compress=3,
    )

    save_charts(
        y_test,
        test_prediction,
        test_probability,
        feature_importance,
        data,
        chart_dir,
    )

    result_lines = [
        "KẾT QUẢ RANDOM FOREST - CHURN PROXY 180 NGÀY",
        "=" * 58,
        f"Train: {len(train_data):,} | Test: {len(test_data):,}",
        f"Ngưỡng dự đoán chọn trên train: {threshold:.2f}",
        f"Accuracy: {test_metrics['accuracy']:.4f}",
        f"Balanced accuracy: {test_metrics['balanced_accuracy']:.4f}",
        f"Macro F1: {test_metrics['macro_f1']:.4f}",
        f"F1 lớp quay lại (0): {test_metrics['return_f1']:.4f}",
        f"F1 lớp churn (1): {test_metrics['churn_f1']:.4f}",
        f"ROC-AUC: {test_metrics['roc_auc']:.4f}",
        f"Average precision lớp quay lại: {test_metrics['return_average_precision']:.4f}",
        "",
        "Confusion matrix [actual x predicted]:",
        matrix_table.to_string(),
        "",
        "Tham số tốt nhất:",
        json.dumps(best_params, ensure_ascii=False, indent=2),
    ]
    (output_dir / "Ketqua_RandomForest_Churn.txt").write_text(
        "\n".join(result_lines), encoding="utf-8"
    )

    print("\nTHAM SỐ TỐT NHẤT")
    print(best_params)
    print("\nKẾT QUẢ TRÊN TẬP TEST")
    print(f"Ngưỡng dự đoán: {threshold:.2f}")
    print(f"Accuracy: {test_metrics['accuracy']:.4f}")
    print(f"Balanced accuracy: {test_metrics['balanced_accuracy']:.4f}")
    print(f"Macro F1: {test_metrics['macro_f1']:.4f}")
    print(f"F1 lớp quay lại: {test_metrics['return_f1']:.4f}")
    print(f"F1 lớp churn: {test_metrics['churn_f1']:.4f}")
    print(f"ROC-AUC: {test_metrics['roc_auc']:.4f}")
    print(f"Thời gian: {elapsed_seconds:.2f} giây")
    print(f"Đã lưu kết quả tại: {output_dir}")


if __name__ == "__main__":
    main()
