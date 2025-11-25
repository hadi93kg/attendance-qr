# app/main.py
import os
from datetime import datetime
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from app.models import User, Attendance
from app.utils.qr_generator import generate_qr

# --- create tables ---
Base.metadata.create_all(bind=engine)

# --- FastAPI app ---
app = FastAPI(title="QR Attendance System")

# --- static & templates ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- uploads dir ---
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- public base URL ---
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:10000")

# --- startup: ensure main attendance QR exists ---
@app.on_event("startup")
def startup_qr():
    qr_path = os.path.join(UPLOAD_DIR, "attendance_qr.png")
    attendance_scan_url = f"{BASE_URL}/scan"
    if not os.path.exists(qr_path):
        generate_qr(attendance_scan_url, qr_path)
    print(f"QR code saved at {qr_path}")

# --- database dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- home page ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    qr_rel = "/static/uploads/attendance_qr.png"
    return templates.TemplateResponse("index.html", {"request": request, "qr_url": qr_rel})

# --- scan landing page ---
@app.get("/scan", response_class=HTMLResponse)
def scan_landing(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})

# --- mark attendance endpoint ---
@app.get("/attendance/mark/{user_id}")
def mark_attendance_get(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    attendance = Attendance(user_id=user_id, timestamp=datetime.utcnow())
    db.add(attendance)
    db.commit()
    return JSONResponse({"message": f"Attendance marked for {user.name}", 
                         "user_id": user.id,
                         "time": attendance.timestamp.strftime("%Y-%m-%d %H:%M:%S")})

# --- dashboard ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    counts = {u.id: db.query(Attendance).filter(Attendance.user_id == u.id).count() for u in users}
    return templates.TemplateResponse("dashboard.html", {"request": request, "users": users, "counts": counts})

# --- add user ---
@app.post("/user/add")
def add_user(name: str = Form(...), db: Session = Depends(get_db)):
    user = User(name=name)
    db.add(user)
    db.commit()
    db.refresh(user)

    qr_filename = f"user_{user.id}.png"
    qr_path = os.path.join(UPLOAD_DIR, qr_filename)
    user_mark_url = f"{BASE_URL}/attendance/mark/{user.id}"
    generate_qr(user_mark_url, qr_path)

    user.qr_code_path = f"/static/uploads/{qr_filename}"
    db.commit()
    return JSONResponse({"message": "User added", "user_id": user.id, "qr_url": user.qr_code_path})
