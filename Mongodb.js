// =====================================================================
// 1. CHỌN CƠ SỞ DỮ LIỆU ĐÍCH
// =====================================================================
const TARGET_DB = "BigData";
db = db.getSiblingDB(TARGET_DB);

print("\n=== [1] BẮT ĐẦU ĐỊNH KIỂU VÀ KIỂM TRA GIÁ TRỊ LỖI TRÊN DATABASE: " + db.getName() + " ===");

// ---------------------------------------------------------------------
// HÀM BỔ TRỢ: THỐNG KÊ GIÁ TRỊ LỖI TRƯỚC KHUYỂN ĐỔI (TRÁNH ÂM THẦM BIẾN THÀNH NULL)
// ---------------------------------------------------------------------
function checkConversionFailures(collectionName, fieldsConfig) {
  print("\n --- Kiểm tra tính hợp lệ trước khi chuyển đổi tại: " + collectionName + " ---");
  var coll = db.getCollection(collectionName);
  
  fieldsConfig.forEach(function(cfg) {
    var field = cfg.field;
    var targetType = cfg.targetType;
    
    var invalidCount = 0;
    if (targetType === "int" || targetType === "double") {
      invalidCount = coll.countDocuments({
        $and: [
          { [field]: { $exists: true, $ne: null } },
          { [field]: { $not: { $type: "number" } } },
          { [field]: { $not: { $regex: "^-?[0-9]+(\\.[0-9]+)?$" } } },
          { [field]: { $nin: ["", "null", "nan", "None"] } }
        ]
      });
    } else if (targetType === "date") {
      invalidCount = coll.countDocuments({
        $and: [
          { [field]: { $exists: true, $ne: null } },
          { [field]: { $not: { $type: "date" } } },
          { [field]: { $not: { $regex: "^[0-9]{4}-[0-9]{2}-[0-9]{2}" } } },
          { [field]: { $nin: ["", "null", "nan", "None"] } }
        ]
      });
    }
    print("   * Trường '" + field + "' -> Kỳ vọng (" + targetType + ") | Giá trị bất thường: " + invalidCount);
  });
}

// Kiểm tra trước khi thực thi
checkConversionFailures("olist_products_clean", [
  { field: "product_name_lenght", targetType: "int" },
  { field: "product_weight_g", targetType: "double" }
]);
checkConversionFailures("olist_orders_clean", [
  { field: "order_purchase_timestamp", targetType: "date" }
]);

// ---------------------------------------------------------------------
// 2. CẬP NHẬT KIỂU DỮ LIỆU TẠI CHỖ (IN-PLACE VIA updateMany PIPELINE)
// ---------------------------------------------------------------------

// 2.1 olist_orders_clean
db.olist_orders_clean.updateMany({}, [
  {
    $set: {
      order_purchase_timestamp: { $convert: { input: "$order_purchase_timestamp", to: "date", onError: null, onNull: null } },
      order_approved_at: { $convert: { input: "$order_approved_at", to: "date", onError: null, onNull: null } },
      order_delivered_carrier_date: { $convert: { input: "$order_delivered_carrier_date", to: "date", onError: null, onNull: null } },
      order_delivered_customer_date: { $convert: { input: "$order_delivered_customer_date", to: "date", onError: null, onNull: null } },
      order_estimated_delivery_date: { $convert: { input: "$order_estimated_delivery_date", to: "date", onError: null, onNull: null } },
      delivered_missing_date: { $eq: [{ $toLower: { $toString: "$delivered_missing_date" } }, "true"] },
      carrier_before_approval: { $eq: [{ $toLower: { $toString: "$carrier_before_approval" } }, "true"] },
      customer_before_carrier: { $eq: [{ $toLower: { $toString: "$customer_before_carrier" } }, "true"] },
      valid_delay_kpi: { $eq: [{ $toLower: { $toString: "$valid_delay_kpi" } }, "true"] }
    }
  }
]);

