# from fastapi import APIRouter, Form, HTTPException, Depends
# from sqlalchemy.orm import Session
# from database import get_db
# from models import Reservation, BookingStatus

# router = APIRouter(prefix="/cms", tags=["cms"])

# @router.get("/pending_reservations")
# def get_pending_reservations(db: Session = Depends(get_db)):
#     return db.query(Reservation).filter(Reservation.status == BookingStatus.pending).all()

# @router.post("/review_reservation")
# def review_reservation(
#     reservation_id: int = Form(...),
#     decision: str = Form(...),
#     db: Session = Depends(get_db)
# ):
#     if decision not in ["approved", "rejected"]:
#         raise HTTPException(status_code=400, detail="無效的審核狀態")
#     reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
#     if not reservation:
#         raise HTTPException(status_code=404, detail="預約不存在")
#     reservation.status = BookingStatus(decision)
#     db.commit()
#     return {"message": f"預約 {decision} 成功"}
from fastapi import APIRouter, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Booking, BookingStatus

router = APIRouter(prefix="/cms", tags=["cms"])

# -------------------------------
# GET /pending_bookings - 取得待審核預約
# -------------------------------
@router.get("/pending_bookings")
def get_pending_bookings(db: Session = Depends(get_db)):
    # 直接用字串比對，不需要 BookingStatus
    return db.query(Booking).filter(Booking.status == BookingStatus.pending).all()

# -------------------------------
# POST /review_booking - 審核預約
# -------------------------------
@router.post("/review_booking")
def review_booking(
    booking_id: int = Form(...),
    decision: str = Form(...),  # 前端會送 "approved" 或 "rejected"
    db: Session = Depends(get_db)
):
    # 確保 decision 合法
    if decision not in [BookingStatus.approved, BookingStatus.rejected]:
        raise HTTPException(status_code=400, detail="無效的審核狀態")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="預約不存在")

    # 直接存字串
    booking.status = decision
    db.commit()
    db.refresh(booking)

    return {"message": f"預約 {decision} 成功", "booking_id": booking.id}
