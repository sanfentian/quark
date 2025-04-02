import psycopg2
from psycopg2 import sql


class PGDatabase:
    def __init__(self):
        self.conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="Xiyou_00",
            host="47.93.241.40"
        )

    def fetch_files(self, file_name) -> bool:
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT file_name FROM all_file 
                WHERE file_name = %s
            """, (file_name,))
            return not bool(cur.fetchone())

    def insert_files(self, file_id, file_name, file_type, share_link):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO all_file 
                VALUES (%s, %s, %s, %s)
            """, (file_id, file_name, file_type, share_link))
            self.conn.commit()

    def update_files(self, file_id, file_name):
        with self.conn.cursor() as cur:
            cur.execute("""
                UPDATE all_file 
                SET file_id = %s 
                WHERE file_name = %s
            """, (file_id, file_name))
            self.conn.commit()
