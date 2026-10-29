from contextlib import closing
from datetime import date
import json
import sqlite3

import streamlit as st

from database import connect_db, get_active_user


STATUSES = [
    "Nháp",
    "Đang triển khai",
    "Hoàn thành",
    "Tạm dừng",
]


# ==============================================
# KHỞI TẠO BẢNG — KHÔNG XÓA DỮ LIỆU HIỆN CÓ
# ==============================================
def init_campaign_tables():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS retention_campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            goal TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            updated_at TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS retention_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campaign_id INTEGER NOT NULL,
            customer_unique_id TEXT NOT NULL,
            created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            updated_at TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            UNIQUE(campaign_id, customer_unique_id)
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS retention_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL,
            campaign_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
    ]

    with closing(connect_db()) as connection:
        with connection:
            for statement in statements:
                connection.execute(statement)


# ==============================================
# KIỂM TRA QUYỀN
# ==============================================
def require_campaign_user(actor_id):
    actor = get_active_user(actor_id)

    if actor is None:
        raise PermissionError("Phiên đăng nhập không còn hợp lệ.")

    return actor


def require_admin_in_transaction(connection, actor_id):
    actor = connection.execute(
        """
        SELECT id, role
        FROM users
        WHERE id = ? AND is_active = 1
        """,
        (actor_id,),
    ).fetchone()

    if actor is None or actor["role"] != "Admin":
        raise PermissionError(
            "Chỉ tài khoản Admin đang hoạt động được thay đổi chiến dịch."
        )


