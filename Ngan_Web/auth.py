from html import escape

import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError

from ui import brand
from google_auth import google_configuration, resolve_google_account
from database import (
    init_db,
    authenticate,
    get_active_user,
    list_users_for_admin,
)


# =========================================================
# ĐĂNG XUẤT
# =========================================================

def logout():
    google_logged_in = st.user.get("is_logged_in", False)

    for key in list(st.session_state.keys()):
        del st.session_state[key]

    if google_logged_in:
        st.logout()


# =========================================================
# HTML VÀ HIỆU ỨNG ĐĂNG NHẬP
# =========================================================

def render_html(content):
    st.markdown(content, unsafe_allow_html=True)


def show_login_feedback(user):
    # Xóa cờ ngay sau khi đọc để không chạy lại khi lọc/đổi tab.
    if not st.session_state.pop("_login_feedback_pending", False):
        return

    name = user.get("email") or user.get("username") or "bạn"
    safe_name = escape(str(name))

    render_html(
        '<div class="login-success-toast" role="status" '
        'aria-live="polite">'
        '<span class="success-toast-icon" aria-hidden="true">✓</span>'
        '<div>'
        '<strong>Đăng nhập thành công</strong>'
        f'<p>Chào mừng {safe_name} trở lại!</p>'
        '</div>'
        '</div>'
    )

    colors = [
        "#2dd4bf",
        "#60a5fa",
        "#a78bfa",
        "#fbbf24",
        "#fb7185",
    ]

    pieces = []

    for index in range(24):
        left = (index * 17 + 5) % 100
        delay = (index % 6) * 0.07
        duration = 1.8 + (index % 4) * 0.2
        drift = ((index % 7) - 3) * 24

        pieces.append(
            '<i class="welcome-confetti-piece" '
            f'style="--left:{left}%;'
            f'--delay:{delay:.2f}s;'
            f'--duration:{duration:.2f}s;'
            f'--drift:{drift}px;'
            f'--piece-color:{colors[index % len(colors)]};">'
            '</i>'
        )

    render_html(
        '<div class="welcome-confetti" aria-hidden="true">'
        + "".join(pieces)
        + '</div>'
    )


