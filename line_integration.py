# # line_integration.py
# import os
# from fastapi import APIRouter, Request, Depends
# from sqlalchemy.orm import Session
# from database import get_db
# from models import Venue, AvailableSlot
# from linebot import LineBotApi, WebhookHandler
# from linebot.exceptions import InvalidSignatureError
# from linebot.models import MessageEvent, TextMessage, TextSendMessage
# from datetime import datetime
# from dotenv import load_dotenv

# # 載入環境變數
# load_dotenv()

# router = APIRouter()

# # LINE Bot 設定 (建議放 .env)
# LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
# LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

# line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
# handler = WebhookHandler(LINE_CHANNEL_SECRET)


# # ---------------------------
# # LINE Webhook
# # ---------------------------
# @router.post("/callback")
# async def callback(request: Request):
#     signature = request.headers.get("X-Line-Signature", "")
#     body = await request.body()
#     try:
#         handler.handle(body.decode("utf-8"), signature)
#     except InvalidSignatureError:
#         return {"status": "invalid signature"}
#     return "OK"


# # ---------------------------
# # 使用者文字訊息處理
# # ---------------------------
# @handler.add(MessageEvent, message=TextMessage)
# def handle_message(event: MessageEvent):
#     text = event.message.text.strip().lower()

#     # 查詢剩餘可預約時段
#     if "剩餘時段" in text or "可預約時段" in text:
#         db: Session = next(get_db())  # 取得資料庫 session
#         now = datetime.now()
#         slots_info = []

#         # 查所有場地
#         venues = db.query(Venue).all()
#         for v in venues:
#             available_slots = (
#                 db.query(AvailableSlot)
#                 .filter(
#                     AvailableSlot.venue_id == v.id,
#                     AvailableSlot.start_time >= now
#                 )
#                 .order_by(AvailableSlot.start_time)
#                 .all()
#             )
#             if available_slots:
#                 slot_text = ", ".join(
#                     [f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}" for s in available_slots]
#                 )
#                 slots_info.append(f"{v.name}: {slot_text}")
#             else:
#                 slots_info.append(f"{v.name}: 無可預約時段")

#         reply_text = "\n".join(slots_info)
#         line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

#     # 其他文字回覆
#     else:
#         line_bot_api.reply_message(
#             event.reply_token,
#             TextSendMessage(text="請使用下方選單或輸入「剩餘時段」查詢可預約時段")
#         )
# line_integration.py
import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse
import psycopg2
import psycopg2.extras
from linebot import LineBotApi, WebhookParser
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime

router = APIRouter()

# ---------- 從環境變數讀設定 ----------
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

if not (LINE_CHANNEL_SECRET and LINE_CHANNEL_ACCESS_TOKEN):
    raise RuntimeError("請先設定 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

# ---------- DB helper ----------
def get_db_connection():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

def format_time(dt):
    if isinstance(dt, datetime):
        return dt.strftime("%H:%M")
    return str(dt)

# ---------- Helper functions ----------
def get_open_venues_text():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, name, capacity FROM venues ORDER BY id;")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return "目前沒有開放的場地。"
    lines = ["📌 目前開放的場地："]
    for r in rows:
        lines.append(f"• {r['name']}（容量 {r['capacity']} 人）")
    return "\n".join(lines)

def get_all_slots_text():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT v.id AS venue_id, v.name AS venue_name, s.start_time, s.end_time
        FROM available_slots s
        JOIN venues v ON s.venue_id = v.id
        ORDER BY v.id, s.start_time;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return "目前沒有可預約時段。"
    lines = ["📅 可預約時段總表："]
    current_venue = None
    for r in rows:
        if r["venue_name"] != current_venue:
            current_venue = r["venue_name"]
            lines.append(f"\n🏟 {current_venue}")
        lines.append(f"• {format_time(r['start_time'])} ～ {format_time(r['end_time'])}")
    return "\n".join(lines)

def get_slots_text_for_venue(venue_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT name FROM venues WHERE id = %s;", (venue_id,))
    v = cur.fetchone()
    if not v:
        cur.close()
        conn.close()
        return "查無該場地。"
    venue_name = v["name"]
    cur.execute("""
        SELECT start_time, end_time
        FROM available_slots
        WHERE venue_id = %s
        ORDER BY start_time;
    """, (venue_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if not rows:
        return f"🏟 {venue_name}\n目前沒有可預約時段。"
    lines = [f"🏟 {venue_name} - 可預約時段："]
    for r in rows:
        lines.append(f"• {format_time(r['start_time'])} ～ {format_time(r['end_time'])}")
    return "\n".join(lines)

# ---------- LINE webhook ----------
@router.post("/callback", response_class=PlainTextResponse)
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature") or request.headers.get("X-Line-Signature")
    if signature is None:
        raise HTTPException(status_code=400, detail="Missing X-Line-Signature header")
    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    for event in events:
        if event.type == "message" and isinstance(event.message, TextMessage):
            user_text = event.message.text.strip()
            reply_text = "請使用下方選單快速查詢：可預約時段 / 目前有開放的場地"

            if user_text == "可預約時段":
                reply_text = get_all_slots_text()
            elif user_text == "目前有開放的場地嗎":
                reply_text = get_open_venues_text()
            elif user_text.startswith("available:"):
                try:
                    venue_id = int(user_text.split(":")[1])
                    reply_text = get_slots_text_for_venue(venue_id)
                except:
                    reply_text = "參數格式錯誤，請傳 available:<venue_id>"
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
            except Exception as e:
                print("LINE reply error:", e)
    return "OK"

# ---------- health check ----------
@router.get("/health")
def health():
    return {"status": "ok"}
