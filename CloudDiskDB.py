import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
from datetime import datetime


class CloudDiskDB:
    def __init__(self, dbname, user, password, host='localhost'):
        self.conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            cursor_factory=DictCursor  # 返回字典形式的结果
        )


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.close()

    def _execute(self, query, params=None):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            if cur.description:  # 如果有返回结果
                return cur.fetchall()
            self.conn.commit()