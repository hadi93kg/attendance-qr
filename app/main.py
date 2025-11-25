# app/main.py
import os
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from models import User, Attendance
from utils.qr_generator import generate_qr
from datetime import datetime

from app.models import User, Attendance
from app.utils.qr_generator import generate_qr

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QR Attendance System")

# Static & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# uploads directory
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# BASE URL (set this in Render environment variables)
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:10000")

# Ensure attendance QR exists on startup
@app.on_event("startup")
def startup_qr():
    qr_path = os.path.join(UPLOAD_DIR, "attendance_qr.png")
    attendance_scan_url = f"{BASE_URL}/scan"
    if not os.path.exists(qr_path):
        generate_qr(attendance_scan_url, qr_path, size=200)  # smaller QR
        print("QR code saved at", qr_path)
    else:
        print("QR already exists at", qr_path)

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Home page
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    qr_rel = "/static/uploads/attendance_qr.png"
    return templates.TemplateResponse("index.html", {"request": request, "qr_url": qr_rel})

# Scan landing
@app.get("/scan", response_class=HTMLResponse)
def scan_landing(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

# Mark attendance
@app.get("/attendance/mark/{user_id}", response_class=HTMLResponse)
def mark_attendance(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"message": "User not found"}
    attendance = Attendance(user_id=user_id, timestamp=datetime.now())
    db.add(attendance)
    db.commit()
    return templates.TemplateResponse("result.html", {"request": Request, "user": user, "timestamp": attendance.timestamp})

# Dashboard
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    counts = {u.id: db.query(Attendance).filter(Attendance.user_id == u.id).count() for u in users}
    return templates.TemplateResponse("dashboard.html", {"request": request, "users": users, "counts": counts})

# Add user
@app.post("/user/add")
def add_user(name: str = Form(...), db: Session = Depends(get_db)):
    user = User(name=name)
    db.add(user)
    db.commit()
    db.refresh(user)

    # generate QR
    qr_filename = f"user_{user.id}.png"
    qr_path = os.path.join(UPLOAD_DIR, qr_filename)
    user_mark_url = f"{BASE_URL}/attendance/mark/{user.id}"
    generate_qr(user_mark_url, qr_path)
    user.qr_code_path = f"/static/uploads/{qr_filename}"
    db.commit()
    return {"message": "User added", "user_id": user.id}
