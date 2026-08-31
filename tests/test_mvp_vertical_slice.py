"""MVP vertical slice: Maya remembers, thinks, and offers a generated quest."""

from __future__ import annotations

from pathlib import Path

import pytest

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager, QuestState
from nyc_world.game.save import apply_save, capture_save, GameSave
from nyc_world.paths import DEFAULT_META_PATH
from nyc_world.simulation.adapters import capture_world_state
from nyc_world.simulation.event_log import EventLog
from nyc_world.game.interactions import assign_quest_npcs


@pytest.fixture
def projection() -> GeoProjection:
    if not DEFAULT_META_PATH.exists():
        pytest.skip("No map metadata")
    return GeoProjection.from_file(DEFAULT_META_PATH)


def test_maya_vertical_slice(projection: GeoProjection, tmp_path: Path):
    city = CitySimulation(projection, 100.0, 100.0, npc_count=8, vehicle_count=0)
    assign_quest_npcs(city.npcs, 100.0, 100.0)
    minds = city.mind_registry
    player = PlayerProfile()
    quests = QuestManager(player, minds=minds)
    quests.set_agents(city.agent_controller)
    event_log = EventLog()

    for i in range(3):
        minds.relationships.record_visit(
            "maya", tick=i + 1, game_day=1, game_time=f"0{i + 8}:00 AM"
        )
    panel = minds.memory_panel_lines("maya")
    assert panel
    assert minds.relationships.get("maya").visit_count >= 3

    minds.on_player_stole("maya", "coffee")
    assert minds.relationships.get("maya").has_fact("stole")

    maya = minds.get("maya")
    assert maya is not None
    maya.needs["money"] = 0.85
    player.complete_quest("missing_camera")
    quests.refresh_generated_quests()
    assert "maya_favor" in quests.quests
    assert quests.quests["maya_favor"].state == QuestState.AVAILABLE

    brain = city.agent_controller.get("maya")
    assert brain is not None
    assert brain.needs.money > 0.5

    save = capture_save(
        player=player,
        relationships=minds.relationships,
        minds=minds,
        quests=quests,
        event_log=event_log,
        tick=42,
        game_day=2,
        player_x=100,
        player_z=100,
        clock_hour=10,
        clock_minute=0,
        clock_weather="clear",
        agents=city.agent_controller.to_dict(),
        economy=city.economy.to_dict(),
    )
    path = tmp_path / "mvp.json"
    save.write(path)

    city2 = CitySimulation(projection, 50.0, 50.0, npc_count=8, vehicle_count=0)
    player2 = PlayerProfile()
    minds2 = city2.mind_registry
    quests2 = QuestManager(player2, minds=minds2)
    apply_save(
        GameSave.load(path),
        player=player2,
        relationships=minds2.relationships,
        minds=minds2,
        quests=quests2,
        event_log=EventLog(),
        city=city2,
    )
    assert minds2.relationships.get("maya").has_fact("stole")
    assert "maya_favor" in quests2.quests

    state = capture_world_state(
        city2,
        player2,
        quests2,
        minds2,
        tick=42,
        player_x=100,
        player_z=100,
        event_count=1,
    )
    assert state.npc_count >= 8
    assert any(r.npc_id == "maya" for r in state.relationships)
    assert "maya_favor" in state.quests.generated_ids or state.quests.available_generated
