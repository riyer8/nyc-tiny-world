"""Tests for game session orchestration."""

from __future__ import annotations

from nyc_world.game import GameSession, INTERIOR_SPAWN
from nyc_world.game.quests import QuestState


class _FakeCity:
    def __init__(self):
        self.landmarks = []
        self.npcs = []


def _make_session() -> GameSession:
    from nyc_world.city.npcs import NPC

    city = _FakeCity()
    city.npcs = [
        NPC("npc_0", "commuter", 0, 0, 1.2, []),
        NPC("npc_1", "student", 0, 0, 1.2, []),
    ]
    return GameSession(city, 500, 500)


def test_session_starts_quest_with_maya():
    session = _make_session()
    maya_x = session.city.npcs[0].x
    maya_z = session.city.npcs[0].z
    session.press_interact(maya_x, maya_z)
    assert session.quests.active_quest is not None
    assert session.hud.dialogue_lines


def test_session_enters_and_exits_interior():
    session = _make_session()
    session.quests.start_quest("missing_camera")
    for i in range(4):
        session.quests.quests["missing_camera"].objectives[i].completed = True

    lib = next(i for i in session.interaction.interactables if i.id == "library_building")
    new_pos = session.press_interact(lib.x, lib.z)
    assert new_pos == INTERIOR_SPAWN
    assert session.in_interior

    session.update(6, 9)
    session.press_interact(6, 9)
    assert not session.in_interior


def test_interior_clamp():
    session = _make_session()
    session.interaction._enter_interior("cafe_interior")
    x, z = session.clamp_interior(-5, -5)
    assert x >= 0.6
    assert z >= 0.6