// 2.2 olist_products_clean (Chuyển chuỗi số "40.0" -> double -> int)
db.olist_products_clean.updateMany({}, [
  {
    $set: {
      product_name_lenght: { $toInt: { $convert: { input: "$product_name_lenght", to: "double", onError: null, onNull: null } } },
      product_description_lenght: { $toInt: { $convert: { input: "$product_description_lenght", to: "double", onError: null, onNull: null } } },
      product_photos_qty: { $toInt: { $convert: { input: "$product_photos_qty", to: "double", onError: null, onNull: null } } },
      product_weight_g: { $convert: { input: "$product_weight_g", to: "double", onError: null, onNull: null } },
      product_length_cm: { $convert: { input: "$product_length_cm", to: "double", onError: null, onNull: null } },
      product_height_cm: { $convert: { input: "$product_height_cm", to: "double", onError: null, onNull: null } },
      product_width_cm: { $convert: { input: "$product_width_cm", to: "double", onError: null, onNull: null } },
      category_missing: { $eq: [{ $toLower: { $toString: "$category_missing" } }, "true"] },
      weight_zero: { $eq: [{ $toLower: { $toString: "$weight_zero" } }, "true"] }
    }
  }
]);

// 2.3 olist_order_items_clean
db.olist_order_items_clean.updateMany({}, [
  {
    $set: {
      order_item_id: { $toInt: { $convert: { input: "$order_item_id", to: "double", onError: null, onNull: null } } },
      shipping_limit_date: { $convert: { input: "$shipping_limit_date", to: "date", onError: null, onNull: null } },
      price: { $convert: { input: "$price", to: "double", onError: null, onNull: null } },
      freight_value: { $convert: { input: "$freight_value", to: "double", onError: null, onNull: null } }
    }
  }
]);

// 2.4 olist_order_payments_clean
db.olist_order_payments_clean.updateMany({}, [
  {
    $set: {
      payment_sequential: { $toInt: { $convert: { input: "$payment_sequential", to: "double", onError: null, onNull: null } } },
      payment_installments: { $toInt: { $convert: { input: "$payment_installments", to: "double", onError: null, onNull: null } } },
      payment_value: { $convert: { input: "$payment_value", to: "double", onError: null, onNull: null } }
    }
  }
]);

// 2.5 olist_order_reviews_clean
db.olist_order_reviews_clean.updateMany({}, [
  {
    $set: {
      review_score: { $toInt: { $convert: { input: "$review_score", to: "double", onError: null, onNull: null } } },
      review_creation_date: { $convert: { input: "$review_creation_date", to: "date", onError: null, onNull: null } },
      review_answer_timestamp: { $convert: { input: "$review_answer_timestamp", to: "date", onError: null, onNull: null } },
      review_before_purchase: { $eq: [{ $toLower: { $toString: "$review_before_purchase" } }, "true"] },
      is_duplicate_review_order: { $eq: [{ $toLower: { $toString: "$is_duplicate_review_order" } }, "true"] }
    }
  }
]);

// 2.6 geo_by_zip
db.geo_by_zip.updateMany({}, [
  {
    $set: {
      geolocation_lat: { $convert: { input: "$geolocation_lat", to: "double", onError: null, onNull: null } },
      geolocation_lng: { $convert: { input: "$geolocation_lng", to: "double", onError: null, onNull: null } },
      point_count: { $toInt: { $convert: { input: "$point_count", to: "double", onError: null, onNull: null } } },
      state_conflict: { $eq: [{ $toLower: { $toString: "$state_conflict" } }, "true"] },
      is_outlier_coord: { $eq: [{ $toLower: { $toString: "$is_outlier_coord" } }, "true"] },
      usable_for_geo: { $eq: [{ $toLower: { $toString: "$usable_for_geo" } }, "true"] }
    }
  }
]);

// ---------------------------------------------------------------------
// 3. TẠO INDEX TRÊN DATABASE BigData
// ---------------------------------------------------------------------
db.olist_customers_clean.createIndex({ customer_id: 1 }, { unique: true });
db.olist_orders_clean.createIndex({ order_id: 1 }, { unique: true });
db.olist_products_clean.createIndex({ product_id: 1 }, { unique: true });
db.olist_sellers_clean.createIndex({ seller_id: 1 }, { unique: true });
db.geo_by_zip.createIndex({ geolocation_zip_code_prefix: 1 }, { unique: true });
db.product_category_name_translation_clean.createIndex({ product_category_name: 1 }, { unique: true });

db.olist_order_items_clean.createIndex({ order_id: 1, order_item_id: 1 }, { unique: true });
db.olist_order_payments_clean.createIndex({ order_id: 1, payment_sequential: 1 }, { unique: true });
db.olist_order_reviews_clean.createIndex({ review_id: 1, order_id: 1 }, { unique: true });

