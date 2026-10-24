"""Chạy một lần: Kaggle + API IBGE -> raw + đếm record + hồ sơ nguồn.

Chạy tại thư mục dự án: python -B source-code/collect_all.py
Chỉ dùng thư viện chuẩn Python 3.10+. Mỗi lần chạy tạo thư mục riêng.
"""

import argparse
import csv
import gzip
import hashlib
import io
import json
import logging
import shutil
import sys
import time
import urllib.error
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

sys.dont_write_bytecode = True

from data_catalog import CATALOG, IBGE_DOCS, IBGE_FIELDS, IBGE_URL, KAGGLE_PAGE, KAGGLE_URL

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
MAX_ZIP = 512 * 1024 * 1024
MAX_API = 2 * 1024 * 1024
USER_AGENT = "ABDA433708-Nhom5-DataCollection/1.0 (academic project)"
LOG = logging.getLogger("huy_collection")


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        return
    with Path(path).open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def download(url, target, limit, timeout=45):
    """Lưu nguyên response body và receipt; không ghi cookie/token vào log."""
    if urlsplit(url).scheme != "https":
        raise ValueError("Chỉ tải từ HTTPS")
    for attempt in range(1, 4):
        started = utc_now()
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": USER_AGENT, "Accept-Encoding": "identity",
            })
            with urllib.request.urlopen(request, timeout=timeout) as response:
                if urlsplit(response.geturl()).scheme != "https":
                    raise ValueError("Nguồn chuyển hướng sang HTTP")
                count = 0
                next_progress = 10 * 1024 * 1024
                with Path(target).open("wb") as stream:
                    while chunk := response.read(1024 * 1024):
                        count += len(chunk)
                        if count > limit:
                            raise ValueError("Response vượt giới hạn kích thước")
                        stream.write(chunk)
                        if count >= next_progress:
                            LOG.info("Đã tải %.1f MiB...", count / 1024**2)
                            next_progress += 10 * 1024 * 1024
                receipt = {
                    "requested_url": url,
                    # Không lưu URL signed sau redirect vì có thể chứa token tạm thời.
                    "final_host": urlsplit(response.geturl()).hostname,
                    "http_status": response.status,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_encoding": response.headers.get("Content-Encoding", "identity"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                    "started_at_utc": started, "retrieved_at_utc": utc_now(),
                    "response_body_bytes": count, "response_sha256": sha256_file(target),
                }
            return receipt
        except (OSError, ValueError) as exc:
            LOG.warning("Lần tải %s/3 thất bại: %s", attempt, exc)
            # 4xx không thể giải quyết bằng retry (ngoại trừ rate limit).
            if isinstance(exc, urllib.error.HTTPError) and exc.code in (401, 403, 404):
                raise RuntimeError(f"Nguồn trả HTTP {exc.code}; không tự vượt chặn truy cập") from exc
            if attempt == 3:
                raise
            time.sleep(attempt)


def extract_olist(archive_path, raw_dir):
    """Chỉ giải nén đúng 9 CSV; từ chối traversal, symlink và tên trùng."""
    with zipfile.ZipFile(archive_path) as archive:
        entries = {}
        if sum(entry.file_size for entry in archive.infolist()) > MAX_ZIP:
            raise ValueError("ZIP có tổng kích thước giải nén quá lớn")
        for entry in archive.infolist():
            name = entry.filename.replace("\\", "/")
            parts = PurePosixPath(name)
            if parts.is_absolute() or ".." in parts.parts or ":" in name:
                raise ValueError(f"Đường dẫn ZIP không an toàn: {name}")
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("ZIP chứa symlink")
            if not entry.is_dir() and parts.name in CATALOG:
                if parts.name in entries:
                    raise ValueError("ZIP chứa tên CSV trùng")
                entries[parts.name] = entry
        missing = set(CATALOG) - set(entries)
        if missing:
            raise ValueError(f"ZIP thiếu: {sorted(missing)}")
        raw_dir.mkdir(parents=True, exist_ok=False)
        for name, entry in entries.items():
            with archive.open(entry) as source, (raw_dir / name).open("xb") as target:
                shutil.copyfileobj(source, target)


