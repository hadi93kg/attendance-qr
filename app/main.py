# app/main.py
import os
from fastapi import FastAPI, Request, Depends, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, engine, Base
from app.models import User, Attendance
from app.utils.qr_generator import generate_qr
from datetime import datetime

# --- Create tables ---
Base.metadata.create_all(bind=engine)

app = FastAPI(title="QR Attendance System")

# --- Static & Templates ---
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# --- Uploads directory ---
UPLOAD_DIR = "app/static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- BASE URL ---
PORT = int(os.environ.get("PORT", 10000))
BASE_URL = os.getenv("BASE_URL", f"http://127.0.0.1:{PORT}")

# --- Startup: Create main QR ---
@app.on_event("startup")
def startup_qr():
    qr_path = os.path.join(UPLOAD_DIR, "attendance_qr.png")
    attendance_scan_url = f"{BASE_URL}/scan"
    if not os.path.exists(qr_path):
        generate_qr(attendance_scan_url, qr_path)
    print("Main QR ready at:", qr_path)


# --- Database dependency ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Home page with main QR ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    qr_rel = "/static/uploads/attendance_qr.png"
    return templates.TemplateResponse("index.html", {"request": request, "qr_url": qr_rel})


# --- Scan page ---
@app.get("/scan", response_class=HTMLResponse)
def scan_landing(request: Request):
    return templates.TemplateResponse("scan.html", {"request": request})


# --- Mark attendance ---
@app.get("/attendance/mark/{user_id}", response_class=HTMLResponse)
def mark_attendance(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    attendance = Attendance(user_id=user_id)
    db.add(attendance)
    db.commit()

    return templates.TemplateResponse(
        "result.html",
        {
            "request": request,
            "user": user,
            "timestamp": attendance.timestamp
        }
    )


# --- Dashboard ---
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    users = db.query(User).all()
    counts = {u.id: db.query(Attendance).filter(Attendance.user_id == u.id).count() for u in users}

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "users": users,
        "counts": counts
    })


# --- ADD USER (redirect instead of JSON) ---
@app.post("/user/add")
def add_user(name: str = Form(...), db: Session = Depends(get_db)):

    user = User(name=name)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate QR for this user
    qr_filename = f"user_{user.id}.png"
    qr_path = os.path.join(UPLOAD_DIR, qr_filename)
    user_mark_url = f"{BASE_URL}/attendance/mark/{user.id}"
    generate_qr(user_mark_url, qr_path)

    user.qr_code_path = f"/static/uploads/{qr_filename}"
    db.commit()

    # After adding → Go back to dashboard
    return RedirectResponse(url="/dashboard", status_code=303)