db.olist_orders_clean.createIndex({ customer_id: 1 });
db.olist_orders_clean.createIndex({ valid_delay_kpi: 1 });
db.olist_order_items_clean.createIndex({ product_id: 1 });
db.olist_order_items_clean.createIndex({ seller_id: 1 });
db.olist_order_reviews_clean.createIndex({ order_id: 1 });
db.olist_customers_clean.createIndex({ customer_unique_id: 1 });

print("=== [2] HOÀN TẤT CẬP NHẬT TẠI CHỖ VÀ TẠO INDEX TRÊN DATABASE BigData ===");

db = db.getSiblingDB("BigData");

print("\n=======================================================================");
print("   BÁO CÁO AUDIT KIỂM TRA TOÀN DIỆN (100% DOCUMENTS) - DATABASE: BigData");
print("=======================================================================");

var overallPassed = true;

function logCheck(section, checkName, status, details) {
  var statusTag = status === "PASS" ? "[ĐẠT - PASS]" : "[KHÔNG ĐẠT - FAIL]";
  print(" " + statusTag + " " + section.padEnd(22) + " | " + checkName);
  if (details) print("      └─ Chi tiết phân phối : " + details);
  if (status === "FAIL") overallPassed = false;
}

// ---------------------------------------------------------------------
// 1. THỐNG KÊ $type CHO CÁC TRƯỜNG QUAN TRỌNG (QUÉT 100% COLLECTION)
// ---------------------------------------------------------------------
print("\n-----------------------------------------------------------------------");
print(" 1. KIỂM TRA KIỂU DỮ LIỆU BSON ($type DISTRIBUTION ACROSS 100% DOCUMENTS)");
print("-----------------------------------------------------------------------");

function checkFieldTypes(collName, fieldName, expectedTypes) {
  var coll = db.getCollection(collName);
  var typeDist = coll.aggregate([
    { $group: { _id: { $type: "$" + fieldName }, count: { $sum: 1 } } }
  ]).toArray();

  var isPass = typeDist.every(t => expectedTypes.includes(t._id));
  var details = typeDist.map(t => t._id + ": " + t.count.toLocaleString() + " docs").join(" | ");
  logCheck("Kiểm Tra Kiểu BSON", collName + "." + fieldName, isPass ? "PASS" : "FAIL", details);
}

// A. Kiểu Ngày Tháng (ISODate)
checkFieldTypes("olist_orders_clean", "order_purchase_timestamp", ["date", "null"]);
checkFieldTypes("olist_orders_clean", "order_delivered_customer_date", ["date", "null"]);
checkFieldTypes("olist_order_items_clean", "shipping_limit_date", ["date", "null"]);
checkFieldTypes("olist_order_reviews_clean", "review_creation_date", ["date", "null"]);

// B. Kiểu Số Tiền & Giá Trị Số (Double / Int32)
checkFieldTypes("olist_order_items_clean", "price", ["double", "null"]);
checkFieldTypes("olist_order_items_clean", "freight_value", ["double", "null"]);
checkFieldTypes("olist_order_payments_clean", "payment_value", ["double", "null"]);
checkFieldTypes("olist_products_clean", "product_weight_g", ["double", "null"]);
checkFieldTypes("olist_order_items_clean", "order_item_id", ["int", "null"]);

// C. Kiểu Cờ Boolean
checkFieldTypes("olist_orders_clean", "valid_delay_kpi", ["bool"]);
checkFieldTypes("olist_orders_clean", "delivered_missing_date", ["bool"]);
checkFieldTypes("geo_by_zip", "usable_for_geo", ["bool"]);

// D. Mã ZIP chuẩn Chuỗi String 5 Ký Tự Số (Regex: ^[0-9]{5}$)
function checkZipFormat(collName, zipField) {
  var coll = db.getCollection(collName);
  var invalidZips = coll.countDocuments({
    $or: [
      { [zipField]: { $not: { $type: "string" } } },
      { [zipField]: { $not: { $regex: "^[0-9]{5}$" } } }
    ]
  });
  logCheck("Định Dạng Mã ZIP", collName + "." + zipField + " (String 5 chữ số)", invalidZips === 0 ? "PASS" : "FAIL", "Vi phạm: " + invalidZips + " bản ghi");
}
checkZipFormat("olist_customers_clean", "customer_zip_code_prefix");
checkZipFormat("olist_sellers_clean", "seller_zip_code_prefix");
checkZipFormat("geo_by_zip", "geolocation_zip_code_prefix");

