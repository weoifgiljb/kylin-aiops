import hashlib
import hmac
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum


class ApprovalError(ValueError):
    pass


class ActionStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    EXECUTED = "executed"


@dataclass
class ActionRequest:
    id: str
    incident_id: str
    node_id: str
    action_name: str
    parameters: dict
    created_at: datetime
    expires_at: datetime
    status: ActionStatus = ActionStatus.PENDING
    approved_by: str | None = None
    approved_at: datetime | None = None

    def approve(self, operator_id: str, now: datetime) -> None:
        if self.status is not ActionStatus.PENDING:
            raise ApprovalError("Only a pending action can be approved")
        if now >= self.expires_at:
            raise ApprovalError("Action request expired before approval")
        if not operator_id.strip():
            raise ApprovalError("Operator identity is required")
        self.status = ActionStatus.APPROVED
        self.approved_by = operator_id
        self.approved_at = now


@dataclass(frozen=True)
class ActionEnvelope:
    action_id: str
    node_id: str
    action_name: str
    parameters: dict
    issued_at: datetime
    expires_at: datetime
    signature: str


def _canonical_payload(data: dict) -> bytes:
    normalized = {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in data.items()
    }
    return json.dumps(normalized, sort_keys=True, separators=(",", ":")).encode()


class ActionSigner:
    def __init__(self, secret: bytes) -> None:
        if len(secret) < 8:
            raise ValueError("Action signing secret is too short")
        self.secret = secret

    def sign(self, action: ActionRequest, now: datetime | None = None) -> ActionEnvelope:
        now = now or datetime.now(UTC)
        if action.status is not ActionStatus.APPROVED:
            raise ApprovalError("Action must be approved before signing")
        if now >= action.expires_at:
            raise ApprovalError("Approved action has expired")
        payload = {
            "action_id": action.id,
            "node_id": action.node_id,
            "action_name": action.action_name,
            "parameters": action.parameters,
            "issued_at": now,
            "expires_at": action.expires_at,
        }
        signature = hmac.new(self.secret, _canonical_payload(payload), hashlib.sha256).hexdigest()
        return ActionEnvelope(signature=signature, **payload)


class ExecutionGuard:
    def __init__(self, secret: bytes) -> None:
        self.secret = secret
        self._executed: set[str] = set()

    def verify(self, envelope: ActionEnvelope, node_id: str, now: datetime) -> ActionEnvelope:
        if envelope.action_id in self._executed:
            raise ApprovalError("Action was already executed")
        if envelope.node_id != node_id:
            raise ApprovalError("Action target does not match this node")
        if now >= envelope.expires_at:
            raise ApprovalError("Action envelope expired")
        payload = asdict(envelope)
        supplied = payload.pop("signature")
        expected = hmac.new(self.secret, _canonical_payload(payload), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied, expected):
            raise ApprovalError("Action signature is invalid")
        return envelope

    def mark_executed(self, action_id: str) -> None:
        self._executed.add(action_id)


def create_action_request(
    incident_id: str,
    node_id: str,
    action_name: str,
    parameters: dict,
    now: datetime | None = None,
    ttl: timedelta = timedelta(minutes=5),
) -> ActionRequest:
    now = now or datetime.now(UTC)
    if ttl <= timedelta(0):
        raise ValueError("Action TTL must be positive")
    return ActionRequest(
        id=str(uuid.uuid4()),
        incident_id=incident_id,
        node_id=node_id,
        action_name=action_name,
        parameters=dict(parameters),
        created_at=now,
        expires_at=now + ttl,
    )
