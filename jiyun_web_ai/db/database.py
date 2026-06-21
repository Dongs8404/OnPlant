import sqlite3
from datetime import datetime
import hashlib

DB_PATH = "db/on_plant.db"


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            soil INTEGER,
            temperature INTEGER,
            humidity INTEGER,
            light INTEGER,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS plant_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mood TEXT,
            message TEXT,
            image TEXT,
            status_list TEXT,
            action_list TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS chat_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_message TEXT,
            ai_response TEXT,
            created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            email TEXT,
            created_at TEXT
        )
    """)

    try:
        cur.execute("ALTER TABLE users ADD COLUMN email TEXT")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS board_posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            content TEXT,
            author TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    try:
        cur.execute("ALTER TABLE board_posts ADD COLUMN views INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE board_posts ADD COLUMN likes INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE board_posts ADD COLUMN is_notice INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        CREATE TABLE IF NOT EXISTS board_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER,
            author TEXT,
            content TEXT,
            created_at TEXT,
            FOREIGN KEY(post_id) REFERENCES board_posts(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def save_sensor_data(sensor):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO sensor_data
        (soil, temperature, humidity, light, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        sensor["soil"],
        sensor["temperature"],
        sensor["humidity"],
        sensor["light"],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def save_plant_status(result):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    action_text_list = []

    for action in result["action_list"]:
        if isinstance(action, dict):
            action_text_list.append(action["text"])
        else:
            action_text_list.append(action)

    cur.execute("""
        INSERT INTO plant_status
        (mood, message, image, status_list, action_list, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        result["mood"],
        result["message"],
        result["image"],
        ", ".join(result["status_list"]),
        ", ".join(action_text_list),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()
def get_recent_sensor_data(limit=10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, soil, temperature, humidity, light, created_at
        FROM sensor_data
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return rows

def save_chat_log(user_message, ai_response):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO chat_log
        (user_message, ai_response, created_at)
        VALUES (?, ?, ?)
    """, (
        user_message,
        ai_response,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()

def get_recent_chat_logs(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT user_message, ai_response, created_at
        FROM chat_log
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))

    rows = cur.fetchall()
    conn.close()

    return rows[::-1]

def get_recent_chat_logs(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT user_message, ai_response, created_at
        FROM chat_log
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

    return rows


def create_user(username, password, email=None):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
            INSERT INTO users
            (username, password_hash, email, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            username,
            hash_password(password),
            email,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def verify_user_recovery_info(username, email):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT username
        FROM users
        WHERE username = ? AND email = ?
    """, (username, email))

    row = cur.fetchone()
    conn.close()
    return row is not None


def verify_user_and_reset_password(username, email, original_password, new_password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT username
        FROM users
        WHERE username = ? AND email = ? AND password_hash = ?
    """, (username, email, hash_password(original_password)))

    row = cur.fetchone()

    if not row:
        conn.close()
        return False

    cur.execute("""
        UPDATE users
        SET password_hash = ?
        WHERE username = ?
    """, (hash_password(new_password), username))

    conn.commit()
    conn.close()
    return True


def authenticate_user(username, password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT username
        FROM users
        WHERE username = ? AND password_hash = ?
    """, (username, hash_password(password)))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


def get_usernames_by_password(password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT username
        FROM users
        WHERE password_hash = ?
    """, (hash_password(password),))

    rows = cur.fetchall()
    conn.close()

    return [row[0] for row in rows]


def reset_user_password(username, new_password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        UPDATE users
        SET password_hash = ?
        WHERE username = ?
    """, (hash_password(new_password), username))

    conn.commit()
    updated = cur.rowcount > 0
    conn.close()

    return updated


def get_board_posts():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT p.id, p.title, p.author, p.created_at, p.updated_at, COALESCE(p.views, 0) AS views,
               (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
               COALESCE(p.likes, 0) AS likes, COALESCE(p.is_notice, 0) AS is_notice
        FROM board_posts p
        ORDER BY p.is_notice DESC, p.id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return rows


def get_board_post(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Automatically increment views when post is fetched
    try:
        cur.execute("""
            UPDATE board_posts
            SET views = COALESCE(views, 0) + 1
            WHERE id = ?
        """, (post_id,))
        conn.commit()
    except sqlite3.OperationalError:
        pass

    cur.execute("""
        SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, COALESCE(p.views, 0) AS views,
               (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
               COALESCE(p.likes, 0) AS likes, COALESCE(p.is_notice, 0) AS is_notice
        FROM board_posts p
        WHERE p.id = ?
    """, (post_id,))

    row = cur.fetchone()
    conn.close()

    return row


def create_board_post(title, content, author, is_notice=0):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO board_posts
        (title, content, author, created_at, updated_at, is_notice)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, content, author, now, now, is_notice))

    conn.commit()
    conn.close()


def update_board_post(post_id, title, content, is_notice=0):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        UPDATE board_posts
        SET title = ?, content = ?, updated_at = ?, is_notice = ?
        WHERE id = ?
    """, (
        title,
        content,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        is_notice,
        post_id
    ))

    conn.commit()
    conn.close()


def delete_board_post(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM board_posts
        WHERE id = ?
    """, (post_id,))

    conn.commit()
    conn.close()


def create_board_comment(post_id, author, content):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        INSERT INTO board_comments
        (post_id, author, content, created_at)
        VALUES (?, ?, ?, ?)
    """, (post_id, author, content, now))

    conn.commit()
    conn.close()


def get_board_comments(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, post_id, author, content, created_at
        FROM board_comments
        WHERE post_id = ?
        ORDER BY id ASC
    """, (post_id,))

    rows = cur.fetchall()
    conn.close()

    return rows


def increment_post_likes(post_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("""
            UPDATE board_posts
            SET likes = COALESCE(likes, 0) + 1
            WHERE id = ?
        """, (post_id,))
        conn.commit()
    except sqlite3.OperationalError:
        pass
    finally:
        conn.close()
