// =====================================================================
// CẤU HÌNH DÙNG CHUNG - TRÁNH GHI CỨNG TÊN DATABASE
// =====================================================================
const CONFIG = {
  dbName: "BigData",
  expectedCounts: {
    olist_orders_clean: 99441,
    olist_order_items_clean: 112650,
    geo_by_zip: 19015,
    olist_customers_clean: 99441
  },
  requiredCollections: [
    "olist_orders_clean", "olist_customers_clean", "olist_order_items_clean",
    "olist_order_payments_clean", "olist_order_reviews_clean", "olist_products_clean",
    "olist_sellers_clean", "geo_by_zip"
  ]
};

db = db.getSiblingDB(CONFIG.dbName);
print("\n>>> ĐÃ KẾT NỐI CSDL: " + db.getName() + " <<<");

// ---------------------------------------------------------------------
// BƯỚC 1: PRE-CHECK TỒN TẠI VÀ SỐ LƯỢNG (DỪNG CHƯƠNG TRÌNH NẾU FAIL)
// ---------------------------------------------------------------------
(function validateDatabaseBeforeExecution() {
  print("\n--- BƯỚC 1: KIỂM TRA ĐIỀU KIỆN TIÊN QUYẾT (PRE-EXECUTION CHECK) ---");
  var existingCollections = db.getCollectionNames();
  var isCriticalError = false;

  CONFIG.requiredCollections.forEach(function(collName) {
    if (!existingCollections.includes(collName)) {
      print(" [FAIL] LỖI CRITICAL: Thiếu Collection '" + collName + "' trong DB " + db.getName());
      isCriticalError = true;
    } else {
      var currentCount = db.getCollection(collName).countDocuments();
      if (currentCount === 0) {
        print(" [FAIL] LỖI CRITICAL: Collection '" + collName + "' bị TRỐNG (0 document)!");
        isCriticalError = true;
      } else if (CONFIG.expectedCounts[collName] && currentCount !== CONFIG.expectedCounts[collName]) {
        print(" [FAIL] LỖI SỐ LIỆU: Collection '" + collName + "' có " + currentCount + " docs (Kỳ vọng: " + CONFIG.expectedCounts[collName] + ")");
        isCriticalError = true;
      } else {
        print(" [PASS] Collection '" + collName + "' hợp lệ (" + currentCount.toLocaleString() + " docs).");
      }
    }
  });

  if (isCriticalError) {
    print("\n=======================================================================");
    print(" KẾT QUẢ PRE-CHECK: [FAIL] - DỪNG TOÀN BỘ QUÁ TRÌNH XỬ LÝ!");
    print("=======================================================================\n");
    throw new Error("PRE-CHECK FAIL: CSDL không đủ điều kiện để thực thi.");
  }
  print(" [SUCCESS] Mọi collection hợp lệ! Chuyển sang bước chuyển đổi BSON.");
})();

// ---------------------------------------------------------------------
// BƯỚC 2: PHÂN BIỆT NULL CÓ SẴN VÀ THỐNG KÊ LỖI CHUYỂN ĐỔI BSON
// ---------------------------------------------------------------------
function auditPreConversionFailures(collectionName, fieldName, targetType) {
  var coll = db.getCollection(collectionName);
  var originalNulls = coll.countDocuments({ $or: [{ [fieldName]: null }, { [fieldName]: "" }, { [fieldName]: "null" }] });
  
  var invalidFormatCount = 0;
  if (targetType === "number") {
    invalidFormatCount = coll.countDocuments({
      $and: [
        { [fieldName]: { $exists: true, $ne: null } },
        { [fieldName]: { $not: { $type: "number" } } },
        { [fieldName]: { $not: { $regex: "^-?[0-9]+(\\.[0-9]+)?$" } } },
        { [fieldName]: { $nin: ["", "null", "nan", "None"] } }
      ]
    });
  }
  print("   * " + collectionName + "." + fieldName + " -> Null ban đầu: " + originalNulls + " | Chuỗi số lỗi: " + invalidFormatCount);
}

print("\n--- BƯỚC 2: KIỂM TRA CHUỖI SỐ LỖI TRƯỚC KHUYỂN ĐỔI ---");
auditPreConversionFailures("olist_products_clean", "product_name_lenght", "number");
auditPreConversionFailures("olist_products_clean", "product_weight_g", "number");

// ---------------------------------------------------------------------
// HÀM BỔ TRỢ: ĐỆM MÃ ZIP CHUẨN 5 CHỮ SỐ (TƯƠNG THÍCH MONGODB 4.2+)
// ---------------------------------------------------------------------
function padZipExpr(fieldPath) {
  return {
    $let: {
      vars: {
        strPadded: {
          $concat: [
            "00000",
            { $toString: { $ifNull: [fieldPath, "0"] } }
          ]
        }
      },
      in: {
        $substrCP: [
          "$$strPadded",
          { $subtract: [{ $strLenCP: "$$strPadded" }, 5] },
          5
        ]
      }
    }
  };
}

