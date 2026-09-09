"""First-run opening beat — Maya in view, mid-conversation."""

from __future__ import annotations

import math

from nyc_world.city.npcs import NPC
from nyc_world.city.world_clock import Weather, WorldClock
from nyc_world.game import GameSession
from nyc_world.game.opening import apply_opening_beat, look_yaw_toward, quest_marker_ids
from nyc_world.simulation.npc_mind import NPCMindRegistry


class _FakeCity:
    def __init__(self):
        self.landmarks = []
        self.npcs = []
        self.vehicles = []
        self.mind_registry = NPCMindRegistry()
        self.clock = WorldClock()


def _fresh_session() -> GameSession:
    city = _FakeCity()
    city.npcs = [
        NPC("npc_0", "commuter", 0, 0, 1.2, []),
        NPC("npc_1", "student", 0, 0, 1.2, []),
    ]
    return GameSession(city, 500, 500, load_save=False)


def test_maya_stands_in_interact_range():
    session = _fresh_session()
    maya = session.city.npcs[0]
    dist = math.hypot(maya.x - 500, maya.z - 500)
    assert dist < 2.5
    assert maya.name == "maya"


def test_opening_beat_shows_maya_dialogue():
    session = _fresh_session()
    yaw = apply_opening_beat(session, 500.0, 500.0, 0.0)
    assert session.hud.dialogue_lines
    assert "camera" in " ".join(session.hud.dialogue_lines).lower()
    maya = session.city.npcs[0]
    assert yaw == look_yaw_toward(500.0, 500.0, maya.x, maya.z)
    assert quest_marker_ids(session) == ["maya"]


def test_opening_beat_skips_loaded_save():
    session = _fresh_session()
    session._loaded_position = (510.0, 520.0)
    apply_opening_beat(session, 510.0, 520.0, 1.2)
    assert session.hud.dialogue_lines == []


def test_sky_gradient_changes_with_time():
    day = WorldClock(hour=12, minute=0, weather=Weather.CLEAR)
    night = WorldClock(hour=22, minute=0, weather=Weather.CLEAR)
    dawn = WorldClock(hour=6, minute=30, weather=Weather.CLEAR)
    assert day.sky_gradient() != night.sky_gradient()
    assert day.sky_gradient()[0] == day.sky_color()
    assert night.sky_gradient()[1][2] < day.sky_gradient()[1][2]
    assert dawn.sky_gradient() != day.sky_gradient()


def test_building_ao_grows_with_height():
    from nyc_world.render.render_gl import building_ao_params

    low_pad, low_a = building_ao_params(8.0)
    high_pad, high_a = building_ao_params(80.0)
    assert high_pad > low_pad
    assert high_a > low_a
