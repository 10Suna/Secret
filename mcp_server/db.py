import os
import pymysql
import pymysql.cursors

DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "swiftrail_db"),
    "cursorclass": pymysql.cursors.DictCursor,
}


def get_connection():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.MySQLError as e:
        raise RuntimeError(f"Database connection failed: {e}")
