from fastapi import APIRouter

router = APIRouter(prefix="/attendance", tags=["Attendance"])

@router.get("/test")
def test_att():
    return {"message": "Attendance route works"}