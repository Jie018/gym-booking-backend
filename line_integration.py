# line_integration.py
import os
from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Venue, AvailableSlot
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from datetime import datetime
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

router = APIRouter()

# LINE Bot 設定 (建議放 .env)
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)


# ---------------------------
# LINE Webhook
# ---------------------------
@router.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        return {"status": "invalid signature"}
    return "OK"


# ---------------------------
# 使用者文字訊息處理
# ---------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event: MessageEvent):
    text = event.message.text.strip().lower()

    # 查詢剩餘可預約時段
    if "剩餘時段" in text or "可預約時段" in text:
        db: Session = next(get_db())  # 取得資料庫 session
        now = datetime.now()
        slots_info = []

        # 查所有場地
        venues = db.query(Venue).all()
        for v in venues:
            available_slots = (
                db.query(AvailableSlot)
                .filter(
                    AvailableSlot.venue_id == v.id,
                    AvailableSlot.start_time >= now
                )
                .order_by(AvailableSlot.start_time)
                .all()
            )
            if available_slots:
                slot_text = ", ".join(
                    [f"{s.start_time.strftime('%H:%M')} - {s.end_time.strftime('%H:%M')}" for s in available_slots]
                )
                slots_info.append(f"{v.name}: {slot_text}")
            else:
                slots_info.append(f"{v.name}: 無可預約時段")

        reply_text = "\n".join(slots_info)
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

    # 其他文字回覆
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="請使用下方選單或輸入「剩餘時段」查詢可預約時段")
        )
