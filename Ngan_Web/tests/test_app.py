from pathlib import Path
import unittest,sys,tempfile,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import database as db
from streamlit.testing.v1 import AppTest
from exports import create_excel
from pdf_export import create_pdf
from customer_care import init_care_tables,init_priority_tables,change_note,read_notes,change_priority,read_priorities
from campaigns import init_campaign_tables,change_campaign,read_campaigns,read_members,read_campaign_logs
import pandas as pd

class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.old_dir,cls.old_path=db.DB_DIR,db.DB_PATH
        db.DB_DIR=Path(cls.temp.name);db.DB_PATH=db.DB_DIR/'test.db'
        cls.env=os.environ.get('OLIST_DB_PATH');os.environ['OLIST_DB_PATH']=str(db.DB_PATH)
        db.init_db();db.create_user('test_admin','TestOnly-2026-Strong','Admin');db.create_user('test_analyst','TestOnly-2026-Strong','Analyst')
        cls.admin=db.authenticate('test_admin','TestOnly-2026-Strong');cls.analyst=db.authenticate('test_analyst','TestOnly-2026-Strong')
        init_care_tables();init_priority_tables();init_campaign_tables()
    @classmethod
    def tearDownClass(cls):
        db.DB_DIR,db.DB_PATH=cls.old_dir,cls.old_path
        if cls.env is None:os.environ.pop('OLIST_DB_PATH',None)
        else:os.environ['OLIST_DB_PATH']=cls.env
        cls.temp.cleanup()
    def test_wrong_password_and_permission(self):
        self.assertIsNone(db.authenticate('test_admin','incorrect'))
        with self.assertRaises(PermissionError):db.list_users_for_admin(self.analyst['id'])
        for actor in [self.analyst['id'],99999]:
            with self.assertRaises(PermissionError):change_note(actor,'CREATE',['c1'],customer_id='c1',content='Test',tag='Cần liên hệ',status='Chưa xử lý')
    def test_admin_crud_and_audit(self):
        change_note(self.admin['id'],'CREATE',['c1'],customer_id='c1',content='Liên hệ khách hàng',tag='Cần liên hệ',status='Chưa xử lý')
        rows=read_notes(self.admin['id']);self.assertEqual(len(rows),1)
        note=rows[0]['id']
        change_note(self.admin['id'],'UPDATE',['c1'],note_id=note,customer_id='c1',content='Đã liên hệ',tag='Cần liên hệ',status='Hoàn thành')
        self.assertEqual(read_notes(self.admin['id'])[0]['content'],'Đã liên hệ')
        change_note(self.admin['id'],'DELETE',['c1'],note_id=note)
        self.assertEqual(len(read_notes(self.admin['id'])),0)
        change_priority(self.admin['id'],'CREATE',['c1'],customer_id='c1',level='Cao',reason='Chăm sóc',status='Chưa xử lý')
        self.assertEqual(len(read_priorities(self.admin['id'])),1)
        with self.assertRaises(PermissionError):change_campaign(self.analyst['id'],'CREATE',['c1'],name='Test',goal='Test',start_date='2026-10-01',end_date='2026-10-30')
        change_campaign(self.admin['id'],'CREATE',['c1'],name='Chăm sóc',goal='Liên hệ',start_date='2026-10-01',end_date='2026-10-30')
        self.assertEqual(len(read_campaigns(self.admin['id'])),1)
        campaign=read_campaigns(self.admin['id'])[0]['id']
        change_campaign(self.admin['id'],'ADD_MEMBER',['c1'],campaign_id=campaign,customer_id='c1')
        self.assertEqual(len(read_members(self.admin['id'],campaign)),1)
        change_campaign(self.admin['id'],'REMOVE_MEMBER',['c1'],campaign_id=campaign,customer_id='c1')
        self.assertEqual(len(read_members(self.admin['id'],campaign)),0)
        change_campaign(self.admin['id'],'DELETE',['c1'],campaign_id=campaign)
        self.assertEqual(len(read_campaigns(self.admin['id'])),0)
        self.assertEqual(len(read_campaign_logs(self.admin['id'])),4)
        priority=read_priorities(self.admin['id'])[0]['id']
        change_priority(self.admin['id'],'DELETE',['c1'],priority_id=priority)
        self.assertEqual(len(read_priorities(self.admin['id'])),0)
        change_priority(self.admin['id'],'CREATE',['c1'],customer_id='c1',level='Cao',reason='Chăm sóc lại',status='Chưa xử lý')
        self.assertEqual(read_priorities(self.admin['id'])[0]['id'],priority)
        with self.assertRaises(ValueError):change_campaign(self.admin['id'],'CREATE',['c1'],name='Sai ngày',goal='Test',start_date='2026-11-01',end_date='2026-10-30')
    def test_exports_vietnamese(self):
        data=pd.DataFrame({'customer_unique_id':['c1'],'label':['Khách hàng']})
        xlsx=create_excel(data,{},'Khách hàng','test');self.assertTrue(xlsx[:2]==b'PK')
        pdf=create_pdf(data,{},'Khách hàng','test',{'customer_unique_id':'Mã','label':'Nhãn'});self.assertTrue(pdf.startswith(b'%PDF'))
    def test_login_and_authenticated_dashboard_and_care(self):
        app=AppTest.from_file(str(Path(__file__).resolve().parents[1]/'app.py'),default_timeout=90).run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.label=='Tên đăng nhập' for x in app.text_input))
        app.text_input[0].set_value('test_admin')
        app.text_input[1].set_value('TestOnly-2026-Strong')
        app.button[0].click().run(timeout=90)
        self.assertFalse(app.exception)
        self.assertTrue(any('Dashboard tương tác'==x.label for x in app.tabs))
        app.text_input(key='ml_search').set_value('khong-co-khach').run(timeout=90)
        self.assertFalse(app.exception)
        self.assertTrue(any('Không có khách có cụm' in x.value for x in app.info))
        app.radio(key='workspace').set_value('Tra cứu & Chăm sóc').run(timeout=90)
        self.assertFalse(app.exception)
        self.assertIn('4.5',app.multiselect(key='cus_reviews').options)
        app.session_state['detail_customer_id']='3725c5b8c1cf5ee69158f66922a862c4'
        app.run(timeout=90)
        self.assertFalse(app.exception)
        self.assertTrue(any(x.label=='Điểm không mua lại trong 180 ngày' for x in app.metric))
        app.button(key='logout_button').click().run(timeout=90)
        self.assertFalse(app.tabs)
        app.text_input[0].set_value('test_analyst')
        app.text_input[1].set_value('TestOnly-2026-Strong')
        app.button[0].click().run(timeout=90)
        app.radio(key='workspace').set_value('Tra cứu & Chăm sóc').run(timeout=90)
        self.assertFalse(app.exception)

if __name__=='__main__':unittest.main()
