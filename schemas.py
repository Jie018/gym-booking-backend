# # schemas.py
# from pydantic import BaseModel

# class BookingOut(BaseModel):
#     id: int
#     venue_name: str
#     date: str
#     start_time: str
#     end_time: str
#     status: str

#     class Config:
#         orm_mode = True

from pydantic import BaseModel

class BookingOut(BaseModel):
    id: int
    venue_name: str
    date: str
    start_time: str
    end_time: str
    status: str

    class Config:
        orm_mode = True
