"""Authorize verified Streamlit OIDC claims without trusting client-supplied roles.

Only call resolve_google_account with st.user after Streamlit validates Google's
signature, audience, state and nonce. This module does not accept browser tokens.
"""
from contextlib import closing
import re
import sqlite3
import time
import math

from database import connect_db

GOOGLE_ISSUERS = {'https://accounts.google.com', 'accounts.google.com'}
GOOGLE_METADATA = 'https://accounts.google.com/.well-known/openid-configuration'


def google_configuration(settings):
    """Return a validated allowlist; incomplete setup keeps only Google login disabled."""
    auth = settings.get('auth', {})
    provider = auth.get('google', {})
    required = [auth.get('redirect_uri'), auth.get('cookie_secret'), provider.get('client_id'), provider.get('client_secret')]
    if not all(isinstance(value, str) and value.strip() for value in required):
        return None
    if any(value.startswith(('YOUR_', 'REPLACE_')) for value in required):
        return None
    if provider.get('server_metadata_url') != GOOGLE_METADATA:
        raise ValueError('Chỉ hỗ trợ máy chủ xác thực Google đã cấu hình.')
    from urllib.parse import urlparse
    redirect = urlparse(auth['redirect_uri'])
    if (redirect.path != '/oauth2callback' or redirect.query or redirect.fragment
            or redirect.username or redirect.password
            or not redirect.netloc or (redirect.scheme != 'https' and
               not (redirect.scheme == 'http' and redirect.hostname in {'localhost','127.0.0.1'}))):
        raise ValueError('Địa chỉ quay về Google không hợp lệ.')
    if len(auth['cookie_secret']) < 32:
        raise ValueError('Khóa bảo vệ phiên phải có ít nhất 32 ký tự ngẫu nhiên.')
    roles = approved_roles(settings.get('google_access', {}))
    if not roles:
        raise ValueError('Chưa cấp quyền Google cho thành viên nào.')
    return roles


def approved_roles(settings):
    roles = {}
    for key, role in [('admins', 'Admin'), ('analysts', 'Analyst')]:
        emails = settings.get(key, [])
        if not isinstance(emails, (list, tuple)):
            raise ValueError('Danh sách email Google phải là một mảng.')
        for raw in emails:
            if not isinstance(raw, str):
                raise ValueError('Email Google không hợp lệ.')
            email = raw.strip().lower()
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email):
                raise ValueError('Email Google không hợp lệ.')
            if email in roles and roles[email] != role:
                raise ValueError('Một email không được có hai vai trò.')
            roles[email] = role
    return roles


def resolve_google_account(claims, roles):
    """Bind by stable Google sub; never silently link an existing password account."""
    message = 'Tài khoản Google chưa được cấp quyền hoặc không còn hợp lệ.'
    subject = claims.get('sub')
    email = claims.get('email')
    expires = claims.get('exp')
    if (claims.get('iss') not in GOOGLE_ISSUERS or claims.get('email_verified') is not True
            or not isinstance(subject, str) or not subject.strip() or len(subject) > 255
            or not isinstance(email, str) or not isinstance(expires, (int, float))
            or isinstance(expires, bool) or not math.isfinite(expires) or expires <= time.time()):
        raise PermissionError(message)
    email = email.strip().lower()
    role = roles.get(email)
    if role not in {'Admin', 'Analyst'}:
        raise PermissionError(message)
    try:
        with closing(connect_db()) as con, con:
            con.execute('BEGIN IMMEDIATE')
            row = con.execute('''SELECT u.id,u.username,u.role,u.is_active,u.auth_kind
                FROM google_identities g JOIN users u ON u.id=g.user_id
                WHERE g.subject=?''', (subject,)).fetchone()
            if row is None:
                # A changed subject cannot take over an email previously bound to someone else.
                if con.execute('SELECT 1 FROM google_identities WHERE verified_email=?', (email,)).fetchone():
                    raise PermissionError(message)
                cursor = con.execute('''INSERT INTO users(username,password_hash,role,auth_kind)
                    VALUES (?,?,?,'google')''', ('google:' + subject, '!', role))
                user_id = cursor.lastrowid
                con.execute('INSERT INTO google_identities(subject,user_id,verified_email) VALUES (?,?,?)', (subject, user_id, email))
                username = 'google:' + subject
            else:
                if not row['is_active'] or row['auth_kind'] != 'google':
                    raise PermissionError(message)
                user_id, username = row['id'], row['username']
                if row['role'] != role:
                    con.execute('UPDATE users SET role=? WHERE id=?', (role, user_id))
                con.execute('UPDATE google_identities SET verified_email=? WHERE subject=? AND verified_email<>?', (email, subject, email))
    except sqlite3.IntegrityError:
        raise PermissionError(message) from None
    return {'id': user_id, 'username': username, 'role': role, 'auth_kind': 'google', 'email': email}