def inspect_csv(path, spec):
    """CSV parser đếm record đúng khi review chứa xuống dòng trong ô."""
    expected = [field[0] for field in spec["fields"]]
    missing = [0] * len(expected)
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream, strict=True)
        header = next(reader, None)
        if header != expected:
            raise ValueError(f"Schema thay đổi trong {path.name}: {header}")
        count = 0
        for record in reader:
            if len(record) != len(expected):
                raise ValueError(f"{path.name}: record {count + 1} sai số cột")
            count += 1
            for index, value in enumerate(record):
                missing[index] += int(value == "")
        physical_lines = reader.line_num - 1
    if count == 0:
        raise ValueError(f"Tệp không có dữ liệu: {path.name}")
    return {
        "file_name": path.name, "record_count": count, "column_count": len(expected),
        "reference_record_count": spec["expected_records"],
        "reference_count_matches": count == spec["expected_records"],
        "physical_data_lines": physical_lines,
        "extra_lines_inside_records": physical_lines - count,
        "file_size_bytes": Path(path).stat().st_size,
        "sha256": sha256_file(path), "schema_valid": True,
        "missing_by_column": dict(zip(expected, missing)),
        "description": spec["description"], "key_notes": spec["key"],
    }


def decode_json_response(raw_path):
    """IBGE có thể gửi gzip dù đã yêu cầu identity; giải nén có giới hạn."""
    body = Path(raw_path).read_bytes()
    if body.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(body)) as stream:
            decoded = stream.read(MAX_API + 1)
    else:
        decoded = body
    if len(decoded) > MAX_API:
        raise ValueError("JSON sau giải nén quá lớn")
    return decoded, json.loads(decoded.decode("utf-8-sig"))


def validate_ibge(data):
    if not isinstance(data, list) or len(data) != 27:
        raise ValueError("API phải trả 27 đơn vị liên bang Brazil")
    codes = set()
    regions = set()
    for row in data:
        state = row["sigla"]
        if not isinstance(state, str) or len(state) != 2 or not state.isupper() or state in codes:
            raise ValueError("Mã bang thiếu, trùng hoặc không hợp lệ")
        if not row["nome"] or not row["regiao"]["nome"]:
            raise ValueError("API thiếu tên bang/vùng")
        codes.add(state)
        regions.add(row["regiao"]["id"])
    if len(regions) != 5:
        raise ValueError("API không có đủ 5 vùng lớn Brazil")
    return codes


def inspect_customer_coverage(customers_path, state_codes):
    matched, total, unknown = 0, 0, set()
    with Path(customers_path).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            total += 1
            state = row["customer_state"]
            matched += int(state in state_codes)
            if state not in state_codes:
                unknown.add(state)
    return {
        "join_rule": "Olist.customer_state = IBGE.sigla",
        "customer_records": total, "matched_records": matched,
        "coverage_percent": round(matched * 100 / total, 4) if total else 0,
        "unmatched_state_codes": sorted(unknown),
    }


