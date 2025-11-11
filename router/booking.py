from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import Booking, User, Venue, AvailableSlot, BookingStatus
from pydantic import BaseModel, validator
from schemas import BookingOut
from datetime import datetime
import traceback

router = APIRouter()

class BookingCreate(BaseModel):
    user_id: int
    venue_id: int
    date: str               # "YYYY-MM-DD"
    time_slots: List[str]   # ["17:00","18:00"]
    people_count: int
    contact_phone: str
    student_ids: List[str] = []

    @validator("time_slots")
    def slots_must_have_two(cls, v):
        if not isinstance(v, list) or len(v) != 2:
            raise ValueError("time_slots 需為兩個時間，例如 ['17:00','18:00']")
        return v

    @validator("student_ids", always=True)
    def ensure_student_ids(cls, v):
        return v or []

    class Config:
        orm_mode = True

# ---------------------------
# 取得使用者所有預約
# ---------------------------
@router.get("/my_bookings", response_model=List[BookingOut])
def get_my_bookings(user_id: int, db: Session = Depends(get_db)):
    bookings = db.query(Booking).filter(Booking.user_id == user_id).all()
    return bookings


@router.post("/book")
def create_booking(data: BookingCreate, db: Session = Depends(get_db)):
    try:
        # 0) 檢查 user / venue 存不存在
        if not db.query(User).filter(User.id == data.user_id).first():
            raise HTTPException(status_code=404, detail="User not found")
        if not db.query(Venue).filter(Venue.id == data.venue_id).first():
            raise HTTPException(status_code=404, detail="Venue not found")

        # 1) 解析時間字串成 datetime
        try:
            start_dt = datetime.strptime(f"{data.date} {data.time_slots[0]}:00", "%Y-%m-%d %H:%M:%S")
            end_dt   = datetime.strptime(f"{data.date} {data.time_slots[1]}:00", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            raise HTTPException(status_code=400, detail="時間格式錯誤（需 YYYY-MM-DD 與 HH:MM）")

        if end_dt <= start_dt:
            raise HTTPException(status_code=400, detail="結束時間需晚於開始時間")

        # 2) 學號數量檢查
        student_ids_clean = [s.strip() for s in data.student_ids if s.strip()]
        if len(student_ids_clean) != data.people_count:
            raise HTTPException(status_code=400, detail="學號數量需與人數一致")

        # 3) 確認在可預約時段內（AvailableSlot）
        # slot_ok = db.query(AvailableSlot).filter(
        #     AvailableSlot.venue_id == data.venue_id,
        #     AvailableSlot.start_time <= start_dt,
        #     AvailableSlot.end_time >= end_dt
        # ).first()
        # 取得時間部分
        start_time_only = start_dt.time()
        end_time_only = end_dt.time()
        slot_ok = db.query(AvailableSlot).filter(
            AvailableSlot.venue_id == data.venue_id,
            AvailableSlot.start_time <= start_time_only,
            AvailableSlot.end_time >= end_time_only
        ).first()
        if not slot_ok:
            raise HTTPException(status_code=400, detail="所選時間段不在可預約時段內")
        # 4a) 同 user 跨場地衝突檢查
        user_conflict = db.query(Booking).filter(
            Booking.user_id == data.user_id,
            Booking.start_time < end_dt,
            Booking.end_time > start_dt,
            Booking.status != BookingStatus.cancelled
        ).first()
        if user_conflict:
            raise HTTPException(status_code=409, detail="您在此時間段已經有其他場地的預約")
        # 4b) 與既有預約衝突檢查（同場地，用 Booking 表）
        conflict = db.query(Booking).filter(
            Booking.venue_id == data.venue_id,
            Booking.start_time < end_dt,
            Booking.end_time > start_dt,
            Booking.status != BookingStatus.cancelled
        ).first()
        if conflict:
            raise HTTPException(status_code=409, detail="該時段已被預約")

        # 5) 建立 booking
        new_b = Booking(
            user_id=data.user_id,
            venue_id=data.venue_id,
            start_time=start_dt,
            end_time=end_dt,
            contact_phone=data.contact_phone,
            people_count=data.people_count,
            student_ids=",".join(student_ids_clean),
            status=BookingStatus.pending
        )
        db.add(new_b)
        db.commit()
        db.refresh(new_b)

        return {
            "success": True,
            "message": "預約成功",
            "booking_id": new_b.id,
            "status": new_b.status.value
        }
    except HTTPException:
        # 已經是明確的 HTTPException，直接丟出
        raise
    except Exception as e:
        # 捕捉所有其他錯誤，方便除錯
        print("❌ 500 Error:", e)
        traceback.print_exc()  
        raise HTTPException(status_code=500, detail=str(e))
    
# ---------------------------
# 更新預約狀態（管理員用）
# ---------------------------
@router.put("/update_booking_status/{booking_id}")
def update_booking_status(booking_id: int, status: str, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    # booking.status = status
    try:
        booking.status = BookingStatus(status)
    except ValueError:
        print(f"❌ Invalid status value received: {status}")
        raise HTTPException(status_code=400, detail="Invalid status value")
        
    db.commit()
    db.refresh(booking)
    return {"status": "success", "booking": booking.id, "new_status": status}

# ---------------------------
# 刪除預約
# ---------------------------
@router.delete("/delete_booking/{booking_id}")
def delete_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()
    return {"status": "success", "deleted_booking_id": booking_id}


# ---------------------------
# 使用者取消預約
# ---------------------------
@router.put("/bookings/{booking_id}/cancel")
def cancel_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="找不到該預約")

    if booking.status == BookingStatus.cancelled:
        raise HTTPException(status_code=400, detail="此預約已被取消")

    # 更新狀態為「取消」
    booking.status = BookingStatus.cancelled
    db.commit()
    db.refresh(booking)

    return {"message": "預約已成功取消", "booking_id": booking_id, "status": booking.status.value}

# ---------------------------
# 後端管理員審核
# ---------------------------
@router.put("/bookings/{booking_id}/approve")
def approve_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="預約不存在")
    if booking.status != BookingStatus.pending:
        raise HTTPException(status_code=400, detail="此預約無法審核")
    
    booking.status = BookingStatus.approved
    db.commit()
    db.refresh(booking)

    return {"message": "預約已通過", "new_status": "已通過"}  # 回傳中文狀態


@router.put("/bookings/{booking_id}/reject")
def reject_booking(booking_id: int, db: Session = Depends(get_db)):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="預約不存在")
    if booking.status != BookingStatus.pending:
        raise HTTPException(status_code=400, detail="此預約無法拒絕")
    
    booking.status = BookingStatus.rejected
    db.commit()
    db.refresh(booking)

    return {"message": "預約已拒絕", "new_status": "已拒絕"}  # 回傳中文狀態


@router.get("/bookings/pending")
def get_pending_bookings(db: Session = Depends(get_db)):
    # 從 bookings 表抓 status = 'pending' 的資料
    pending_bookings = db.query(Booking).filter(Booking.status == BookingStatus.pending).all()
    
    result = []
    for b in pending_bookings:
        result.append({
            "booking_id": b.id,
            "username": b.user.username,      # 修正這裡
            "venue_name": b.venue.name,        # 對應 venues 表
            "start_time": b.start_time.isoformat(),
            "end_time": b.end_time.isoformat(),
            "people_count": b.people_count,
            "contact_phone": b.contact_phone,
            "student_ids": b.student_ids,             # 新增欄位
            "created_at": b.created_at.isoformat(),   # 新增欄位
            "status": b.status.value
        })
    
    return {"bookings": result}