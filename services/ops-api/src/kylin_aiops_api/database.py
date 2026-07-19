from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class NodeRow(Base):
    __tablename__ = "nodes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    hostname: Mapped[str] = mapped_column(String(255), unique=True)
    architecture: Mapped[str | None] = mapped_column(String(64))
    kylin_version: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="offline")
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ServiceRow(Base):
    __tablename__ = "services"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    service_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32))


class DependencyEdgeRow(Base):
    __tablename__ = "dependency_edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    target_service_id: Mapped[str] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    source: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IncidentRow(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    fault_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    root_node_id: Mapped[str | None] = mapped_column(ForeignKey("nodes.id"))


class EvidenceRow(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"))
    kind: Mapped[str] = mapped_column(String(32))
    summary: Mapped[str] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(Text)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DiagnosisRow(Base):
    __tablename__ = "diagnoses"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True
    )
    root_cause: Mapped[str] = mapped_column(String(128))
    summary: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float)
    propagation_path: Mapped[list[str]] = mapped_column(JSON)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON)
    recommended_steps: Mapped[list[str]] = mapped_column(JSON)
    action_candidates: Mapped[list[str]] = mapped_column(JSON)
    source: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActionRequestRow(Base):
    __tablename__ = "action_requests"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), index=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"))
    action_name: Mapped[str] = mapped_column(String(128))
    parameters: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32), index=True)
    approved_by: Mapped[str | None] = mapped_column(String(128))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ActionExecutionRow(Base):
    __tablename__ = "action_executions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    action_request_id: Mapped[str] = mapped_column(ForeignKey("action_requests.id"), unique=True)
    exit_code: Mapped[int] = mapped_column(Integer)
    stdout: Mapped[str] = mapped_column(Text, default="")
    stderr: Mapped[str] = mapped_column(Text, default="")
    health_check_passed: Mapped[bool] = mapped_column(Boolean)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvaluationRunRow(Base):
    __tablename__ = "evaluation_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    code_version: Mapped[str] = mapped_column(String(128))
    model_hash: Mapped[str] = mapped_column(String(128))
    environment: Mapped[dict[str, Any]] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TrialResultRow(Base):
    __tablename__ = "trial_results"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    evaluation_run_id: Mapped[str] = mapped_column(ForeignKey("evaluation_runs.id"), index=True)
    experiment_id: Mapped[str] = mapped_column(String(64), index=True)
    ground_truth: Mapped[str] = mapped_column(String(64))
    predicted_type: Mapped[str] = mapped_column(String(64))
    ground_truth_root: Mapped[str] = mapped_column(String(64))
    predicted_roots: Mapped[list[str]] = mapped_column(JSON)
    detected_in_seconds: Mapped[float | None] = mapped_column(Float)
    diagnosed_in_seconds: Mapped[float | None] = mapped_column(Float)
    remediation_succeeded: Mapped[bool] = mapped_column(Boolean)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    actor_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    target: Mapped[str] = mapped_column(String(255))
    request_id: Mapped[str] = mapped_column(String(64))
    details: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