def create_reports(run, manifest):
    meta = run / "metadata"
    meta.mkdir(exist_ok=True)
    write_json(meta / "source_manifest.json", manifest)
    files = manifest["olist"]["files"]
    summary_rows = [{
        "source": "Olist / Kaggle", "file_name": row["file_name"],
        "record_count": row["record_count"], "column_count": row["column_count"],
        "file_size_bytes": row["file_size_bytes"], "sha256": row["sha256"],
        "description": row["description"],
    } for row in files]
    api = manifest["ibge"]
    if api["status"] == "success":
        summary_rows.append({
            "source": "IBGE API", "file_name": "ibge_states_raw.json",
            "record_count": api["record_count"], "column_count": len(IBGE_FIELDS),
            "file_size_bytes": api["json_bytes"], "sha256": api["json_sha256"],
            "description": "27 đơn vị liên bang Brazil, gồm bang/đặc khu và 5 vùng lớn",
        })
    write_csv(meta / "record_counts.csv", summary_rows)
    dictionary = []
    for name, spec in CATALOG.items():
        if not any(row["file_name"] == name for row in files):
            continue
        for column, dtype, description in spec["fields"]:
            dictionary.append({"source": "Olist", "file": name, "column": column,
                               "suggested_etl_type": dtype, "description_vi": description})
    if api["status"] == "success":
        dictionary.extend({"source": "IBGE", "file": "ibge_states_raw.json", "column": col,
                           "suggested_etl_type": dtype, "description_vi": desc}
                          for col, dtype, desc in IBGE_FIELDS)
    write_csv(meta / "data_dictionary.csv", dictionary)
    total_olist = sum(row["record_count"] for row in files)
    total_api = api.get("record_count", 0)
    lines = [
        "# KẾT QUẢ THU THẬP DỮ LIỆU - NGUYỄN GIA HUY / NHÓM 5",
        "", f"- Trạng thái: **{manifest['status'].upper()}**",
        f"- Run ID: `{manifest['run_id']}`",
        f"- Thời gian bắt đầu (UTC): {manifest['started_at_utc']}",
        f"- Thời gian kết thúc (UTC): {manifest['finished_at_utc']}",
        f"- Olist: **{len(files)} CSV / {total_olist:,} bản ghi**",
        f"- IBGE API: **{total_api} bản ghi**; trạng thái: {api['status']}",
        f"- Tổng bản ghi trên các tệp nguồn: **{total_olist + total_api:,}**",
        "", "Tổng trên là tổng các bảng, không phải số đơn hàng hoặc khách hàng duy nhất.",
        "", "## Nguồn và phương thức", "",
        f"- Olist: {KAGGLE_PAGE}",
        f"- Phương thức Olist: `{manifest['olist'].get('mode', 'failed')}`.",
        "- Giấy phép dataset Olist: CC BY-NC-SA 4.0; giữ ghi công và tuân thủ điều kiện của nguồn.",
        f"- IBGE: {IBGE_DOCS}", f"- Endpoint: {IBGE_URL}",
        "- IBGE được dùng để bổ sung nhãn bang/vùng cho BI; không suy diễn GDP/dân số lịch sử.",
        "- Chưa xác minh số phiên bản Kaggle; mỗi tệp được định danh bằng SHA-256 và thời điểm tải.",
        "", "## Số lượng và mô tả dữ liệu raw", "",
        "| Tệp | Record | Cột | Mô tả |", "|---|---:|---:|---|",
    ]
    lines.extend(f"| {r['file_name']} | {r['record_count']:,} | {r['column_count']} | {r['description']} |"
                 for r in summary_rows)
    if manifest.get("join_coverage"):
        coverage = manifest["join_coverage"]
        lines += ["", "## Khả năng liên kết nguồn", "",
                  f"`{coverage['join_rule']}`",
                  f"Khớp {coverage['matched_records']:,}/{coverage['customer_records']:,} bản ghi khách hàng "
                  f"({coverage['coverage_percent']}%).",
                  f"Mã bang chưa khớp: {coverage['unmatched_state_codes']}"]
    lines += ["", "## Tệp bằng chứng", "",
        "- `raw/olist/brazilian-ecommerce.zip`: tệp ZIP gốc (nếu tải thành công).",
              "- `raw/olist/*.csv`: 9 CSV nguyên bản, không làm sạch hoặc đổi tên cột.",
              "- `raw/ibge/ibge_response.bin`: response body gốc; có thể được mã hóa gzip.",
              "- `raw/ibge/ibge_states_raw.json`: JSON sau giải mã truyền tải, giữ nguyên nội dung.",
              "- `metadata/source_manifest.json`: nguồn, mô tả, checksum, thời điểm, HTTP receipt.",
              "- `metadata/record_counts.csv`: số record từng tệp.",
              "- `metadata/data_dictionary.csv`: ý nghĩa và kiểu đề xuất cho từng trường.",
              "- `logs/collection.log`: nhật ký chạy.", "", "## Lưu ý khi bàn giao", "",
              "- Đếm CSV bằng parser vì review có nội dung nhiều dòng.",
              "- Giá tiền là BRL; mã bưu chính cần giữ dạng chuỗi.",
              "- Nhận diện khách mua lại bằng customer_unique_id, liên kết đơn qua customer_id.",
              "- Thiên tiếp nhận raw để làm sạch/ETL/MongoDB; Thọ phụ trách nhãn và ML; Tâm phụ trách BI.",
              "- Không cộng lại giá trị sau các phép join 1-n nếu chưa tổng hợp về đúng cấp đơn hàng.",
              "- Dữ liệu IBGE được lấy ở thời điểm chạy hiện tại, dùng làm bảng tham chiếu địa lý."]
    if manifest["errors"]:
        lines += ["", "## Lỗi cần xử lý", ""] + [f"- {x}" for x in manifest["errors"]]
    report = "\n".join(lines) + "\n"
    (run / "THONG_TIN_DU_LIEU.md").write_text(report, encoding="utf-8")


