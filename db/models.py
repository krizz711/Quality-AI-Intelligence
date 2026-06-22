import datetime
import uuid

from sqlalchemy import UUID, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Measurement(Base):
    __tablename__ = "measurements"
    __table_args__ = (
        UniqueConstraint("source_event_id", "timestamp", name="uq_measurements_source_event_id_timestamp"),
    )

    # TimescaleDB hypertables require the partition column in primary keys.
    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    part_number: Mapped[str] = mapped_column(String(64))
    characteristic_name: Mapped[str] = mapped_column(String(128))
    nominal_value: Mapped[float | None] = mapped_column(Float)
    measured_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(16))
    operator_id: Mapped[str | None] = mapped_column(String(64))
    equipment_id: Mapped[str | None] = mapped_column(String(64))
    shift: Mapped[str | None] = mapped_column(String(16))
    source_event_id: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    created_by: Mapped[str] = mapped_column(String(64), default="system")


class GrrStudy(Base):
    __tablename__ = "grr_studies"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    equipment_id: Mapped[str] = mapped_column(String(64))
    characteristic_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    ev: Mapped[float | None] = mapped_column(Float)
    av: Mapped[float | None] = mapped_column(Float)
    pv: Mapped[float | None] = mapped_column(Float)
    grr_pct: Mapped[float | None] = mapped_column(Float)
    ndc: Mapped[int | None] = mapped_column(Integer)
    operator_count: Mapped[int | None] = mapped_column(Integer)
    part_count: Mapped[int | None] = mapped_column(Integer)
    acceptance_decision: Mapped[str | None] = mapped_column(String(32))
    report_path: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    review_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    created_by: Mapped[str] = mapped_column(String(64), default="system")


class QualityViolation(Base):
    __tablename__ = "quality_violations"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    part_number: Mapped[str | None] = mapped_column(String(64))
    characteristic_name: Mapped[str | None] = mapped_column(String(128))
    violation_type: Mapped[str | None] = mapped_column(String(64))
    severity: Mapped[str | None] = mapped_column(String(16))
    measured_value: Mapped[float | None] = mapped_column(Float)
    ucl: Mapped[float | None] = mapped_column(Float)
    lcl: Mapped[float | None] = mapped_column(Float)
    alert_sent: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class ReviewQueue(Base):
    __tablename__ = "review_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    study_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("grr_studies.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    assigned_to: Mapped[str | None] = mapped_column(String(64))
    due_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    decision_notes: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    actor: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128))
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(128))
    details: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))
    actor: Mapped[str | None] = mapped_column(String(128))
    user_id: Mapped[str | None] = mapped_column(String(128))
    event_type: Mapped[str] = mapped_column(String(128))
    component: Mapped[str | None] = mapped_column(String(128))
    input_hash: Mapped[str | None] = mapped_column(String(128))
    algorithm_version: Mapped[str | None] = mapped_column(String(64))
    result_summary: Mapped[dict | None] = mapped_column(JSON)
    details: Mapped[dict | None] = mapped_column("metadata", JSON)
    ip_address: Mapped[str | None] = mapped_column(String(64))


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    type: Mapped[str] = mapped_column(String(32))
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    process_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(16), default="active")
    payload: Mapped[dict | None] = mapped_column("metadata", JSON)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[str | None] = mapped_column(String(128))


class AlertFeedback(Base):
    __tablename__ = "alert_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("alerts.id"))
    is_relevant: Mapped[bool] = mapped_column(Boolean)
    category: Mapped[str | None] = mapped_column(String(64))
    notes: Mapped[str | None] = mapped_column(Text)
    submitted_by: Mapped[str] = mapped_column(String(128), default="quality-engineer")
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID | None] = mapped_column(UUID, ForeignKey("alerts.id"))
    channel: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32))
    recipient: Mapped[str | None] = mapped_column(String(256))
    response_reference: Mapped[str | None] = mapped_column(String(128))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class Gage(Base):
    """Inspection gage / fixture in the registry."""

    __tablename__ = "gages"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(200), default="Inspection gage")
    nominal: Mapped[float | None] = mapped_column(Float)
    tolerance: Mapped[float | None] = mapped_column(Float)
    calibration_due: Mapped[str | None] = mapped_column(String(32))
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class AlertRule(Base):
    """No-code routing rule: WHEN <trigger> ON <scope> THEN notify <channels>."""

    __tablename__ = "alert_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    trigger: Mapped[str] = mapped_column(String(48))
    threshold: Mapped[float | None] = mapped_column(Float)
    scope: Mapped[str] = mapped_column(String(200), default="Any process")
    channels: Mapped[list | None] = mapped_column(JSON)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )


class SystemSetting(Base):
    """Runtime config (integration credentials, LLM key) set via the admin UI.

    Secret values are stored encrypted (see core/settings_store.py).
    """

    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str | None] = mapped_column(Text)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    )
    updated_by: Mapped[str | None] = mapped_column(String(128))


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(128), unique=True)
    hashed_password: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[datetime.datetime] = mapped_column(default=lambda: datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None))


class ConversationSession(Base):
    """Persistent multi-turn chat context per user."""

    __tablename__ = "conversation_sessions"

    id: Mapped[uuid.UUID] = mapped_column(UUID, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    turns: Mapped[list | None] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )
    last_active: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
    )


__all__ = [
    "Alert",
    "AlertFeedback",
    "AuditLog",
    "AuditEvent",
    "Base",
    "ConversationSession",
    "GrrStudy",
    "Measurement",
    "NotificationDelivery",
    "QualityViolation",
    "ReviewQueue",
    "User",
]
