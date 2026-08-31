"""Tests for tag-based dialogue routing."""

from nyc_world.game.dialogue import pick_npc_greeting
from nyc_world.simulation.relationships import RelationshipStore


def test_hostile_greeting_after_theft():
    store = RelationshipStore()
    store.record_fact(
        "maya",
        "stole",
        "You stole her coffee",
        tick=1,
        game_day=1,
        game_time="09:00 AM",
    )
    rel = store.get("maya")
    key = pick_npc_greeting("maya", rel, quest_active_id=None, quest_completed={"missing_camera"})
    assert key == "maya_hostile"


def test_hoping_you_come_by_greeting():
    store = RelationshipStore()
    rel = store.get("maya")
    rel.visit_count = 3
    rel.trust = 65
    rel.friendship = 50
    key = pick_npc_greeting("maya", rel, quest_active_id=None, quest_completed={"missing_camera"})
    assert key == "maya_hoping_you_come_by"
