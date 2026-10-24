"""Đọc lại file thực tế sau khi chạy; xuất biên bản kiểm tra vào chính run đó."""

import argparse
import csv
import hashlib
import json
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.dont_write_bytecode = True

from collect_all import decode_json_response, inspect_customer_coverage, validate_ibge
from data_catalog import CATALOG, IBGE_FIELDS

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent


def digest(stream):
    checksum = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
        checksum.update(chunk)
    return checksum.hexdigest()


def audit(run):
    run = Path(run).resolve()
    manifest = json.loads((run / "metadata/source_manifest.json").read_text(encoding="utf-8"))
    checks = []

    def check(name, passed, evidence):
        checks.append({"check": name, "passed": bool(passed), "evidence": evidence})

    check("Thư mục dữ liệu đang mở tồn tại", run.is_dir()
          and (run / "raw/olist").is_dir() and (run / "raw/ibge").is_dir(), str(run))
    if run.is_relative_to(PROJECT_ROOT / "dataset"):
        dataset = PROJECT_ROOT / "dataset"
        pointer = json.loads((dataset / "latest_success.json").read_text(encoding="utf-8"))
        pointer_path = Path(pointer["run_path"])
        check("Đường dẫn bàn giao tương đối trỏ đúng dữ liệu", not pointer_path.is_absolute()
              and (dataset / pointer_path).resolve() == run,
              f"dataset/latest_success.json -> {pointer['run_path']}")
        launch = json.loads((PROJECT_ROOT / ".vscode/launch.json").read_text(encoding="utf-8"))
        program = Path(launch["configurations"][0]["program"].replace("${workspaceFolder}", str(PROJECT_ROOT)))
        check("F5 trỏ đúng mã nguồn sau khi dọn", program.resolve() == (ROOT / "collect_all.py").resolve()
              and program.is_file(), str(program))

    olist, ibge = manifest["olist"], manifest["ibge"]
    check("Tải Olist qua HTTPS từ Kaggle", olist.get("mode") == "https_kaggle_download"
          and olist.get("http_receipt", {}).get("http_status") == 200,
          olist.get("http_receipt", {}).get("requested_url", olist.get("mode")))
    check("Gọi IBGE API trực tiếp", ibge.get("mode") == "https_api"
          and ibge.get("http_receipt", {}).get("http_status") == 200,
          ibge.get("endpoint"))
    check("Trạng thái chạy hoàn tất", manifest["status"] == "success" and not manifest["errors"],
          f"Run {manifest['run_id']}; kết thúc {manifest['finished_at_utc']}")

    file_stats = []
    by_name = {row["file_name"]: row for row in olist["files"]}
    archive_path = run / "raw/olist/brazilian-ecommerce.zip"
    with archive_path.open("rb") as stream:
        archive_hash = digest(stream)
    check("ZIP gốc đúng checksum HTTP", archive_hash == olist["archive_sha256"]
          == olist.get("http_receipt", {}).get("response_sha256"), archive_hash)
    with zipfile.ZipFile(archive_path) as archive:
        for name, spec in CATALOG.items():
            path = run / "raw/olist" / name
            with path.open("rb") as stream:
                disk_hash = digest(stream)
            archive_member = next(entry for entry in archive.infolist()
                                  if Path(entry.filename).name == name)
            with archive.open(archive_member) as stream:
                zip_hash = digest(stream)
            with path.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream, strict=True)
                header = next(reader)
                count = 0
                valid_width = True
                for row in reader:
                    count += 1
                    valid_width &= len(row) == len(header)
            actual_size = path.stat().st_size
            record = by_name[name]
            passed = (disk_hash == zip_hash == record["sha256"] and
                      count == record["record_count"] and
                      actual_size == record["file_size_bytes"] and valid_width and
                      header == [field[0] for field in spec["fields"]])
            check(f"Raw CSV: {name}", passed,
                  f"{count:,} record, {actual_size:,} byte; CSV nguyên vẹn so với ZIP và manifest")
            file_stats.append({"file": name, "records": count, "bytes": actual_size})

    wire = run / "raw/ibge/ibge_response.bin"
    raw_json = run / "raw/ibge/ibge_states_raw.json"
    decoded, states = decode_json_response(wire)
    codes = validate_ibge(states)
    with wire.open("rb") as stream:
        wire_hash = digest(stream)
    with raw_json.open("rb") as stream:
        json_hash = digest(stream)
    check("Lưu response IBGE và JSON raw nguyên vẹn",
          wire_hash == ibge["http_receipt"]["response_sha256"]
          and json_hash == ibge["json_sha256"] and raw_json.read_bytes() == decoded
          and len(states) == ibge["record_count"],
          f"{len(states)} record; {raw_json.stat().st_size:,} byte JSON")
    coverage = inspect_customer_coverage(run / "raw/olist/olist_customers_dataset.csv", codes)
    check("Nguồn phụ ghép được với Olist", coverage == manifest["join_coverage"]
          and coverage["coverage_percent"] == 100,
          f"Khớp {coverage['matched_records']:,}/{coverage['customer_records']:,} bản ghi khách hàng")

    with (run / "metadata/record_counts.csv").open(encoding="utf-8-sig", newline="") as stream:
        counts = list(csv.DictReader(stream))
    expected_counts = {row["file"]: row["records"] for row in file_stats}
    expected_counts["ibge_states_raw.json"] = len(states)
    check("Bảng đếm khớp file thực tế", {r["file_name"]: int(r["record_count"]) for r in counts}
          == expected_counts, f"{len(counts)} tệp dữ liệu trên 2 nguồn")
    with (run / "metadata/data_dictionary.csv").open(encoding="utf-8-sig", newline="") as stream:
        dictionary = list(csv.DictReader(stream))
    expected_fields = {(name, field[0]) for name, spec in CATALOG.items() for field in spec["fields"]}
    expected_fields |= {("ibge_states_raw.json", field[0]) for field in IBGE_FIELDS}
    check("Có mô tả đầy đủ các trường", {(r["file"], r["column"]) for r in dictionary} == expected_fields
          and all(r["description_vi"] and r["suggested_etl_type"] for r in dictionary),
          f"{len(dictionary)} trường có tên, kiểu đề xuất và ý nghĩa")
    log = (run / "logs/collection.log").read_text(encoding="utf-8")
    check("Có nhật ký và báo cáo", all((run / p).is_file() for p in (
        "THONG_TIN_DU_LIEU.md", "logs/collection.log"))
        and "HOÀN THÀNH" in log, "Có log đầy đủ 5 bước và thông tin dữ liệu")

    result = {"run_id": manifest["run_id"], "run_path": str(run),
              "verified_at_bangkok": datetime.now(timezone(timedelta(hours=7))).isoformat(),
              "all_passed": all(row["passed"] for row in checks), "checks": checks,
              "olist_records": sum(row["records"] for row in file_stats), "ibge_records": len(states),
              "scope": "5 yêu cầu thu thập của Huy; không chứng nhận điểm hoặc toàn bộ đồ án"}
    (run / "metadata/verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                                    encoding="utf-8")
    report = ["# BIÊN BẢN KIỂM TRA DỮ LIỆU THU THẬP", "",
              f"- Run: `{manifest['run_id']}`",
              f"- Kiểm tra lúc: {result['verified_at_bangkok']} (UTC+7)",
              f"- Kết quả kỹ thuật: {'ĐẠT' if result['all_passed'] else 'CÓ MỤC CHƯA ĐẠT'}",
              "", "| Kiểm tra | Kết quả | Bằng chứng |", "|---|---|---|"]
    report.extend(f"| {r['check']} | {'ĐẠT' if r['passed'] else 'CHƯA ĐẠT'} | {r['evidence']} |"
                  for r in checks)
    report += ["", "## Đối chiếu phạm vi", "",
               "Đường dẫn hiện tại: `dataset/runs/` trong thư mục Huy_ThuThap_Olist. "
               "Các cửa sổ, liên kết hoặc log cũ trỏ tới `data/runs/` cần mở lại ở đường dẫn hiện tại. "
               "Không cần tải lại dữ liệu để khắc phục thông báo Location is not available.", "",
               "Đã thực hiện 5 yêu cầu: tải Olist từ Kaggle, gọi API phù hợp, lưu raw, đếm record, ghi nguồn và mô tả raw.",
               "", "Đối chiếu LabF: có 2 nguồn, có chương trình thu thập, dữ liệu trên 5.000 record. "
               "Phần lưu DBMS, làm sạch, thiết kế MongoDB và phân tích/ML cần nhóm tiếp tục thực hiện theo phân công.",
               "", "Tài liệu crawl của thầy Khải minh họa Scrapy/HTML và lưu MongoDB Atlas. "
               "Chương trình hiện tại thu thập qua HTTPS (ZIP/JSON API); chưa cài spider Scrapy, chưa đẩy dữ liệu lên Atlas. "
               "Nếu áp dụng nguyên yêu cầu bài thực hành trong PDF thì cần làm thêm các phần đó và đúng website của bài lab. "
               "Theo phạm vi đồ án đã chia, Huy bàn giao raw và hồ sơ nguồn cho Thiên làm ETL/MongoDB.",
               "", "Dữ liệu là lần thu thập mới từ Internet của dataset lịch sử; nội dung đơn hàng vẫn thuộc kỳ dữ liệu Olist công bố. "
               "Kết quả kiểm tra kỹ thuật không thay thế đánh giá cuối cùng của giảng viên.", ""]
    (run / "BIEN_BAN_KIEM_TRA.md").write_text("\n".join(report), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path)
    args = parser.parse_args()
    run = args.run_dir
    if run is None:
        dataset = PROJECT_ROOT / "dataset"
        run = dataset / json.loads((dataset / "latest_success.json").read_text(encoding="utf-8"))["run_path"]
    result = audit(run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
