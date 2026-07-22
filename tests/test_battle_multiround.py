"""Tests for the 1v1 battle multi-round flow.

Covers:
- CreateRoomRequest rounds validation (only 3/5/7 allowed).
- Round advance: after a round finalizes and the match isn't decided, the
  room returns to `ready` on the next round with a fresh prompt.
- Early clinch: a side reaching the majority ends the match immediately.
- Full match: alternating wins run to the decider.
- round_history accumulates one entry per completed round.
"""

import asyncio

import pytest

from app.battles.room_manager import RoomManager
from app.battles.schemas import BattlePrompt, CreateRoomRequest, PlayerScore, WSInbound


def _prompts(n):
    return [
        BattlePrompt(id=str(i), text=f"sentence {i}", difficulty="easy")
        for i in range(n)
    ]


def _score(pron):
    return PlayerScore(
        pronunciation_score=pron, clarity_score=90, pace_wpm=145, analysis_id="a"
    )


async def _play_round(mgr, code, host_id, opp_id, host_pron, opp_pron):
    await mgr.handle_inbound(code, host_id, WSInbound(type="ready"))
    await mgr.handle_inbound(code, opp_id, WSInbound(type="ready"))
    # Force into recording state (skip the timed countdown for the test).
    state = await mgr.get_state(code)
    state.status = "recording"
    await mgr.handle_inbound(
        code, host_id, WSInbound(type="score_submitted", score=_score(host_pron))
    )
    await mgr.handle_inbound(
        code, opp_id, WSInbound(type="score_submitted", score=_score(opp_pron))
    )


def test_create_room_request_accepts_valid_rounds():
    for n in (3, 5, 7):
        assert CreateRoomRequest(host_name="p", rounds=n).rounds == n


def test_create_room_request_rejects_invalid_rounds():
    for n in (1, 2, 4, 6, 8):
        with pytest.raises(ValueError):
            CreateRoomRequest(host_name="p", rounds=n)


def test_early_clinch_ends_match_best_of_three():
    async def scenario():
        mgr = RoomManager()
        code, host_id = await mgr.create_room("Host", _prompts(3), total_rounds=3)
        opp_id = await mgr.join_room(code, "Opp")

        await _play_round(mgr, code, host_id, opp_id, 95, 60)
        state = await mgr.get_state(code)
        assert state.status == "ready"
        assert state.current_round == 2
        assert state.host_rounds_won == 1

        # Host wins round 2 → 2-0 clinches best of 3.
        await _play_round(mgr, code, host_id, opp_id, 95, 60)
        state = await mgr.get_state(code)
        assert state.status == "complete"
        assert state.match_winner == "host"
        assert len(state.round_history) == 2

    asyncio.run(scenario())


def test_full_match_runs_to_decider():
    async def scenario():
        mgr = RoomManager()
        code, host_id = await mgr.create_room("Host", _prompts(3), total_rounds=3)
        opp_id = await mgr.join_room(code, "Opp")

        await _play_round(mgr, code, host_id, opp_id, 95, 60)  # host
        await _play_round(mgr, code, host_id, opp_id, 60, 95)  # opponent
        state = await mgr.get_state(code)
        assert state.status == "ready"
        assert state.current_round == 3
        assert state.host_rounds_won == 1
        assert state.opponent_rounds_won == 1

        await _play_round(mgr, code, host_id, opp_id, 95, 60)  # host takes decider
        state = await mgr.get_state(code)
        assert state.status == "complete"
        assert state.match_winner == "host"
        assert len(state.round_history) == 3

    asyncio.run(scenario())


def test_single_round_still_completes_immediately():
    async def scenario():
        mgr = RoomManager()
        code, host_id = await mgr.create_room("Host", _prompts(1), total_rounds=1)
        opp_id = await mgr.join_room(code, "Opp")

        await _play_round(mgr, code, host_id, opp_id, 95, 60)
        state = await mgr.get_state(code)
        assert state.status == "complete"
        assert state.match_winner == "host"
        assert len(state.round_history) == 1

    asyncio.run(scenario())
