"""
Support ticket API endpoints.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Literal, Optional, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal, get_db
from enums.support_status import SupportTicketStatus
from enums.support_topic import SupportTicketTopic
from models.support_ticket import SupportTicket
from models.user import User
from schemas.support import (
    SupportMessageResponse,
    SupportTicketDetailResponse,
    SupportTicketSummaryResponse,
    SupportTicketStatusUpdate,
    SupportTopicOption,
)
from services.auth_service import require_admin, require_auth, resolve_user_from_token
from services.support_service import support_service
from services.support_storage_service import support_storage_service

router = APIRouter(prefix="/support", tags=["support"])


class SupportConnectionManager:
    """
    Manages live WebSocket connections per ticket.
    """

    def __init__(self) -> None:
        self._connections: Dict[int, set[WebSocket]] = {}

    async def connect(self, ticket_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(ticket_id, set()).add(websocket)

    def disconnect(self, ticket_id: int, websocket: WebSocket) -> None:
        connections = self._connections.get(ticket_id)
        if not connections:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(ticket_id, None)

    async def broadcast(self, ticket_id: int, event: str, payload: dict) -> None:
        connections = self._connections.get(ticket_id)
        if not connections:
            return

        stale_connections: list[WebSocket] = []
        for ws in connections:
            try:
                await ws.send_json({"event": event, "data": payload})
            except Exception:
                stale_connections.append(ws)

        for ws in stale_connections:
            self.disconnect(ticket_id, ws)


class GlobalTicketConnectionManager:
    """
    Manages live WebSocket connections for global ticket notifications.
    """

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, event: str, payload: dict) -> None:
        if not self._connections:
            return

        stale_connections: list[WebSocket] = []
        for ws in self._connections:
            try:
                await ws.send_json({"event": event, "data": payload})
            except Exception:
                stale_connections.append(ws)

        for ws in stale_connections:
            self.disconnect(ws)


connection_manager = SupportConnectionManager()
global_connection_manager = GlobalTicketConnectionManager()
@router.get("/topics", response_model=list[SupportTopicOption])
async def list_topics() -> list[SupportTopicOption]:
    """
    List support topics for ticket creation.
    """
    return support_service.list_topics()


@router.get("/tickets", response_model=list[SupportTicketSummaryResponse])
async def list_tickets(
    scope: Literal["mine", "all"] = Query("mine"),
    status_filter: Optional[SupportTicketStatus] = Query(default=None, alias="status"),
    include_closed: bool = Query(default=False),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> list[SupportTicketSummaryResponse]:
    """
    Retrieve tickets for the current user, or all tickets for admins.
    """
    tickets = support_service.list_tickets(
        db=db,
        current_user=current_user,
        scope=scope,
        status_filter=status_filter,
        include_closed=include_closed,
    )
    return [support_service.to_summary_response(ticket) for ticket in tickets]


@router.post(
    "/tickets",
    response_model=SupportTicketDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ticket(
    subject: str = Form(..., min_length=4, max_length=255),
    topic: SupportTicketTopic = Form(...),
    message: str = Form(..., min_length=10, max_length=5000),
    attachments: List[UploadFile] = File(default=[]),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> SupportTicketDetailResponse:
    """
    Create a new ticket and its initial message.
    """
    stored_attachments = await support_storage_service.store_many(attachments)
    ticket = support_service.create_ticket(
        db=db,
        user=current_user,
        subject=subject,
        topic=topic,
        message=message,
        attachments=stored_attachments,
    )
    response = support_service.to_detail_response(ticket)
    await connection_manager.broadcast(
        ticket.id,
        event="ticket.created",
        payload=response.model_dump(mode="json"),
    )
    # Broadcast to global ticket list listeners
    summary = support_service.to_summary_response(ticket)
    await global_connection_manager.broadcast(
        event="ticket.created",
        payload=summary.model_dump(mode="json"),
    )
    return response


@router.get("/tickets/{ticket_id}", response_model=SupportTicketDetailResponse)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> SupportTicketDetailResponse:
    """
    Retrieve a single ticket with its conversation.
    """
    ticket = support_service.get_ticket(db, ticket_id, current_user)
    return support_service.to_detail_response(ticket)


@router.post(
    "/tickets/{ticket_id}/messages",
    response_model=SupportMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_message(
    ticket_id: int,
    message: str = Form(..., max_length=5000),
    attachments: List[UploadFile] = File(default=[]),
    current_user: User = Depends(require_auth),
    db: Session = Depends(get_db),
) -> SupportMessageResponse:
    """
    Post a message in a ticket conversation.
    """
    if not message.strip() and not attachments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message or attachments are required."
        )
    ticket = support_service.get_ticket(db, ticket_id, current_user)
    stored_attachments = await support_storage_service.store_many(attachments)
    support_message = support_service.add_message(
        db=db,
        ticket=ticket,
        sender=current_user,
        content=message,
        attachments=stored_attachments,
    )
    response = support_service.to_message_response(support_message)
    await connection_manager.broadcast(
        ticket_id,
        event="message.created",
        payload=response.model_dump(mode="json"),
    )
    ticket_summary = support_service.to_summary_response(ticket)
    await connection_manager.broadcast(
        ticket_id,
        event="ticket.updated",
        payload=ticket_summary.model_dump(mode="json"),
    )
    # Broadcast to global ticket list listeners with sender info
    update_payload = ticket_summary.model_dump(mode="json")
    update_payload["_sender_id"] = current_user.id  # Add sender ID for filtering
    update_payload["_sender_name"] = current_user.name  # Add sender name for notification
    await global_connection_manager.broadcast(
        event="ticket.message",
        payload=update_payload,
    )
    return response


@router.patch(
    "/tickets/{ticket_id}/status",
    response_model=SupportTicketSummaryResponse,
)
async def update_ticket_status(
    ticket_id: int,
    payload: SupportTicketStatusUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> SupportTicketSummaryResponse:
    """
    Update ticket status (admin only).
    """
    ticket = support_service.get_ticket(db, ticket_id, current_user)
    ticket = support_service.update_status(db, ticket, payload.status)
    response = support_service.to_summary_response(ticket)
    await connection_manager.broadcast(
        ticket_id,
        event="ticket.updated",
        payload=response.model_dump(mode="json"),
    )
    return response


@router.get("/attachments/{object_key:path}")
async def get_local_attachment(object_key: str) -> FileResponse:
    """
    Serve locally stored attachments (non-production).
    """
    if settings.is_production and settings.support_ftp_public_base_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    base_dir = Path(settings.support_local_upload_dir).resolve()
    file_path = (base_dir / object_key).resolve()

    if not str(file_path).startswith(str(base_dir)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid path.")

    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")

    return FileResponse(file_path)


@router.websocket("/tickets/{ticket_id}/ws")
async def ticket_websocket(
    websocket: WebSocket,
    ticket_id: int,
    token: str | None = Query(default=None),
) -> None:
    """
    Real-time conversation channel for a ticket.
    """
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db: Session = SessionLocal()
    try:
        user = resolve_user_from_token(token, db)
        ticket = support_service.get_ticket(db, ticket_id, user)

        await connection_manager.connect(ticket.id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            connection_manager.disconnect(ticket.id, websocket)
        except Exception:
            connection_manager.disconnect(ticket.id, websocket)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        db.close()


@router.websocket("/tickets/ws")
async def global_tickets_websocket(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """
    Real-time channel for global ticket list notifications.
    Notifies about new tickets and ticket updates.
    """
    if token is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    db: Session = SessionLocal()
    try:
        # Verify user authentication
        user = resolve_user_from_token(token, db)
        
        await global_connection_manager.connect(websocket)
        try:
            while True:
                # Keep connection alive
                await websocket.receive_text()
        except WebSocketDisconnect:
            global_connection_manager.disconnect(websocket)
        except Exception:
            global_connection_manager.disconnect(websocket)
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
    finally:
        db.close()


