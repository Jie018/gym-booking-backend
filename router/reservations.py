# # from fastapi import APIRouter, Depends, HTTPException
# # from sqlalchemy.orm import Session
# # from database import get_db
# # from pydantic import BaseModel
# # from models import Reservation, ReservationStatus
# # from typing import List

# # router = APIRouter()

# # # 查詢所有預約資料
# # @router.get("/reservations")
# # async def get_reservations(db: Session = Depends(get_db)):
# #     reservations = db.query(Reservation).all()
# #     return reservations

# # # BookingData 只保留目前送出的欄位
# # class BookingData(BaseModel):
# #     date: str
# #     people_count: int
# #     student_ids: List[str]
# #     contact_phone: str
# #     time_slots: List[str]

# # # 簡化後的 POST 預約路由
# # @router.post("/api/book")
# # async def create_reservation(data: BookingData, db: Session = Depends(get_db)):
# #     # 暫時假設 user_id 和 venue_id 固定（未來從登入 session 取得）
# #     user_id = 1
# #     venue_id = 1

# #     # 建立每個 time_slot 對應的 Reservation
# #     for slot in data.time_slots:
# #         try:
# #             start_time, end_time = slot.split("-")
# #         except ValueError:
# #             raise HTTPException(status_code=400, detail=f"無效的時間格式：{slot}")

# #         reservation = Reservation(
# #             user_id=user_id,
# #             venue_id=venue_id,
# #             start_time=start_time,
# #             end_time=end_time,
# #             status=ReservationStatus.pending
# #         )
# #         db.add(reservation)

# #     db.commit()

# #     return {"success": True, "message": "預約成功"}

# from fastapi import APIRouter, Depends, HTTPException
# from sqlalchemy.orm import Session
# from database import get_db
# from pydantic import BaseModel
# from models import Reservation, AvailableSlot, ReservationStatus
# from typing import List

# router = APIRouter()

# # ✅ 這是簡化後的預約資料模型
# class BookingData(BaseModel):
#     venue_id: int
#     contact_phone: str


# @router.post("/api/book")
# async def create_reservation(data: BookingData, db: Session = Depends(get_db)):
#     print("✅ 成功接收到資料：", data.dict())  # 建議用 data.dict() 比較可讀
#     user_id = 1  # ✅ 寫死的 user_id，先用來測試
#     start_time = "2025-05-08 17:00:00"
#     end_time = "2025-05-08 18:00:00"

#     available_slot = db.query(AvailableSlot).filter(
#         AvailableSlot.venue_id == data.venue_id,
#         AvailableSlot.start_time <= start_time,
#         AvailableSlot.end_time >= end_time
#     ).first()

#     if not available_slot:
#         raise HTTPException(status_code=400, detail="所選時間段不可用")

#     reservation = Reservation(
#         user_id=user_id,
#         venue_id=data.venue_id,
#         start_time=start_time,
#         end_time=end_time,
#         status=ReservationStatus.pending
#     )
#     db.add(reservation)
#     db.commit()
#     db.refresh(reservation)  # 這樣才能確保 reservation.id 能正確取得
#     print("✅ 已寫入資料庫 Reservation ID:", reservation.id)
#     return {"success": True, "message": "預約成功"}
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
