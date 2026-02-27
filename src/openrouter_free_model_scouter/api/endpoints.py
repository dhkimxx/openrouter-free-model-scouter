from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..services.stats_service import StatsService
from ..schemas import Summary, ModelStats, ModelHistoryPoint

router = APIRouter()

@router.get("/summary", response_model=Summary)
def get_summary(db: Session = Depends(get_db)):
    service = StatsService(db)
    return service.get_summary()

@router.get("/models", response_model=List[ModelStats])
def get_models(db: Session = Depends(get_db)):
    service = StatsService(db)
    return service.get_models_stats()

@router.get("/models/{model_id:path}/history", response_model=List[ModelHistoryPoint])
def get_model_history(model_id: str, db: Session = Depends(get_db)):
    service = StatsService(db)
    return service.get_model_history(model_id)
