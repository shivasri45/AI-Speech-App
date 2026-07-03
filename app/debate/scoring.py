"""Pure scoring functions for the group-debate feature.

See `.kiro/specs/group-debate/design.md` Section "Winner Selection" for the
governing pseudocode. These helpers are intentionally free of I/O and framework
imports so they can be unit- and property-tested in isolation.
"""

from typing import Optional

from app.debate.schemas import DebateTurn, ParticipantInternal


def compute_effective_score(turn: DebateTurn) -> float:
    """Effective_Score := teacher_override_score if present, else ai_score."""
    if turn.teacher_override_score is not None:
        return float(turn.teacher_override_score)
    return float(turn.ai_score)


def compute_winner(
    turns: list[DebateTurn],
    participants: list[ParticipantInternal],
) -> Optional[str]:
    """Requirement 9 cascade.

    Order participants by (highest effective_score DESC, earliest submitted_at
    ASC, smallest turn_index ASC, participant_id ASC as a final deterministic
    tiebreak). Return the first participant_id, or ``None`` if there are no
    scorable turns.
    """
    if not turns:
        return None
    turn_by_pid: dict[str, DebateTurn] = {t.participant_id: t for t in turns}
    scored: list[tuple[float, float, int, str]] = []
    for p in participants:
        t = turn_by_pid.get(p.participant_id)
        if t is None:
            continue
        eff = compute_effective_score(t)
        # Sort key: negative effective score (max first), then submitted_at asc,
        # then turn_index asc, then participant_id asc for deterministic
        # tiebreak.
        scored.append((-eff, t.submitted_at, t.turn_index, p.participant_id))
    if not scored:
        return None
    scored.sort()
    return scored[0][3]