# ==============================================
# ĐỌC DỮ LIỆU
# ==============================================
def read_campaigns(actor_id):
    require_campaign_user(actor_id)

    with closing(connect_db()) as connection:
        rows = connection.execute(
            """
            SELECT c.*,
                   (
                       SELECT COUNT(*)
                       FROM retention_members AS m
                       WHERE m.campaign_id = c.id
                         AND m.is_deleted = 0
                   ) AS customer_count
            FROM retention_campaigns AS c
            WHERE c.is_deleted = 0
            ORDER BY c.id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def read_members(actor_id, campaign_id):
    require_campaign_user(actor_id)

    with closing(connect_db()) as connection:
        rows = connection.execute(
            """
            SELECT m.customer_unique_id, m.created_at,
                   m.updated_at
            FROM retention_members AS m
            JOIN retention_campaigns AS c
              ON c.id = m.campaign_id
            WHERE m.campaign_id = ?
              AND m.is_deleted = 0
              AND c.is_deleted = 0
            ORDER BY m.customer_unique_id
            """,
            (campaign_id,),
        ).fetchall()

    return [dict(row) for row in rows]


def read_campaign_logs(actor_id):
    with closing(connect_db()) as connection:
        require_admin_in_transaction(connection, actor_id)

        rows = connection.execute(
            """
            SELECT a.id, u.username, a.campaign_id,
                   a.action, a.created_at, a.details
            FROM retention_audit_logs AS a
            LEFT JOIN users AS u ON u.id = a.actor_id
            ORDER BY a.id DESC
            LIMIT 100
            """
        ).fetchall()

    return [dict(row) for row in rows]


# ==============================================
# GHI DỮ LIỆU VÀ NHẬT KÝ TRONG CÙNG GIAO DỊCH
# ==============================================
def change_campaign(
    actor_id,
    action,
    valid_customers,
    campaign_id=None,
    name="",
    goal="",
    start_date="",
    end_date="",
    status="Nháp",
    customer_id="",
):
    allowed_actions = {
        "CREATE",
        "UPDATE",
        "DELETE",
        "ADD_MEMBER",
        "REMOVE_MEMBER",
    }

    if action not in allowed_actions:
        raise ValueError("Thao tác không hợp lệ.")

    name = name.strip()
    goal = goal.strip()
    customer_id = customer_id.strip()

    if action in {"CREATE", "UPDATE"}:
        if not name or len(name) > 150:
            raise ValueError("Tên chiến dịch cần từ 1 đến 150 ký tự.")

        if not goal or len(goal) > 2000:
            raise ValueError("Mục tiêu cần từ 1 đến 2.000 ký tự.")

        if status not in STATUSES:
            raise ValueError("Trạng thái không hợp lệ.")

        try:
            start = date.fromisoformat(str(start_date))
            end = date.fromisoformat(str(end_date))
        except (ValueError, TypeError):
            raise ValueError("Ngày bắt đầu hoặc kết thúc không hợp lệ.")

        if end < start:
            raise ValueError(
                "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu."
            )

        start_date = start.isoformat()
        end_date = end.isoformat()

    if action == "ADD_MEMBER":
        if customer_id not in valid_customers:
            raise ValueError(
                "Mã khách hàng không tồn tại trong dữ liệu website."
            )

    with closing(connect_db()) as connection:
        with connection:
            # Khóa ghi trong lúc kiểm tra và thay đổi dữ liệu,
            # tránh hai thao tác đồng thời tạo trạng thái không nhất quán.
            connection.execute("BEGIN IMMEDIATE")
            require_admin_in_transaction(connection, actor_id)

            before = None
            after = None

            if action != "CREATE":
                row = connection.execute(
                    """
                    SELECT *
                    FROM retention_campaigns
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (campaign_id,),
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "Chiến dịch không còn tồn tại hoặc đã bị xóa."
                    )

                before = dict(row)

            if action == "CREATE":
                cursor = connection.execute(
                    """
                    INSERT INTO retention_campaigns (
                        name, goal, start_date, end_date,
                        status, created_by
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name, goal, start_date, end_date,
                        status, actor_id,
                    ),
                )
                campaign_id = cursor.lastrowid

            elif action == "UPDATE":
                connection.execute(
                    """
                    UPDATE retention_campaigns
                    SET name = ?, goal = ?, start_date = ?,
                        end_date = ?, status = ?,
                        updated_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (
                        name, goal, start_date, end_date,
                        status, actor_id, campaign_id,
                    ),
                )

            elif action == "DELETE":
                connection.execute(
                    """
                    UPDATE retention_campaigns
                    SET is_deleted = 1,
                        updated_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (actor_id, campaign_id),
                )

                # Giữ các thành viên để bảo toàn lịch sử.
                # Các truy vấn thành viên đều loại chiến dịch đã xóa.

            else:
                member = connection.execute(
                    """
                    SELECT *
                    FROM retention_members
                    WHERE campaign_id = ?
                      AND customer_unique_id = ?
                    """,
                    (campaign_id, customer_id),
                ).fetchone()

                before = dict(member) if member else None

                if action == "ADD_MEMBER":
                    if member and member["is_deleted"] == 0:
                        raise ValueError(
                            "Khách hàng đã có trong chiến dịch."
                        )

                    if member:
                        connection.execute(
                            """
                            UPDATE retention_members
                            SET is_deleted = 0,
                                updated_by = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (actor_id, member["id"]),
                        )
                    else:
                        connection.execute(
                            """
                            INSERT INTO retention_members (
                                campaign_id,
                                customer_unique_id,
                                created_by
                            )
                            VALUES (?, ?, ?)
                            """,
                            (campaign_id, customer_id, actor_id),
                        )

                else:
                    if member is None or member["is_deleted"] == 1:
                        raise ValueError(
                            "Khách hàng không còn trong chiến dịch."
                        )

                    connection.execute(
                        """
                        UPDATE retention_members
                        SET is_deleted = 1,
                            updated_by = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (actor_id, member["id"]),
                    )

                after = dict(
                    connection.execute(
                        """
                        SELECT *
                        FROM retention_members
                        WHERE campaign_id = ?
                          AND customer_unique_id = ?
                        """,
                        (campaign_id, customer_id),
                    ).fetchone()
                )

                connection.execute(
                    """
                    UPDATE retention_campaigns
                    SET updated_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (actor_id, campaign_id),
                )

            if action in {"CREATE", "UPDATE", "DELETE"}:
                after = dict(
                    connection.execute(
                        """
                        SELECT *
                        FROM retention_campaigns
                        WHERE id = ?
                        """,
                        (campaign_id,),
                    ).fetchone()
                )

            connection.execute(
                """
                INSERT INTO retention_audit_logs (
                    actor_id, campaign_id, action, details
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    actor_id,
                    campaign_id,
                    action,
                    json.dumps(
                        {"before": before, "after": after},
                        ensure_ascii=False,
                    ),
                ),
            )


def submit_change(message, **kwargs):
    try:
        change_campaign(**kwargs)
    except (ValueError, PermissionError) as error:
        st.error(str(error))
    except sqlite3.Error:
        st.error(
            "Không lưu được dữ liệu. "
            "Hãy thử lại và kiểm tra quyền ghi thư mục storage."
        )
    else:
        st.session_state["campaign_message"] = message
        st.rerun()


# ==============================================
# GIAO DIỆN
# ==============================================
def render_campaigns(user, customer_ids):
    st.subheader("Chiến dịch giữ chân khách hàng")
    st.caption(
        "Quản lý kế hoạch và khách hàng tham gia. "
        "Chức năng này chưa tự gửi email hoặc tin nhắn."
    )

    try:
        actor = require_campaign_user(user["id"])
        init_campaign_tables()
        campaigns = read_campaigns(actor["id"])
    except PermissionError as error:
        st.error(str(error))
        return
    except sqlite3.Error:
        st.error("Không truy cập được dữ liệu chiến dịch.")
        return

    valid_customers = {
        str(value).strip() for value in customer_ids
        if value is not None and str(value).strip()
    }

    common = {
        "actor_id": actor["id"],
        "valid_customers": valid_customers,
    }

    message = st.session_state.pop("campaign_message", None)
    if message:
        st.success(message)

    st.metric("Số chiến dịch chưa bị xóa", len(campaigns))

    search = st.text_input(
        "Tìm chiến dịch theo tên",
        key="campaign_search",
    ).strip()

    status_filter = st.multiselect(
        "Lọc trạng thái chiến dịch",
        STATUSES,
        key="campaign_status_filter",
    )

    visible = [
        item
        for item in campaigns
        if search.casefold() in item["name"].casefold()
        and (
            not status_filter
            or item["status"] in status_filter
        )
    ]

    if visible:
        st.dataframe(
            [
                {
                    "Mã": item["id"],
                    "Tên chiến dịch": item["name"],
                    "Mục tiêu": item["goal"],
                    "Bắt đầu": item["start_date"],
                    "Kết thúc": item["end_date"],
                    "Trạng thái": item["status"],
                    "Số khách": item["customer_count"],
                }
                for item in visible
            ],
            hide_index=True,
            width="stretch",
        )
    else:
        st.info("Chưa có chiến dịch phù hợp.")

    is_admin = actor["role"] == "Admin"

    if not is_admin:
        st.caption(
            "Analyst được xem chiến dịch và danh sách khách tham gia. "
            "Thay đổi dữ liệu chỉ dành cho Admin."
        )

    if is_admin:
        with st.expander("Tạo chiến dịch"):
            with st.form("campaign_create_form"):
                name = st.text_input(
                    "Tên chiến dịch",
                    max_chars=150,
                )
                goal = st.text_area(
                    "Mục tiêu / nội dung chăm sóc",
                    max_chars=2000,
                )

                col1, col2 = st.columns(2)
                with col1:
                    start = st.date_input(
                        "Ngày bắt đầu",
                        value=date.today(),
                    )
                with col2:
                    end = st.date_input(
                        "Ngày kết thúc",
                        value=date.today(),
                    )

                status = st.selectbox("Trạng thái", STATUSES)
                create = st.form_submit_button("Tạo chiến dịch")

            if create:
                submit_change(
                    "Đã tạo chiến dịch. Nếu đang lọc danh sách, "
                    "hãy xóa bộ lọc để tìm chiến dịch mới.",
                    **common,
                    action="CREATE",
                    name=name,
                    goal=goal,
                    start_date=start,
                    end_date=end,
                    status=status,
                )

    if visible:
        campaign_map = {item["id"]: item for item in visible}

        if st.session_state.get("campaign_selected") not in campaign_map:
            st.session_state.pop("campaign_selected", None)

        selected_id = st.selectbox(
            "Chọn chiến dịch để xem chi tiết",
            options=list(campaign_map),
            format_func=lambda value: (
                f"#{value} — {campaign_map[value]['name']}"
            ),
            key="campaign_selected",
        )

        selected = campaign_map[selected_id]

        st.write("**Mục tiêu:**")
        st.text(selected["goal"])

        try:
            members = read_members(actor["id"], selected_id)
        except (PermissionError, sqlite3.Error):
            st.error("Không đọc được danh sách khách tham gia.")
            return

        st.write("**Khách hàng tham gia chiến dịch**")

        if members:
            st.dataframe(
                [
                    {
                        "Mã khách hàng": item["customer_unique_id"],
                        "Ngày thêm (UTC)": item["created_at"],
                        "Cập nhật (UTC)": item["updated_at"],
                    }
                    for item in members
                ],
                hide_index=True,
                width="stretch",
            )
        else:
            st.info("Chiến dịch chưa có khách hàng tham gia.")

        if is_admin:
            with st.expander("Sửa thông tin chiến dịch"):
                with st.form(f"campaign_edit_{selected_id}"):
                    new_name = st.text_input(
                        "Tên chiến dịch",
                        value=selected["name"],
                        max_chars=150,
                    )

                    new_goal = st.text_area(
                        "Mục tiêu / nội dung",
                        value=selected["goal"],
                        max_chars=2000,
                    )

                    new_start = st.date_input(
                        "Ngày bắt đầu",
                        value=date.fromisoformat(
                            selected["start_date"]
                        ),
                    )

                    new_end = st.date_input(
                        "Ngày kết thúc",
                        value=date.fromisoformat(
                            selected["end_date"]
                        ),
                    )

                    new_status = st.selectbox(
                        "Trạng thái",
                        STATUSES,
                        index=STATUSES.index(selected["status"]),
                    )

                    save = st.form_submit_button("Lưu thay đổi")

                if save:
                    submit_change(
                        "Đã cập nhật chiến dịch.",
                        **common,
                        action="UPDATE",
                        campaign_id=selected_id,
                        name=new_name,
                        goal=new_goal,
                        start_date=new_start,
                        end_date=new_end,
                        status=new_status,
                    )

            with st.expander("Thêm hoặc bỏ khách tham gia"):
                with st.form(f"campaign_add_member_{selected_id}"):
                    customer_id = st.text_input(
                        "Mã customer_unique_id đầy đủ",
                        help="Copy mã từ tab Khách hàng RFM.",
                    )
                    add = st.form_submit_button(
                        "Thêm khách vào chiến dịch"
                    )

                if add:
                    submit_change(
                        "Đã thêm khách hàng vào chiến dịch.",
                        **common,
                        action="ADD_MEMBER",
                        campaign_id=selected_id,
                        customer_id=customer_id,
                    )

                if members:
                    with st.form(
                        f"campaign_remove_member_{selected_id}"
                    ):
                        remove_id = st.selectbox(
                            "Khách hàng cần bỏ khỏi chiến dịch",
                            [
                                item["customer_unique_id"]
                                for item in members
                            ],
                        )

                        confirmed = st.checkbox(
                            "Xác nhận bỏ khách này khỏi chiến dịch"
                        )

                        remove = st.form_submit_button(
                            "Bỏ khách khỏi chiến dịch"
                        )

                    if remove:
                        if not confirmed:
                            st.warning("Hãy tích ô xác nhận.")
                        else:
                            submit_change(
                                "Đã bỏ khách khỏi chiến dịch "
                                "bằng xóa mềm.",
                                **common,
                                action="REMOVE_MEMBER",
                                campaign_id=selected_id,
                                customer_id=remove_id,
                            )

            with st.expander("Xóa mềm chiến dịch"):
                with st.form(f"campaign_delete_{selected_id}"):
                    st.write(
                        "Chiến dịch sẽ bị ẩn khỏi danh sách. "
                        "Dữ liệu và nhật ký vẫn được giữ lại."
                    )

                    confirmed = st.checkbox(
                        "Tôi xác nhận xóa mềm chiến dịch này"
                    )

                    delete = st.form_submit_button(
                        "Xóa mềm chiến dịch"
                    )

                if delete:
                    if not confirmed:
                        st.warning("Hãy tích ô xác nhận.")
                    else:
                        submit_change(
                            "Đã xóa mềm chiến dịch và lưu nhật ký.",
                            **common,
                            action="DELETE",
                            campaign_id=selected_id,
                        )

    if is_admin:
        with st.expander("Nhật ký chiến dịch — 100 thao tác gần nhất"):
            try:
                logs = read_campaign_logs(actor["id"])
            except (PermissionError, sqlite3.Error):
                st.error("Không đọc được nhật ký.")
            else:
                if logs:
                    st.dataframe(
                        logs,
                        hide_index=True,
                        width="stretch",
                    )
                else:
                    st.info("Chưa có nhật ký chiến dịch.")

            st.caption("Thời gian nhật ký được ghi theo UTC.")
