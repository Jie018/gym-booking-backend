from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, get_db
from models import Base, User
from router.users import router as users_router
from router import booking, cms, available_slots, my_reservations

# 建立資料表
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 掛載路由
app.include_router(users_router)
app.include_router(booking.router)
app.include_router(cms.router)
app.include_router(available_slots.router, prefix="/api")
app.include_router(booking.router, prefix="/api")
app.include_router(my_reservations.router, prefix="/api")


@app.get("/")
def home():
    return {"message": "Welcome to Gym Booking System"}

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email
    }