// ---------------------------------------------------------------------
// 2. KIỂM TRA TRÙNG KHÓA (PRIMARY & COMPOSITE KEYS)
// ---------------------------------------------------------------------
print("\n-----------------------------------------------------------------------");
print(" 2. KIỂM TRA ĐỘC NHẤT CỦA KHÓA CHÍNH VÀ KHÓA PHỨC HỢP");
print("-----------------------------------------------------------------------");

function checkUniqueKey(collName, keySpec, keyLabel) {
  var coll = db.getCollection(collName);
  var dups = coll.aggregate([
    { $group: { _id: keySpec, count: { $sum: 1 } } },
    { $match: { count: { $gt: 1 } } }
  ]).toArray().length;
  logCheck("Kiểm Tra Khóa Trùng", collName + " -> " + keyLabel, dups === 0 ? "PASS" : "FAIL", dups > 0 ? "Số khóa trùng: " + dups : "Không trùng lặp");
}

checkUniqueKey("olist_customers_clean", "$customer_id", "Primary Key (customer_id)");
checkUniqueKey("olist_orders_clean", "$order_id", "Primary Key (order_id)");
checkUniqueKey("olist_products_clean", "$product_id", "Primary Key (product_id)");
checkUniqueKey("olist_sellers_clean", "$seller_id", "Primary Key (seller_id)");
checkUniqueKey("geo_by_zip", "$geolocation_zip_code_prefix", "Primary Key (zip_code_prefix)");
checkUniqueKey("olist_order_items_clean", { order_id: "$order_id", item_id: "$order_item_id" }, "Composite Key (order_id, order_item_id)");
checkUniqueKey("olist_order_payments_clean", { order_id: "$order_id", seq: "$payment_sequential" }, "Composite Key (order_id, payment_sequential)");
checkUniqueKey("olist_order_reviews_clean", { review_id: "$review_id", order_id: "$order_id" }, "Composite Key (review_id, order_id)");

// ---------------------------------------------------------------------
// 3. KIỂM TRA BẢN GHI MỒ CÔI (REFERENTIAL INTEGRITY ACROSS ALL FKs)
// ---------------------------------------------------------------------
print("\n-----------------------------------------------------------------------");
print(" 3. KIỂM TRA BẢN GHI MỒ CÔI VÀ TÍNH TOÀN VẸN THAM CHIẾU");
print("-----------------------------------------------------------------------");

function checkOrphans(sourceColl, targetColl, foreignKey, targetKey) {
  var coll = db.getCollection(sourceColl);
  var orphans = coll.aggregate([
    { $match: { [foreignKey]: { $ne: null } } },
    {
      $lookup: {
        from: targetColl,
        localField: foreignKey,
        foreignField: targetKey,
        as: "ref"
      }
    },
    { $match: { ref: { $size: 0 } } }
  ]).toArray().length;

  logCheck("Liên Kết Tham Chiếu", sourceColl + "." + foreignKey + " -> " + targetColl + "." + targetKey, orphans === 0 ? "PASS" : "FAIL", orphans > 0 ? "Bản ghi mồ côi: " + orphans : "100% khớp khóa ngoại");
}

checkOrphans("olist_orders_clean", "olist_customers_clean", "customer_id", "customer_id");
checkOrphans("olist_order_items_clean", "olist_orders_clean", "order_id", "order_id");
checkOrphans("olist_order_items_clean", "olist_products_clean", "product_id", "product_id");
checkOrphans("olist_order_items_clean", "olist_sellers_clean", "seller_id", "seller_id");
checkOrphans("olist_order_payments_clean", "olist_orders_clean", "order_id", "order_id");
checkOrphans("olist_order_reviews_clean", "olist_orders_clean", "order_id", "order_id");

// ---------------------------------------------------------------------
// KẾT LUẬN TỔNG THỂ
// ---------------------------------------------------------------------
print("\n=======================================================================");
print(" KẾT LUẬN KIỂM ĐỊNH TOÀN BỘ CSDL BigData: " + (overallPassed ? "ĐẠT (PASS 100%)" : "KHÔNG ĐẠT (FAIL)"));
print("=======================================================================\n");

db = db.getSiblingDB("BigData");

var inputCustomerUniqueId = "863336d82222cd6501d03103002b000b";

