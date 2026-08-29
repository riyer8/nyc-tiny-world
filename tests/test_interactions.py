"""Tests for interaction and quest systems."""

from __future__ import annotations

from nyc_world.game.interactables import Interactable, InteractableKind
from nyc_world.game.interactions import InteractionSystem, build_world_interactables
from nyc_world.game.quests import QuestManager, QuestState, create_missing_camera_quest


def _make_session_interaction(
    interactables: list[Interactable] | None = None,
) -> tuple[QuestManager, InteractionSystem]:
    quests = QuestManager()
    items = interactables or [
        Interactable("maya", InteractableKind.NPC, 10, 10, "Maya", radius=3),
        Interactable("alex", InteractableKind.NPC, 40, 30, "Alex", radius=3),
        Interactable("cafe_village", InteractableKind.CAFE, 35, 25, "Village Cafe", interior_id="cafe_interior"),
        Interactable(
            "library_building",
            InteractableKind.BUILDING,
            60,
            50,
            "Library",
            interior_id="library_interior",
            radius=5,
        ),
    ]
    return quests, InteractionSystem(items, quests)


def test_interactable_prompt():
    cafe = Interactable("cafe", InteractableKind.CAFE, 0, 0, "Village Cafe")
    assert "☕" in cafe.prompt_text()
    assert "VILLAGE CAFE" in cafe.prompt_text()
    assert "[ E ]" in cafe.prompt_text()
    assert "ENTER" in cafe.prompt_text()


def test_nearest_interactable():
    _, system = _make_session_interaction()
    system.update_player(10.5, 10.5)
    assert system.nearest is not None
    assert system.nearest.id == "maya"


def test_talk_to_maya_starts_quest():
    quests, system = _make_session_interaction()
    system.update_player(10, 10)
    result = system.try_interact(10, 10)
    assert result.success
    assert quests.active_quest is not None
    assert quests.active_quest.id == "missing_camera"
    assert quests.active_quest.objectives[0].completed


def test_visit_cafe_advances_quest():
    quests, system = _make_session_interaction()
    quests.start_quest("missing_camera")
    quests.quests["missing_camera"].objectives[0].completed = True
    system.update_player(35, 25)
    result = system.try_interact(35, 25)
    assert result.success
    assert quests.active_quest.objectives[1].completed
    assert any("Alex" in line for line in result.lines)


def test_enter_library_and_collect_camera():
    quests, system = _make_session_interaction()
    quests.start_quest("missing_camera")
    for i in range(4):
        quests.quests["missing_camera"].objectives[i].completed = True

    system.update_player(60, 50)
    result = system.try_interact(60, 50)
    assert result.entered_interior == "library_interior"
    assert system.mode == "interior"

    system.update_player(8, 5)
    result = system.try_interact(8, 5)
    assert quests.has_item("camera")
    assert quests.active_quest.objectives[4].completed


def test_return_camera_completes_quest():
    quests, system = _make_session_interaction()
    quests.start_quest("missing_camera")
    for obj in quests.quests["missing_camera"].objectives[:-1]:
        obj.completed = True
    quests.player.add_item("camera")

    system.update_player(10, 10)
    result = system.try_interact(10, 10)
    assert quests.quests["missing_camera"].state == QuestState.COMPLETED
    assert any("QUEST COMPLETE" in line for line in result.lines)
    assert quests.player.has_item("coffee")
    assert quests.player.xp == 75
    assert quests.player.money == 52


def test_missing_camera_quest_structure():
    quest = create_missing_camera_quest()
    assert quest.title == "The Missing Camera"
    assert len(quest.objectives) == 6
    assert quest.objectives[0].description.startswith("Talk to Maya")


def test_build_world_interactables_has_quest_npcs():
    from nyc_world.city.npcs import NPC

    npcs = [
        NPC("maya", "commuter", 0, 0, 1.2, []),
        NPC("alex", "student", 0, 0, 1.2, []),
    ]
    items = build_world_interactables([], npcs, 500, 500)
    ids = {i.id for i in items}
    assert "maya" in ids
    assert "alex" in ids
    assert "cafe_village" in ids
    assert "library_building" in ids
