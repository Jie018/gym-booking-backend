from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Reservation, Venue
from typing import List
from datetime import datetime

router = APIRouter(prefix="/api", tags=["reservations"])

@router.get("/my_reservations/{user_id}")
def get_my_reservations(user_id: int, db: Session = Depends(get_db)):
    reservations = (
        db.query(Reservation)
        .join(Venue, Reservation.venue_id == Venue.id)
        .filter(Reservation.user_id == user_id)
        .all()
    )

    if not reservations:
        return {"message": "目前沒有預約紀錄"}

    result = []
    for r in reservations:
        result.append({
            "id": r.id,
            "venue_name": r.venue.name,
            "start_time": r.start_time.strftime("%Y-%m-%d %H:%M"),
            "end_time": r.end_time.strftime("%Y-%m-%d %H:%M"),
            "status": r.status.value
        })
    return result
