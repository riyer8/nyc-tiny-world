"""Tests for player profile, inventory, and progression."""

from __future__ import annotations

import pytest

from nyc_world.game.profile import PlayerProfile, QuestReward
from nyc_world.game.quests import QuestManager, QuestState, create_missing_camera_quest


def test_profile_starts_with_metrocard_and_money():
    player = PlayerProfile()
    assert player.money == 37
    assert player.has_item("metro_card")
    assert player.item_count("metro_card") == 1
    assert player.level == 1
    assert player.xp == 0


def test_inventory_add_remove():
    player = PlayerProfile()
    player.add_item("coffee", 2)
    assert player.item_count("coffee") == 2
    assert player.remove_item("coffee", 1)
    assert player.item_count("coffee") == 1
    assert player.remove_item("coffee", 1)
    assert not player.has_item("coffee")


def test_xp_and_level_up():
    player = PlayerProfile()
    lines = player.add_xp(100)
    assert player.level == 2
    assert any("Level 2" in line for line in lines)


def test_relationship_adjustment():
    player = PlayerProfile()
    player.adjust_relationship("maya", 0.5)
    assert player.get_relationship("maya") == pytest.approx(0.5)
    label = player.relationship_label("maya")
    assert "Maya" in label
    assert "likes you" in label


def test_apply_reward():
    player = PlayerProfile()
    reward = QuestReward(xp=50, money=10, items={"coffee": 1}, relationship_changes={"maya": 0.3})
    lines = player.apply_reward(reward)
    assert player.xp == 50
    assert player.money == 47
    assert player.has_item("coffee")
    assert player.get_relationship("maya") == pytest.approx(0.3)
    assert lines


def test_profile_round_trip():
    player = PlayerProfile()
    player.add_xp(25)
    player.add_item("mysterious_key")
    player.complete_quest("missing_camera")
    restored = PlayerProfile.from_dict(player.to_dict())
    assert restored.xp == player.xp
    assert restored.items == player.items
    assert restored.quests_completed == player.quests_completed


def test_profile_lines_include_inventory():
    player = PlayerProfile()
    lines = player.profile_lines()
    assert any("MetroCard" in line for line in lines)
    assert any("$37" in line for line in lines)


def test_quest_completion_grants_rewards():
    quests = QuestManager()
    quests.start_quest("missing_camera")
    for obj in quests.quests["missing_camera"].objectives[:-1]:
        obj.completed = True
    quests.player.add_item("camera")

    lines = quests.on_talk_npc("maya")
    assert quests.quests["missing_camera"].state == QuestState.COMPLETED
    assert "missing_camera" in quests.completed_quests
    assert quests.player.has_item("coffee")
    assert quests.player.money == 52
    assert quests.player.xp == 75
    assert quests.player.get_relationship("maya") == pytest.approx(0.5)
    assert not quests.player.has_item("camera")
    assert any("QUEST COMPLETE" in line for line in lines)


def test_missing_camera_quest_has_reward():
    quest = create_missing_camera_quest()
    assert quest.reward.xp == 75
    assert quest.reward.money == 15
    assert "coffee" in quest.reward.items
