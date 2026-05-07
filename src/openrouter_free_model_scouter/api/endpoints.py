from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..services.event_service import EventService
from ..services.stats_service import StatsService
from ..schemas import EventList, Summary, ModelStats, ModelHistoryPoint

router = APIRouter()

@router.get("/summary", response_model=Summary)
def get_summary(db: Session = Depends(get_db)):
    service = StatsService(db)
    return service.get_summary()

@router.get("/models", response_model=List[ModelStats])
def get_models(db: Session = Depends(get_db)):
    service = StatsService(db)
    return service.get_models_stats()

@router.get("/events", response_model=EventList)
def get_events(
    type: str = "important",
    period: str = "30d",
    limit: int = 5,
    offset: int = 0,
    model_id: str | None = None,
    db: Session = Depends(get_db),
):
    service = EventService(db)
    return service.list_events(
        event_group=type,
        period=period,
        limit=limit,
        offset=offset,
        model_id=model_id,
    )

@router.get("/models/{model_id:path}/history", response_model=List[ModelHistoryPoint])
def get_model_history(model_id: str, period: str = "1d", db: Session = Depends(get_db)):
    service = StatsService(db)
    return service.get_model_history(model_id, period=period)
