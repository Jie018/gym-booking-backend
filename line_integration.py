# line_integration.py
import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
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
    raise RuntimeError("請先設定 LINE_CHANNEL_SECRET 與 LINE_CHANNEL_ACCESS_TOKEN 環境變數")

# LINE SDK 初始化
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
parser = WebhookParser(LINE_CHANNEL_SECRET)

# ---------- DB helper ----------
def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

def format_time(dt):
    if isinstance(dt, (str,)):
        try:
            dt_obj = datetime.fromisoformat(dt)
            return dt_obj.strftime("%H:%M")
        except Exception:
            return dt
    elif isinstance(dt, datetime):
        return dt.strftime("%H:%M")
    else:
        return str(dt)

# ---------- API: 查詢目前有開放的場地 ----------
@router.get("/api/opened_venues")
def api_opened_venues():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT id, name, capacity FROM venues ORDER BY id;")
        rows = cur.fetchall()
        venues = [{"id": r["id"], "name": r["name"], "capacity": r["capacity"]} for r in rows]
        cur.close()
        conn.close()
        return JSONResponse({"venues": venues})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- API: 查詢指定場地的可預約時段 ----------
@router.get("/api/available_slots")
def api_available_slots(venue_id: int):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute("SELECT name FROM venues WHERE id = %s;", (venue_id,))
        v = cur.fetchone()
        if not v:
            cur.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Venue not found")

        venue_name = v["name"]
        today = datetime.now()

        cur.execute("""
            SELECT s.start_time, s.end_time
            FROM available_slots s
            LEFT JOIN bookings b
              ON s.venue_id = b.venue_id
              AND s.start_time = b.start_time
            WHERE s.venue_id = %s AND s.start_time >= %s AND b.id IS NULL
            ORDER BY s.start_time;
        """, (venue_id, today))
        rows = cur.fetchall()
        slots = [{"start": format_time(r["start_time"]), "end": format_time(r["end_time"])} for r in rows]

        cur.close()
        conn.close()
        return JSONResponse({"venue": venue_name, "slots": slots})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- LINE webhook: /callback ----------
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
        if event.type == "message" and event.message.type == "text":
            user_text = event.message.text.strip()
            reply_text = "請使用下方選單快速查詢：可預約時段 / 目前有開放的場地嗎"

            if user_text == "可預約時段":
                try:
                    reply_text = get_all_slots_text()
                except Exception as e:
                    reply_text = f"查詢時發生錯誤：{e}"

            elif user_text == "目前有開放的場地嗎":
                try:
                    reply_text = get_open_venues_text()
                except Exception as e:
                    reply_text = f"查詢時發生錯誤：{e}"

            elif user_text.startswith("available:"):
                try:
                    _, vid = user_text.split(":", 1)
                    vid = int(vid)
                    reply_text = get_slots_text_for_venue(vid)
                except Exception as e:
                    reply_text = "參數格式錯誤，請傳 available:<venue_id>（例如 available:4）"

            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
            except Exception as e:
                print("LINE reply error:", e)

    return "OK"

# ---------- helper functions ----------
def get_open_venues_text():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("SELECT id, name, capacity FROM venues ORDER BY id;")
    rows = cur.fetchall()
    if not rows:
        text = "目前沒有開放的場地。"
    else:
        text_lines = ["📌 目前開放的場地："]
        for r in rows:
            text_lines.append(f"• {r['name']}（容量 {r['capacity']} 人） — 請點選下方選單查詢時段")
        text = "\n".join(text_lines)
    cur.close()
    conn.close()
    return text

def get_all_slots_text():
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    now = datetime.now()

    cur.execute("""
        SELECT s.venue_id, v.name AS venue_name, s.start_time, s.end_time
        FROM available_slots s
        JOIN venues v ON s.venue_id = v.id
        LEFT JOIN bookings b 
          ON s.venue_id = b.venue_id 
          AND s.start_time = b.start_time
        WHERE s.start_time >= %s AND b.id IS NULL
        ORDER BY v.id, s.start_time;
    """, (now,))
    
    rows = cur.fetchall()
    if not rows:
        text = "目前沒有可預約時段。"
    else:
        text_lines = ["📅 可預約時段總表："]
        current_venue = None
        for r in rows:
            if r["venue_name"] != current_venue:
                current_venue = r["venue_name"]
                text_lines.append(f"\n🏟 {current_venue}")
            text_lines.append(f" - {format_time(r['start_time'])} ～ {format_time(r['end_time'])}")
        text = "\n".join(text_lines)

    cur.close()
    conn.close()
    return text

def get_slots_text_for_venue(venue_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    now = datetime.now()

    cur.execute("SELECT name FROM venues WHERE id = %s;", (venue_id,))
    v = cur.fetchone()
    if not v:
        cur.close()
        conn.close()
        return "查無該場地。"

    venue_name = v["name"]
    cur.execute("""
        SELECT s.start_time, s.end_time
        FROM available_slots s
        LEFT JOIN bookings b
          ON s.venue_id = b.venue_id
          AND s.start_time = b.start_time
        WHERE s.venue_id = %s AND s.start_time >= %s AND b.id IS NULL
        ORDER BY s.start_time;
    """, (venue_id, now))
    rows = cur.fetchall()
    if not rows:
        text = f"🏟 {venue_name}\n目前沒有可預約時段。"
    else:
        lines = [f"🏟 {venue_name} - 可預約時段："]
        for r in rows:
            lines.append(f"• {format_time(r['start_time'])} ～ {format_time(r['end_time'])}")
        text = "\n".join(lines)

    cur.close()
    conn.close()
    return text

# ---------- health check ----------
@router.get("/health")
def health():
    return {"status": "ok"}
