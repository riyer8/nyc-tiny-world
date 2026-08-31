"""Tests for NPC cognition (Chunk 16)."""

from __future__ import annotations

from nyc_world.simulation.npc_mind import NPCMindRegistry, create_maya_mind


def test_maya_mind_profile():
    maya = create_maya_mind()
    assert maya.workplace_id == "cafe_village"
    assert maya.hates_rain is True
    assert maya.npc_relationships["alex"] > 0


def test_player_helped_creates_memory():
    registry = NPCMindRegistry()
    registry.register(create_maya_mind())
    registry.set_time_context(tick=1, game_day=1, game_time="08:00 AM")
    registry.on_player_helped("maya", "missing_camera")
    mind = registry.get("maya")
    assert mind is not None
    assert mind.has_memory("player_helped")
    rel = registry.relationships.get("maya")
    assert rel.trust >= 60
    assert rel.has_fact("quest_complete") or rel.has_fact("helped")


def test_player_stole_reduces_trust():
    registry = NPCMindRegistry()
    registry.register(create_maya_mind())
    registry.set_time_context(tick=1, game_day=1, game_time="08:00 AM")
    registry.on_player_stole("maya", "coffee")
    mind = registry.get("maya")
    assert mind is not None
    assert mind.has_memory("player_stole")
    rel = registry.relationships.get("maya")
    assert rel.trust < 50
    assert rel.has_fact("stole")


def test_rain_lowers_mood_for_maya():
    registry = NPCMindRegistry()
    registry.register(create_maya_mind())
    mind = registry.get("maya")
    assert mind is not None
    start_mood = mind.mood
    for _ in range(20):
        registry.update(12, 0, True, {"maya": (10.0, 10.0)})
    assert mind.mood < start_mood


def test_summary_mentions_help():
    registry = NPCMindRegistry()
    registry.register(create_maya_mind())
    registry.on_player_helped("maya", "missing_camera")
    summary = registry.summary_for("maya")
    assert summary is not None
    assert "remembers you helped" in summary
