"""Audit ingestion and retrieval routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request, status

from authsome.audit import AuditEvent
from authsome.auth import AuthService
from authsome.server.routes._deps import get_protected_auth_service
from authsome.server.schemas import AuditEventRequest, AuditEventsResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def submit_audit_event(
    body: AuditEventRequest,
    request: Request,
    auth: AuthService = Depends(get_protected_auth_service),
) -> dict[str, str]:
    await request.app.state.store.append_audit_event(
        AuditEvent(
            event=body.event,
            provider=body.provider,
            connection=body.connection,
            identity=auth.identity,
            status=body.status,
            metadata=body.metadata,
        )
    )
    return {"status": "accepted"}


@router.get("/events", response_model=AuditEventsResponse)
async def list_audit_events(
    request: Request,
    auth: AuthService = Depends(get_protected_auth_service),
    limit: int = Query(default=50, ge=1, le=500),
) -> AuditEventsResponse:
    events = await request.app.state.store.list_audit_events(identity=auth.identity, limit=limit)
    return AuditEventsResponse(events=events)
