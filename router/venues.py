from fastapi import APIRouter
from sqlalchemy.orm import relationship
router = APIRouter()

@router.get("/venues")
async def get_venues():
    return {"message": "This is the venues route"}

available_slots = relationship("AvailableSlot", back_populates="venue")