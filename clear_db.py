import sqlite3
import os

db_path = 'pybo.db'

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # alembic_version 테이블 초기화
        cursor.execute('DELETE FROM alembic_version')
        
        # 테이블 확인
        cursor.execute("SELECT * FROM alembic_version")
        result = cursor.fetchall()
        print(f"Cleared alembic_version: {result}")
        
        conn.commit()
        conn.close()
        print("Successfully cleared migration history")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Database file not found")
