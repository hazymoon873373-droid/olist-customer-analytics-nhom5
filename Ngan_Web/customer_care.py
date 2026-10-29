from contextlib import closing
import csv
import io
import json
import sqlite3

import streamlit as st

from database import connect_db, get_active_user


TAGS = [
    "Cần liên hệ",
    "Khách hàng ưu tiên",
    "Theo dõi phản hồi",
    "Hỗ trợ sau mua",
]

STATUSES = [
    "Chưa xử lý",
    "Đang xử lý",
    "Hoàn thành",
]

PRIORITY_LEVELS = [
    "Cao",
    "Trung bình",
    "Thấp",
]


# =========================================================
# KHỞI TẠO BẢNG DỮ LIỆU
# =========================================================

def init_care_tables():
    with closing(connect_db()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS customer_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    updated_at TEXT,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    note_id INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def init_priority_tables():
    with closing(connect_db()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS priority_customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_unique_id TEXT NOT NULL UNIQUE,
                    level TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_by INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER,
                    updated_at TEXT,
                    is_deleted INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS priority_audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    priority_id INTEGER NOT NULL,
                    details TEXT NOT NULL,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


# =========================================================
# KIỂM TRA QUYỀN
# =========================================================

def check_user(actor_id, admin_only=False):
    user = get_active_user(actor_id)

    if user is None:
        raise PermissionError("Bạn cần đăng nhập lại.")

    if admin_only and user["role"] != "Admin":
        raise PermissionError(
            "Chỉ Admin được thay đổi dữ liệu chăm sóc."
        )

    return user


def check_transaction_user(connection, actor_id, admin_only=False):
    """Kiểm tra quyền bằng chính kết nối đang thực hiện giao dịch."""
    row = connection.execute(
        """
        SELECT id, role
        FROM users
        WHERE id = ? AND is_active = 1
        """,
        (actor_id,),
    ).fetchone()

    if row is None:
        raise PermissionError("Bạn cần đăng nhập lại.")

    if admin_only and row["role"] != "Admin":
        raise PermissionError(
            "Chỉ Admin được thay đổi dữ liệu chăm sóc."
        )


# =========================================================
# ĐỌC VÀ CRUD GHI CHÚ
# =========================================================

def read_notes(actor_id):
    check_user(actor_id)

    with closing(connect_db()) as connection:
        rows = connection.execute(
            """
            SELECT id, customer_id, content, tag, status,
                   created_by, created_at, updated_by, updated_at
            FROM customer_notes
            WHERE is_deleted = 0
            ORDER BY id DESC
            """
        ).fetchall()

    return [dict(row) for row in rows]


def change_note(
    actor_id,
    action,
    valid_customers,
    note_id=None,
    customer_id="",
    content="",
    tag="",
    status="",
):
    check_user(actor_id, admin_only=True)

    content = content.strip()
    customer_id = customer_id.strip()

    if action not in ("CREATE", "UPDATE", "DELETE"):
        raise ValueError("Thao tác không hợp lệ.")

    if action in ("CREATE", "UPDATE"):
        if not content:
            raise ValueError(
                "Nội dung ghi chú không được để trống."
            )

        if len(content) > 2000:
            raise ValueError("Ghi chú tối đa 2.000 ký tự.")

        if tag not in TAGS or status not in STATUSES:
            raise ValueError(
                "Nhãn hoặc trạng thái không hợp lệ."
            )

    if action == "CREATE" and customer_id not in valid_customers:
        raise ValueError(
            "Mã khách hàng không tồn tại trong dữ liệu."
        )

    with closing(connect_db()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            check_transaction_user(
                connection,
                actor_id,
                admin_only=True,
            )

            before = None

            if action in ("UPDATE", "DELETE"):
                row = connection.execute(
                    """
                    SELECT *
                    FROM customer_notes
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (note_id,),
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "Ghi chú không còn tồn tại."
                    )

                before = dict(row)

            if action == "CREATE":
                cursor = connection.execute(
                    """
                    INSERT INTO customer_notes (
                        customer_id,
                        content,
                        tag,
                        status,
                        created_by
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        customer_id,
                        content,
                        tag,
                        status,
                        actor_id,
                    ),
                )

                note_id = cursor.lastrowid

            elif action == "UPDATE":
                connection.execute(
                    """
                    UPDATE customer_notes
                    SET content = ?,
                        tag = ?,
                        status = ?,
                        updated_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (
                        content,
                        tag,
                        status,
                        actor_id,
                        note_id,
                    ),
                )

            else:
                connection.execute(
                    """
                    UPDATE customer_notes
                    SET is_deleted = 1,
                        updated_by = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (actor_id, note_id),
                )

            after = dict(
                connection.execute(
                    """
                    SELECT *
                    FROM customer_notes
                    WHERE id = ?
                    """,
                    (note_id,),
                ).fetchone()
            )

            connection.execute(
                """
                INSERT INTO audit_logs (
                    actor_id,
                    action,
                    note_id,
                    details
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    actor_id,
                    action,
                    note_id,
                    json.dumps(
                        {
                            "before": before,
                            "after": after,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )


def submit_note(message, **kwargs):
    try:
        change_note(**kwargs)
    except (ValueError, PermissionError) as error:
        st.error(str(error))
    except sqlite3.Error:
        st.error(
            "Chưa lưu được ghi chú. Hãy thử lại; "
            "không xóa file database."
        )
    else:
        st.session_state["care_message"] = message
        st.rerun()


# =========================================================
# GIAO DIỆN GHI CHÚ
# =========================================================

def render_notes(user, customer_ids):
    init_care_tables()

    actor = check_user(user["id"])
    valid_customers = set(customer_ids)

    common = {
        "actor_id": actor["id"],
        "valid_customers": valid_customers,
    }

    st.subheader("Ghi chú và nhãn chăm sóc")
    st.caption(
        "Ghi chú được lưu riêng, không sửa dữ liệu "
        "khách hàng hoặc đơn hàng gốc."
    )

    flash = st.session_state.pop("care_message", None)

    if flash:
        st.success(flash)

    notes = read_notes(actor["id"])

    search = st.text_input(
        "Lọc ghi chú theo mã khách hàng",
        key="care_search",
    ).strip()

    visible_notes = [
        note
        for note in notes
        if search.casefold() in note["customer_id"].casefold()
    ]

    if visible_notes:
        st.dataframe(
            visible_notes,
            width="stretch",
            hide_index=True,
        )
    else:
        st.info("Chưa có ghi chú phù hợp.")

    if actor["role"] != "Admin":
        st.caption(
            "Analyst được xem ghi chú. "
            "Thêm, sửa và xóa chỉ dành cho Admin."
        )
        return

    with st.expander("Thêm ghi chú"):
        with st.form("create_note", clear_on_submit=False):
            customer_id = st.text_input(
                "Mã khách hàng đầy đủ — customer_unique_id"
            )

            content = st.text_area(
                "Nội dung ghi chú",
                max_chars=2000,
            )

            tag = st.selectbox("Nhãn chăm sóc", TAGS)
            status = st.selectbox("Trạng thái", STATUSES)

            submitted = st.form_submit_button(
                "Lưu ghi chú"
            )

        if submitted:
            submit_note(
                "Đã thêm ghi chú.",
                **common,
                action="CREATE",
                customer_id=customer_id,
                content=content,
                tag=tag,
                status=status,
            )

    if visible_notes:
        with st.expander("Sửa hoặc xóa ghi chú"):
            note_map = {
                note["id"]: note
                for note in visible_notes
            }

            if st.session_state.get("care_selected_note") not in note_map:
                st.session_state["care_selected_note"] = next(
                    iter(note_map)
                )

            selected_id = st.selectbox(
                "Chọn ghi chú",
                options=list(note_map),
                key="care_selected_note",
                format_func=lambda value: (
                    f"#{value} — "
                    f"{note_map[value]['customer_id']} — "
                    f"{note_map[value]['tag']}"
                ),
            )

            selected = note_map[selected_id]

            with st.form(f"edit_note_{selected_id}"):
                edited_content = st.text_area(
                    "Nội dung",
                    value=selected["content"],
                    max_chars=2000,
                )

                edited_tag = st.selectbox(
                    "Nhãn",
                    TAGS,
                    index=TAGS.index(selected["tag"]),
                )

                edited_status = st.selectbox(
                    "Trạng thái xử lý",
                    STATUSES,
                    index=STATUSES.index(selected["status"]),
                )

                save = st.form_submit_button(
                    "Lưu thay đổi"
                )

            if save:
                submit_note(
                    "Đã sửa ghi chú.",
                    **common,
                    action="UPDATE",
                    note_id=selected_id,
                    content=edited_content,
                    tag=edited_tag,
                    status=edited_status,
                )

            with st.form(f"delete_note_form_{selected_id}"):
                confirm_delete = st.checkbox(
                    "Tôi xác nhận xóa mềm ghi chú này"
                )

                delete = st.form_submit_button(
                    "Xóa ghi chú"
                )

            if delete:
                if not confirm_delete:
                    st.warning(
                        "Hãy đánh dấu xác nhận trước khi xóa."
                    )
                else:
                    submit_note(
                        "Đã xóa mềm ghi chú và lưu nhật ký.",
                        **common,
                        action="DELETE",
                        note_id=selected_id,
                    )

    with st.expander("Nhật ký ghi chú gần nhất"):
        with closing(connect_db()) as connection:
            check_transaction_user(
                connection,
                actor["id"],
                admin_only=True,
            )

            rows = connection.execute(
                """
                SELECT a.id,
                       u.username,
                       a.action,
                       a.note_id,
                       a.created_at,
                       a.details
                FROM audit_logs AS a
                LEFT JOIN users AS u ON u.id = a.actor_id
                ORDER BY a.id DESC
                LIMIT 100
                """
            ).fetchall()

        if rows:
            st.dataframe(
                [dict(row) for row in rows],
                width="stretch",
                hide_index=True,
            )
        else:
            st.info("Chưa có thao tác được ghi nhận.")

        st.caption("Thời gian database được ghi theo UTC.")


# =========================================================
# ĐỌC VÀ CRUD KHÁCH HÀNG ƯU TIÊN
# =========================================================

def read_priorities(actor_id, audit=False):
    with closing(connect_db()) as connection:
        check_transaction_user(
            connection,
            actor_id,
            admin_only=audit,
        )

        if audit:
            rows = connection.execute(
                """
                SELECT a.id,
                       u.username,
                       a.action,
                       a.priority_id,
                       a.created_at,
                       a.details
                FROM priority_audit_logs AS a
                LEFT JOIN users AS u ON u.id = a.actor_id
                ORDER BY a.id DESC
                LIMIT 100
                """
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT *
                FROM priority_customers
                WHERE is_deleted = 0
                ORDER BY
                    CASE level
                        WHEN 'Cao' THEN 0
                        WHEN 'Trung bình' THEN 1
                        ELSE 2
                    END,
                    id DESC
                """
            ).fetchall()

    return [dict(row) for row in rows]


def change_priority(
    actor_id,
    action,
    valid_customers,
    priority_id=None,
    customer_id="",
    level="",
    reason="",
    status="",
):
    if action not in ("CREATE", "UPDATE", "DELETE"):
        raise ValueError("Thao tác không hợp lệ.")

    customer_id = customer_id.strip()
    reason = reason.strip()

    if action in ("CREATE", "UPDATE"):
        if not 1 <= len(reason) <= 2000:
            raise ValueError(
                "Lý do cần từ 1 đến 2.000 ký tự."
            )

        if level not in PRIORITY_LEVELS:
            raise ValueError("Mức ưu tiên không hợp lệ.")

        if status not in STATUSES:
            raise ValueError("Trạng thái không hợp lệ.")

    if action == "CREATE" and customer_id not in valid_customers:
        raise ValueError(
            "Mã khách hàng không tồn tại trong dữ liệu."
        )

    with closing(connect_db()) as connection:
        with connection:
            connection.execute("BEGIN IMMEDIATE")

            check_transaction_user(
                connection,
                actor_id,
                admin_only=True,
            )

            before = None
            audit_action = action

            if action == "CREATE":
                existing = connection.execute(
                    """
                    SELECT *
                    FROM priority_customers
                    WHERE customer_unique_id = ?
                    """,
                    (customer_id,),
                ).fetchone()

                if existing and not existing["is_deleted"]:
                    raise ValueError(
                        "Khách hàng đã có trong danh sách ưu tiên."
                    )

                if existing:
                    # Khôi phục bản ghi đã xóa mềm.
                    before = dict(existing)
                    priority_id = existing["id"]
                    audit_action = "RESTORE"

                    connection.execute(
                        """
                        UPDATE priority_customers
                        SET level = ?,
                            reason = ?,
                            status = ?,
                            is_deleted = 0,
                            updated_by = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            level,
                            reason,
                            status,
                            actor_id,
                            priority_id,
                        ),
                    )
                else:
                    cursor = connection.execute(
                        """
                        INSERT INTO priority_customers (
                            customer_unique_id,
                            level,
                            reason,
                            status,
                            created_by
                        )
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            customer_id,
                            level,
                            reason,
                            status,
                            actor_id,
                        ),
                    )

                    priority_id = cursor.lastrowid

            else:
                row = connection.execute(
                    """
                    SELECT *
                    FROM priority_customers
                    WHERE id = ? AND is_deleted = 0
                    """,
                    (priority_id,),
                ).fetchone()

                if row is None:
                    raise ValueError(
                        "Bản ghi không còn trong danh sách ưu tiên."
                    )

                before = dict(row)

                if action == "UPDATE":
                    connection.execute(
                        """
                        UPDATE priority_customers
                        SET level = ?,
                            reason = ?,
                            status = ?,
                            updated_by = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (
                            level,
                            reason,
                            status,
                            actor_id,
                            priority_id,
                        ),
                    )
                else:
                    connection.execute(
                        """
                        UPDATE priority_customers
                        SET is_deleted = 1,
                            updated_by = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """,
                        (actor_id, priority_id),
                    )

            after = dict(
                connection.execute(
                    """
                    SELECT *
                    FROM priority_customers
                    WHERE id = ?
                    """,
                    (priority_id,),
                ).fetchone()
            )

            # Lưu thay đổi và nhật ký trong cùng giao dịch.
            connection.execute(
                """
                INSERT INTO priority_audit_logs (
                    actor_id,
                    action,
                    priority_id,
                    details
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    actor_id,
                    audit_action,
                    priority_id,
                    json.dumps(
                        {
                            "before": before,
                            "after": after,
                        },
                        ensure_ascii=False,
                    ),
                ),
            )


def submit_priority(message, **kwargs):
    try:
        change_priority(**kwargs)
    except (ValueError, PermissionError) as error:
        st.error(str(error))
    except sqlite3.Error:
        st.error(
            "Chưa lưu được dữ liệu. Hãy thử lại; "
            "không xóa file database."
        )
    else:
        st.session_state["priority_message"] = message
        st.rerun()


# =========================================================
# XUẤT CSV DANH SÁCH ƯU TIÊN
# =========================================================

def priority_csv(rows):
    def safe(value):
        text = str(value) if value is not None else ""

        # Hạn chế nội dung bị diễn giải thành công thức Excel.
        if (
            text.lstrip().startswith(("=", "+", "-", "@"))
            or text.startswith(("\t", "\r", "\n"))
        ):
            return "'" + text

        return text

    stream = io.StringIO(newline="")
    writer = csv.writer(stream)

    writer.writerow(
        [
            "Mã khách hàng",
            "Mức ưu tiên",
            "Lý do",
            "Trạng thái",
            "Ngày tạo (UTC)",
            "Ngày cập nhật (UTC)",
        ]
    )

    fields = [
        "customer_unique_id",
        "level",
        "reason",
        "status",
        "created_at",
        "updated_at",
    ]

    for row in rows:
        writer.writerow(
            [safe(row[field]) for field in fields]
        )

    return stream.getvalue().encode("utf-8-sig")


# =========================================================
# GIAO DIỆN KHÁCH HÀNG ƯU TIÊN
# =========================================================

def render_priorities(user, customer_ids):
    st.subheader("⭐ Danh sách khách hàng ưu tiên")

    st.caption(
        "Mức ưu tiên do Admin chọn để chăm sóc khách hàng; "
        "đây không phải điểm rủi ro ML. "
        "Danh sách này độc lập với nhãn trên ghi chú. "
        "Thời gian được lưu theo UTC."
    )

    actor = check_user(user["id"])
    init_priority_tables()

    rows = read_priorities(actor["id"])

    valid_customers = {
        str(value).strip()
        for value in customer_ids
        if value is not None
    }

    common = {
        "actor_id": actor["id"],
        "valid_customers": valid_customers,
    }

    flash = st.session_state.pop("priority_message", None)

    if flash:
        st.success(flash)

    search = st.text_input(
        "Tìm mã khách hàng ưu tiên",
        key="priority_search",
    ).strip().casefold()

    col1, col2 = st.columns(2)

    levels = col1.multiselect(
        "Mức ưu tiên",
        PRIORITY_LEVELS,
        key="priority_filter_level",
    )

    statuses = col2.multiselect(
        "Trạng thái chăm sóc",
        STATUSES,
        key="priority_filter_status",
    )

    visible = [
        row
        for row in rows
        if search in row["customer_unique_id"].casefold()
        and (not levels or row["level"] in levels)
        and (not statuses or row["status"] in statuses)
    ]

    st.caption(
        f"Đang hiển thị {len(visible)} / "
        f"{len(rows)} khách hàng ưu tiên."
    )

    if visible:
        display = [
            {
                "Mã khách hàng": row["customer_unique_id"],
                "Mức ưu tiên": row["level"],
                "Lý do": row["reason"],
                "Trạng thái": row["status"],
                "Ngày tạo (UTC)": row["created_at"],
                "Cập nhật (UTC)": row["updated_at"],
            }
            for row in visible
        ]

        st.dataframe(
            display,
            width="stretch",
            hide_index=True,
        )

        st.download_button(
            label="Tải CSV danh sách đã lọc",
            data=priority_csv(visible),
            file_name="khach_hang_uu_tien_da_loc.csv",
            mime="text/csv",
            key="priority_csv",
        )
    else:
        st.info(
            "Không có khách hàng ưu tiên phù hợp."
        )

    if actor["role"] != "Admin":
        st.caption(
            "Analyst được xem, lọc và xuất danh sách. "
            "Admin được thêm, sửa và xóa mềm."
        )
        return

    with st.expander("Thêm khách hàng ưu tiên"):
        with st.form("priority_create"):
            customer_id = st.text_input(
                "Mã đầy đủ — customer_unique_id"
            )

            level = st.selectbox(
                "Mức ưu tiên",
                PRIORITY_LEVELS,
            )

            reason = st.text_area(
                "Lý do ưu tiên",
                max_chars=2000,
            )

            status = st.selectbox(
                "Trạng thái",
                STATUSES,
            )

            create = st.form_submit_button(
                "Thêm vào danh sách"
            )

        if create:
            submit_priority(
                "Đã thêm khách hàng ưu tiên.",
                **common,
                action="CREATE",
                customer_id=customer_id,
                level=level,
                reason=reason,
                status=status,
            )

    if visible:
        with st.expander(
            "Sửa hoặc bỏ khách hàng khỏi danh sách ưu tiên"
        ):
            mapping = {
                row["id"]: row
                for row in visible
            }

            if st.session_state.get("priority_selected") not in mapping:
                st.session_state["priority_selected"] = next(
                    iter(mapping)
                )

            selected_id = st.selectbox(
                "Chọn khách hàng",
                options=list(mapping),
                key="priority_selected",
                format_func=lambda value: (
                    mapping[value]["customer_unique_id"]
                ),
            )

            selected = mapping[selected_id]

            with st.form(f"priority_edit_{selected_id}"):
                level = st.selectbox(
                    "Mức ưu tiên mới",
                    PRIORITY_LEVELS,
                    index=PRIORITY_LEVELS.index(
                        selected["level"]
                    ),
                )

                reason = st.text_area(
                    "Lý do",
                    value=selected["reason"],
                    max_chars=2000,
                )

                status = st.selectbox(
                    "Trạng thái mới",
                    STATUSES,
                    index=STATUSES.index(
                        selected["status"]
                    ),
                )

                save = st.form_submit_button(
                    "Lưu thay đổi"
                )

            if save:
                submit_priority(
                    "Đã cập nhật khách hàng ưu tiên.",
                    **common,
                    action="UPDATE",
                    priority_id=selected_id,
                    level=level,
                    reason=reason,
                    status=status,
                )

            with st.form(f"priority_delete_{selected_id}"):
                confirm = st.checkbox(
                    "Xác nhận bỏ khách hàng này "
                    "khỏi danh sách ưu tiên"
                )

                delete = st.form_submit_button(
                    "Bỏ khỏi danh sách (xóa mềm)"
                )

            if delete:
                if not confirm:
                    st.warning(
                        "Hãy đánh dấu xác nhận "
                        "trước khi xóa mềm."
                    )
                else:
                    submit_priority(
                        "Đã xóa mềm và lưu nhật ký.",
                        **common,
                        action="DELETE",
                        priority_id=selected_id,
                    )

    with st.expander(
        "Nhật ký danh sách ưu tiên — 100 thao tác gần nhất"
    ):
        logs = read_priorities(
            actor["id"],
            audit=True,
        )

        if logs:
            st.dataframe(
                logs,
                width="stretch",
                hide_index=True,
            )
        else:
            st.info(
                "Chưa có nhật ký danh sách ưu tiên."
            )


# =========================================================
# HÀM ĐƯỢC APP.PY GỌI
# =========================================================

def render_customer_care(user, customer_ids):
    customer_ids = list(customer_ids)

    try:
        check_user(user["id"])
    except PermissionError as error:
        st.error(str(error))
        return

    section = st.radio(
        "Chọn nội dung chăm sóc",
        options=[
            "Ghi chú và nhãn",
            "Khách hàng ưu tiên",
        ],
        horizontal=True,
        key="care_section",
    )

    try:
        if section == "Ghi chú và nhãn":
            render_notes(user, customer_ids)
        else:
            render_priorities(user, customer_ids)

    except PermissionError as error:
        st.error(str(error))

    except sqlite3.Error:
        st.error(
            "Không thể đọc hoặc ghi dữ liệu chăm sóc. "
            "Hãy thử lại; không xóa file database."
        )
