from contextlib import closing
from pathlib import Path
import sqlite3
import os

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = Path(os.environ.get('OLIST_DB_PATH',BASE_DIR / 'storage' / 'olist_app.db')).resolve()
DB_DIR = DB_PATH.parent

password_hasher = PasswordHasher()


def connect_db():
    DB_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )
    connection.row_factory = sqlite3.Row

    return connection


def init_db():
    with closing(connect_db()) as connection:
        with connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL
                        CHECK(role IN ('Admin', 'Analyst')),
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL
                        DEFAULT CURRENT_TIMESTAMP
                )
                """
            )


def create_user(username, password, role):
    username = username.strip().lower()

    if not username:
        raise ValueError("Tên đăng nhập không được để trống.")

    if len(password) < 10:
        raise ValueError("Mật khẩu cần ít nhất 10 ký tự.")

    if role not in ("Admin", "Analyst"):
        raise ValueError("Vai trò không hợp lệ.")

    password_hash = password_hasher.hash(password)

    with closing(connect_db()) as connection:
        with connection:
            connection.execute(
                """
                INSERT INTO users (
                    username,
                    password_hash,
                    role
                )
                VALUES (?, ?, ?)
                """,
                (username, password_hash, role),
            )


def authenticate(username, password):
    username = username.strip().lower()

    with closing(connect_db()) as connection:
        row = connection.execute(
            """
            SELECT id, username, password_hash, role, is_active
            FROM users
            WHERE username = ?
            """,
            (username,),
        ).fetchone()

    if row is None or not row["is_active"]:
        return None

    try:
        password_hasher.verify(
            row["password_hash"],
            password,
        )
    except (VerificationError, InvalidHashError):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "role": row["role"],
    }


def get_active_user(user_id):
    with closing(connect_db()) as connection:
        row = connection.execute(
            """
            SELECT id, username, role
            FROM users
            WHERE id = ? AND is_active = 1
            """,
            (user_id,),
        ).fetchone()

    return dict(row) if row else None


def list_users_for_admin(actor_id):
    # Kiểm tra quyền tại hàm xử lý dữ liệu.
    actor = get_active_user(actor_id)

    if actor is None or actor["role"] != "Admin":
        raise PermissionError("Chức năng chỉ dành cho Admin.")

    with closing(connect_db()) as connection:
        rows = connection.execute(
            """
            SELECT username, role, is_active, created_at
            FROM users
            ORDER BY id
            """
        ).fetchall()

    # Không trả về mật khẩu đã băm.
    return [dict(row) for row in rows]


def setup_accounts():
    from getpass import getpass

    init_db()

    print("Tạo hai tài khoản cho website.")
    print("Khi nhập mật khẩu, terminal không hiện ký tự.")

    for username, role in [
        ("admin", "Admin"),
        ("analyst", "Analyst"),
    ]:
        with closing(connect_db()) as connection:
            existing = connection.execute(
                "SELECT id FROM users WHERE username = ?",
                (username,),
            ).fetchone()

        if existing:
            print(f"Tài khoản {username} đã có, giữ nguyên.")
            continue

        while True:
            print(f"\nTạo tài khoản: {username} ({role})")

            password = getpass("Mật khẩu, ít nhất 10 ký tự: ")
            confirmation = getpass("Nhập lại mật khẩu: ")

            if password != confirmation:
                print("Hai mật khẩu không giống nhau. Nhập lại.")
                continue

            try:
                create_user(username, password, role)
            except ValueError as error:
                print(error)
                continue

            print(f"Đã tạo tài khoản {username}.")
            break

    print(f"\nHoàn tất. Database được lưu tại: {DB_PATH}")


if __name__ == "__main__":
    setup_accounts()
