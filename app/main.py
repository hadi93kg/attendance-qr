# app/main.py
import os
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from app.models import User, Attendance
from app.utils.qr_generator import generate_qr

# create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="QR Attendance System")

# static & templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# uploads dir
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# get public base url from env (set this on Render to your service URL), fallback localhost
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:10000")

# ensure attendance QR exists on startup
@app.on_event("startup")
def startup_qr():
    qr_path = os.path.join(UPLOAD_DIR, "attendance_qr.png")
    # QR leads to a landing page that instructs the user how to mark attendance:
    attendance_scan_url = f"{BASE_URL}/scan"
    if not os.path.exists(qr_path):
        generate_qr(attendance_scan_url, qr_path)
        print("QR code saved at", qr_path)
    else:
        print("QR already exists at", qr_path)

# dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# home page (shows QR)
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    qr_rel = "/static/uploads/attendance_qr.png"
    return templates.TemplateResponse("index.html", {"request": request, "qr_url": qr_rel})

# scan landing page — shows options or instructions
@app.get("/scan", response_class=HTMLResponse)
def scan_landing(request: Request):
    # Simple landing: show instructions and a small form to enter ID (or tablet scan can open specific url)
    return templates.TemplateResponse("scan.html", {"request": request})

# endpoint to mark attendance by user_id (GET so mobile scanners opening URL can trigger)
@app.get("/attendance/mark/{user_id}")
def mark_attendance_get(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    attendance = Attendance(user_id=user_id)
    db.add(attendance)
    db.commit()
    return {"message": f"Attendance marked for {user.name}"}

# dashboard
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    # create a map of counts
    counts = {u.id: db.query(Attendance).filter(Attendance.user_id == u.id).count() for u in users}
    return templates.TemplateResponse("dashboard.html", {"request": request, "users": users, "counts": counts})

# add user (simple form submission)
@app.post("/user/add")
def add_user(name: str = None, db: Session = Depends(get_db)):
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    user = User(name=name)
    db.add(user)
    db.commit()
    db.refresh(user)

    # generate QR for user that points to mark endpoint
    qr_filename = f"user_{user.id}.png"
    qr_path = os.path.join(UPLOAD_DIR, qr_filename)
    user_mark_url = f"{BASE_URL}/attendance/mark/{user.id}"
    generate_qr(user_mark_url, qr_path)
    user.qr_code_path = f"/static/uploads/{qr_filename}"
    db.commit()
    return {"message": "User added", "user_id": user.id}