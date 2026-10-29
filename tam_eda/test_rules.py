import unittest
import pandas as pd
from pathlib import Path
import tempfile,json
from analytics_rules import parse_flags, filter_dates, review_mean, set_delivery_metrics, rfm_core, cohort_tables, require_keys, apply_multidimensional_filter

class RuleTests(unittest.TestCase):
    def test_last_day_is_included(self):
        d=pd.DataFrame({'order_purchase_timestamp':pd.to_datetime(['2018-08-31 14:00','2018-09-01 00:00'])})
        self.assertEqual(len(filter_dates(d,end_date='2018-08-31')),1)
    def test_unknown_flag_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'flag'):parse_flags(pd.Series(['true','maybe']))
    def test_missing_delivery_is_unknown(self):
        d=pd.DataFrame({'order_purchase_timestamp':pd.to_datetime(['2018-08-01']), 'order_delivered_customer_date':[pd.NaT], 'order_estimated_delivery_date':pd.to_datetime(['2018-08-10']),'valid_delay_kpi':[False]})
        out=set_delivery_metrics(d);self.assertTrue(pd.isna(out.loc[0,'is_delayed']))
    def test_bad_valid_flag_cannot_claim_missing_delivery(self):
        d=pd.DataFrame({'order_purchase_timestamp':pd.to_datetime(['2018-08-01']), 'order_delivered_customer_date':[pd.NaT], 'order_estimated_delivery_date':pd.to_datetime(['2018-08-10']),'valid_delay_kpi':[True]})
        with self.assertRaises(ValueError):set_delivery_metrics(d)
    def test_review_excludes_flagged_and_keeps_fraction(self):
        r=pd.DataFrame({'order_id':['a','a','a'],'review_score':[1,4,5],'review_before_purchase':[True,False,False]})
        self.assertEqual(review_mean(r).loc['a'],4.5)
    def test_duplicate_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate'):require_keys(pd.DataFrame({'id':['x','x']}),['id'],'orders')
    def test_rfm_midnight_normalization_and_cutoff(self):
        d=pd.DataFrame({'order_id':['a','b'],'customer_unique_id':['u','u'],'order_status':['delivered']*2,'order_purchase_timestamp':pd.to_datetime(['2018-08-30 23:59:59','2018-08-31 01:00:00']),'total_products_value':[10,90]})
        r=rfm_core(d);self.assertEqual(r.recency.iloc[0],0);self.assertEqual(r.frequency.iloc[0],1);self.assertEqual(r.monetary.iloc[0],10)
    def test_cohort_zero_and_future_are_distinct(self):
        d=pd.DataFrame({'customer_unique_id':['u','v'],'order_status':['delivered']*2,'order_purchase_timestamp':pd.to_datetime(['2018-06-01','2018-08-01'])})
        c,r=cohort_tables(d)
        self.assertEqual(r.loc['2018-06',1],0);self.assertTrue(pd.isna(r.loc['2018-08',1]));self.assertEqual(r.loc['2018-06',0],1)
    def test_input_failure_does_not_replace_existing_handover(self):
        from build_handover import build,ROOT
        with tempfile.TemporaryDirectory() as folder:
            out=Path(folder)/'handover';out.mkdir();(out/'manifest.json').write_text('{}');(out/'sentinel.csv').write_text('old data')
            with self.assertRaises(FileNotFoundError):build(Path(folder)/'missing',ROOT/'inputs/ml',out)
            self.assertEqual((out/'sentinel.csv').read_text(),'old data')
            self.assertEqual(sorted(p.name for p in out.iterdir()),['manifest.json','sentinel.csv'])
    def test_category_filter_does_not_include_other_basket_items(self):
        orders=pd.DataFrame({'order_id':['a','b'],'order_status':['delivered']*2,'customer_state':['SP','RJ'],'order_purchase_timestamp':pd.to_datetime(['2018-08-31 14:00','2018-08-31 15:00'])})
        items=pd.DataFrame({'order_id':['a','a','b'],'category_english':['health','other','health']})
        payments=pd.DataFrame({'order_id':['a','b'],'payment_type':['card','boleto']})
        o,i=apply_multidimensional_filter(orders,items,payments,end_date='2018-08-31',states=['sp'],categories=['health'],payment_types=['card'])
        self.assertEqual(o.order_id.tolist(),['a']);self.assertEqual(i.category_english.tolist(),['health'])

if __name__=='__main__':unittest.main(verbosity=2)
