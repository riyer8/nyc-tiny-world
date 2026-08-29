"""Backward-compatible import path. Prefer: from nyc_world.game.quests import ..."""

from nyc_world.game.quests import (
    DIALOGUE,
    Quest,
    QuestManager,
    QuestObjective,
    QuestState,
    create_missing_camera_quest,
)

__all__ = [
    "DIALOGUE",
    "Quest",
    "QuestManager",
    "QuestObjective",
    "QuestState",
    "create_missing_camera_quest",
]
