"""将数据库行转换为稳定 API 结构，序列化过程不得发起数据库查询。"""

from datetime import datetime
from typing import Any

from .database import DiagnosisRow, EvidenceRow, IncidentRow


def datetime_text(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def serialize_incident(
    row: IncidentRow,
    evidence_rows: list[EvidenceRow],
    diagnosis: DiagnosisRow | None,
) -> dict[str, Any]:
    """使用调用方已批量加载的数据构造事件响应，避免隐式 N+1 查询。"""

    evidence = [
        {
            "id": item.id,
            "kind": item.kind,
            "node_id": item.node_id,
            "summary": item.summary,
            "observed_at": datetime_text(item.observed_at),
        }
        for item in evidence_rows
    ]
    diagnosis_data = {
        "summary": diagnosis.summary if diagnosis else "等待诊断",
        "root_cause": diagnosis.root_cause if diagnosis else row.root_node_id or "",
        "severity": diagnosis.severity if diagnosis else row.severity,
        "propagation_path": diagnosis.propagation_path if diagnosis else [],
        "evidence_refs": diagnosis.evidence_refs if diagnosis else [],
        "recommended_steps": diagnosis.recommended_steps if diagnosis else [],
        "action_candidates": diagnosis.action_candidates if diagnosis else [],
        "confidence": diagnosis.confidence if diagnosis else 0.0,
        "source": diagnosis.source if diagnosis else "pending",
    }
    return {
        "id": row.id,
        "title": row.title,
        "fault_type": row.fault_type,
        "severity": row.severity,
        "status": row.status,
        "source": row.source,
        "started_at": datetime_text(row.started_at),
        "ended_at": datetime_text(row.ended_at),
        "root_node": row.root_node_id,
        "assignee_user_id": row.assignee_user_id,
        "handling_notes": row.handling_notes,
        "version": row.version,
        "archived_at": datetime_text(row.archived_at),
        "propagation_path": diagnosis_data["propagation_path"],
        "evidence": evidence,
        "diagnosis": diagnosis_data,
    }
