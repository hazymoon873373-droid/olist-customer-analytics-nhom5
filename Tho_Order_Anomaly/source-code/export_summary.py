from pathlib import Path
import json

import pandas as pd
import xlsxwriter


def export_summary(output_dir):
    metrics = json.loads((output_dir / "model_metrics.json").read_text(encoding="utf-8"))
    reasons = pd.read_csv(output_dir / "anomaly_reason_counts.csv")
    profile = pd.read_csv(output_dir / "anomaly_feature_profile.csv")
    orders = pd.read_csv(output_dir / "anomalous_orders.csv").head(50)
    columns = ["order_id", "customer_unique_id", "valid_delay_kpi", "delivery_days", "late_days", "anomaly_score", "anomaly_reason"]
    workbook = xlsxwriter.Workbook(output_dir / "anomaly_summary.xlsx")
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
                if isinstance(value, (bool, int, float, str)):
                    sheet.write(row_index, col_index, value, header if row_index == 0 else None)
                else:
                    sheet.write(row_index, col_index, str(value), header if row_index == 0 else None)
        sheet.freeze_panes(1, 0)

    write_sheet("Tong_quan", [["Chỉ tiêu", "Giá trị"], ["Phiên bản", metrics["model_version"]],
        ["Số đơn delivered", metrics["total_orders"]], ["Không đủ KPI giao hàng", metrics["invalid_delay_kpi_orders"]],
        ["Số đơn bất thường", metrics["anomaly_orders"]], ["Tỷ lệ bất thường", metrics["anomaly_rate"]],
        ["Jaccard seed 42 và 7", metrics["seed_7_42_jaccard"]], ["Nguồn", metrics["source_metadata"]["source_status"]]], [32, 65])
    write_sheet("Dau_hieu", [reasons.columns.tolist()] + reasons.values.tolist(), [35, 18])
    write_sheet("Feature_profile", [profile.columns.tolist()] + profile.values.tolist(), [32, 22, 22, 26])
    write_sheet("Top_50", [columns] + orders[columns].values.tolist(), [36, 36, 19, 18, 18, 20, 60])
    workbook.close()


if __name__ == "__main__":
    export_summary(Path(__file__).resolve().parents[1] / "outputs")
