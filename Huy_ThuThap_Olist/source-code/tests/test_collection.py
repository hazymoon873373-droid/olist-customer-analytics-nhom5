"""Kiểm tra các lỗi dễ làm sai dữ liệu/bằng chứng thu thập."""

import csv
import gzip
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from collect_all import decode_json_response, extract_olist, inspect_csv, inspect_customer_coverage, validate_ibge
from data_catalog import CATALOG


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_multiline_csv_counts_records_not_lines(self):
        path = self.root / "reviews.csv"
        path.write_text('id,comment\n1,"good\nproduct"\n2,"ok, thanks"\n', encoding="utf-8")
        spec = {"fields": [("id", "string", "id"), ("comment", "string", "comment")],
                "expected_records": 2, "description": "reviews", "key": "id"}
        result = inspect_csv(path, spec)
        self.assertEqual(result["record_count"], 2)
        self.assertEqual(result["physical_data_lines"], 3)
        self.assertEqual(result["extra_lines_inside_records"], 1)

    def test_schema_drift_and_bad_width_are_rejected(self):
        path = self.root / "data.csv"
        spec = {"fields": [("id", "string", "id")], "expected_records": 1, "description": "", "key": ""}
        for content in ("renamed\n1\n", "id\n1,extra\n"):
            path.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                inspect_csv(path, spec)

    def test_zip_traversal_rejected_before_extracting(self):
        path = self.root / "bad.zip"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("../escape.csv", "bad")
        with self.assertRaises(ValueError):
            extract_olist(path, self.root / "raw")
        self.assertFalse((self.root / "escape.csv").exists())
        self.assertFalse((self.root / "raw").exists())

    def test_zip_requires_all_nine_and_rejects_duplicate_basename(self):
        missing = self.root / "missing.zip"
        with zipfile.ZipFile(missing, "w") as archive:
            archive.writestr("olist_orders_dataset.csv", "order_id\n1\n")
        with self.assertRaises(ValueError):
            extract_olist(missing, self.root / "missing_raw")
        duplicate = self.root / "duplicate.zip"
        with zipfile.ZipFile(duplicate, "w") as archive:
            for name in CATALOG:
                archive.writestr(name, "data")
            archive.writestr("nested/olist_orders_dataset.csv", "duplicate")
        with self.assertRaises(ValueError):
            extract_olist(duplicate, self.root / "duplicate_raw")

    def test_gzip_api_decoding_preserves_json_bytes(self):
        content = json.dumps([{"sigla": "SP", "nome": "São Paulo"}], ensure_ascii=False).encode("utf-8")
        path = self.root / "response.bin"
        path.write_bytes(gzip.compress(content))
        decoded, data = decode_json_response(path)
        self.assertEqual(decoded, content)
        self.assertEqual(data[0]["nome"], "São Paulo")

    def test_duplicate_api_state_codes_rejected(self):
        data = [{"sigla": "SP", "nome": "São Paulo", "regiao": {"nome": "Sudeste", "id": 3}}] * 27
        with self.assertRaises(ValueError):
            validate_ibge(data)

    def test_coverage_reports_unmatched_state(self):
        path = self.root / "customers.csv"
        with path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.writer(stream)
            writer.writerows([["customer_id", "customer_state"], ["1", "SP"], ["2", "XX"]])
        result = inspect_customer_coverage(path, {"SP"})
        self.assertEqual(result["coverage_percent"], 50)
        self.assertEqual(result["unmatched_state_codes"], ["XX"])


if __name__ == "__main__":
    unittest.main()
