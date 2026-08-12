import os
import uuid
import secrets
from datetime import datetime, timedelta

import psycopg
from psycopg.rows import dict_row
from psycopg.errors import UniqueViolation


SESSION_DURATION_DAYS = 7


def get_connection():
    """
    Lazily read DATABASE_URL and connect only when a DB call is
    actually made. This is important on Vercel: if this raised at
    IMPORT time (module load), it would crash the entire serverless
    function for every single route -- including the homepage --
    which is exactly what causes the "This Serverless Function has
    crashed" screen.

    By failing only when a DB-backed route is called, the rest of
    the app (static pages, etc.) keeps working, and the error message
    the user sees is clear and specific instead of a generic crash.
    """

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not set. "
            "Add it in Vercel -> Project Settings -> Environment "
            "Variables (Postgres connection string), then redeploy."
        )

    return psycopg.connect(database_url, row_factory=dict_row)


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS pdfs (
                id SERIAL PRIMARY KEY,
                uuid TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                filepath TEXT NOT NULL,
                extracted_text TEXT,
                uploaded_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                created_at TEXT NOT NULL
            )
        """)


def create_user(name, email, password_hash):
    user_uuid = str(uuid.uuid4())
    created_at = datetime.now().isoformat()
    clean_email = email.lower().strip()

    try:
        with get_connection() as connection:
            row = connection.execute("""
                INSERT INTO users (uuid, name, email, password_hash, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (user_uuid, name, clean_email, password_hash, created_at)).fetchone()

            return {
                "id": row["id"],
                "uuid": user_uuid,
                "name": name,
                "email": clean_email,
                "created_at": created_at
            }

    except UniqueViolation:
        return None


def get_user_by_email(email):
    with get_connection() as connection:
        user = connection.execute("""
            SELECT * FROM users WHERE email = %s
        """, (email.lower().strip(),)).fetchone()
        return dict(user) if user else None


def get_user_by_id(user_id):
    with get_connection() as connection:
        user = connection.execute("""
            SELECT * FROM users WHERE id = %s
        """, (user_id,)).fetchone()
        return dict(user) if user else None


def create_session(user_id):
    token = secrets.token_urlsafe(32)
    created_at = datetime.now()
    expires_at = created_at + timedelta(days=SESSION_DURATION_DAYS)

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO sessions (token, user_id, created_at, expires_at)
            VALUES (%s, %s, %s, %s)
        """, (token, user_id, created_at.isoformat(), expires_at.isoformat()))

    return token, expires_at


def get_session_user(token):
    if not token:
        return None

    with get_connection() as connection:
        row = connection.execute("""
            SELECT sessions.expires_at, users.*
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = %s
        """, (token,)).fetchone()

    if not row:
        return None

    row = dict(row)
    expires_at = datetime.fromisoformat(row["expires_at"])

    if expires_at < datetime.now():
        delete_session(token)
        return None

    return row


def delete_session(token):
    with get_connection() as connection:
        connection.execute("""
            DELETE FROM sessions WHERE token = %s
        """, (token,))


def add_pdf(user_id, filename, filepath, extracted_text):
    pdf_uuid = str(uuid.uuid4())
    uploaded_at = datetime.now().isoformat()

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO pdfs
            (uuid, user_id, filename, filepath, extracted_text, uploaded_at)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (pdf_uuid, user_id, filename, filepath, extracted_text, uploaded_at))

    return pdf_uuid


def get_all_pdfs(user_id):
    with get_connection() as connection:
        pdfs = connection.execute("""
            SELECT uuid, filename, filepath, uploaded_at
            FROM pdfs
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,)).fetchall()
        return [dict(pdf) for pdf in pdfs]


def get_all_pdf_text(user_id):
    with get_connection() as connection:
        pdfs = connection.execute("""
            SELECT uuid, filename, extracted_text
            FROM pdfs
            WHERE user_id = %s
            ORDER BY id DESC
        """, (user_id,)).fetchall()
        return [dict(pdf) for pdf in pdfs]


def get_selected_pdf_text(user_id, pdf_uuids):
    if not pdf_uuids:
        return []

    placeholders = ",".join(["%s"] * len(pdf_uuids))

    with get_connection() as connection:
        pdfs = connection.execute(
            f"""
            SELECT uuid, filename, extracted_text
            FROM pdfs
            WHERE user_id = %s AND uuid IN ({placeholders})
            ORDER BY id DESC
            """,
            [user_id] + list(pdf_uuids)
        ).fetchall()
        return [dict(pdf) for pdf in pdfs]


def delete_pdf(user_id, pdf_uuid):
    with get_connection() as connection:
        pdf = connection.execute("""
            SELECT filepath
            FROM pdfs
            WHERE uuid = %s AND user_id = %s
        """, (pdf_uuid, user_id)).fetchone()

        if not pdf:
            return None

        connection.execute("""
            DELETE FROM pdfs
            WHERE uuid = %s AND user_id = %s
        """, (pdf_uuid, user_id))

        return pdf["filepath"]


def add_chat(user_id, question, answer, sources):
    created_at = datetime.now().isoformat()

    with get_connection() as connection:
        connection.execute("""
            INSERT INTO chat_history
            (user_id, question, answer, sources, created_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, question, answer, ", ".join(sources), created_at))


def get_chat_history(user_id):
    with get_connection() as connection:
        chats = connection.execute("""
            SELECT id, question, answer, sources, created_at
            FROM chat_history
            WHERE user_id = %s
            ORDER BY id ASC
        """, (user_id,)).fetchall()
        return [dict(chat) for chat in chats]


def clear_chat_history(user_id):
    with get_connection() as connection:
        connection.execute("""
            DELETE FROM chat_history WHERE user_id = %s
        """, (user_id,))