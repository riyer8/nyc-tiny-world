"""Bridge live game objects ↔ WorldState snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nyc_world.simulation.npc_mind import NPCMindRegistry
from nyc_world.simulation.state import (
    ClockState,
    NPCState,
    PlayerState,
    QuestSnapshot,
    VehicleState,
    WorldState,
)

if TYPE_CHECKING:
    from nyc_world.city.city_sim import CitySimulation
    from nyc_world.game.profile import PlayerProfile
    from nyc_world.game.quests import QuestManager


def capture_world_state(
    city: CitySimulation,
    player_profile: PlayerProfile,
    quest_manager: QuestManager,
    minds: NPCMindRegistry,
    *,
    tick: int,
    player_x: float,
    player_z: float,
    player_yaw: float = 0.0,
    in_interior: bool = False,
    building_count: int = 0,
) -> WorldState:
    clock = city.clock
    quest = quest_manager.active_quest
    obj = quest.current_objective if quest else None

    npc_states: list[NPCState] = []
    for npc in city.npcs:
        mind = minds.get(npc.name)
        npc_states.append(
            NPCState(
                id=npc.name,
                name=npc.name,
                x=npc.x,
                z=npc.z,
                personality=npc.personality,
                goal=mind.current_goal_text() if mind else "",
                mood=mind.mood if mind else 0.5,
                player_affinity=mind.player_affinity if mind else 0.0,
            )
        )

    vehicle_states = [
        VehicleState(id=f"vehicle_{i}", kind=v.kind, x=v.x, z=v.z)
        for i, v in enumerate(city.vehicles)
    ]

    return WorldState(
        tick=tick,
        clock=ClockState(
            hour=clock.hour,
            minute=clock.minute,
            weather=clock.weather.value,
            tick=tick,
        ),
        player=PlayerState(
            x=player_x,
            z=player_z,
            yaw=player_yaw,
            money=player_profile.money,
            xp=player_profile.xp,
            items=dict(player_profile.items),
            relationships=dict(player_profile.relationships),
            in_interior=in_interior,
        ),
        npcs=npc_states,
        vehicles=vehicle_states,
        quests=QuestSnapshot(
            active_quest_id=quest_manager.active_quest_id,
            completed=list(player_profile.quests_completed),
            current_objective=obj.description if obj else None,
        ),
        building_count=building_count,
        npc_count=len(city.npcs),
        vehicle_count=len(city.vehicles),
    )