// ---------------------------------------------------------------------
// BƯỚC 3: CẬP NHẬT KIỂU DỮ LIỆU TẠI CHỖ (IN-PLACE updateMany PIPELINE)
// Quy ước thời gian: ISO-8601 UTC (YYYY-MM-DDTHH:mm:ssZ)
// ---------------------------------------------------------------------
print("\n--- BƯỚC 3: THỰC THI updateMany CHUYỂN ĐỔI BSON VÀ ĐỆM MÃ ZIP ---");

// 3.1 olist_orders_clean
db.olist_orders_clean.updateMany({}, [
  {
    $set: {
      order_purchase_timestamp: { $convert: { input: "$order_purchase_timestamp", to: "date", onError: null, onNull: null } },
      order_approved_at: { $convert: { input: "$order_approved_at", to: "date", onError: null, onNull: null } },
      order_delivered_carrier_date: { $convert: { input: "$order_delivered_carrier_date", to: "date", onError: null, onNull: null } },
      order_delivered_customer_date: { $convert: { input: "$order_delivered_customer_date", to: "date", onError: null, onNull: null } },
      order_estimated_delivery_date: { $convert: { input: "$order_estimated_delivery_date", to: "date", onError: null, onNull: null } },
      delivered_missing_date: { $eq: [{ $toLower: { $toString: "$delivered_missing_date" } }, "true"] },
      valid_delay_kpi: { $eq: [{ $toLower: { $toString: "$valid_delay_kpi" } }, "true"] }
    }
  }
]);

// 3.2 olist_products_clean (Chuyển chuỗi "40.0" -> double -> int)
db.olist_products_clean.updateMany({}, [
  {
    $set: {
      product_name_lenght: { $toInt: { $convert: { input: "$product_name_lenght", to: "double", onError: null, onNull: null } } },
      product_description_lenght: { $toInt: { $convert: { input: "$product_description_lenght", to: "double", onError: null, onNull: null } } },
      product_photos_qty: { $toInt: { $convert: { input: "$product_photos_qty", to: "double", onError: null, onNull: null } } },
      product_weight_g: { $convert: { input: "$product_weight_g", to: "double", onError: null, onNull: null } },
      category_missing: { $eq: [{ $toLower: { $toString: "$category_missing" } }, "true"] }
    }
  }
]);

// 3.3 olist_order_items_clean
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

// 3.4 olist_order_payments_clean
db.olist_order_payments_clean.updateMany({}, [
  {
    $set: {
      payment_sequential: { $toInt: { $convert: { input: "$payment_sequential", to: "double", onError: null, onNull: null } } },
      payment_installments: { $toInt: { $convert: { input: "$payment_installments", to: "double", onError: null, onNull: null } } },
      payment_value: { $convert: { input: "$payment_value", to: "double", onError: null, onNull: null } }
    }
  }
]);

// 3.5 Ép kiểu và Đệm chuỗi Mã ZIP chuẩn 5 chữ số
db.olist_customers_clean.updateMany({}, [
  { $set: { customer_zip_code_prefix: padZipExpr("$customer_zip_code_prefix") } }
]);

db.olist_sellers_clean.updateMany({}, [
  { $set: { seller_zip_code_prefix: padZipExpr("$seller_zip_code_prefix") } }
]);

db.geo_by_zip.updateMany({}, [
  {
    $set: {
      geolocation_zip_code_prefix: padZipExpr("$geolocation_zip_code_prefix"),
      geolocation_lat: { $convert: { input: "$geolocation_lat", to: "double", onError: null, onNull: null } },
      geolocation_lng: { $convert: { input: "$geolocation_lng", to: "double", onError: null, onNull: null } },
      point_count: { $toInt: { $convert: { input: "$point_count", to: "double", onError: null, onNull: null } } },
      usable_for_geo: { $eq: [{ $toLower: { $toString: "$usable_for_geo" } }, "true"] }
    }
  }
]);

// ---------------------------------------------------------------------
// BƯỚC 4: TẠO HỆ THỐNG INDEX TRÊN DATABASE BigData
// ---------------------------------------------------------------------
print("\n--- BƯỚC 4: TẠO INDEXES TRÊN BigData ---");
db.olist_customers_clean.createIndex({ customer_id: 1 }, { unique: true });
db.olist_orders_clean.createIndex({ order_id: 1 }, { unique: true });
db.olist_products_clean.createIndex({ product_id: 1 }, { unique: true });
db.olist_sellers_clean.createIndex({ seller_id: 1 }, { unique: true });
db.geo_by_zip.createIndex({ geolocation_zip_code_prefix: 1 }, { unique: true });

db.olist_order_items_clean.createIndex({ order_id: 1, order_item_id: 1 }, { unique: true });
db.olist_order_payments_clean.createIndex({ order_id: 1, payment_sequential: 1 }, { unique: true });

db.olist_orders_clean.createIndex({ customer_id: 1 });
db.olist_orders_clean.createIndex({ valid_delay_kpi: 1 });
db.olist_customers_clean.createIndex({ customer_unique_id: 1 });

print("\n=== HOÀN TẤT ĐỊNH KIỂU VÀ TẠO INDEX TRÊN DATABASE " + db.getName() + " ===");

