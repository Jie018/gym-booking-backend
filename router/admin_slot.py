# routers/admin_slot.py
from fastapi import APIRouter, Form, Depends
from sqlalchemy.orm import Session
from database import get_db
from available_slots import AvailableSlot

router = APIRouter(prefix="/slots", tags=["Slot Management"])

@router.post("/add")
def add_slot(
    venue_id: int = Form(...),
    start_time: str = Form(...),
    end_time: str = Form(...),
    db: Session = Depends(get_db)
):
    slot = AvailableSlot(
        venue_id=venue_id,
        start_time=start_time,
        end_time=end_time
    )
    db.add(slot)
    db.commit()
    return {"message": "時段新增成功"}
