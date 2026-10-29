"""Private, user-owns-data embedding. Microsoft retains authentication and permissions."""
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def secure_embed_url(value):
    message = 'Cần đường dẫn nhúng riêng tư từ Power BI: File → Embed report → Website or portal.'
    try:
        url = urlsplit(value.strip())
        if (url.scheme != 'https' or url.hostname != 'app.powerbi.com' or url.port not in (None,443)
                or url.username or url.password or url.fragment or url.path != '/reportEmbed'):
            raise ValueError(message)
        pairs = parse_qsl(url.query, keep_blank_values=True, strict_parsing=True)
        values = dict(pairs)
        allowed = {'reportId','groupId','ctid','pageName','autoAuth','filterPaneEnabled','navContentPaneEnabled'}
        if len(values) != len(pairs) or set(values)-allowed or 'reportId' not in values:
            raise ValueError(message)
        for key in ['reportId','groupId','ctid']:
            if key in values:
                if not re.fullmatch(r'[0-9a-fA-F-]{36}', values[key]): raise ValueError(message)
                values[key] = str(UUID(values[key]))
        for key in ['autoAuth','filterPaneEnabled','navContentPaneEnabled']:
            if key in values and values[key].lower() not in {'true','false'}: raise ValueError(message)
        if 'pageName' in values and not re.fullmatch(r'[A-Za-z0-9_-]{1,256}',values['pageName']):
            raise ValueError(message)
        values['autoAuth'] = 'true'
    except (ValueError, TypeError, AttributeError):
        raise ValueError(message) from None
    return urlunsplit(('https','app.powerbi.com','/reportEmbed',urlencode(values),''))


def can_embed(host_url):
    return urlsplit(host_url or '').scheme == 'https'


def configured_url():
    value = os.environ.get('OLIST_POWERBI_EMBED_URL')
    if value is not None: return value.strip()
    try: return st.secrets.get('powerbi', {}).get('embed_url', '').strip()
    except StreamlitSecretNotFoundError: return ''


def render_secure_powerbi(value=None):
    if value is None: value = configured_url()
    if not value:
        st.info('Báo cáo Power BI trực tuyến đang chờ kết nối với tài khoản Microsoft của nhóm.')
        return
    try: url = secure_embed_url(value)
    except ValueError as error:
        st.error(str(error))
        return
    st.caption('Đăng nhập Microsoft bằng tài khoản đã được chia sẻ báo cáo. Quyền Google trên website và quyền Power BI được quản lý riêng.')
    st.link_button('Mở báo cáo trong Power BI', url)
    if not can_embed(st.context.url):
        st.warning('Để xem báo cáo ngay trong trang này, website cần chạy bằng HTTPS. Hiện có thể mở báo cáo riêng tư bằng nút phía trên; Power BI vẫn yêu cầu đăng nhập Microsoft.')
        return
    st.iframe(url, height=780, width='stretch', alt='Báo cáo Power BI riêng tư — yêu cầu đăng nhập Microsoft')
    st.caption('Nếu bị yêu cầu đăng nhập lại, cho phép cửa sổ đăng nhập Microsoft hoặc mở báo cáo bằng nút phía trên. Việc nhúng không tự cấp giấy phép hoặc quyền xem báo cáo.')
