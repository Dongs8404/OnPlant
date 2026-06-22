import hashlib
import os
from contextlib import contextmanager
from datetime import datetime

import pymysql
from pymysql.err import IntegrityError


DB_HOST = os.getenv("MYSQL_HOST", os.getenv("DB_HOST", "localhost"))
DB_PORT = int(os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306")))
DB_USER = os.getenv("MYSQL_USER", os.getenv("DB_USER", "root"))
DB_PASSWORD = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD", ""))
DB_NAME = os.getenv("MYSQL_DATABASE", os.getenv("DB_NAME", "on_plant"))


def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _quote_identifier(value):
    return "`" + value.replace("`", "``") + "`"


def _connect(use_database=True):
    config = {
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "charset": "utf8mb4",
        "autocommit": False,
    }
    if use_database:
        config["database"] = DB_NAME
    return pymysql.connect(**config)


@contextmanager
def _connection():
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _add_column_if_missing(cur, table_name, column_name, column_definition):
    cur.execute(
        """
        SELECT COUNT(*)
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = %s
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (DB_NAME, table_name, column_name),
    )

    if cur.fetchone()[0] == 0:
        cur.execute(
            f"ALTER TABLE {_quote_identifier(table_name)} "
            f"ADD COLUMN {_quote_identifier(column_name)} {column_definition}"
        )


def init_db():
    conn = _connect(use_database=False)
    try:
        cur = conn.cursor()
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS {_quote_identifier(DB_NAME)} "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        conn.commit()
    finally:
        conn.close()

    with _connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
           CREATE TABLE IF NOT EXISTS sensor_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                robot_id VARCHAR(50),
                light FLOAT,
                temperature FLOAT,
                humidity FLOAT,
                soil_moisture FLOAT,
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS plant_status (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mood TEXT,
                message TEXT,
                image TEXT,
                status_list TEXT,
                action_list TEXT,
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_message TEXT,
                ai_response TEXT,
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE,
                password_hash CHAR(64),
                email VARCHAR(255),
                created_at DATETIME
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS board_posts (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(255),
                content TEXT,
                author VARCHAR(255),
                created_at DATETIME,
                updated_at DATETIME,
                views INT DEFAULT 0,
                likes INT DEFAULT 0,
                is_notice TINYINT DEFAULT 0
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS board_comments (
                id INT AUTO_INCREMENT PRIMARY KEY,
                post_id INT,
                author VARCHAR(255),
                content TEXT,
                created_at DATETIME,
                CONSTRAINT fk_board_comments_post
                    FOREIGN KEY (post_id)
                    REFERENCES board_posts(id)
                    ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """
        )

        _add_column_if_missing(cur, "users", "email", "VARCHAR(255)")
        _add_column_if_missing(cur, "board_posts", "views", "INT DEFAULT 0")
        _add_column_if_missing(cur, "board_posts", "likes", "INT DEFAULT 0")
        _add_column_if_missing(cur, "board_posts", "is_notice", "TINYINT DEFAULT 0")


def save_sensor_logs(sensor):
    with _connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO sensor_logs
            (
                robot_id,
                light,
                temperature,
                humidity,
                soil_moisture,
                created_at
            )
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                sensor["robot_id"],
                sensor["light"],
                sensor["temperature"],
                sensor["humidity"],
                sensor["soil_moisture"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def save_plant_status(result):
    action_text_list = []

    for action in result["action_list"]:
        if isinstance(action, dict):
            action_text_list.append(action["text"])
        else:
            action_text_list.append(action)

    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO plant_status
            (mood, message, image, status_list, action_list, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                result["mood"],
                result["message"],
                result["image"],
                ", ".join(result["status_list"]),
                ", ".join(action_text_list),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def get_recent_sensor_logs(limit=10):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, robot_id, light, temperature, humidity, soil_moisture, created_at
            FROM sensor_logs
            ORDER BY id DESC
            LIMIT %s
            """,
            (int(limit),),
        )
        return cur.fetchall()


def save_fsm_state(
    robot_id,
    current_state,
    previous_state,
    event_name,
    duration
):
    with _connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO fsm_state
            (
                robot_id,
                current_state,
                previous_state,
                event_name,
                duration
            )
            VALUES (%s,%s,%s,%s,%s)
            """,
            (
                robot_id,
                current_state,
                previous_state,
                event_name,
                duration
            ),
        )


def save_chat_log(user_message, ai_response):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO chat_log
            (user_message, ai_response, created_at)
            VALUES (%s, %s, %s)
            """,
            (
                user_message,
                ai_response,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def get_recent_chat_logs(limit=5):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT user_message, ai_response, created_at
            FROM chat_log
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (int(limit),),
        )
        return cur.fetchall()


def create_user(username, password, email=None):
    conn = _connect()
    try:
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT INTO users
                (username, password_hash, email, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    username,
                    hash_password(password),
                    email,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            )
            conn.commit()
            return True
        except IntegrityError:
            conn.rollback()
            return False
    finally:
        conn.close()


def verify_user_recovery_info(username, email):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT username
            FROM users
            WHERE username = %s AND email = %s
            """,
            (username, email),
        )
        return cur.fetchone() is not None


def verify_user_and_reset_password(username, email, original_password, new_password):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT username
            FROM users
            WHERE username = %s AND email = %s AND password_hash = %s
            """,
            (username, email, hash_password(original_password)),
        )

        row = cur.fetchone()

        if not row:
            return False

        cur.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE username = %s
            """,
            (hash_password(new_password), username),
        )
        return True


