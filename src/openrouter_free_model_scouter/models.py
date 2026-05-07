from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from .database import Base


class Run(Base):
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Stored as UTC ISO-8601 text; clients render it in browser-local time.
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


class RunMetadata(Base):
    __tablename__ = "run_metadata"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, unique=True)
    scan_scope_key = Column(String, nullable=False)
    model_id_contains = Column(Text, nullable=True)
    max_models = Column(Integer, nullable=True)


class ModelEvent(Base):
    __tablename__ = "model_events"
    __table_args__ = (UniqueConstraint("fingerprint", name="uq_model_events_fingerprint"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False)
    previous_run_id = Column(Integer, ForeignKey("runs.id"), nullable=True)
    event_datetime = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    model_id = Column(String, nullable=False)
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    message = Column(Text, nullable=False)
    metadata_json = Column(Text, nullable=True)
    fingerprint = Column(String, nullable=False)