# =========================================================
# KIỂM TRA ĐĂNG NHẬP
# =========================================================

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

    user_id = st.session_state.get("auth_user_id")

    user = (
        get_active_user(user_id)
        if user_id is not None
        else None
    )

    google_error = False
    method = st.session_state.get("auth_method")

    if (
        method == "google"
        or (
            user is None
            and st.user.get("is_logged_in", False)
        )
    ):
        user = None

        if (
            google_roles is not None
            and st.user.get("is_logged_in", False)
        ):
            try:
                user = resolve_google_account(
                    st.user.to_dict(),
                    google_roles,
                )

                # Chỉ phát hiệu ứng khi bắt đầu phiên Google mới.
                is_new_google_session = (
                    method != "google"
                    or user_id != user["id"]
                )

                st.session_state["auth_user_id"] = user["id"]
                st.session_state["auth_method"] = "google"

                if is_new_google_session:
                    st.session_state["_login_feedback_pending"] = True

            except PermissionError:
                google_error = True
        else:
            google_error = True

    elif user is not None and user["auth_kind"] != "local":
        # ID SQLite không đủ để đăng nhập tài khoản chỉ dùng Google.
        user = None

    if user is None:
        st.session_state.pop("auth_user_id", None)
        st.session_state.pop("_login_feedback_pending", None)

        left, center = st.columns(
            [1.1, 1],
            gap="large",
            vertical_alignment="center",
        )

        with left:
            brand()

            render_html(
                '<div class="login-intro">'

                '<div class="page-path">'
                '✦ KHÔNG GIAN DỮ LIỆU KHÁCH HÀNG'
                '</div>'

                '<h1>'
                'Hiểu khách hàng.<br>'
                '<em>Nhìn rõ cơ hội.</em>'
                '</h1>'

                '<p>'
                'Kết nối lịch sử mua sắm, kết quả phân tích '
                'và hoạt động chăm sóc trong một không gian làm việc.'
                '</p>'

                '<div class="login-workflow">'

                '<div class="login-step">'
                '<span aria-hidden="true">🗂️</span>'
                '<div>'
                '<strong>Dữ liệu có nền tảng</strong>'
                '<small>Thu thập, làm sạch và đối soát nguồn</small>'
                '</div>'
                '</div>'

                '<div class="login-step">'
                '<span aria-hidden="true">🔎</span>'
                '<div>'
                '<strong>Phân tích có ngữ cảnh</strong>'
                '<small>Dashboard, RFM và mô hình mua lại</small>'
                '</div>'
                '</div>'

                '<div class="login-step">'
                '<span aria-hidden="true">🎯</span>'
                '<div>'
                '<strong>Chăm sóc có trọng tâm</strong>'
                '<small>Tra cứu khách hàng và lập chiến dịch</small>'
                '</div>'
                '</div>'

                '</div>'

                '<div class="login-footnote">'
                'Đồ án ABDA433708 · HCMUTE · Nhóm 5'
                '</div>'

                '</div>'
            )

        with center, st.container(
            border=True,
            key="login_panel",
        ):
            render_html(
                '<div class="login-panel-heading">'
                '<span class="login-lock" aria-hidden="true">🔐</span>'
                '<div class="login-panel-eyebrow">'
                'CHÀO MỪNG TRỞ LẠI'
                '</div>'
                '<h2>Đăng nhập hệ thống</h2>'
                '<p>Truy cập không gian làm việc của nhóm.</p>'
                '</div>'
            )

            if google_error:
                st.error(
                    "Tài khoản Google chưa được cấp quyền, "
                    "đã bị vô hiệu hóa hoặc phiên đã hết hạn."
                )

                st.button(
                    "Đổi tài khoản Google",
                    on_click=st.logout,
                    key="google_switch",
                )

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
                    "Đăng nhập",
                    width="stretch",
                )

            if submitted:
                if not username.strip() or not password:
                    st.warning(
                        "Vui lòng nhập tên đăng nhập và mật khẩu."
                    )
                else:
                    account = authenticate(username, password)

                    if account is None:
                        st.error(
                            "Thông tin đăng nhập không đúng "
                            "hoặc tài khoản đã bị vô hiệu hóa."
                        )
                    else:
                        st.session_state["auth_user_id"] = account["id"]
                        st.session_state["auth_method"] = "local"
                        st.session_state["_login_feedback_pending"] = True

                        st.rerun()

            st.divider()

            st.button(
                "Đăng nhập bằng Google",
                key="google_login",
                width="stretch",
                disabled=google_roles is None,
                on_click=st.login,
                args=("google",),
            )

            if google_roles is None:
                if configuration_error:
                    st.caption(
                        "Đăng nhập Google chưa được cấu hình "
                        "hợp lệ trên máy này."
                    )
                else:
                    st.caption(
                        "Đăng nhập Google chưa được cấu hình "
                        "trên máy này."
                    )

            render_html(
                '<div class="login-support">'
                'Cần hỗ trợ tài khoản? '
                '<strong>Liên hệ người quản trị.</strong>'
                '</div>'
            )

        st.stop()

    with st.sidebar:
        brand()

    show_login_feedback(user)

    return user


# =========================================================
# TÀI KHOẢN VÀ PHÂN QUYỀN TRÊN SIDEBAR
# =========================================================

def render_account_menu(user):
    with st.sidebar:
        render_html(
            '<div class="sidebar-guide">'
            '<div class="sidebar-guide-icon" aria-hidden="true">🌎</div>'
            '<strong>Dữ liệu lịch sử Olist</strong>'
            '<p>'
            'Brazil · 2016–2018<br>'
            'BRL · Phân tích & chăm sóc khách hàng'
            '</p>'
            '</div>'
        )

        label = str(user.get("email") or user["username"])

        display_role = (
            "Quản trị viên"
            if user["role"] == "Admin"
            else "Chuyên viên phân tích"
        )

        initial = escape(label[:1].upper())
        safe_label = escape(label)
        safe_role = escape(display_role)

        render_html(
            '<div class="account-card">'
            f'<span class="account-initial">{initial}</span>'
            '<div>'
            f'<strong>{safe_label}</strong>'
            f'<small>{safe_role}</small>'
            '</div>'
            '</div>'
        )

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
                    accounts = list_users_for_admin(user["id"])
                    st.dataframe(accounts)
                except PermissionError as error:
                    st.error(str(error))
        else:
            st.caption(
                "Bạn có quyền xem, tra cứu và xuất báo cáo. "
                "Không có quyền xem danh sách tài khoản."
            )
            