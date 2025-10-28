# router/my_reservations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Booking, Venue  # 調整成你專案真實 model 名稱
from datetime import datetime
import mysql.connector

router = APIRouter(tags=["reservations"])

@router.get("/my_reservations")
def get_my_reservations(user_id: int, db: Session = Depends(get_db)):
    """
    回傳該 user 的預約紀錄（依日期遞減）。
    回傳格式：
    {
      "reservations": [
        {
          "booking_id": 1,
          "venue_id": 2,
          "venue_name": "羽球場",
          "start_time": "2025-09-26 18:00:00",
          "end_time": "2025-09-26 19:00:00",
          "status": "pending"
        }, ...
      ]
    }
    """
    # 檢查 user_id 是否存在（若你想要）
    # user = db.query(User).filter(User.id == user_id).first()
    # if not user:
    #     raise HTTPException(status_code=404, detail="User not found")

    bookings = (
        db.query(Booking)
        .filter(Booking.user_id == user_id)
        .order_by(Booking.start_time.desc())
        .all()
    )

    result = []
    for b in bookings:
        # 若你的 Booking model 已經有 venue relationship，則可用 b.venue.name
        venue_name = None
        try:
            venue_name = b.venue.name
        except Exception:
            v = db.query(Venue).filter(Venue.id == b.venue_id).first()
            venue_name = v.name if v else ""

        result.append({
            "booking_id": b.id,
            "venue_id": b.venue_id,
            "venue_name": venue_name,
            "start_time": b.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": b.end_time.strftime("%Y-%m-%d %H:%M:%S"),
            "people_count": getattr(b, "people_count", None),
            "contact_phone": getattr(b, "contact_phone", None),
            "student_ids": getattr(b, "student_ids", None),
            "status": getattr(b, "status", None).value if getattr(b, "status", None) is not None else getattr(b, "status", None)
        })

    return {"reservations": result}

@router.put("/{reservation_id}/cancel")
def cancel_reservation(reservation_id: int):
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    
    # 確認該預約存在
    cursor.execute("SELECT * FROM reservations WHERE id = %s", (reservation_id,))
    reservation = cursor.fetchone()
    if not reservation:
        raise HTTPException(status_code=404, detail="Reservation not found")

    # 更新狀態
    cursor.execute("UPDATE reservations SET status = 'cancelled' WHERE id = %s", (reservation_id,))
    conn.commit()

    return {"message": "Reservation cancelled successfully", "id": reservation_id}