def collect(output_root, timeout=45, local_zip=None):
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid.uuid4().hex[:6]
    run = output_root / run_id
    (run / "logs").mkdir(parents=True)
    (run / "raw" / "olist").mkdir(parents=True)
    (run / "raw" / "ibge").mkdir(parents=True)
    LOG.setLevel(logging.INFO)
    LOG.handlers.clear()
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    for handler in [logging.StreamHandler(sys.stdout),
                    logging.FileHandler(run / "logs" / "collection.log", encoding="utf-8")]:
        handler.setFormatter(formatter)
        LOG.addHandler(handler)
    manifest = {
        "run_id": run_id, "started_at_utc": utc_now(), "status": "running",
        "collector": "Nguyen Gia Huy - Nhom 5 - ABDA433708", "errors": [],
        "olist": {"status": "pending", "source_page": KAGGLE_PAGE, "files": []},
        "ibge": {"status": "pending", "documentation": IBGE_DOCS, "endpoint": IBGE_URL},
    }
    LOG.info("BẮT ĐẦU THU THẬP - run %s", run_id)
    LOG.info("Thư mục kết quả: %s", run)
    try:
        LOG.info("[1/5] Tải dataset Olist từ Kaggle")
        archive = run / "raw" / "olist" / "brazilian-ecommerce.zip"
        if local_zip:
            shutil.copyfile(local_zip, archive)
            manifest["olist"].update(mode="local_zip_explicit", local_path=str(Path(local_zip).resolve()))
            LOG.info("Dùng ZIP cục bộ theo tham số --local-zip; không ghi nhận là tải mới")
        else:
            receipt = download(KAGGLE_URL, archive, MAX_ZIP, timeout)
            manifest["olist"].update(mode="https_kaggle_download", http_receipt=receipt)
        if not zipfile.is_zipfile(archive):
            raise ValueError("Kaggle không trả ZIP; có thể là trang đăng nhập hoặc lỗi")
        manifest["olist"]["archive_sha256"] = sha256_file(archive)
        LOG.info("[2/5] Lưu 9 CSV raw và đếm bản ghi bằng CSV parser")
        # Giải nén vào thư mục mới rồi chuyển từng CSV ra cạnh ZIP gốc.
        staging = run / "raw" / "olist" / "csv"
        extract_olist(archive, staging)
        for name, spec in CATALOG.items():
            path = run / "raw" / "olist" / name
            (staging / name).replace(path)
            result = inspect_csv(path, spec)
            manifest["olist"]["files"].append(result)
            LOG.info("%-40s %10s record | %2s cột", name, f"{result['record_count']:,}", result["column_count"])
            if not result["reference_count_matches"]:
                LOG.warning("Số lượng khác bản tham chiếu: cần kiểm tra phiên bản dataset")
        staging.rmdir()
        manifest["olist"]["status"] = "success"
    except Exception as exc:
        manifest["olist"]["status"] = "failed"
        manifest["errors"].append(f"Olist: {type(exc).__name__}: {exc}")
        LOG.exception("Bước Olist thất bại")
    try:
        LOG.info("[3/5] Gọi API IBGE - bang/vùng Brazil")
        wire_path = run / "raw" / "ibge" / "ibge_response.bin"
        receipt = download(IBGE_URL, wire_path, MAX_API, timeout)
        decoded, data = decode_json_response(wire_path)
        state_codes = validate_ibge(data)
        json_path = run / "raw" / "ibge" / "ibge_states_raw.json"
        json_path.write_bytes(decoded)
        manifest["ibge"].update(
            status="success", mode="https_api", http_receipt=receipt,
            record_count=len(data), json_bytes=len(decoded), json_sha256=sha256_file(json_path),
            description="27 đơn vị liên bang và 5 vùng lớn Brazil; nối Olist.customer_state = IBGE.sigla",
            temporal_scope="Tham chiếu địa lý tại thời điểm tải; không phải dữ liệu kinh tế lịch sử 2016-2018",
            license_note="Giữ nguồn IBGE; chưa khẳng định mã giấy phép riêng cho endpoint",
        )
        LOG.info("IBGE: %s bản ghi; %s vùng lớn", len(data), len({r['regiao']['id'] for r in data}))
        customers = run / "raw" / "olist" / "olist_customers_dataset.csv"
        if manifest["olist"]["status"] == "success":
            manifest["join_coverage"] = inspect_customer_coverage(customers, state_codes)
            LOG.info("Ghép customer_state với sigla: %.2f%%", manifest["join_coverage"]["coverage_percent"])
    except Exception as exc:
        manifest["ibge"]["status"] = "failed"
        manifest["errors"].append(f"IBGE: {type(exc).__name__}: {exc}")
        LOG.exception("Bước API IBGE thất bại")
    manifest["finished_at_utc"] = utc_now()
    manifest["status"] = "success" if not manifest["errors"] else "partial_failure"
    LOG.info("[4/5] Ghi nguồn, mô tả raw, data dictionary và checksum")
    create_reports(run, manifest)
    if manifest["status"] == "success":
        write_json(output_root.parent / "latest_success.json", {
            "run_id": run_id, "run_path": run.relative_to(output_root.parent).as_posix(),
        })
    LOG.info("[5/5] %s", "HOÀN THÀNH" if not manifest["errors"] else "CÓ LỖI - xem log/manifest")
    total = sum(row["record_count"] for row in manifest["olist"]["files"])
    LOG.info("Olist: %s record | IBGE: %s record", f"{total:,}", manifest["ibge"].get("record_count", 0))
    LOG.info("Thông tin dữ liệu: %s", run / "THONG_TIN_DU_LIEU.md")
    for handler in LOG.handlers[:]:
        handler.flush()
        handler.close()
        LOG.removeHandler(handler)
    return run, manifest


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=PROJECT_ROOT / "dataset" / "runs")
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--local-zip", type=Path, help="Tùy chọn ZIP có sẵn; vẫn gọi IBGE trực tiếp")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("timeout phải lớn hơn 0")
    run, manifest = collect(args.output_root, args.timeout, args.local_zip)
    print("\nKẾT QUẢ ĐÃ LƯU TẠI:", run, flush=True)
    return 0 if manifest["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
