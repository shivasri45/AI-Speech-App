"""HTTP + WebSocket routes for the group-debate feature.

Endpoints (prefix ``/debate``):

- POST   /debate/rooms                    → create room (random motion)
- POST   /debate/rooms/{code}/join        → join existing room
- POST   /debate/rooms/{code}/ready       → toggle ready flag
- POST   /debate/rooms/{code}/turn        → upload turn audio (multipart)
- GET    /debate/rooms/{code}             → fetch public room state
- GET    /debate/rooms/{code}/audio/{turn_id} → serve turn audio file
- GET    /debate/motions                  → list catalog of motions
- GET    /debate/my-debates               → completed debates for caller
- WS     /debate/ws/{code}                → live state stream + keepalive

Room state mutation is delegated to ``debate_room_manager``. This module
is thin: it validates auth, unpacks arguments, and translates the
manager's ``ValueError`` sentinels into HTTP status codes.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel

from app.auth import User, require_user, verify_token_string
from app.debate.room_manager import _load_motions, debate_room_manager
from app.debate.schemas import (
    CreateRoomResponse,
    JoinRoomResponse,
    Motion,
    PublicDebateRoom,
    ReadyResponse,
    TurnUploadResponse,
    to_public,
)
from app.debate.service import analyze_turn_audio
from app.storage import debate_turns as debate_turns_store
from app.storage import debates as debates_store


logger = logging.getLogger("debate.routes")

router = APIRouter(prefix="/debate", tags=["debate"])


# ---------------------------------------------------------------------------
# Local response shapes
# ---------------------------------------------------------------------------


class MyDebateEntry(BaseModel):
    """One row in the ``GET /debate/my-debates`` response.

    Projects a ``DebateRecord`` down to just the caller-relevant fields
    (their turn's scores, plus room-level winner + motion). Kept local
    to this module so schemas.py stays untouched.
    """

    debate_id: str
    code: str
    motion: Motion
    completed_at: float
    ai_score: Optional[float] = None
    teacher_override_score: Optional[int] = None
    teacher_comment: Optional[str] = None
    winner_participant_id: Optional[str] = None


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


@router.post("/rooms", response_model=CreateRoomResponse)
async def create_room(
    current_user: User = Depends(require_user),
) -> CreateRoomResponse:
    room = await debate_room_manager.create_room(current_user)
    first = room.participants[0]
    return CreateRoomResponse(
        room_code=room.code,
        participant_id=first.participant_id,
        state=to_public(room),
    )


@router.post("/rooms/{code}/join", response_model=JoinRoomResponse)
async def join_room(
    code: str,
    current_user: User = Depends(require_user),
) -> JoinRoomResponse:
    normalized = code.strip().upper()
    room = await debate_room_manager.join_room(normalized, current_user)
    participant = next(
        (p for p in room.participants if p.user_id == current_user.uid),
        None,
    )
    if participant is None:
        # Should never happen — join_room either raises or appends.
        raise HTTPException(status_code=500, detail="participant_missing")
    return JoinRoomResponse(
        room_code=room.code,
        participant_id=participant.participant_id,
        state=to_public(room),
    )


@router.post("/rooms/{code}/ready", response_model=ReadyResponse)
async def flip_ready(
    code: str,
    current_user: User = Depends(require_user),
) -> ReadyResponse:
    normalized = code.strip().upper()
    room = await debate_room_manager.flip_ready(normalized, current_user)
    return ReadyResponse(state=to_public(room))


@router.post("/rooms/{code}/turn", response_model=TurnUploadResponse)
async def upload_turn(
    code: str,
    file: UploadFile = File(...),
    current_user: User = Depends(require_user),
) -> TurnUploadResponse:
    normalized = code.strip().upper()
    room = debate_room_manager.get_state(normalized)
    if room is None:
        raise HTTPException(status_code=404, detail="room_not_found")
    if room.paused:
        raise HTTPException(status_code=409, detail="debate_paused")
    if room.state != "speaking":
        raise HTTPException(status_code=409, detail="not_in_speaking_state")
    participant = next(
        (p for p in room.participants if p.user_id == current_user.uid),
        None,
    )
    if participant is None:
        raise HTTPException(status_code=403, detail="not_a_participant")
    if participant.turn_index != room.active_turn_index:
        raise HTTPException(status_code=409, detail="not_your_turn")

    # Run the /analyze pipeline. This is the slow step (Whisper); no
    # room lock is held here so concurrent uploads to other rooms proceed
    # in parallel. Out-of-turn uploads were already rejected above.
    try:
        audio_asset, transcription, pronunciation, fluency, analysis_id = (
            await analyze_turn_audio(file=file, user=current_user)
        )
    except Exception as exc:  # noqa: BLE001 — defensive: pipeline failure
        logger.warning(
            "debate_analyze_failed room=%s user=%s err=%s",
            normalized,
            current_user.email,
            type(exc).__name__,
        )
        raise HTTPException(status_code=502, detail="analysis_failed")

    try:
        turn, updated_room = await debate_room_manager.submit_turn(
            code=normalized,
            user=current_user,
            audio_asset=audio_asset,
            transcription=transcription,
            pronunciation=pronunciation,
            fluency=fluency,
            analysis_id=analysis_id,
        )
    except ValueError as exc:
        # e.g. state changed between the pre-check and now
        # (paused / not_your_turn race).
        raise HTTPException(status_code=409, detail=str(exc))

    return TurnUploadResponse(
        turn_id=turn.turn_id,
        ai_score=turn.ai_score,
        scoring_unavailable=turn.scoring_unavailable,
        analysis_id=turn.analysis_id,
        audio_url=turn.audio_url,
        content_score=turn.content_score,
        content_feedback=turn.content_feedback,
        score_breakdown=turn.score_breakdown,
        state=to_public(updated_room),
    )


@router.get("/rooms/{code}/audio/{turn_id}")
async def get_turn_audio(
    code: str,
    turn_id: str,
    current_user: User = Depends(require_user),
) -> FileResponse:
    """Serve the audio file for a specific turn.
    
    Only participants in the debate can access the audio.
    """
    normalized = code.strip().upper()
    room = debate_room_manager.get_state(normalized)
    
    # Check room exists (either in-memory or completed)
    if room is None:
        # Try to find in completed debates
        turns = debate_turns_store.list_turns_for_debate_by_code(normalized)
        if not turns:
            raise HTTPException(status_code=404, detail="room_not_found")
    else:
        # Verify caller is a participant
        participant = next(
            (p for p in room.participants if p.user_id == current_user.uid),
            None,
        )
        if participant is None:
            raise HTTPException(status_code=403, detail="not_a_participant")
    
    # Find the turn
    turns = debate_turns_store.list_turns_for_debate_by_turn_id(turn_id)
    if not turns:
        raise HTTPException(status_code=404, detail="turn_not_found")
    
    turn = turns[0]
    if not turn.audio_url:
        raise HTTPException(status_code=404, detail="audio_not_available")
    
    # Extract file path from URL (URL is like /debate/rooms/{code}/audio/{turn_id})
    # The actual file is stored in uploads/
    audio_path = f"uploads/{turn_id}.webm"
    if not os.path.exists(audio_path):
        # Try other extensions
        for ext in ["wav", "mp3", "ogg", "m4a"]:
            alt_path = f"uploads/{turn_id}.{ext}"
            if os.path.exists(alt_path):
                audio_path = alt_path
                break
        else:
            raise HTTPException(status_code=404, detail="audio_file_not_found")
    
    return FileResponse(
        audio_path,
        media_type="audio/webm",
        filename=f"turn_{turn.turn_index + 1}.webm",
    )


@router.get("/rooms/{code}", response_model=PublicDebateRoom)
async def get_room(
    code: str,
    current_user: User = Depends(require_user),
) -> PublicDebateRoom:
    normalized = code.strip().upper()
    room = debate_room_manager.get_state(normalized)
    if room is None:
        raise HTTPException(status_code=404, detail="room_not_found")
    return to_public(room)


@router.get("/motions", response_model=List[Motion])
async def list_motions(
    current_user: User = Depends(require_user),
) -> List[Motion]:
    # _load_motions raises HTTPException(500, "motions_unavailable") on
    # parse failure — FastAPI propagates that verbatim.
    return _load_motions()


@router.get("/my-debates", response_model=List[MyDebateEntry])
async def my_debates(
    current_user: User = Depends(require_user),
) -> List[MyDebateEntry]:
    records = debates_store.list_debates_for_user(current_user.uid)
    entries: list[MyDebateEntry] = []
    for record in records:
        # Locate the caller's participant snapshot inside the debate.
        caller_participant_id: Optional[str] = None
        for participant in record.participants:
            if (
                isinstance(participant, dict)
                and participant.get("user_id") == current_user.uid
            ):
                caller_participant_id = participant.get("participant_id")
                break

        ai_score: Optional[float] = None
        teacher_override_score: Optional[int] = None
        teacher_comment: Optional[str] = None
        if caller_participant_id is not None:
            turns = debate_turns_store.list_turns_for_debate(record.debate_id)
            for turn in turns:
                if turn.participant_id == caller_participant_id:
                    ai_score = turn.ai_score
                    teacher_override_score = turn.teacher_override_score
                    teacher_comment = turn.teacher_comment
                    break

        entries.append(
            MyDebateEntry(
                debate_id=record.debate_id,
                code=record.code,
                motion=Motion(
                    id=record.motion_id,
                    title=record.motion_title,
                    text=record.motion_text,
                ),
                completed_at=record.completed_at,
                ai_score=ai_score,
                teacher_override_score=teacher_override_score,
                teacher_comment=teacher_comment,
                winner_participant_id=record.winner_participant_id,
            )
        )
    return entries


# ---------------------------------------------------------------------------
# WebSocket route
# ---------------------------------------------------------------------------


@router.websocket("/ws/{code}")
async def debate_websocket(
    websocket: WebSocket,
    code: str,
    participant_id: str = Query(...),
    id_token: str = Query(default=""),
) -> None:
    # Verify the Firebase ID token BEFORE accepting. Close with 4401 on
    # any failure — never ``accept()`` first.
    try:
        user = verify_token_string(id_token)
    except HTTPException:
        await websocket.close(code=4401)
        return
    except Exception:  # noqa: BLE001 — defensive
        await websocket.close(code=4401)
        return

    normalized = code.strip().upper()
    room = debate_room_manager.get_state(normalized)
    if room is None:
        await websocket.close(code=4404)
        return

    # Caller must own the participant slot they're claiming.
    participant = next(
        (
            p
            for p in room.participants
            if p.participant_id == participant_id and p.user_id == user.uid
        ),
        None,
    )
    if participant is None:
        await websocket.close(code=4401)
        return

    await websocket.accept()
    await debate_room_manager.attach_socket(normalized, participant_id, websocket)

    # Send the current state immediately so the client doesn't have to
    # wait for the next broadcast.
    try:
        await websocket.send_json(
            {"type": "state", "state": to_public(room).model_dump()}
        )
    except Exception:  # noqa: BLE001
        await debate_room_manager.detach_socket(
            normalized, participant_id, websocket
        )
        return

    try:
        while True:
            raw = await websocket.receive_json()
            # Only ``{"type": "ping"}`` is accepted; anything else is ignored.
            if isinstance(raw, dict) and raw.get("type") == "ping":
                try:
                    await websocket.send_json({"type": "pong"})
                except Exception:  # noqa: BLE001
                    pass
    except WebSocketDisconnect:
        await debate_room_manager.detach_socket(
            normalized, participant_id, websocket
        )
    except Exception as exc:  # noqa: BLE001 — defensive
        logger.warning(
            "debate_ws_error code=%s err=%s", normalized, type(exc).__name__
        )
        await debate_room_manager.detach_socket(
            normalized, participant_id, websocket
        )