def authenticate_user(username, password):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT username
            FROM users
            WHERE username = %s AND password_hash = %s
            """,
            (username, hash_password(password)),
        )
        row = cur.fetchone()
        return row[0] if row else None


def get_usernames_by_password(password):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT username
            FROM users
            WHERE password_hash = %s
            """,
            (hash_password(password),),
        )
        rows = cur.fetchall()
        return [row[0] for row in rows]


def reset_user_password(username, new_password):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE users
            SET password_hash = %s
            WHERE username = %s
            """,
            (hash_password(new_password), username),
        )
        return cur.rowcount > 0


def get_board_posts():
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT p.id, p.title, p.author, p.created_at, p.updated_at, COALESCE(p.views, 0) AS views,
                   (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
                   COALESCE(p.likes, 0) AS likes, COALESCE(p.is_notice, 0) AS is_notice
            FROM board_posts p
            ORDER BY p.is_notice DESC, p.id DESC
            """
        )
        return cur.fetchall()


def get_board_post(post_id):
    with _connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE board_posts
            SET views = COALESCE(views, 0) + 1
            WHERE id = %s
            """,
            (post_id,),
        )

        cur.execute(
            """
            SELECT p.id, p.title, p.content, p.author, p.created_at, p.updated_at, COALESCE(p.views, 0) AS views,
                   (SELECT COUNT(*) FROM board_comments c WHERE c.post_id = p.id) AS comment_count,
                   COALESCE(p.likes, 0) AS likes, COALESCE(p.is_notice, 0) AS is_notice
            FROM board_posts p
            WHERE p.id = %s
            """,
            (post_id,),
        )
        return cur.fetchone()


def create_board_post(title, content, author, is_notice=0):
    with _connection() as conn:
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO board_posts
            (title, content, author, created_at, updated_at, is_notice)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (title, content, author, now, now, is_notice),
        )


def update_board_post(post_id, title, content, is_notice=0):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE board_posts
            SET title = %s, content = %s, updated_at = %s, is_notice = %s
            WHERE id = %s
            """,
            (
                title,
                content,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                is_notice,
                post_id,
            ),
        )


def delete_board_post(post_id):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            DELETE FROM board_posts
            WHERE id = %s
            """,
            (post_id,),
        )


def create_board_comment(post_id, author, content):
    with _connection() as conn:
        cur = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            """
            INSERT INTO board_comments
            (post_id, author, content, created_at)
            VALUES (%s, %s, %s, %s)
            """,
            (post_id, author, content, now),
        )


def get_board_comments(post_id):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, post_id, author, content, created_at
            FROM board_comments
            WHERE post_id = %s
            ORDER BY id ASC
            """,
            (post_id,),
        )
        return cur.fetchall()


def increment_post_likes(post_id):
    with _connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE board_posts
            SET likes = COALESCE(likes, 0) + 1
            WHERE id = %s
            """,
            (post_id,),
        )
