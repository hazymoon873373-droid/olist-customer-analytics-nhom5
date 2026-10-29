from pathlib import Path
import json,hashlib,tempfile,unittest,subprocess,sys
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parent
class HandoverTests(unittest.TestCase):
    def test_sources_keys_dates_reviews_and_flags(self):
        o=pd.read_csv(ROOT/'handover_v3/olist_powerbi_orders_master.csv',dtype={'customer_zip_code_prefix':str})
        c=pd.read_csv(ROOT/'inputs/clean/olist_orders_clean.csv').set_index('order_id').reindex(o.order_id)
        self.assertTrue(o.order_id.is_unique)
        for k in ['order_purchase_timestamp','order_approved_at','order_delivered_carrier_date','order_delivered_customer_date','order_estimated_delivery_date']:
            a=pd.to_datetime(o[k],format='mixed');b=pd.to_datetime(c[k],format='mixed').reset_index(drop=True)
            self.assertTrue((a.eq(b)|(a.isna()&b.isna())).all(),k)
        self.assertEqual(o.valid_delay_kpi.sum(),95097)
        self.assertTrue(o.loc[~o.valid_delay_kpi,'is_delayed'].isna().all())
        self.assertTrue(o.customer_zip_code_prefix.str.fullmatch(r'\d{5}').all())
        self.assertEqual(o.review_score.isna().sum(),829)
        self.assertEqual(o.review_score.eq(0).sum(),0)
    def test_cohort_and_ml_eligibility(self):
        c=pd.read_csv(ROOT/'handover_v3/cohort_counts_matrix.csv').set_index('CohortMonth')
        r=pd.read_csv(ROOT/'handover_v3/cohort_retention_matrix.csv').set_index('CohortMonth')
        np.testing.assert_allclose(r,c.div(c['0'],axis=0).round(4),equal_nan=True)
        for cohort in c.index:
            for age in c.columns:
                self.assertEqual(pd.isna(c.loc[cohort,age]),pd.Period(cohort,freq='M')+int(age)>pd.Period('2018-08',freq='M'))
        s=pd.read_csv(ROOT/'handover_v3/olist_powerbi_customer_snapshot_temporal_v4.csv')
        self.assertTrue(s.customer_unique_id.is_unique);self.assertEqual(len(s),96089)
        self.assertEqual(s.ml_scored.sum(),1170)
        self.assertTrue(s.loc[~s.ml_scored,'ml_churn_probability'].isna().all())
        t=pd.read_csv(ROOT/'handover_v3/churn_test_predictions_temporal_v4.csv')
        self.assertEqual(len(t),944);self.assertTrue(t.customer_unique_id.is_unique)
        np.testing.assert_array_equal(t.repurchased_true,1-t.churn_proxy_180d)
    def test_manifest_and_rebuild(self):
        manifest=json.loads((ROOT/'handover_v3/manifest.json').read_text(encoding='utf8'))
        for filename,digest in manifest['output_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT/'handover_v3'/filename).read_bytes()).hexdigest(),digest,filename)
        with tempfile.TemporaryDirectory() as folder:
            subprocess.run([sys.executable,'-B',str(ROOT/'build_handover.py'),'--output',folder],check=True,capture_output=True)
            for filename,digest in manifest['output_sha256'].items():
                self.assertEqual(hashlib.sha256((Path(folder)/filename).read_bytes()).hexdigest(),digest,filename)
    def test_business_kpis_reconcile_to_delivered_items(self):
        k=pd.read_csv(ROOT/'handover_v3/kpi_summary_tam.csv').set_index('metric').value
        i=pd.read_csv(ROOT/'handover_v3/olist_powerbi_items_master.csv')
        d=i.loc[i.order_status.eq('delivered')]
        self.assertAlmostEqual(k['gmv_products_delivered'],d.price.sum(),places=6)
        self.assertAlmostEqual(k['gross_value_with_freight_delivered'],(d.price+d.freight_value).sum(),places=6)
        self.assertAlmostEqual(k['aov_products_delivered'],d.price.sum()/k['delivered_orders'],places=6)
        self.assertAlmostEqual(k['late_delivery_rate_valid'],7793/95097,places=10)
        stats=pd.read_csv(ROOT/'handover_v3/descriptive_statistics.csv')
        self.assertTrue({'count','mean','median','min','max','std'}.issubset(stats.columns))
    def test_integration_contract_resolves_actual_files_and_keys(self):
        contract=json.loads((ROOT/'handover_v3/integration_contract.json').read_text(encoding='utf8'))
        for role,spec in contract['datasets'].items():
            frame=pd.read_csv(ROOT/'handover_v3'/spec['file'],low_memory=False)
            self.assertEqual(len(frame),spec['rows'],role)
            self.assertEqual(list(frame.columns),spec['columns'],role)
            self.assertFalse(frame.duplicated(spec['key']).any(),role)
            self.assertFalse(frame[spec['key']].isna().any().any(),role)
        self.assertEqual(contract['upstream_filename_map']['bi_web_customers.csv'],contract['datasets']['ml_bi']['file'])
        self.assertEqual(contract['upstream_bi_column_map']['churn_probability'],'ml_churn_probability')
if __name__=='__main__':unittest.main(verbosity=2)
