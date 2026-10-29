"""Google tokens are validated by Streamlit; these tests cover our authorization boundary."""
from pathlib import Path
from contextlib import closing
from unittest.mock import patch
import tempfile
import time
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import database as db
from google_auth import approved_roles, resolve_google_account, google_configuration, GOOGLE_METADATA
from setup_google import build_settings
import tomllib
from streamlit.testing.v1 import AppTest


class GoogleAuthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.paths = patch.multiple(db, DB_DIR=Path(self.temp.name), DB_PATH=Path(self.temp.name)/'auth.db')
        self.paths.start()
        db.init_db()
        self.roles = approved_roles({'admins': ['lead@example.com'], 'analysts': ['member@example.com']})
        self.claims = {'iss': 'https://accounts.google.com', 'sub': 'google-subject-123',
                       'email': 'lead@example.com', 'email_verified': True, 'exp': int(time.time()) + 3600}

    def tearDown(self):
        self.paths.stop()
        self.temp.cleanup()

    def test_repeated_identity_same_user_no_password(self):
        user = resolve_google_account(self.claims, self.roles)
        again = resolve_google_account(self.claims, self.roles)
        self.assertEqual(user['id'], again['id'])
        self.assertEqual(user['role'], 'Admin')
        self.assertEqual(user['auth_kind'], 'google')
        self.assertIsNone(db.authenticate(user['username'], '!'))

    def test_unverified_wrong_issuer_expired_or_unknown_denied(self):
        for change in [{'email_verified': False}, {'email_verified': 'true'}, {'iss': 'https://attacker.example'},
                       {'exp': 1}, {'exp':float('nan')}, {'email': 'stranger@example.com'}, {'sub': ''}]:
            with self.subTest(change=change), self.assertRaises(PermissionError):
                resolve_google_account(self.claims | change, self.roles)

    def test_role_claim_cannot_escalate_analyst(self):
        user = resolve_google_account(self.claims | {'email': 'member@example.com', 'role': 'Admin'}, self.roles)
        self.assertEqual(user['role'], 'Analyst')
        with self.assertRaises(PermissionError): db.list_users_for_admin(user['id'])

    def test_removed_allowlist_and_disabled_account_denied(self):
        user = resolve_google_account(self.claims, self.roles)
        with self.assertRaises(PermissionError): resolve_google_account(self.claims, {})
        with closing(db.connect_db()) as con, con:
            con.execute('UPDATE users SET is_active=0 WHERE id=?', (user['id'],))
        with self.assertRaises(PermissionError): resolve_google_account(self.claims, self.roles)

    def test_no_link_to_local_account_by_email(self):
        db.create_user('lead@example.com', 'Test-only-strong-2026', 'Analyst')
        local = db.authenticate('lead@example.com', 'Test-only-strong-2026')
        google = resolve_google_account(self.claims, self.roles)
        self.assertNotEqual(local['id'], google['id'])
        self.assertEqual(db.get_active_user(local['id'])['role'], 'Analyst')

    def test_subject_is_stable_and_email_cannot_bind_to_second_subject(self):
        resolve_google_account(self.claims, self.roles)
        with self.assertRaises(PermissionError):
            resolve_google_account(self.claims | {'sub': 'different-subject'}, self.roles)

    def test_conflicting_roles_rejected(self):
        with self.assertRaises(ValueError): approved_roles({'admins':['lead@example.com'], 'analysts':['LEAD@example.com']})

    def test_existing_local_database_migrated_without_losing_password(self):
        db.create_user('existing', 'Test-only-strong-2026', 'Admin')
        db.init_db()
        self.assertIsNotNone(db.authenticate('existing', 'Test-only-strong-2026'))

    def test_configuration_requires_safe_redirect_and_allowlist(self):
        self.assertIsNone(google_configuration({}))
        config = {'auth': {'redirect_uri':'http://localhost:8501/oauth2callback', 'cookie_secret':'x'*48,
                          'google':{'client_id':'test.apps.googleusercontent.com','client_secret':'test-only', 'server_metadata_url':GOOGLE_METADATA}},
                  'google_access': {'admins':['lead@example.com']}}
        self.assertEqual(google_configuration(config),{'lead@example.com':'Admin'})
        for uri in ['http://external.example/oauth2callback', 'https://example.com/wrong', 'https://example.com/oauth2callback?next=evil']:
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                google_configuration(config | {'auth':config['auth'] | {'redirect_uri':uri}})

    def test_real_old_schema_migration(self):
        old = Path(self.temp.name)/'old.db'
        with patch.object(db, 'DB_PATH', old):
            with closing(db.connect_db()) as con, con:
                con.execute('''CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL, role TEXT NOT NULL, is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP)''')
            db.create_user('oldadmin', 'Test-only-strong-2026', 'Admin')
            db.init_db()
            self.assertIsNotNone(db.authenticate('oldadmin', 'Test-only-strong-2026'))
            self.assertEqual(db.get_active_user(1)['auth_kind'],'local')

    def test_downloaded_client_configuration(self):
        web = {'web': {'client_id':'test.apps.googleusercontent.com','client_secret':'test-only-secret',
                       'redirect_uris':['http://localhost:8501/oauth2callback']}}
        text = build_settings(web, ['lead@example.com'], ['member@example.com'], 'http://localhost:8501/oauth2callback')
        config = tomllib.loads(text)
        self.assertEqual(google_configuration(config), self.roles)
        self.assertGreaterEqual(len(config['auth']['cookie_secret']),32)
        with self.assertRaises(ValueError):
            build_settings(web, ['lead@example.com'], [], 'https://example.com/oauth2callback')

    def test_template_does_not_enable_google(self):
        example = Path(__file__).resolve().parents[1]/'.streamlit/secrets.example.toml'
        self.assertIsNone(google_configuration(tomllib.loads(example.read_text())))

    def auth_app(self):
        app = AppTest.from_string("from auth import require_login\nimport streamlit as st\nu = require_login()\nst.write('AUTHORIZED:'+u['role'])")
        web = {'web':{'client_id':'test.apps.googleusercontent.com','client_secret':'test-only',
                      'redirect_uris':['http://localhost:8501/oauth2callback']}}
        app.secrets.update(tomllib.loads(build_settings(web,['lead@example.com'],['member@example.com'],'http://localhost:8501/oauth2callback')))
        return app

    def test_google_ui_authorization_rechecked_every_rerun(self):
        # Mock the verified framework identity only; this does not claim to test Google OAuth.
        class FrameworkUser(dict):
            def to_dict(self): return dict(self)
        identity = FrameworkUser(self.claims | {'is_logged_in':True})
        app = self.auth_app()
        with patch('auth.st.user', identity):
            app.run()
            self.assertFalse(app.exception)
            self.assertTrue(any(x.value=='AUTHORIZED:Admin' for x in app.markdown))
            app.secrets['google_access']['admins'] = []
            app.run()
            self.assertFalse(app.exception)
            self.assertFalse(any(x.value.startswith('AUTHORIZED:') for x in app.markdown))
            self.assertTrue(app.error)

    def test_database_id_without_google_cookie_is_denied(self):
        user = resolve_google_account(self.claims, self.roles)
        app = self.auth_app()
        app.session_state['auth_user_id'] = user['id']
        with patch('auth.st.user', {'is_logged_in':False}):
            app.run()
        self.assertFalse(app.exception)
        self.assertTrue(any(x.label=='Tên đăng nhập' for x in app.text_input))
        self.assertFalse(any(x.value.startswith('AUTHORIZED:') for x in app.markdown))

    def test_logout_clears_local_state_and_google_cookie(self):
        from auth import logout
        state={'auth_user_id':1,'auth_method':'google','filter':'SP'}
        with patch('auth.st.user',{'is_logged_in':True}), patch('auth.st.session_state',state), patch('auth.st.logout') as clear_cookie:
            logout()
        self.assertEqual(state,{})
        clear_cookie.assert_called_once()


if __name__ == '__main__': unittest.main()
