"""Bridge live game objects ↔ WorldState snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nyc_world.simulation.npc_mind import NPCMindRegistry
from nyc_world.simulation.state import (
    ClockState,
    EconomySnapshot,
    FeedSnapshot,
    MysterySnapshot,
    NPCState,
    PlayerState,
    QuestSnapshot,
    RelationshipSnapshot,
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
    event_count: int = 0,
    mystery=None,
) -> WorldState:
    clock = city.clock
    quest = quest_manager.active_quest
    obj = quest.current_objective if quest else None

    npc_states: list[NPCState] = []
    for npc in city.npcs:
        mind = minds.get(npc.name)
        rel = minds.relationships.get(npc.name)
        brain = city.agent_controller.get(npc.name) if hasattr(city, "agent_controller") else None
        npc_states.append(
            NPCState(
                id=npc.name,
                name=npc.name,
                x=npc.x,
                z=npc.z,
                personality=brain.personality.summary() if brain else npc.personality,
                goal=brain.goal_text if brain and brain.goal_text else (mind.current_goal_text() if mind else ""),
                mood=mind.mood if mind else 0.5,
                player_affinity=rel.affinity,
                trust=rel.trust,
                friendship=rel.friendship,
                visit_count=rel.visit_count,
                hunger=brain.needs.hunger if brain else 0.0,
                energy=brain.needs.energy if brain else 0.0,
                social_need=brain.needs.social if brain else 0.0,
                money_need=brain.needs.money if brain else 0.0,
                current_action=brain.current_action if brain else "",
                plan_summary=brain.plan_summary if brain else "",
            )
        )

    vehicle_states = [
        VehicleState(id=f"vehicle_{i}", kind=v.kind, x=v.x, z=v.z)
        for i, v in enumerate(city.vehicles)
    ]

    feed_mods = getattr(city, "feed_modifiers", None)
    feed_snap = FeedSnapshot()
    if feed_mods:
        feed_snap = FeedSnapshot(
            weather=feed_mods.weather_override,
            subway_boarding_rate=feed_mods.subway_boarding_rate,
            transit_affected_npcs=feed_mods.transit_affected_npcs,
            banner_lines=list(feed_mods.debug_notes),
        )

    relationships = [
        RelationshipSnapshot(
            npc_id=npc_id,
            trust=rel.trust,
            friendship=rel.friendship,
            opinion=rel.opinion,
            visit_count=rel.visit_count,
            fact_count=len(rel.facts),
        )
        for npc_id, rel in minds.relationships.all_relations().items()
    ]

    economy_snap = EconomySnapshot()
    economy = getattr(city, "economy", None)
    if economy:
        economy_snap = EconomySnapshot(
            week=economy.week,
            open_businesses=sum(1 for b in economy.businesses.values() if b.open),
            village_rent_index=economy.village_rent_index,
            journal_lines=[e.line for e in economy.journal[-8:]],
        )

    mystery_snap = MysterySnapshot()
    if mystery and getattr(mystery, "case", None):
        mystery_snap = MysterySnapshot(
            title=mystery.case.title,
            solved=mystery.solved,
            clues_discovered=len(mystery.discovered_entry_ids),
            crime_time=mystery.case.crime_time,
        )

    generated_meta = []
    generated_ids = []
    for qid, quest in quest_manager.quests.items():
        if quest.generated:
            generated_ids.append(qid)
            if quest.state.value == "available":
                generated_meta.append(
                    {
                        "id": qid,
                        "title": quest.title,
                        "giver_npc_id": quest.giver_npc_id,
                    }
                )

    mod_npc_ids = []
    registry = getattr(city, "mod_registry", None)
    if registry:
        mod_npc_ids = [n.id for n in registry.all()]

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
            generated_ids=generated_ids,
            available_generated=generated_meta,
        ),
        building_count=building_count,
        npc_count=len(city.npcs),
        vehicle_count=len(city.vehicles),
        event_count=event_count,
        game_day=city.clock.day,
        feeds=feed_snap,
        relationships=relationships,
        economy=economy_snap,
        mystery=mystery_snap,
        mod_npc_ids=mod_npc_ids,
    )
