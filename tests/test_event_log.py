"""Tests for simulation event log."""

from nyc_world.simulation.event_log import EventLog


def test_event_log_append_and_recent():
    log = EventLog()
    log.append(
        tick=1,
        game_day=1,
        game_time="08:00 AM",
        actor_id="maya",
        action="enter",
        location_id="cafe_village",
    )
    log.append(
        tick=2,
        game_day=1,
        game_time="08:05 AM",
        actor_id="player",
        action="interact",
        location_id="maya",
    )
    assert len(log.entries) == 2
    assert log.recent(1)[0].actor_id == "player"


def test_event_log_roundtrip():
    log = EventLog()
    log.append(tick=1, game_day=1, game_time="08:00 AM", actor_id="alex", action="leave", location_id="cafe")
    restored = EventLog.from_dict(log.to_dict())
    assert len(restored.entries) == 1
    assert restored.entries[0].action == "leave"
