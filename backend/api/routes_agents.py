from fastapi import APIRouter

router = APIRouter()

@router.post("/trigger")
def trigger_agent():
    return {"status": "triggered"}
