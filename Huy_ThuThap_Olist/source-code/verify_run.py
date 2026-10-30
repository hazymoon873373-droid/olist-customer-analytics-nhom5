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

    rel_run = run.relative_to(PROJECT_ROOT).as_posix() if run.is_relative_to(PROJECT_ROOT) else str(run)
    check("Thư mục dữ liệu đang mở tồn tại", run.is_dir()
          and (run / "raw/olist").is_dir() and (run / "raw/ibge").is_dir(), rel_run)
    if run.is_relative_to(PROJECT_ROOT / "dataset"):
        dataset = PROJECT_ROOT / "dataset"
        pointer = json.loads((dataset / "latest_success.json").read_text(encoding="utf-8"))
        pointer_path = Path(pointer["run_path"])
        check("Đường dẫn bàn giao tương đối trỏ đúng dữ liệu", not pointer_path.is_absolute()
              and (dataset / pointer_path).resolve() == run,
              f"dataset/latest_success.json -> {pointer['run_path']}")
        launch = json.loads((PROJECT_ROOT / ".vscode/launch.json").read_text(encoding="utf-8"))
        program = Path(launch["configurations"][0]["program"].replace("${workspaceFolder}", str(PROJECT_ROOT)))
        resolved_prog = program.resolve()
        rel_prog = resolved_prog.relative_to(PROJECT_ROOT).as_posix() if resolved_prog.is_relative_to(PROJECT_ROOT) else str(program)
        check("F5 trỏ đúng mã nguồn sau khi dọn", resolved_prog == (ROOT / "collect_all.py").resolve()
              and program.is_file(), rel_prog)

    olist, ibge = manifest["olist"], manifest["ibge"]
    olist_live = olist.get("mode") == "https_kaggle_download" and olist.get("http_receipt", {}).get("http_status") == 200
    olist_local = olist.get("mode") == "local_zip_explicit"
    check("Có ZIP Olist nguồn để tái lập", olist_live or olist_local,
          "tải mới từ Kaggle" if olist_live else "dùng ZIP cục bộ; không ghi nhận tải mới" if olist_local else olist.get("mode"))
    ibge_mode = ibge.get("mode")
    ibge_ok = ((ibge_mode == "https_api" and ibge.get("http_receipt", {}).get("http_status") == 200)
               or (ibge_mode == "geocoded_api_with_ibge_region_reference" and
                   sum(page.get("records", 0) for page in ibge.get("response_pages", [])) == 27)
               or (ibge_mode == "verified_local_snapshot" and bool(ibge.get("source_run_id"))))
    check("Nguồn địa lý có 27 UF và provenance", ibge_ok,
          f"{ibge_mode}; endpoint={ibge.get('endpoint')}; snapshot={ibge.get('region_reference_run_id', ibge.get('source_run_id', 'n/a'))}")
    check("Trạng thái chạy hoàn tất", manifest["status"] in ("success", "success_with_alternative_api", "success_with_cached_reference") and not manifest["errors"],
          f"Run {manifest['run_id']}; kết thúc {manifest['finished_at_utc']}")

    file_stats = []
    by_name = {row["file_name"]: row for row in olist["files"]}
    archive_path = run / "raw/olist/brazilian-ecommerce.zip"
    with archive_path.open("rb") as stream:
        archive_hash = digest(stream)
    http_hash = olist.get("http_receipt", {}).get("response_sha256")
    check("ZIP gốc khớp checksum đã ghi", archive_hash == olist["archive_sha256"]
          and (not http_hash or archive_hash == http_hash), archive_hash)
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
    if ibge.get("mode") == "https_api":
        source_hash_ok = wire_hash == ibge.get("http_receipt", {}).get("response_sha256")
        provenance_detail = "response trực tiếp khớp HTTP receipt"
    elif ibge.get("mode") == "geocoded_api_with_ibge_region_reference":
        receipts = ibge.get("response_pages", [])
        pages_ok = bool(receipts)
        for receipt in receipts:
            page_path = run / "raw/ibge" / receipt["file"]
            if not page_path.is_file():
                pages_ok = False
                break
            with page_path.open("rb") as stream:
                pages_ok &= digest(stream) == receipt["sha256"]
        data_root = run.parent.parent
        source_run = (data_root / "runs" / ibge.get("region_reference_run_id", "")).resolve()
        region_ref = source_run / "raw/ibge/ibge_states_raw.json"
        inside_dataset = data_root.resolve() in source_run.parents
        region_ok = False
        if inside_dataset and region_ref.is_file():
            reference = {row["sigla"]: row["regiao"] for row in json.loads(region_ref.read_text(encoding="utf-8"))}
            region_ok = all(reference.get(row["sigla"]) == row["regiao"] for row in states)
        source_hash_ok = pages_ok and region_ok
        provenance_detail = f"Geocoded payload pages checksum verified; region mapping source run {ibge.get('region_reference_run_id')}"
    elif ibge.get("mode") == "verified_local_snapshot":
        dataset_root = run.parent.parent
        source_run = (dataset_root / "runs" / ibge.get("source_run_id", "")).resolve()
        source_wire = source_run / "raw/ibge/ibge_response.bin"
        source_json = source_run / "raw/ibge/ibge_states_raw.json"
        source_hash_ok = (dataset_root.resolve() in source_run.parents and
                          source_wire.is_file() and source_json.is_file() and
                          source_wire.read_bytes() == wire.read_bytes() and
                          source_json.read_bytes() == raw_json.read_bytes())
        provenance_detail = f"snapshot khớp run nguồn {ibge.get('source_run_id')}"
    else:
        source_hash_ok = False
        provenance_detail = f"mode nguồn không được hỗ trợ: {ibge.get('mode')}"
    check("Lưu dữ liệu API địa lý và provenance nguyên vẹn",
          source_hash_ok
          and json_hash == ibge["json_sha256"] and raw_json.read_bytes() == decoded
          and len(states) == ibge["record_count"],
          f"{len(states)} record; {raw_json.stat().st_size:,} byte JSON; {provenance_detail}")
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

    verification_path = run / "metadata/verification.json"
    verified_at = datetime.now(timezone(timedelta(hours=7))).isoformat()
    if verification_path.is_file():
        try:
            prior = json.loads(verification_path.read_text(encoding="utf-8"))
            if (prior.get("run_id") == manifest["run_id"]
                    and prior.get("run_path") == rel_run
                    and prior.get("checks") == checks
                    and prior.get("all_passed") == all(row["passed"] for row in checks)):
                verified_at = prior.get("verified_at_bangkok", verified_at)
        except (OSError, json.JSONDecodeError):
            pass
    result = {"run_id": manifest["run_id"], "run_path": rel_run,
              "verified_at_bangkok": verified_at,
              "all_passed": all(row["passed"] for row in checks), "checks": checks,
              "olist_records": sum(row["records"] for row in file_stats), "ibge_records": len(states),
              "scope": "5 yêu cầu thu thập của Huy; không chứng nhận điểm hoặc toàn bộ đồ án"}
    verification_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
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
               ("Đã lưu 9 CSV Olist và dữ liệu IBGE; lượt chạy này đã gọi API trực tiếp."
                if ibge_mode == "https_api" else
                "Đã lưu 9 CSV Olist và 27 UF từ Geocoded API trực tiếp kèm vùng tham chiếu IBGE; chi tiết ở source_manifest.json."
                if ibge_mode == "geocoded_api_with_ibge_region_reference" else
                "Đã lưu 9 CSV Olist và snapshot IBGE đã xác minh; lượt chạy này không truy cập được API trực tiếp, chi tiết ở source_manifest.json."),
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
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
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
