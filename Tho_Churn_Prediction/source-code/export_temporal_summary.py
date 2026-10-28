from pathlib import Path
import json

import pandas as pd
import xlsxwriter


def export_summary(output_dir):
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))
    workbook = xlsxwriter.Workbook(output_dir / "temporal_summary.xlsx")
    header = workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78"})

    def write_sheet(name, rows, widths):
        sheet = workbook.add_worksheet(name)
        sheet.hide_gridlines(2)
        for i, width in enumerate(widths):
            sheet.set_column(i, i, width)
        for row_index, row in enumerate(rows):
            for col_index, value in enumerate(row):
                if value is None or pd.isna(value):
                    continue
                sheet.write(row_index, col_index, value, header if row_index == 0 else None)
        sheet.freeze_panes(1, 0)

    write_sheet("Tong_quan", [
        ["Chỉ tiêu", "Giá trị"], ["Phiên bản", metrics["version"]],
        ["Trạng thái", metrics["source_status"]], ["T0 test", metrics["test_t0"]],
        ["Kết thúc nhãn train muộn nhất", metrics["train_max_label_end"]],
        ["Mốc theo dõi giả định", metrics["observation_end_exclusive"]],
        ["Số mẫu train", metrics["train_rows"]], ["Train mua lại (0)", metrics["train_return_0"]],
        ["Train không mua lại (1)", metrics["train_no_repurchase_1"]], ["Số mẫu test", metrics["rows"]],
        ["Test mua lại (0)", metrics["return_0"]], ["Test không mua lại (1)", metrics["no_repurchase_1"]],
        ["ROC-AUC lớp 1", metrics["roc_auc_churn_1"]], ["AP không mua lại (1)", metrics["average_precision_churn_1"]],
        ["AP mua lại (0)", metrics["average_precision_repurchase_0"]],
        ["Top decile lift lớp 1", metrics["top_decile_lift_churn_1"]],
        ["Thứ tự decile", metrics["top_decile_ranked_by"]], ["Ngưỡng dự đoán", metrics["threshold"]],
    ], [34, 65])
    report = metrics["classification_report"]
    write_sheet("Classification", [["Nhóm", "Precision", "Recall", "F1", "Support"]] + [
        [name, report[name]["precision"], report[name]["recall"], report[name]["f1-score"], report[name]["support"]]
        for name in ["0", "1", "macro avg", "weighted avg"]
    ], [22, 18, 18, 18, 18])
    matrix = metrics["confusion_matrix_actual_rows_predicted_columns_0_1"]
    write_sheet("Confusion_matrix", [["Thực tế / dự đoán", "Mua lại (0)", "Không mua lại (1)"],
                                     ["Mua lại (0)", *matrix[0]], ["Không mua lại (1)", *matrix[1]]], [26, 20, 24])
    importance = pd.read_csv(output_dir / "feature_importance.csv").head(20)
    write_sheet("Feature_importance", [["Feature", "Importance"]] + importance.values.tolist(), [45, 22])
    comparison_path = output_dir / "baseline_comparison.json"
    if comparison_path.exists():
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
        rows = [["Mô hình", "Accuracy", "Recall mua lại", "Precision mua lại", "F1 mua lại", "ROC-AUC"]]
        for name in ["random_forest", "logistic_regression", "always_no_repurchase"]:
            metric = comparison[name]
            report = metric["classification_report"]
            rows.append([name, report["accuracy"], report["0"]["recall"], report["0"]["precision"], report["0"]["f1-score"], metric["roc_auc_churn_1"]])
        write_sheet("Baseline_comparison", rows, [28, 16, 20, 22, 18, 16])
    workbook.close()


if __name__ == "__main__":
    export_summary(Path(__file__).resolve().parents[1] / "outputs" / "temporal_v3_provisional")