db.olist_customers_clean.aggregate([
  { $match: { customer_unique_id: inputCustomerUniqueId } },
  {
    $lookup: {
      from: "olist_orders_clean",
      localField: "customer_id",
      foreignField: "customer_id",
      as: "orders"
    }
  },
  { $unwind: "$orders" },
  {
    $lookup: {
      from: "olist_order_items_clean",
      let: { order_id: "$orders.order_id" },
      pipeline: [
        { $match: { $expr: { $eq: ["$order_id", "$$order_id"] } } },
        {
          $lookup: {
            from: "olist_products_clean",
            localField: "product_id",
            foreignField: "product_id",
            as: "product_detail"
          }
        },
        { $unwind: { path: "$product_detail", preserveNullAndEmptyArrays: true } }
      ],
      as: "orders.items"
    }
  },
  {
    $lookup: {
      from: "olist_order_payments_clean",
      localField: "orders.order_id",
      foreignField: "order_id",
      as: "orders.payments"
    }
  },
  {
    $lookup: {
      from: "olist_order_reviews_clean",
      localField: "orders.order_id",
      foreignField: "order_id",
      as: "orders.reviews"
    }
  },
  {
    $addFields: {
      "orders.order_total_payment": { $round: [{ $sum: "$orders.payments.payment_value" }, 2] },
      "orders.total_items_count": { $size: "$orders.items" }
    }
  },
  {
    $group: {
      _id: "$customer_unique_id",
      customer_city: { $first: "$customer_city" },
      customer_state: { $first: "$customer_state" },
      total_orders_placed: { $sum: 1 },
      total_lifetime_spent: { $sum: "$orders.order_total_payment" },
      orders_history: { $push: "$orders" }
    }
  },
  {
    $project: {
      _id: 0,
      customer_unique_id: "$_id",
      customer_city: 1,
      customer_state: 1,
      total_orders_placed: 1,
      total_lifetime_spent: { $round: ["$total_lifetime_spent", 2] },
      orders_history: 1
    }
  }
]);

db = db.getSiblingDB("BigData");

var filterStatus = "delivered";
var startDate = ISODate("2018-01-01T00:00:00Z");
var endDate = ISODate("2018-09-01T00:00:00Z");
var filterState = "SP";

db.olist_orders_clean.aggregate([
  {
    $match: {
      order_status: filterStatus,
      order_purchase_timestamp: { $gte: startDate, $lt: endDate }
    }
  },
  {
    $lookup: {
      from: "olist_customers_clean",
      localField: "customer_id",
      foreignField: "customer_id",
      as: "customer"
    }
  },
  { $unwind: "$customer" },
  { $match: { "customer.customer_state": filterState } },
  {
    $lookup: {
      from: "olist_order_payments_clean",
      localField: "order_id",
      foreignField: "order_id",
      as: "payments"
    }
  },
  {
    $lookup: {
      from: "olist_order_items_clean",
      localField: "order_id",
      foreignField: "order_id",
      as: "items"
    }
  },
  {
    $project: {
      order_id: 1,
      valid_delay_kpi: 1,
      order_delivered_customer_date: 1,
      order_estimated_delivery_date: 1,
      order_payment_amount: { $sum: "$payments.payment_value" },
      order_goods_amount: { $sum: "$items.price" },
      order_freight_amount: { $sum: "$items.freight_value" },
      order_item_qty: { $size: "$items" },
      is_delayed_order: {
        $cond: [
          {
            $and: [
              { $eq: ["$valid_delay_kpi", true] },
              { $gt: ["$order_delivered_customer_date", "$order_estimated_delivery_date"] }
            ]
          },
          1,
          0
        ]
      }
    }
  },
  {
    $group: {
      _id: null,
      total_orders: { $sum: 1 },
      total_gross_revenue: { $sum: "$order_payment_amount" },
      total_goods_value: { $sum: "$order_goods_amount" },
      total_freight_value: { $sum: "$order_freight_amount" },
      total_products_sold: { $sum: "$order_item_qty" },
      valid_kpi_orders_count: { $sum: { $cond: ["$valid_delay_kpi", 1, 0] } },
      delayed_orders_count: { $sum: "$is_delayed_order" }
    }
  },
  {
    $project: {
      _id: 0,
      total_orders: 1,
      total_gross_revenue: { $round: ["$total_gross_revenue", 2] },
      total_goods_value: { $round: ["$total_goods_value", 2] },
      total_freight_value: { $round: ["$total_freight_value", 2] },
      total_products_sold: 1,
      valid_kpi_orders_count: 1,
      delayed_orders_count: 1,
      delay_rate_pct: {
        $round: [
          { $multiply: [{ $divide: ["$delayed_orders_count", "$valid_kpi_orders_count"] }, 100] },
          2
        ]
      }
    }
  }
]);