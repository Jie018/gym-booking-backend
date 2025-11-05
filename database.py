# import os
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# import mysql.connector
# import logging


# logging.basicConfig(level=logging.INFO)


# def get_db():
#     try:
#         conn = mysql.connector.connect(
#             host=os.getenv("DB_HOST"),
#             user=os.getenv("DB_USER"),
#             password=os.getenv("DB_PASSWORD"),
#             database=os.getenv("DB_NAME")
#         )
#         logging.info("資料庫連線成功")
#         return conn
#     except Exception as e:
#         logging.error(f"資料庫連線失敗: {e}")
#         raise

# # 讀取環境變數 DATABASE_URL，如果不存在就用本地測試資料庫
# DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Aa001!school@localhost:3306/gym_booking")

# # 建立 SQLAlchemy Engine
# engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# # 建立 Session
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# # 建立 Base
# Base = declarative_base()

# # DB Session 依賴
# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 設定 log 輸出
logging.basicConfig(level=logging.INFO)

# 嘗試從環境變數讀取 DATABASE_URL（Render 上會自動設定）
DATABASE_URL = os.getenv("DATABASE_URL")

# 如果 Render 上沒有設定 DATABASE_URL，則使用本機 MySQL（方便開發）
if not DATABASE_URL:
    DATABASE_URL = "mysql+pymysql://root:你的本機MySQL密碼@localhost:3306/gym_booking"
    logging.info("⚙️ 使用本機 MySQL 連線")
else:
    # Render 上使用 PostgreSQL 時自動套用
    if DATABASE_URL.startswith("postgres://"):
        # Render 會自動提供舊格式 postgres://，但 SQLAlchemy 需要 postgresql+psycopg2://
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg2://", 1)
    logging.info("🌐 使用 Render PostgreSQL 連線")

# 建立資料庫引擎
try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    logging.info("✅ 資料庫引擎建立成功")
except Exception as e:
    logging.error(f"❌ 無法建立資料庫引擎: {e}")
    raise

# 建立 Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立 Base
Base = declarative_base()

# 測試資料庫連線
def test_connection():
    try:
        with engine.connect() as conn:
            logging.info("✅ 成功連線到資料庫")
    except Exception as e:
        logging.error(f"❌ 資料庫連線失敗: {e}")

# FastAPI 依賴：取得 DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
