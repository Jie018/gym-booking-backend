from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum, TIMESTAMP
from sqlalchemy.orm import relationship
from database import Base
import enum
from sqlalchemy.sql import func




class BookingStatus(str, enum.Enum):
    pending = "審核中"       # 審核中
    approved = "預約成功"     # 預約成功
    rejected = "預約失敗"     # 預約失敗
    cancelled = "已取消"   # 已取消


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="student")
    email = Column(String(255), unique=True, nullable=False)

    # 關聯到 Booking
    bookings = relationship("Booking", back_populates="user")

class Venue(Base):
    __tablename__ = "venues"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    bookings = relationship("Booking", back_populates="venue")
    available_slots = relationship("AvailableSlot", back_populates="venue")

    def __repr__(self):
        return f"<Venue(name={self.name}, capacity={self.capacity})>"

class AvailableSlot(Base):
    __tablename__ = "available_slots"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)

    # 與場地關聯
    venue = relationship("Venue", back_populates="available_slots")

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    venue_id = Column(Integer, ForeignKey("venues.id"), nullable=False)
    people_count = Column(Integer, nullable=False)
    contact_phone = Column(String(20), nullable=False)
    # created_at = Column(TIMESTAMP, nullable=False)  # 對應 MySQL 的 timestamp
    created_at = Column(
    TIMESTAMP,
    nullable=False,
    server_default=func.now()  # 自動用目前時間填入
)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    student_ids = Column(String(255), nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.pending, nullable=False)

    # 關聯到 User
    user = relationship("User", back_populates="bookings")
    # 關聯到 Venue
    venue = relationship("Venue", back_populates="bookings")