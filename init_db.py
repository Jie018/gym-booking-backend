from database import engine, Base
from router import users
from models import Base


# 建立資料庫表格
Base.metadata.create_all(bind=engine)

