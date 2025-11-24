from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["Admin"])

@router.get("/test")
def test_admin():
    return {"message": "Admin route works"}