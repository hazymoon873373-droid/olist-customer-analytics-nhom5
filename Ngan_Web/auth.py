import streamlit as st
from html import escape
from ui import brand
from streamlit.errors import StreamlitSecretNotFoundError
from google_auth import google_configuration, resolve_google_account

from database import (
    init_db,
    authenticate,
    get_active_user,
    list_users_for_admin,
)


def logout():
    # Xóa phiên đăng nhập và các bộ lọc của người dùng cũ.
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    if st.user.get('is_logged_in', False):
        st.logout()


def require_login():
    init_db()
    google_roles = None
    configuration_error = False
    try:
        google_roles = google_configuration(st.secrets.to_dict())
    except StreamlitSecretNotFoundError:
        pass
    except (ValueError, TypeError, AttributeError):
        configuration_error = True

    # Đọc lại vai trò và trạng thái từ database.
    user_id = st.session_state.get("auth_user_id")

    user = (
        get_active_user(user_id)
        if user_id is not None
        else None
    )
    google_error = False
    method = st.session_state.get('auth_method')
    if method == 'google' or (user is None and st.user.get('is_logged_in', False)):
        user = None
        if google_roles is not None and st.user.get('is_logged_in', False):
            try:
                user = resolve_google_account(st.user.to_dict(), google_roles)
                st.session_state['auth_user_id'] = user['id']
                st.session_state['auth_method'] = 'google'
            except PermissionError:
                google_error = True
        else:
            google_error = True
    elif user is not None and user['auth_kind'] != 'local':
        # An SQLite id alone never authenticates a Google-only account.
        user = None

    if user is None:
        st.session_state.pop("auth_user_id", None)

        left, center = st.columns([1.1, 1], gap='large', vertical_alignment='center')
        with left:
            brand()
            st.markdown(
                '<div class="login-intro"><div class="page-path">Phân tích dữ liệu lớn trong kinh doanh</div>'
                '<h1>Hiểu khách hàng.<br>Nhìn rõ cơ hội.</h1>'
                '<p>Khám phá hành trình mua sắm trên Olist: từ đơn hàng, phân khúc khách hàng đến kế hoạch chăm sóc.</p>'
                '<div class="login-workflow">'
                '<div class="login-step"><span>01</span><div><strong>Dữ liệu có nền tảng</strong><small>Thu thập, làm sạch và đối soát nguồn</small></div></div>'
                '<div class="login-step"><span>02</span><div><strong>Phân tích có ngữ cảnh</strong><small>Dashboard, RFM và mô hình mua lại</small></div></div>'
                '<div class="login-step"><span>03</span><div><strong>Chăm sóc có trọng tâm</strong><small>Tra cứu khách hàng và lập chiến dịch</small></div></div>'
                '</div><div class="login-footnote">Đồ án ABDA433708 · HCMUTE · Nhóm 5</div></div>',
                unsafe_allow_html=True,
            )

        with center, st.container(border=True, key='login_panel'):
            st.subheader("Đăng nhập hệ thống")
            st.caption("Truy cập không gian làm việc của nhóm.")
            if google_error:
                st.error('Tài khoản Google chưa được cấp quyền, đã bị vô hiệu hóa hoặc phiên đã hết hạn.')
                st.button('Đổi tài khoản Google', on_click=st.logout, key='google_switch')

            with st.form(
                "login_form",
                clear_on_submit=True,
            ):
                username = st.text_input(
                    "Tên đăng nhập",
                    placeholder="Nhập tên đăng nhập",
                )

                password = st.text_input(
                    "Mật khẩu",
                    type="password",
                    placeholder="Nhập mật khẩu",
                )

                submitted = st.form_submit_button(
                    "Đăng nhập", width="stretch"
                )

            if submitted:
                account = authenticate(username, password)

                if account is None:
                    st.error(
                        "Thông tin đăng nhập không đúng "
                        "hoặc tài khoản đã bị vô hiệu hóa."
                    )
                else:
                    st.session_state["auth_user_id"] = account["id"]
                    st.session_state['auth_method'] = 'local'
                    st.rerun()

            st.divider()
            st.button('Đăng nhập bằng Google', key='google_login', width='stretch',
                      disabled=google_roles is None, on_click=st.login, args=('google',))
            if google_roles is None:
                st.caption('Đăng nhập Google chưa được cấu hình hợp lệ trên máy này.' if configuration_error
                           else 'Đăng nhập Google chưa được cấu hình trên máy này.')

        # Không chạy phần dữ liệu phía dưới khi chưa đăng nhập.
        st.stop()

    with st.sidebar:
        brand()
    return user


def render_account_menu(user):
    with st.sidebar:
        st.markdown('<div class="sidebar-guide"><strong>Dữ liệu lịch sử Olist</strong><p>Brazil · 2016–2018<br>BRL · Phân tích & chăm sóc khách hàng</p></div>', unsafe_allow_html=True)
        label = user.get('email', user['username'])
        display_role = 'Quản trị viên' if user['role'] == 'Admin' else 'Chuyên viên phân tích'
        st.markdown(f'<div class="account-card"><span class="account-initial">{escape(label[:1].upper())}</span><div><strong>{escape(label)}</strong><small>{escape(display_role)}</small></div></div>', unsafe_allow_html=True)
        st.button(
            "Đăng xuất",
            on_click=logout,
            key="logout_button",
        )

        st.divider()

        if user["role"] == "Admin":
            st.caption("Bạn có quyền quản trị.")

            if st.checkbox(
                "Xem danh sách tài khoản",
                key="show_accounts",
            ):
                try:
                    accounts = list_users_for_admin(
                        user["id"]
                    )
                    st.dataframe(accounts)
                except PermissionError as error:
                    st.error(str(error))
        else:
            st.caption(
                "Bạn có quyền xem, tra cứu và xuất báo cáo. "
                "Không có quyền xem danh sách tài khoản."
            )
