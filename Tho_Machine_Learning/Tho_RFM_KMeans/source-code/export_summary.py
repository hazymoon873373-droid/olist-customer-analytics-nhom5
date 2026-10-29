from pathlib import Path
import json

import pandas as pd
import xlsxwriter


def export_summary(output_dir):
    output_dir = Path(output_dir)
    metrics = json.loads((output_dir / "model_metrics.json").read_text(encoding="utf-8"))
    profiles = pd.read_csv(output_dir / "cluster_profiles.csv")
    evaluation = pd.read_csv(output_dir / "k_evaluation.csv")
    workbook = xlsxwriter.Workbook(output_dir / "rfm_kmeans_summary.xlsx")
    header = workbook.add_format({"bold": True, "font_color": "white", "bg_color": "#1F4E78"})

    def write_sheet(name, rows, widths):
        sheet = workbook.add_worksheet(name)
        sheet.hide_gridlines(2)
        for index, width in enumerate(widths):
            sheet.set_column(index, index, width)
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                if value is None or pd.isna(value):
                    continue
                sheet.write(row_index, column_index, value, header if row_index == 0 else None)
        sheet.freeze_panes(1, 0)

    write_sheet("Tong_quan", [
        ["Chỉ tiêu", "Giá trị"], ["Ngày tham chiếu", metrics["reference_date"]],
        ["Số khách", metrics["customer_count"]], ["K được chọn", metrics["selected_k"]],
        ["Silhouette", metrics["silhouette"]], ["Davies-Bouldin", metrics["davies_bouldin"]],
        ["Calinski-Harabasz", metrics["calinski_harabasz"]], ["Stability ARI", metrics["stability_ari"]],
        ["Mô hình", "K-Means"],
    ], [28, 20])
    write_sheet("Cac_cum", [profiles.columns.tolist()] + profiles.values.tolist(), [12, 18, 18, 18, 18, 18, 18, 18, 18, 60])
    write_sheet("Danh_gia_K", [evaluation.columns.tolist()] + evaluation.values.tolist(), [12, 20, 18, 20, 22, 18, 22, 22])
    workbook.close()


if __name__ == "__main__":
    export_summary(Path(__file__).resolve().parents[1] / "outputs")
