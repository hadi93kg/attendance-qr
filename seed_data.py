# seed_data.py
from database import SessionLocal, engine, Base
from app.models import User, Attendance
from datetime import datetime

Base.metadata.create_all(bind=engine)

db = SessionLocal()
users = [User(name="Ali Rezaei"), User(name="Sara Ahmadi"), User(name="Mina Karimi")]
for u in users:
    db.add(u)
db.commit()

# optional attendance samples
db.add(Attendance(user_id=1))
db.add(Attendance(user_id=1))
db.add(Attendance(user_id=2))
db.commit()
db.close()
print("Seed data added.")