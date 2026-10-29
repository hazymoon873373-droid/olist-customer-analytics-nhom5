"""Validate the typed clean database and optionally install strict BSON validators.

Run after Mongodb.js. No data is deleted or repaired by this script.
"""
import argparse
import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from pymongo import MongoClient

ROOT = Path(__file__).resolve().parents[1]
TYPES = {
    'olist_orders_clean': {k: 'date' for k in ['order_purchase_timestamp', 'order_approved_at', 'order_delivered_carrier_date', 'order_delivered_customer_date', 'order_estimated_delivery_date']},
    'olist_order_items_clean': {'order_item_id': 'int', 'shipping_limit_date': 'date', 'price': 'double', 'freight_value': 'double'},
    'olist_order_payments_clean': {'payment_sequential': 'int', 'payment_installments': 'int', 'payment_value': 'double'},
    'olist_order_reviews_clean': {'review_score': 'int', 'review_creation_date': 'date', 'review_answer_timestamp': 'date'},
    'olist_products_clean': {**{k: 'int' for k in ['product_name_lenght', 'product_description_lenght', 'product_photos_qty']}, **{k: 'double' for k in ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']}},
    'geo_by_zip': {'geolocation_lat': 'double', 'geolocation_lng': 'double', 'point_count': 'int'},
    'olist_geolocation_clean': {'geolocation_lat': 'double', 'geolocation_lng': 'double'},
}
FLAGS = {
    'olist_orders_clean': ['delivered_missing_date', 'carrier_before_approval', 'customer_before_carrier', 'valid_delay_kpi'],
    'olist_products_clean': ['category_missing', 'weight_zero'],
    'olist_order_reviews_clean': ['review_before_purchase', 'is_duplicate_review_order'],
    'geo_by_zip': ['state_conflict', 'is_outlier_coord', 'usable_for_geo'],
}
KEYS = {'olist_orders_clean': ['order_id'], 'olist_customers_clean': ['customer_id'], 'olist_products_clean': ['product_id'], 'olist_sellers_clean': ['seller_id'], 'olist_order_items_clean': ['order_id', 'order_item_id'], 'geo_by_zip': ['geolocation_zip_code_prefix'], 'product_category_name_translation_clean': ['product_category_name']}


def schemas(directory):
    result = {}
    for path in sorted(directory.glob('*.csv')):
        if path.name == 'audit_report.csv':
            continue
        with path.open(encoding='utf-8-sig', newline='') as stream:
            fields = next(csv.reader(stream))
        props = {k: {'bsonType': [TYPES.get(path.stem, {}).get(k, 'string'), 'null']} for k in fields}
        for k in FLAGS.get(path.stem, []):
            props[k] = {'bsonType': 'bool'}
        for k in KEYS.get(path.stem, []):
            props[k] = {'bsonType': TYPES.get(path.stem, {}).get(k, 'string')}
        for k in ['customer_zip_code_prefix', 'seller_zip_code_prefix']:
            if k in props:
                props[k] = {'bsonType': 'string', 'pattern': '^[0-9]{5}$'}
        if path.stem == 'geo_by_zip':
            props['geolocation_zip_code_prefix']['pattern'] = '^[0-9]{5}$'
        result[path.stem] = {'$jsonSchema': {'bsonType': 'object', 'required': fields, 'properties': props}}
    return result


def inspect(client, name, directory, apply=False):
    database = client[name]
    validators = schemas(directory)
    results = {}
    for collection, validator in validators.items():
        path = directory / (collection + '.csv')
        with path.open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.reader(stream)
            next(reader)
            expected = sum(1 for _ in reader)
        actual = database[collection].count_documents({})
        violations = database[collection].count_documents({'$nor': [validator]})
        if actual != expected or violations:
            raise ValueError(f'{collection}: expected={expected}, actual={actual}, schema_errors={violations}')
        if apply:
            database.command('collMod', collection, validator=validator, validationLevel='strict', validationAction='error')
        results[collection] = {'documents': actual, 'schema_violations': violations, 'indexes': list(database[collection].list_indexes()), 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    relationships = []
    for source, key, target, target_key in [
        ('olist_orders_clean','customer_id','olist_customers_clean','customer_id'),
        ('olist_order_items_clean','order_id','olist_orders_clean','order_id'),
        ('olist_order_items_clean','product_id','olist_products_clean','product_id'),
        ('olist_order_items_clean','seller_id','olist_sellers_clean','seller_id'),
        ('olist_order_payments_clean','order_id','olist_orders_clean','order_id'),
        ('olist_order_reviews_clean','order_id','olist_orders_clean','order_id'),
    ]:
        rows = list(database[source].aggregate([
            {'$lookup': {'from': target, 'localField': key, 'foreignField': target_key, 'as': 'parent'}},
            {'$match': {'parent': {'$size': 0}}}, {'$count': 'n'}
        ]))
        missing = rows[0]['n'] if rows else 0
        relationships.append({'source': source, 'target': target, 'orphans': missing})
        if missing:
            raise ValueError(f'Orphans: {source} / {target}: {missing}')
    quality = {k: database.olist_orders_clean.count_documents({k: True}) for k in FLAGS['olist_orders_clean']}
    if quality['valid_delay_kpi'] != 95097 or quality['delivered_missing_date'] != 8:
        raise ValueError('Quality counts differ from the clean snapshot')
    example = database.olist_orders_clean.find_one({}, {'_id': 0, 'order_id': 1})
    plan = database.command('explain', {'find': 'olist_orders_clean', 'filter': example}, verbosity='executionStats')
    return {'database': name, 'server_version': client.server_info()['version'], 'collections': results, 'relationships': relationships, 'quality_flags': quality, 'index_query': {'filter': example, 'nReturned': plan['executionStats']['nReturned'], 'totalDocsExamined': plan['executionStats']['totalDocsExamined'], 'winningPlan': plan['queryPlanner']['winningPlan']}, 'all_checks_pass': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--uri', default=os.environ.get('MONGODB_URI', 'mongodb://127.0.0.1:27017'))
    parser.add_argument('--db', default='BigData')
    parser.add_argument('--input-dir', type=Path, default=ROOT/'processed')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apply-validators', action='store_true')
    args = parser.parse_args()
    with MongoClient(args.uri, serverSelectionTimeoutMS=5000) as client:
        result = inspect(client, args.db, args.input_dir, args.apply_validators)
    result['checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding='utf8')
    if args.apply_validators:
        (args.output.parent/'bson_validators.json').write_text(json.dumps(schemas(args.input_dir), ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({'all_checks_pass': True, 'collections': len(result['collections']), 'documents': sum(x['documents'] for x in result['collections'].values()), 'output': str(args.output)}, ensure_ascii=False))
