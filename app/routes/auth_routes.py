from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.get("/test")
def test_auth():
    return {"message": "Auth route works"}