from fastapi import APIRouter

router = APIRouter()

@router.get("/summary")
def get_metrics_summary():
    return {"metrics": []}
