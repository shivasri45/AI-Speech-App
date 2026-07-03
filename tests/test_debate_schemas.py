"""Property tests for the group-debate schemas.

Property 10: ``PublicDebateRoom`` hides internal fields.
Validates: Requirements 11.1, 11.5.

The broadcast projection produced by ``to_public`` MUST NOT leak internal
bookkeeping — no ``user_email``, no ``user_id``, no ``ws_connected_since``,
no ``disconnected_at``, and no ``_pause_started_at``. This module drives
random ``DebateRoom`` instances through ``to_public`` and asserts none of
those substrings appear in the resulting JSON dump.

To make the substring check robust the internal-only fields are seeded
with markers that literally contain the forbidden tokens (e.g. an email
like ``user_email-MARKER-...@example.com``). If the projection ever
leaked a value (not merely a field name), the assertion still catches
it. Conversely, the public-exposed text fields (``display_name``,
``motion_title``, ``motion_text``, ...) are drawn from an alphabet that
excludes ``_``; because every forbidden substring contains ``_``, this
prevents random legitimate values from producing false-positive matches.
"""

from __future__ import annotations

from hypothesis import HealthCheck
from hypothesis import given
from hypothesis import settings
from hypothesis import strategies as st

from app.debate.schemas import DebateRoom
from app.debate.schemas import ParticipantInternal
from app.debate.schemas import to_public


# ---------------------------------------------------------------------------
# Forbidden substrings — none of these may appear anywhere in the JSON
# produced by ``to_public(room).model_dump_json()``.
# ---------------------------------------------------------------------------

FORBIDDEN_SUBSTRINGS = (
    "user_email",
    "user_id",
    "ws_connected_since",
    "disconnected_at",
    "_pause_started_at",
)


# Alphabet used for every string field that IS legitimately exposed by
# the public projection (display_name, motion_text, motion_title, ...).
# It intentionally omits ``_`` so no legitimately-visible value can
# collide with any forbidden substring above (each of which contains
# at least one underscore).
SAFE_ALPHABET = (
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789 -.@"
)

safe_text = st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=40)

# Positive, finite unix-second timestamps.
timestamp_st = st.floats(
    min_value=0.0,
    max_value=1e10,
    allow_nan=False,
    allow_infinity=False,
)

optional_timestamp_st = st.one_of(st.none(), timestamp_st)

state_st = st.sampled_from(
    ["waiting", "prep", "speaking", "scoring", "complete", "abandoned"]
)

# Room codes use the manager's alphabet (unambiguous uppercase letters +
# digits, no 0/O/1/I/L). Any alphanumeric set without ``_`` works here.
room_code_st = st.text(
    alphabet="ABCDEFGHJKMNPQRSTUVWXYZ23456789",
    min_size=6,
    max_size=6,
)


@st.composite
def participant_internal_st(draw, turn_index: int):
    """Random ``ParticipantInternal`` with marker-laced internal fields."""
    tag = draw(st.text(alphabet=SAFE_ALPHABET, min_size=1, max_size=6))
    return ParticipantInternal(
        participant_id=f"p-{turn_index}-{tag}",
        # Internal-only fields deliberately carry the forbidden tokens
        # as VALUES so a leaked value (not just a field name) also fails
        # the substring assertion.
        user_id=f"user_id-MARKER-{turn_index}-{tag}",
        user_email=f"user_email-MARKER-{turn_index}-{tag}@example.com",
        display_name=draw(safe_text),
        joined_at=draw(timestamp_st),
        is_ready=draw(st.booleans()),
        turn_index=turn_index,
        is_forfeit=draw(st.booleans()),
        ws_connected_since=draw(optional_timestamp_st),
        disconnected_at=draw(optional_timestamp_st),
    )


@st.composite
def debate_room_st(draw):
    """Random ``DebateRoom`` with 1–6 participants and every optional set."""
    n = draw(st.integers(min_value=1, max_value=6))
    participants = [draw(participant_internal_st(i)) for i in range(n)]
    room = DebateRoom(
        debate_id=draw(safe_text),
        code=draw(room_code_st),
        motion_id=draw(safe_text),
        motion_title=draw(safe_text),
        motion_text=draw(safe_text),
        state=draw(state_st),
        paused=draw(st.booleans()),
        participants=participants,
        active_turn_index=draw(
            st.one_of(
                st.none(),
                st.integers(min_value=0, max_value=n - 1),
            )
        ),
        prep_deadline=draw(optional_timestamp_st),
        turn_deadline=draw(optional_timestamp_st),
        reconnect_deadline=draw(optional_timestamp_st),
        created_at=draw(timestamp_st),
        completed_at=draw(st.one_of(st.none(), timestamp_st)),
        winner_participant_id=draw(st.one_of(st.none(), safe_text)),
    )
    # Exercise the private pause bookkeeping so the assertion also
    # covers ``_pause_started_at`` (a Pydantic ``PrivateAttr``).
    if draw(st.booleans()):
        room._pause_started_at = draw(timestamp_st)
    return room


# ---------------------------------------------------------------------------
# Property 10: PublicDebateRoom hides internal fields
# ---------------------------------------------------------------------------


@given(room=debate_room_st())
@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
def test_public_debate_room_hides_internal_fields(room: DebateRoom) -> None:
    """PublicDebateRoom JSON never contains internal field names or values.

    Property 10: PublicDebateRoom hides internal fields.
    Validates: Requirements 11.1, 11.5.
    """
    dumped = to_public(room).model_dump_json()
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in dumped, (
            f"Forbidden substring {forbidden!r} leaked into the public "
            f"projection JSON. Full dump: {dumped}"
        )


# ---------------------------------------------------------------------------
# Concrete regression example — pinned so a future refactor of the
# projection is caught even outside the randomised search.
# ---------------------------------------------------------------------------


def test_public_debate_room_hides_internal_fields_concrete_example() -> None:
    """Explicit example with marker values in every internal-only field."""
    participant = ParticipantInternal(
        participant_id="p-0",
        user_id="user_id-LEAK-CHECK",
        user_email="user_email-LEAK-CHECK@example.com",
        display_name="Alice",
        joined_at=1.0,
        is_ready=True,
        turn_index=0,
        is_forfeit=False,
        ws_connected_since=2.0,
        disconnected_at=3.0,
    )
    room = DebateRoom(
        debate_id="deb-1",
        code="ABCDEF",
        motion_id="m-1",
        motion_title="THB uniforms",
        motion_text="This house believes school uniforms should be abolished.",
        state="speaking",
        paused=True,
        participants=[participant],
        active_turn_index=0,
        prep_deadline=100.0,
        turn_deadline=200.0,
        reconnect_deadline=300.0,
        created_at=0.0,
        completed_at=None,
        winner_participant_id=None,
    )
    room._pause_started_at = 42.0

    dumped = to_public(room).model_dump_json()

    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in dumped, (
            f"Forbidden substring {forbidden!r} leaked into the public "
            f"projection JSON. Full dump: {dumped}"
        )
