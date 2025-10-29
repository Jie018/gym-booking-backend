# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base

# SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:Aa001!school@localhost:3306/gym_booking"

# engine = create_engine(SQLALCHEMY_DATABASE_URL)

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 讀取環境變數 DATABASE_URL，如果不存在就用本地測試資料庫
DATABASE_URL = os.getenv("DATABASE_URL", "mysql+pymysql://root:Aa001!school@localhost:3306/gym_booking")

# 建立 SQLAlchemy Engine
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# 建立 Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 建立 Base
Base = declarative_base()

# DB Session 依賴
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
