import re, os, mysql.connector
import logging  # ⬅️ 加入 logging
from fastapi import APIRouter, HTTPException, Form
import mysql.connector
from passlib.context import CryptContext
from database import get_db


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
    if not re.search(r"[A-Z]", password):  # 至少一個大寫
        return False
    if not re.search(r"[a-z]", password):  # 至少一個小寫
        return False
    if not re.search(r"[0-9]", password):  # 至少一個數字
        return False
    if not password.isalnum():  # 僅限英數字
        return False
    return True

# 資料庫連線函式
# def get_db():
#     return mysql.connector.connect(
#         host=os.getenv("DB_HOST", "localhost"),
#         user=os.getenv("DB_USER", "root"),
#         password=os.getenv("DB_PASSWORD", "Aa001!school"),
#         database=os.getenv("DB_NAME", "gym_booking")
#     )
# def get_db():
#     return mysql.connector.connect(
#         host=os.getenv("DB_HOST"),
#         user=os.getenv("DB_USER"),
#         password=os.getenv("DB_PASSWORD"),
#         database=os.getenv("DB_NAME")
#     )
    
# 查詢所有使用者
@router.get("/users", operation_id="get_all_users")
def get_users():
    logging.info("正在查詢所有使用者")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username FROM users")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    logging.info(f"共查詢到 {len(result)} 筆使用者資料")
    return result

# 使用者登入
@router.post("/login", operation_id="user_login")
def login(username: str = Form(...), password: str = Form(...)):
    logging.info(f"登入請求：username={username}")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()

    if not user:
        logging.warning(f"登入失敗：使用者 {username} 不存在")
        cursor.close()
        conn.close()
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    db_password = user["password"]

    # 如果密碼不是 bcrypt 開頭，進行轉換
    if not db_password.startswith("$2"):
        logging.warning(f"使用者 {username} 密碼不是加密格式，進行轉換")
        new_hashed = pwd_context.hash(db_password)
        update_cursor = conn.cursor()
        update_cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_hashed, username))
        conn.commit()
        update_cursor.close()
        db_password = new_hashed

    if not pwd_context.verify(password, db_password):
        logging.warning(f"使用者 {username} 登入失敗：密碼錯誤")
        cursor.close()
        conn.close()
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    logging.info(f"使用者 {username} 登入成功")
    cursor.close()
    conn.close()
    return {
        "message": f"登入成功，歡迎 {username}！",
        "user_id": user["id"],
        "username": username
    }

# 註冊帳號
@router.post("/register", operation_id="user_register")
def register(username: str = Form(...), password: str = Form(...), email: str = Form(...)):
    logging.info(f"註冊請求：username={username}, email={email}")

    if not is_valid_password(password):
        logging.warning("密碼格式錯誤")
        raise HTTPException(status_code=400, detail="密碼格式錯誤，需包含大小寫英文與數字，且長度至少8位")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cursor.fetchone():
        logging.warning(f"註冊失敗：帳號 {username} 已存在")
        cursor.close()
        conn.close()
        raise HTTPException(status_code=400, detail="帳號已存在")

    hashed_password = pwd_context.hash(password)
    cursor.execute(
        "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
        (username, hashed_password, email)
    )
    conn.commit()
    cursor.close()
    conn.close()
    logging.info(f"使用者 {username} 註冊成功")
    return {"message": "註冊成功"}

# 檢查帳號是否存在
@router.get("/check_username", operation_id="check_username_exists")
def check_username(username: str):
    logging.info(f"檢查帳號是否存在：{username}")
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    cursor.close()
    conn.close()
    exists = bool(user)
    logging.info(f"帳號 {username} 是否存在：{exists}")
    return {"exists": exists}
