# router/public_slot.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, time
from typing import List
from database import get_db
from models import AvailableSlot

router = APIRouter(prefix="/api", tags=["public"])

@router.get("/available_slots")
def get_available_slots(
    venue_id: int = Query(..., ge=1),
    date: str = Query(..., description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    # 1) 驗證並轉換日期
    try:
        q_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式錯誤，需 YYYY-MM-DD")

    # 2) 組出完整的一天範圍（DATETIME）
    start_of_day = datetime.combine(q_date, time.min)  # 00:00:00
    end_of_day   = datetime.combine(q_date, time.max)  # 23:59:59.999999

    print(f"🔍 venue_id={venue_id}, start={start_of_day}, end={end_of_day}")

    # 3) 依照 DATETIME 欄位做查詢
    slots = (
        db.query(AvailableSlot)
        .filter(
            AvailableSlot.venue_id == venue_id,
            AvailableSlot.start_time >= start_of_day,
            AvailableSlot.end_time <= end_of_day,
        )
        .order_by(AvailableSlot.start_time.asc())
        .all()
    )

    # 4) 轉成前端期待的回傳格式（秒數）
    def to_seconds(dt: datetime) -> int:
        return dt.hour * 3600 + dt.minute * 60 + dt.second

    return [
        {
            "id": s.id,
            "start_time": to_seconds(s.start_time),  # e.g. 17:00:00 -> 61200
            "end_time": to_seconds(s.end_time),      # e.g. 18:00:00 -> 64800
        }
        for s in slots
    ]
