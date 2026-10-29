"""Create a gzip archive, restore into an EMPTY separate database, and compare.

Requires MongoDB Database Tools on PATH or explicit --dump-tool/--restore-tool.
Never uses --drop and refuses to restore over an existing database.
"""
import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient


def run_tool(arguments):
    result = subprocess.run(arguments, capture_output=True, text=True, encoding='utf8', errors='replace')
    if result.returncode:
        # Do not put a URI (possibly containing a password) in saved evidence.
        raise RuntimeError('MongoDB tool failed; inspect locally. Exit=' + str(result.returncode))


def snapshot(database):
    hashes = database.command('dbHash')['collections']
    return {name: {'documents': database[name].count_documents({}), 'bson_md5': hashes[name],
                   'indexes': sorted(database[name].list_indexes(), key=lambda index: index['name']), 'options': database[name].options()}
            for name in sorted(database.list_collection_names()) if not name.startswith('system.')}


def backup_and_compare(uri, source, target, archive, evidence, dump_tool, restore_tool):
    archive, evidence = Path(archive), Path(evidence)
    if source == target or archive.exists():
        raise ValueError('Source and target must differ; archive must be a new file.')
    archive.parent.mkdir(parents=True, exist_ok=True)
    with MongoClient(uri, serverSelectionTimeoutMS=5000) as client:
        if target in client.list_database_names():
            raise ValueError('Refusing to restore into an existing database: ' + target)
        before = snapshot(client[source])
        if not before:
            raise ValueError('Source database is empty')
        run_tool([dump_tool, '--uri', uri, '--db', source, '--gzip', '--archive='+str(archive)])
        run_tool([restore_tool, '--uri', uri, '--gzip', '--archive='+str(archive), '--nsInclude='+source+'.*', '--nsFrom='+source+'.*', '--nsTo='+target+'.*'])
        after = snapshot(client[target])
        if before != after:
            raise ValueError('Restore verification failed: documents, BSON hashes, indexes or validators differ')
        if snapshot(client[source]) != before:
            raise ValueError('Source database changed during verification')
        result = {'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'environment': 'isolated MongoDB on localhost; not Atlas',
                  'server_version': client.server_info()['version'], 'source_database': source, 'restored_database': target,
                  'archive_file': archive.name, 'archive_bytes': archive.stat().st_size,
                  'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                  'dump_tool_version': subprocess.check_output([dump_tool, '--version'], text=True).splitlines()[0],
                  'restore_tool_version': subprocess.check_output([restore_tool, '--version'], text=True).splitlines()[0],
                  'collections': before, 'all_checks_pass': True,
                  'checks': ['same collection names', 'same document counts', 'same server BSON dbHash MD5 per collection', 'same index definitions', 'same validators and options', 'source unchanged']}
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(result, indent=2, ensure_ascii=False, default=str), encoding='utf8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uri', default=os.environ.get('MONGODB_URI','mongodb://127.0.0.1:27017'))
    parser.add_argument('--source-db', default='BigData')
    parser.add_argument('--restore-db', required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--dump-tool', default='mongodump')
    parser.add_argument('--restore-tool', default='mongorestore')
    args = parser.parse_args()
    result = backup_and_compare(args.uri, args.source_db, args.restore_db, args.archive, args.evidence, args.dump_tool, args.restore_tool)
    print(json.dumps({'all_checks_pass': result['all_checks_pass'], 'collections': len(result['collections']), 'archive_bytes': result['archive_bytes']}))
