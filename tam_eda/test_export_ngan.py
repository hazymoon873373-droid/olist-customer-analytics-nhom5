import json,tempfile,unittest,hashlib
from pathlib import Path
from export_ngan import export_ngan,ROOT

class NganExportTests(unittest.TestCase):
    def test_existing_handover_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            sentinel=Path(tmp)/'keep.txt';sentinel.write_text('keep')
            with self.assertRaises(FileExistsError):export_ngan(tmp)
            self.assertEqual(sentinel.read_text(),'keep')

    def test_missing_source_does_not_publish_partial_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'out'
            with self.assertRaises(FileNotFoundError):export_ngan(output,source=Path(tmp)/'missing')
            self.assertFalse(output.exists())

    def test_real_export_files_and_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'ngan';result=export_ngan(output)
            for name,digest in result['files_sha256'].items():
                self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(),digest)
            contract=json.loads((output/result['datasets_contract']).read_text(encoding='utf8'))
            for role,spec in contract['datasets'].items():self.assertTrue((output/'data'/spec['file']).is_file(),role)
            self.assertTrue((output/'data/processed/olist_order_reviews_clean.csv').is_file())

if __name__=='__main__':unittest.main()
