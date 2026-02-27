from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Storing datetime as string to match existing schema: TEXT NOT NULL
    # Format: YYYY-MM-DD HH:MM:SS
    run_datetime = Column(String, nullable=False)

    healthchecks = relationship("HealthCheck", back_populates="run")

class HealthCheck(Base):
    __tablename__ = "healthchecks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    model_id = Column(String, nullable=False)
    ok = Column(Boolean, nullable=False)
    http_status = Column(Integer, nullable=True)
    error_category = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=True)

    run = relationship("Run", back_populates="healthchecks")
