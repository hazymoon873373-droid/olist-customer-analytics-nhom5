"""Import a verified clean snapshot into empty collections without replacing data."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
from pymongo import MongoClient


def import_snapshot(client, database, directory):
    directory = Path(directory)
    manifest = json.loads((directory/'manifest.json').read_text(encoding='utf8'))['sha256']
    files = sorted(p for p in directory.glob('*.csv') if p.name != 'audit_report.csv')
    for path in files:
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest[path.name]:
            raise ValueError('Clean input checksum differs: ' + path.name)
        if client[database][path.stem].count_documents({}) != 0:
            raise ValueError('Refusing to overwrite nonempty collection: ' + path.stem)
    results = []
    for path in files:
        collection = client[database][path.stem]
        batch, count = [], 0
        with path.open(encoding='utf-8-sig', newline='') as stream:
            for row in csv.DictReader(stream):
                batch.append({k: None if value in ('','null') else value for k,value in row.items()})
                if len(batch) == 2000:
                    collection.insert_many(batch)
                    count += len(batch)
                    batch = []
            if batch:
                collection.insert_many(batch)
                count += len(batch)
        results.append({'collection':path.stem,'documents':count,'sha256':manifest[path.name]})
        print(json.dumps(results[-1]), flush=True)
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uri',default=os.environ.get('MONGODB_URI','mongodb://127.0.0.1:27017'))
    parser.add_argument('--db',default='BigData')
    parser.add_argument('--input-dir',type=Path,default=Path(__file__).resolve().parents[1]/'processed')
    args=parser.parse_args()
    with MongoClient(args.uri,serverSelectionTimeoutMS=5000) as client:
        client.admin.command('ping')
        import_snapshot(client,args.db,args.input_dir)
