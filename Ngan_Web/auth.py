import streamlit as st

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


def require_login():
    init_db()

    # Đọc lại vai trò và trạng thái từ database.
    user_id = st.session_state.get("auth_user_id")

    user = (
        get_active_user(user_id)
        if user_id is not None
        else None
    )

    if user is None:
        st.session_state.pop("auth_user_id", None)

        st.markdown(
            """
            <div class="hero-banner">
                <div class="hero-eyebrow">
                    Olist · Nhóm 5
                </div>
                <h1>Phân tích khách hàng Olist</h1>
                <p>
                    Đăng nhập để tra cứu đơn hàng,
                    khám phá khách hàng và xuất báo cáo.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        left, center, right = st.columns([1, 2, 1])

        with center:
            st.subheader("Đăng nhập hệ thống")

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
                    "Đăng nhập"
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
                    st.rerun()

        # Không chạy phần dữ liệu phía dưới khi chưa đăng nhập.
        st.stop()

    with st.sidebar:
        st.markdown('<h2 style="color:#1b6c80">olist<span style="color:#131416"> / analytics</span></h2>', unsafe_allow_html=True)
        st.caption("Đồ án ABDA433708 · Nhóm 5")
        st.divider()

        st.write(f"**Tài khoản:** {user['username']}")
        st.write(f"**Vai trò:** {user['role']}")

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

    return user
