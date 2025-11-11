from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from database import get_db
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from models import AvailableSlot, Booking


router = APIRouter()

def to_seconds(dt):
    return dt.hour * 3600 + dt.minute * 60 + dt.second

@router.get("/available_slots")

def available_slots(venue_id: int, date: str, db: Session = Depends(get_db)):
    try:
        # 1) 驗證日期格式
        try:
            date_obj = datetime.strptime(date.strip(), "%Y-%m-%d")
        except ValueError:
            return {"error": "日期格式錯誤，需 YYYY-MM-DD"}

        start_of_day = date_obj
        start_of_next_day = start_of_day + timedelta(days=1)

        # 2) 查 AvailableSlot
        slots = (
            db.query(AvailableSlot).filter(
                AvailableSlot.venue_id == venue_id,
                AvailableSlot.start_time >= start_of_day,
                AvailableSlot.start_time < start_of_next_day
            )
            .order_by(AvailableSlot.start_time.asc())
            .all()
        )
        print("slots:", [(s.id, s.start_time) for s in slots])

        slot_list = []
        for s in slots:
            slot_info = {
                "id": s.id,
                "venue_id": s.venue_id,
                "start_time": to_seconds(s.start_time),
                "end_time": to_seconds(s.end_time)
            }
            slot_list.append(slot_info)

        # 3) 查當日已預約時段
        booked_slots = db.query(Booking).filter(
            Booking.venue_id == venue_id,
            Booking.start_time >= start_of_day,
            Booking.start_time < start_of_next_day
        ).all()
        print("booked_slots:", [(b.id, b.start_time, b.end_time) for b in booked_slots])

        # 4) 過濾衝突
        filtered_slots = []
        for s in slot_list:
            conflict = False
            for b in booked_slots:
                if not (s["end_time"] <= to_seconds(b.start_time) or s["start_time"] >= to_seconds(b.end_time)):
                    conflict = True
                    break
            if not conflict:
                filtered_slots.append(s)

        print("filtered_slots:", filtered_slots)  # ✅ 移到這裡
        return {"slots_count": len(filtered_slots), "slots": filtered_slots}

    except Exception as e:
        return {"error": str(e)}