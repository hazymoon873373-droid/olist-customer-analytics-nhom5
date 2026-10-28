// Offline execution tests; does not connect to or modify a real MongoDB.
const fs = require('fs');
const vm = require('vm');
const assert = require('assert');
const source = fs.readFileSync(require('path').join(__dirname, '..', 'Mongodb.js'), 'utf8');
const counts = {olist_orders_clean:99441, olist_order_items_clean:112650, geo_by_zip:19015,
  olist_customers_clean:99441, olist_order_payments_clean:103886,
  olist_order_reviews_clean:99224, olist_products_clean:32951, olist_sellers_clean:3095, product_category_name_translation_clean:71};

function run({empty=false, invalidZip=false, invalidConversion=false, customDb=false}={}) {
  const calls=[], writes=[];
  function database(name) {
    function collection(key) { return {
      countDocuments: q => q && q.valid_delay_kpi ? 95097 : q && q.delivered_missing_date ? 8 : q && q.$or ? 0 : counts[key] || 0,
      updateMany: () => writes.push(name+'.'+key), createIndex: () => writes.push(name+'.index'),
      aggregate: pipeline => ({toArray: () => {
        if (pipeline.some(stage => stage.$count)) return invalidZip ? [{n:1}] : [];
        if (pipeline[1] && pipeline[1].$group && pipeline[1].$group.errors)
          return [{nulls:0, errors:invalidConversion ? 1 : 0}];
        return [];
      }}),
    }; }
    return new Proxy({}, {get: (_, prop) => {
      if (prop === 'getSiblingDB') return n => {calls.push(n);return database(n)};
      if (prop === 'getName') return () => name;
      if (prop === 'getCollectionNames') return () => empty ? [] : Object.keys(counts);
      if (prop === 'getCollection') return collection;
      return collection(prop);
    }});
  }
  const code = customDb ? source.replace('dbName: "BigData"', 'dbName: "review_db"') : source;
  try {vm.runInNewContext(code,{db:database('initial'),print:()=>{},ISODate:s=>new Date(s)});return {calls,writes};}
  catch (error) {return {calls,writes,error};}
}
new vm.Script(source);
for (const scenario of [{empty:true},{invalidZip:true},{invalidConversion:true}]) {
  const result=run(scenario); assert(result.error); assert.equal(result.writes.length,0);
}
const custom=run({customDb:true});
assert(!custom.error); assert(custom.calls.every(name=>name==='review_db'));
assert(source.includes('review_score: { $convert'));
console.log('MongoDB script: syntax, empty DB, bad ZIP, bad conversion and configured DB checks passed (mock).');