db = db.getSiblingDB("BigData");

print("\n=======================================================================");
print("   BÁO CÁO AUDIT DỮ LIỆU VÀ ĐỐI SOÁT BẰNG CHỨNG (DATABASE: BigData)");
print("=======================================================================");

var auditStatus = true;

function logResult(category, checkName, passCondition, detailMsg) {
  var tag = passCondition ? "[PASS]" : "[FAIL]";
  print(" " + tag + " " + category.padEnd(20) + " | " + checkName);
  if (detailMsg) print("      └─ Details: " + detailMsg);
  if (!passCondition) auditStatus = false;
}

// 1. Kiểm tra Mốc Số Lượng Bắt Buộc
var orderCount = db.olist_orders_clean.countDocuments();
logResult("Document Count", "olist_orders_clean == 99,441", orderCount === 99441, "Actual: " + orderCount);

var itemCount = db.olist_order_items_clean.countDocuments();
logResult("Document Count", "olist_order_items_clean == 112,650", itemCount === 112650, "Actual: " + itemCount);

var zipCount = db.geo_by_zip.countDocuments();
logResult("Document Count", "geo_by_zip == 19,015", zipCount === 19015, "Actual: " + zipCount);

var validKpiCount = db.olist_orders_clean.countDocuments({ valid_delay_kpi: true });
logResult("Quality Flag", "valid_delay_kpi == 95,097", validKpiCount === 95097, "Actual: " + validKpiCount);

var missingDeliveredCount = db.olist_orders_clean.countDocuments({ delivered_missing_date: true });
logResult("Quality Flag", "delivered_missing_date == 8", missingDeliveredCount === 8, "Actual: " + missingDeliveredCount);

// 2. Kiểm tra Phân Phối Kiểu BSON ($type)
var dateTypeDist = db.olist_orders_clean.aggregate([{ $group: { _id: { $type: "$order_purchase_timestamp" }, count: { $sum: 1 } } }]).toArray();
logResult("BSON Type Check", "order_purchase_timestamp ISODate", dateTypeDist.every(t => t._id === "date"), JSON.stringify(dateTypeDist));

var priceTypeDist = db.olist_order_items_clean.aggregate([{ $group: { _id: { $type: "$price" }, count: { $sum: 1 } } }]).toArray();
logResult("BSON Type Check", "price Double", priceTypeDist.every(t => t._id === "double"), JSON.stringify(priceTypeDist));

// 3. Kiểm tra Chuỗi Mã ZIP 5 Chữ Số (Regex: ^[0-9]{5}$)
var invalidCustZip = db.olist_customers_clean.countDocuments({
  $or: [
    { customer_zip_code_prefix: { $not: { $type: "string" } } },
    { customer_zip_code_prefix: { $not: { $regex: "^[0-9]{5}$" } } }
  ]
});
logResult("ZIP Code Format", "customer_zip_code_prefix String 5-digits", invalidCustZip === 0, "Violations: " + invalidCustZip);

// 4. Kiểm tra Bản ghi Mồ côi (Referential Integrity)
var orphanItems = db.olist_order_items_clean.aggregate([
  { $lookup: { from: "olist_orders_clean", localField: "order_id", foreignField: "order_id", as: "matched" } },
  { $match: { matched: { $size: 0 } } }
]).toArray().length;
logResult("Referential Check", "Order Items mồ côi order_id == 0", orphanItems === 0, "Orphans: " + orphanItems);

print("\n=======================================================================");
print(" KẾT LUẬN AUDIT TOÀN BỘ CSDL BigData: " + (auditStatus ? "ĐẠT (PASS 100%)" : "KHÔNG ĐẠT (FAIL)"));
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
  { $unwind: { path: "$orders", preserveNullAndEmptyArrays: true } },
  {
    $lookup: {
      from: "olist_order_items_clean",
      localField: "orders.order_id",
      foreignField: "order_id",
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
    $addFields: {
      "orders.order_total_payment": { $round: [{ $sum: "$orders.payments.payment_value" }, 2] }
    }
  },
  {
    $group: {
      _id: "$customer_unique_id",
      customer_city: { $first: "$customer_city" },
      customer_state: { $first: "$customer_state" },
      total_orders_placed: { $sum: { $cond: [{ $ifNull: ["$orders.order_id", false] }, 1, 0] } },
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

// Tham số Bộ Lọc Web (Test trường hợp không có kết quả: dùng Bang 'XX')
var filterStatus = "delivered";
var startDate = ISODate("2018-01-01T00:00:00Z");
var endDate = ISODate("2018-07-01T00:00:00Z");
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
      valid_kpi_orders_count: 1,
      delayed_orders_count: 1,
      // Bảo vệ lỗi chia cho 0 (Zero-Denominator Safe)
      delay_rate_pct: {
        $cond: [
          { $gt: ["$valid_kpi_orders_count", 0] },
          { $round: [{ $multiply: [{ $divide: ["$delayed_orders_count", "$valid_kpi_orders_count"] }, 100] }, 2] },
          0.0
        ]
      }
    }
  }
]);