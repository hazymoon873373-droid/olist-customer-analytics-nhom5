import os
import argparse
import numpy as np
import pandas as pd

class StrictOlistCleaner:
    def __init__(self, raw_dir='.', output_dir='./processed'):
        self.raw_dir = raw_dir
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.audit_rows = []

    @staticmethod
    def _format_zip_code(series):
        """Đưa mã bưu chính về chuỗi đúng 5 ký tự số (thêm '0' vào trước mã 4 ký tự)."""
        def fix_val(x):
            if pd.isna(x) or str(x).strip() in ['', 'nan', 'null', 'None']:
                return np.nan
            val_str = str(x).strip()
            if val_str.isdigit() and len(val_str) <= 5:
                return val_str.zfill(5)
            return val_str
        return series.apply(fix_val)

    @staticmethod
    def _count_pk_nulls(series):
        """Đếm chính xác số lượng giá trị thiếu trong cột khóa (nhận diện cả NaN và chuỗi khuyết)."""
        return int((series.isna() | series.astype(str).str.strip().isin(['', 'null', 'nan', 'None'])).sum())

    def _add_audit(self, category, metric, value, expected, is_mandatory=True):
        """Thêm 1 dòng kiểm định và tính toán tự động trạng thái PASS/FAIL hoặc INFO."""
        if is_mandatory:
            status = 'PASS' if value == expected else 'FAIL'
        else:
            status = 'INFO' if value == expected else 'WARNING'
            
        self.audit_rows.append({
            'category': category,
            'metric': metric,
            'value': value,
            'expected': expected,
            'status': status,
            'is_mandatory': is_mandatory
        })

    def clean_customers(self):
        raw_path = os.path.join(self.raw_dir, 'olist_customers_dataset.csv')
        df = pd.read_csv(raw_path, dtype=str)
        raw_count = len(df)

        df['customer_zip_code_prefix'] = self._format_zip_code(df['customer_zip_code_prefix'])
        df_clean = df.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_customers_clean.csv'), index=False)

        # Audit
        self._add_audit('File Row Counts', 'customers_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'customers_pk_nulls', self._count_pk_nulls(df['customer_id']), 0)
        self._add_audit('Primary Key Checks', 'customers_pk_duplicates', int(df['customer_id'].duplicated().sum()), 0)
        return df_clean

    def clean_geolocation(self):
        raw_path = os.path.join(self.raw_dir, 'olist_geolocation_dataset.csv')
        df_raw = pd.read_csv(raw_path, dtype={'geolocation_zip_code_prefix': str})
        raw_count = len(df_raw)

        exact_duplicates_count = int(df_raw.duplicated().sum())
        df_unique_rows = df_raw.drop_duplicates().copy()

        df_raw['geolocation_zip_code_prefix'] = self._format_zip_code(df_raw['geolocation_zip_code_prefix'])
        df_unique_rows['geolocation_zip_code_prefix'] = self._format_zip_code(df_unique_rows['geolocation_zip_code_prefix'])
        df_unique_rows['geolocation_lat'] = pd.to_numeric(df_unique_rows['geolocation_lat'], errors='coerce')
        df_unique_rows['geolocation_lng'] = pd.to_numeric(df_unique_rows['geolocation_lng'], errors='coerce')

        # Xuất bảng gốc (bảo toàn trọn vẹn 1.000.163 dòng)
        df_clean = df_raw.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_geolocation_clean.csv'), index=False)

        # Tạo bảng geo_by_zip (1 dòng per ZIP)
        geo_group = df_unique_rows.groupby('geolocation_zip_code_prefix')
        geo_by_zip = geo_group.agg(
            geolocation_lat=('geolocation_lat', 'median'),
            geolocation_lng=('geolocation_lng', 'median'),
            geolocation_city=('geolocation_city', lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]),
            geolocation_state=('geolocation_state', lambda x: x.mode().iloc[0] if not x.mode().empty else x.iloc[0]),
            state_count=('geolocation_state', 'nunique'),
            point_count=('geolocation_lat', 'count')
        ).reset_index()

        # Đánh dấu cờ kiểm tra
        geo_by_zip['state_conflict'] = geo_by_zip['state_count'] > 1
        lat = geo_by_zip['geolocation_lat']
        lng = geo_by_zip['geolocation_lng']
        geo_by_zip['is_outlier_coord'] = (lat < -35.0) | (lat > 6.0) | (lng < -74.0) | (lng > -30.0)
        geo_by_zip['usable_for_geo'] = (~geo_by_zip['state_conflict']) & (~geo_by_zip['is_outlier_coord'])

        # Kiểm tra bắt buộc: số tọa độ ngoài giới hạn nhưng vẫn usable_for_geo = True phải bằng 0
        outlier_and_usable_conflict = int((geo_by_zip['is_outlier_coord'] & geo_by_zip['usable_for_geo']).sum())

        geo_by_zip_clean = geo_by_zip.drop(columns=['state_count']).replace(r'^\s*$', np.nan, regex=True).fillna("null")
        geo_by_zip_clean.to_csv(os.path.join(self.output_dir, 'geo_by_zip.csv'), index=False)

        # Audit
        expected_unique_zips = df_raw['geolocation_zip_code_prefix'].nunique()
        self._add_audit('File Row Counts', 'geolocation_row_count', len(df_clean), raw_count)
        self._add_audit('File Row Counts', 'geo_by_zip_row_count', len(geo_by_zip_clean), expected_unique_zips)
        self._add_audit('Primary Key Checks', 'geo_by_zip_pk_nulls', self._count_pk_nulls(geo_by_zip['geolocation_zip_code_prefix']), 0)
        self._add_audit('Primary Key Checks', 'geo_by_zip_pk_duplicates', int(geo_by_zip['geolocation_zip_code_prefix'].duplicated().sum()), 0)
        
        self._add_audit('Business Rule Exceptions', 'geolocation_exact_duplicates', exact_duplicates_count, 261831)
        self._add_audit('Business Rule Exceptions', 'geo_zip_state_conflict', int(geo_by_zip['state_conflict'].sum()), 8)
        
        # Cảnh báo địa lý (không làm rớt kiểm định bắt buộc)
        outlier_coord_cnt = int(geo_by_zip['is_outlier_coord'].sum())
        self._add_audit('Geographic Warnings', 'geo_zip_outlier_coord_warning', outlier_coord_cnt, 8, is_mandatory=False)
        
        # Kiểm tra bắt buộc
        self._add_audit('Mandatory Geo Integrity', 'geo_zip_outlier_usable_conflict', outlier_and_usable_conflict, 0, is_mandatory=True)

        return df_clean, geo_by_zip_clean

    def clean_orders(self):
        raw_path = os.path.join(self.raw_dir, 'olist_orders_dataset.csv')
        df = pd.read_csv(raw_path, dtype={'order_id': str, 'customer_id': str})
        raw_count = len(df)

        date_cols = [
            'order_purchase_timestamp', 'order_approved_at', 
            'order_delivered_carrier_date', 'order_delivered_customer_date', 
            'order_estimated_delivery_date'
        ]
        for col in date_cols:
            df[col] = pd.to_datetime(df[col], errors='coerce')

        df['delivered_missing_date'] = (df['order_status'] == 'delivered') & df['order_delivered_customer_date'].isna()
        df['carrier_before_approval'] = (
            df['order_delivered_carrier_date'].notna() & 
            df['order_approved_at'].notna() & 
            (df['order_delivered_carrier_date'] < df['order_approved_at'])
        )
        df['customer_before_carrier'] = (
            df['order_delivered_customer_date'].notna() & 
            df['order_delivered_carrier_date'].notna() & 
            (df['order_delivered_customer_date'] < df['order_delivered_carrier_date'])
        )
        df['valid_delay_kpi'] = (
            (df['order_status'] == 'delivered') & 
            df['order_delivered_customer_date'].notna() & 
            df['order_estimated_delivery_date'].notna() & 
            (~df['carrier_before_approval']) & 
            (~df['customer_before_carrier'])
        )

        df_out = df.copy()
        for col in date_cols:
            df_out[col] = df_out[col].dt.strftime('%Y-%m-%d %H:%M:%S')

        df_clean = df_out.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_orders_clean.csv'), index=False)

        # Audit
        self._add_audit('File Row Counts', 'orders_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'orders_pk_nulls', self._count_pk_nulls(df['order_id']), 0)
        self._add_audit('Primary Key Checks', 'orders_pk_duplicates', int(df['order_id'].duplicated().sum()), 0)
        self._add_audit('Business Rule Exceptions', 'orders_delivered_missing_date', int(df['delivered_missing_date'].sum()), 8)
        self._add_audit('Business Rule Exceptions', 'orders_carrier_before_approval', int(df['carrier_before_approval'].sum()), 1359)
        self._add_audit('Business Rule Exceptions', 'orders_customer_before_carrier', int(df['customer_before_carrier'].sum()), 23)
        self._add_audit('Business Rule Exceptions', 'orders_valid_delay_kpi', int(df['valid_delay_kpi'].sum()), 95097)

        return df

    def clean_order_reviews(self, df_orders):
        raw_path = os.path.join(self.raw_dir, 'olist_order_reviews_dataset.csv')
        df = pd.read_csv(raw_path, dtype={'review_id': str, 'order_id': str})
        raw_count = len(df)

        df['review_creation_date'] = pd.to_datetime(df['review_creation_date'], errors='coerce')
        df['review_answer_timestamp'] = pd.to_datetime(df['review_answer_timestamp'], errors='coerce')

        orders_sub = df_orders[['order_id', 'order_purchase_timestamp']].copy()
        df = df.merge(orders_sub, on='order_id', how='left')

        rev_date = df['review_creation_date'].dt.date
        pur_date = df['order_purchase_timestamp'].dt.date

        before_purchase_day_mask = (rev_date < pur_date)
        same_day_uncertain_mask = (rev_date == pur_date) & (df['review_creation_date'] < df['order_purchase_timestamp'])

        df['review_time_status'] = 'normal'
        df.loc[before_purchase_day_mask, 'review_time_status'] = 'before_purchase_day'
        df.loc[same_day_uncertain_mask, 'review_time_status'] = 'same_day_uncertain'

        df['review_before_purchase'] = (df['review_time_status'] == 'before_purchase_day')
        composite_dups = int(df.duplicated(subset=['review_id', 'order_id']).sum())
        df['is_duplicate_review_order'] = df.duplicated(subset=['review_id', 'order_id'], keep=False)

        df_out = df.drop(columns=['order_purchase_timestamp'], errors='ignore').copy()
        df_out['review_creation_date'] = df_out['review_creation_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_out['review_answer_timestamp'] = df_out['review_answer_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        df_clean = df_out.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_order_reviews_clean.csv'), index=False)

        # Audit
        review_pk_nulls = int((df['review_id'].isna() | df['order_id'].isna()).sum())
        self._add_audit('File Row Counts', 'order_reviews_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'order_reviews_pk_nulls', review_pk_nulls, 0)
        self._add_audit('Primary Key Checks', 'order_reviews_pk_duplicates', composite_dups, 0)
        self._add_audit('Business Rule Exceptions', 'reviews_before_purchase', int((df['review_time_status'] == 'before_purchase_day').sum()), 64)
        self._add_audit('Business Rule Exceptions', 'reviews_same_day_uncertain', int((df['review_time_status'] == 'same_day_uncertain').sum()), 10)
        self._add_audit('Business Rule Exceptions', 'reviews_composite_key_duplicates', composite_dups, 0)

        return df_clean

    def clean_products(self):
        raw_path = os.path.join(self.raw_dir, 'olist_products_dataset.csv')
        df = pd.read_csv(raw_path, dtype={'product_id': str})
        raw_count = len(df)

        df['category_missing'] = df['product_category_name'].isna() | (df['product_category_name'].str.strip() == '') | (df['product_category_name'] == 'null')

        prod_num_cols = [
            'product_name_lenght', 'product_description_lenght', 'product_photos_qty',
            'product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm'
        ]
        for col in prod_num_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['weight_zero'] = df['product_weight_g'].notna() & (df['product_weight_g'] == 0)

        df_clean = df.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_products_clean.csv'), index=False)

        # Audit
        self._add_audit('File Row Counts', 'products_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'products_pk_nulls', self._count_pk_nulls(df['product_id']), 0)
        self._add_audit('Primary Key Checks', 'products_pk_duplicates', int(df['product_id'].duplicated().sum()), 0)
        self._add_audit('Business Rule Exceptions', 'products_category_missing', int(df['category_missing'].sum()), 610)
        self._add_audit('Business Rule Exceptions', 'products_weight_zero', int(df['weight_zero'].sum()), 4)

        return df_clean

    def clean_order_items(self):
        raw_path = os.path.join(self.raw_dir, 'olist_order_items_dataset.csv')
        df = pd.read_csv(raw_path, dtype={'order_id': str, 'product_id': str, 'seller_id': str})
        raw_count = len(df)

        df['shipping_limit_date'] = pd.to_datetime(df['shipping_limit_date'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['freight_value'] = pd.to_numeric(df['freight_value'], errors='coerce')

        df_clean = df.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_order_items_clean.csv'), index=False)

        # Audit
        items_pk_nulls = int((df['order_id'].isna() | df['order_item_id'].isna()).sum())
        items_pk_dups = int(df.duplicated(subset=['order_id', 'order_item_id']).sum())
        self._add_audit('File Row Counts', 'order_items_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'order_items_pk_nulls', items_pk_nulls, 0)
        self._add_audit('Primary Key Checks', 'order_items_pk_duplicates', items_pk_dups, 0)

        return df_clean

    def clean_order_payments(self):
        raw_path = os.path.join(self.raw_dir, 'olist_order_payments_dataset.csv')
        df = pd.read_csv(raw_path, dtype={'order_id': str})
        raw_count = len(df)

        df['payment_value'] = pd.to_numeric(df['payment_value'], errors='coerce')
        df['payment_installments'] = pd.to_numeric(df['payment_installments'], errors='coerce')

        df_clean = df.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_order_payments_clean.csv'), index=False)

        # Audit
        pay_pk_nulls = int((df['order_id'].isna() | df['payment_sequential'].isna()).sum())
        pay_pk_dups = int(df.duplicated(subset=['order_id', 'payment_sequential']).sum())
        self._add_audit('File Row Counts', 'order_payments_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'order_payments_pk_nulls', pay_pk_nulls, 0)
        self._add_audit('Primary Key Checks', 'order_payments_pk_duplicates', pay_pk_dups, 0)

        return df_clean

    def clean_sellers(self):
        raw_path = os.path.join(self.raw_dir, 'olist_sellers_dataset.csv')
        df = pd.read_csv(raw_path, dtype=str)
        raw_count = len(df)

        df['seller_zip_code_prefix'] = self._format_zip_code(df['seller_zip_code_prefix'])
        df_clean = df.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'olist_sellers_clean.csv'), index=False)

        # Audit
        self._add_audit('File Row Counts', 'sellers_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'sellers_pk_nulls', self._count_pk_nulls(df['seller_id']), 0)
        self._add_audit('Primary Key Checks', 'sellers_pk_duplicates', int(df['seller_id'].duplicated().sum()), 0)

        return df_clean

    def clean_category_translation(self):
        raw_path = os.path.join(self.raw_dir, 'product_category_name_translation.csv')
        df = pd.read_csv(raw_path)
        raw_count = len(df)

        df_clean = df.replace(r'^\s*$', np.nan, regex=True).fillna("null")
        df_clean.to_csv(os.path.join(self.output_dir, 'product_category_name_translation_clean.csv'), index=False)

        # Audit
        self._add_audit('File Row Counts', 'product_category_name_translation_row_count', len(df_clean), raw_count)
        self._add_audit('Primary Key Checks', 'product_category_translation_pk_nulls', self._count_pk_nulls(df['product_category_name']), 0)
        self._add_audit('Primary Key Checks', 'product_category_translation_pk_duplicates', int(df['product_category_name'].duplicated().sum()), 0)

        return df_clean

    def run_referential_integrity_checks(self):
        """Kiểm tra bản ghi mồ côi (Orphan Records)."""
        orders = pd.read_csv(os.path.join(self.output_dir, 'olist_orders_clean.csv'), dtype=str)
        customers = pd.read_csv(os.path.join(self.output_dir, 'olist_customers_clean.csv'), dtype=str)
        items = pd.read_csv(os.path.join(self.output_dir, 'olist_order_items_clean.csv'), dtype=str)
        products = pd.read_csv(os.path.join(self.output_dir, 'olist_products_clean.csv'), dtype=str)
        sellers = pd.read_csv(os.path.join(self.output_dir, 'olist_sellers_clean.csv'), dtype=str)
        payments = pd.read_csv(os.path.join(self.output_dir, 'olist_order_payments_clean.csv'), dtype=str)
        reviews = pd.read_csv(os.path.join(self.output_dir, 'olist_order_reviews_clean.csv'), dtype=str)

        cust_ids = set(customers['customer_id'])
        order_ids = set(orders['order_id'])
        prod_ids = set(products['product_id'])
        seller_ids = set(sellers['seller_id'])

        self._add_audit('Referential Integrity', 'orphan_orders_customer_id', int((~orders['customer_id'].isin(cust_ids)).sum()), 0)
        self._add_audit('Referential Integrity', 'orphan_items_order_id', int((~items['order_id'].isin(order_ids)).sum()), 0)
        self._add_audit('Referential Integrity', 'orphan_items_product_id', int((~items['product_id'].isin(prod_ids)).sum()), 0)
        self._add_audit('Referential Integrity', 'orphan_items_seller_id', int((~items['seller_id'].isin(seller_ids)).sum()), 0)
        self._add_audit('Referential Integrity', 'orphan_payments_order_id', int((~payments['order_id'].isin(order_ids)).sum()), 0)
        self._add_audit('Referential Integrity', 'orphan_reviews_order_id', int((~reviews['order_id'].isin(order_ids)).sum()), 0)

    def run_flag_consistency_checks(self):
        """Kiểm tra tính nhất quán giữa các cờ."""
        reviews = pd.read_csv(os.path.join(self.output_dir, 'olist_order_reviews_clean.csv'), dtype=str)
        orders = pd.read_csv(os.path.join(self.output_dir, 'olist_orders_clean.csv'), dtype=str)
        products = pd.read_csv(os.path.join(self.output_dir, 'olist_products_clean.csv'), dtype=str)

        rev_flag_match = (reviews['review_before_purchase'].astype(str) == (reviews['review_time_status'] == 'before_purchase_day').astype(str)).all()

        kpi_mask = orders['valid_delay_kpi'].astype(str) == 'True'
        kpi_no_carrier_err = (orders.loc[kpi_mask, 'carrier_before_approval'].astype(str) == 'False').all()
        kpi_no_cust_err = (orders.loc[kpi_mask, 'customer_before_carrier'].astype(str) == 'False').all()
        kpi_delivered = (orders.loc[kpi_mask, 'order_status'] == 'delivered').all()
        orders_flag_match = kpi_no_carrier_err and kpi_no_cust_err and kpi_delivered

        prod_category_is_null = products['product_category_name'].isna() | (products['product_category_name'] == 'null')
        prod_flag_match = (products['category_missing'].astype(str) == prod_category_is_null.astype(str)).all()

        self._add_audit('Flag Consistency', 'review_before_purchase_consistent', bool(rev_flag_match), True)
        self._add_audit('Flag Consistency', 'valid_delay_kpi_consistent', bool(orders_flag_match), True)
        self._add_audit('Flag Consistency', 'product_category_missing_consistent', bool(prod_flag_match), True)

    def run_automated_audit(self):
        """Thực thi kiểm định tự động và xuất báo cáo audit_report.csv."""
        self.run_referential_integrity_checks()
        self.run_flag_consistency_checks()

        # Xét kết luận chung dựa trên TẤT CẢ các kiểm tra bắt buộc (is_mandatory == True)
        mandatory_rows = [row for row in self.audit_rows if row.get('is_mandatory', True)]
        all_mandatory_passed = all(row['status'] == 'PASS' for row in mandatory_rows)

        self.audit_rows.append({
            'category': 'Overall Audit Summary',
            'metric': 'overall_audit_passed',
            'value': all_mandatory_passed,
            'expected': True,
            'status': 'PASS' if all_mandatory_passed else 'FAIL',
            'is_mandatory': True
        })

        csv_path = os.path.join(self.output_dir, 'audit_report.csv')
        df_audit = pd.DataFrame(self.audit_rows)
        df_out = df_audit.drop(columns=['is_mandatory'], errors='ignore')
        df_out.to_csv(csv_path, index=False)

        print("\n=======================================================================")
        print("          BÁO CÁO KIỂM ĐỊNH TỰ ĐỘNG (AUTOMATED AUDIT LOG)")
        print("=======================================================================")
        print(f" Tổng số mục kiểm tra bắt buộc : {len(mandatory_rows)}")
        print(f" Số mục bắt buộc ĐẠT (PASS)    : {sum(1 for row in mandatory_rows if row['status'] == 'PASS')}")
        print(f" Số mục bắt buộc FAIL          : {sum(1 for row in mandatory_rows if row['status'] == 'FAIL')}")
        print(f" Số cảnh báo địa lý (INFO)     : {sum(1 for row in self.audit_rows if row['status'] == 'INFO')}")
        print("-----------------------------------------------------------------------")
        print(f" === KẾT LUẬN TOÀN DIỆN (overall_audit_passed): {all_mandatory_passed} ===")
        print("=======================================================================\n")

    def run_all(self):
        self.clean_customers()
        _, _ = self.clean_geolocation()
        df_orders = self.clean_orders()
        self.clean_order_reviews(df_orders)
        self.clean_products()
        self.clean_order_items()
        self.clean_order_payments()
        self.clean_sellers()
        self.clean_category_translation()
        self.run_automated_audit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Quy trình ETL làm sạch và kiểm định tự động bộ dữ liệu Olist.")
    parser.add_argument('--raw_dir', type=str, default='.', help='Đường dẫn thư mục chứa 9 tệp CSV thô.')
    parser.add_argument('--output_dir', type=str, default='./processed', help='Đường dẫn thư mục lưu kết quả làm sạch.')
    
    args = parser.parse_args()
    cleaner = StrictOlistCleaner(raw_dir=args.raw_dir, output_dir=args.output_dir)
    cleaner.run_all()