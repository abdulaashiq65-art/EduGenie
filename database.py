import sqlite3
import hashlib
from datetime import datetime


DATABASE_NAME = "edugenie.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_connection():

    conn = sqlite3.connect(
        DATABASE_NAME
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# PASSWORD HASH
# =========================================================

def hash_password(password):

    return hashlib.sha256(
        password.encode("utf-8")
    ).hexdigest()


# =========================================================
# CREATE TABLES
# =========================================================

def create_tables():

    conn = get_connection()
    cursor = conn.cursor()

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            created_at TEXT NOT NULL

        )
        """
    )

    # -----------------------------------------------------
    # CONVERSATIONS
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            user_id INTEGER NOT NULL,

            title TEXT DEFAULT 'New Chat',

            created_at TEXT NOT NULL,

            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE

        )
        """
    )

    # -----------------------------------------------------
    # MESSAGES
    # -----------------------------------------------------

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            conversation_id INTEGER NOT NULL,

            role TEXT NOT NULL,

            content TEXT NOT NULL,

            created_at TEXT NOT NULL,

            FOREIGN KEY (conversation_id)
                REFERENCES conversations(id)
                ON DELETE CASCADE

        )
        """
    )

    conn.commit()
    conn.close()


# =========================================================
# CREATE USER
# =========================================================

def create_user(
    username,
    password
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users
            (
                username,
                password,
                created_at
            )

            VALUES (?, ?, ?)
            """,
            (
                username,
                hash_password(password),
                datetime.now().isoformat()
            )
        )

        conn.commit()

        user_id = cursor.lastrowid

        return user_id

    except sqlite3.IntegrityError:

        return None

    finally:

        conn.close()


# =========================================================
# AUTHENTICATE USER
# =========================================================

def authenticate_user(
    username,
    password
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *

        FROM users

        WHERE username = ?

        AND password = ?
        """,
        (
            username,
            hash_password(password)
        )
    )

    user = cursor.fetchone()

    conn.close()

    if user:

        return dict(user)

    return None


# =========================================================
# CREATE CONVERSATION
# =========================================================

def create_conversation(
    user_id
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO conversations
        (
            user_id,
            title,
            created_at
        )

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            "New Chat",
            datetime.now().isoformat()
        )
    )

    conn.commit()

    conversation_id = cursor.lastrowid

    conn.close()

    return conversation_id


# =========================================================
# SAVE MESSAGE
# =========================================================

def save_message(
    conversation_id,
    role,
    content
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO messages
        (
            conversation_id,
            role,
            content,
            created_at
        )

        VALUES (?, ?, ?, ?)
        """,
        (
            conversation_id,
            role,
            content,
            datetime.now().isoformat()
        )
    )

    conn.commit()

    conn.close()


# =========================================================
# GET MESSAGES
# =========================================================

def get_messages(
    conversation_id
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            conversation_id,
            role,
            content,
            created_at

        FROM messages

        WHERE conversation_id = ?

        ORDER BY id ASC
        """,
        (
            conversation_id,
        )
    )

    messages = cursor.fetchall()

    conn.close()

    return [
        dict(message)
        for message in messages
    ]


# =========================================================
# GET CONVERSATIONS
# =========================================================

def get_conversations(
    user_id
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            id,
            user_id,
            title,
            created_at

        FROM conversations

        WHERE user_id = ?

        ORDER BY id DESC
        """,
        (
            user_id,
        )
    )

    conversations = cursor.fetchall()

    conn.close()

    return [
        dict(conversation)
        for conversation in conversations
    ]


# =========================================================
# UPDATE CONVERSATION TITLE
# =========================================================

def update_conversation_title(
    conversation_id,
    title
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE conversations

        SET title = ?

        WHERE id = ?
        """,
        (
            title,
            conversation_id
        )
    )

    conn.commit()

    conn.close()


# =========================================================
# CHECK CONVERSATION OWNERSHIP
# =========================================================

def conversation_belongs_to_user(
    conversation_id,
    user_id
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id

        FROM conversations

        WHERE id = ?

        AND user_id = ?
        """,
        (
            conversation_id,
            user_id
        )
    )

    result = cursor.fetchone()

    conn.close()

    return result is not None


# =========================================================
# DELETE CONVERSATION
# =========================================================

def delete_conversation(
    conversation_id,
    user_id
):

    conn = get_connection()
    cursor = conn.cursor()

    try:

        # Check ownership first
        cursor.execute(
            """
            SELECT id

            FROM conversations

            WHERE id = ?

            AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        )

        conversation = cursor.fetchone()

        if conversation is None:

            return False

        # Delete messages
        cursor.execute(
            """
            DELETE FROM messages

            WHERE conversation_id = ?
            """,
            (
                conversation_id,
            )
        )

        # Delete conversation
        cursor.execute(
            """
            DELETE FROM conversations

            WHERE id = ?

            AND user_id = ?
            """,
            (
                conversation_id,
                user_id
            )
        )

        conn.commit()

        return True

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()
def delete_conversation(conversation_id, user_id):
    conn = get_connection()
    cursor = conn.cursor()

    # Make sure the conversation belongs to this user
    cursor.execute(
        """
        SELECT id
        FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, user_id)
    )

    conversation = cursor.fetchone()

    if conversation is None:
        conn.close()
        return False

    # Delete messages first
    cursor.execute(
        """
        DELETE FROM messages
        WHERE conversation_id = ?
        """,
        (conversation_id,)
    )

    # Delete conversation
    cursor.execute(
        """
        DELETE FROM conversations
        WHERE id = ? AND user_id = ?
        """,
        (conversation_id, user_id)
    )

    conn.commit()
    conn.close()

    return True