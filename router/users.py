import re
import logging
from fastapi import APIRouter, HTTPException, Form, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from database import get_db
from models import User

# 設定 logging 格式
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 密碼格式驗證函式
def is_valid_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if len(password.encode('utf-8')) > 72:  # 新增：最大 72 bytes
        return False
    if not re.search(r"[A-Z]", password):  # 至少一個大寫
        return False
    if not re.search(r"[a-z]", password):  # 至少一個小寫
        return False
    if not re.search(r"[0-9]", password):  # 至少一個數字
        return False
    if not password.isalnum():  # 僅限英數字
        return False
    return True

# 查詢所有使用者
@router.get("/users", operation_id="get_all_users")
def get_users(db: Session = Depends(get_db)):
    logging.info("正在查詢所有使用者")
    result = db.query(User.id, User.username).all()
    logging.info(f"共查詢到 {len(result)} 筆使用者資料")
    return [{"id": u.id, "username": u.username} for u in result]

# 使用者登入
@router.post("/login", operation_id="user_login")
def login(
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    logging.info(f"登入請求：username={username}")
    user = db.query(User).filter(User.username == username).first()

    if not user:
        logging.warning(f"登入失敗：使用者 {username} 不存在")
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    db_password = user.password

    # 如果密碼不是 bcrypt 開頭，進行轉換
    if not db_password.startswith("$2"):
        logging.warning(f"使用者 {username} 密碼不是加密格式，進行轉換")
        new_hashed = pwd_context.hash(db_password)
        user.password = new_hashed
        db.commit()
        db_password = new_hashed

    if not pwd_context.verify(password, db_password):
        logging.warning(f"使用者 {username} 登入失敗：密碼錯誤")
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    logging.info(f"使用者 {username} 登入成功")
    return {
        "message": f"登入成功，歡迎 {username}！",
        "user_id": user.id,
        "username": username
    }

# 註冊帳號
@router.post("/register", operation_id="user_register")
def register(
    username: str = Form(...),
    password: str = Form(...),
    email: str = Form(...),
    db: Session = Depends(get_db)
):
    logging.info(f"註冊請求：username={username}, email={email}")

    if not is_valid_password(password):
        logging.warning("密碼格式錯誤")
        raise HTTPException(
            status_code=400,
            detail="密碼格式錯誤，需包含大小寫英文與數字，且長度至少8位"
        )

    if db.query(User).filter(User.username == username).first():
        logging.warning(f"註冊失敗：帳號 {username} 已存在")
        raise HTTPException(status_code=400, detail="帳號已存在")

    hashed_password = pwd_context.hash(password[:72])
    new_user = User(username=username, password=hashed_password, email=email)
    db.add(new_user)
    db.commit()

    logging.info(f"使用者 {username} 註冊成功")
    return {"message": "註冊成功"}

# 檢查帳號是否存在
@router.get("/check_username", operation_id="check_username_exists")
def check_username(username: str, db: Session = Depends(get_db)):
    logging.info(f"檢查帳號是否存在：{username}")
    user = db.query(User).filter(User.username == username).first()
    exists = bool(user)
    logging.info(f"帳號 {username} 是否存在：{exists}")
    return {"exists": exists}
