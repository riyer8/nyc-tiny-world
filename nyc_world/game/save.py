"""Save and load persistent game state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.game.quest_types import ObjectiveType, Quest, QuestObjective, QuestState
from nyc_world.paths import SAVES_DIR
from nyc_world.simulation.event_log import EventLog
from nyc_world.simulation.npc_mind import NPCMindRegistry
from nyc_world.simulation.relationships import RelationshipStore

SAVE_VERSION = 1


@dataclass
class GameSave:
    version: int = SAVE_VERSION
    tick: int = 0
    game_day: int = 1
    player: dict = field(default_factory=dict)
    relationships: dict = field(default_factory=dict)
    minds: dict = field(default_factory=dict)
    quests: dict = field(default_factory=dict)
    active_quest_id: str | None = None
    event_log: dict = field(default_factory=dict)
    player_x: float = 0.0
    player_z: float = 0.0
    clock_hour: int = 8
    clock_minute: int = 0
    clock_weather: str = "clear"
    agents: dict = field(default_factory=dict)
    mystery: dict = field(default_factory=dict)
    economy: dict = field(default_factory=dict)

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: Path) -> GameSave:
        data = json.loads(path.read_text())
        return cls.from_dict(data)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "tick": self.tick,
            "game_day": self.game_day,
            "player": self.player,
            "relationships": self.relationships,
            "minds": self.minds,
            "quests": self.quests,
            "active_quest_id": self.active_quest_id,
            "event_log": self.event_log,
            "player_x": self.player_x,
            "player_z": self.player_z,
            "clock_hour": self.clock_hour,
            "clock_minute": self.clock_minute,
            "clock_weather": self.clock_weather,
            "agents": self.agents,
            "mystery": self.mystery,
            "economy": self.economy,
        }

    @classmethod
    def from_dict(cls, data: dict) -> GameSave:
        return cls(
            version=data.get("version", 1),
            tick=data.get("tick", 0),
            game_day=data.get("game_day", 1),
            player=data.get("player", {}),
            relationships=data.get("relationships", {}),
            minds=data.get("minds", {}),
            quests=data.get("quests", {}),
            active_quest_id=data.get("active_quest_id"),
            event_log=data.get("event_log", {}),
            player_x=data.get("player_x", 0.0),
            player_z=data.get("player_z", 0.0),
            clock_hour=data.get("clock_hour", 8),
            clock_minute=data.get("clock_minute", 0),
            clock_weather=data.get("clock_weather", "clear"),
            agents=data.get("agents", {}),
            mystery=data.get("mystery", {}),
            economy=data.get("economy", {}),
        )


def default_save_path(slot: str = "default") -> Path:
    return SAVES_DIR / f"{slot}.json"


def capture_save(
    *,
    player: PlayerProfile,
    relationships: RelationshipStore,
    minds: NPCMindRegistry,
    quests: QuestManager,
    event_log: EventLog,
    tick: int,
    game_day: int,
    player_x: float,
    player_z: float,
    clock_hour: int,
    clock_minute: int,
    clock_weather: str,
    agents: dict | None = None,
    mystery: dict | None = None,
    economy: dict | None = None,
) -> GameSave:
    relationships.sync_to_profile(player)
    quest_data: dict[str, dict] = {}
    for qid, quest in quests.quests.items():
        quest_data[qid] = {
            "state": quest.state.value,
            "title": quest.title,
            "emoji": quest.emoji,
            "generated": quest.generated,
            "giver_npc_id": quest.giver_npc_id,
            "intro_key": quest.intro_key,
            "complete_key": quest.complete_key,
            "objectives": [
                {
                    "id": o.id,
                    "description": o.description,
                    "type": o.type.value,
                    "target_id": o.target_id,
                    "completed": o.completed,
                }
                for o in quest.objectives
            ],
        }
    return GameSave(
        tick=tick,
        game_day=game_day,
        player=player.to_dict(),
        relationships=relationships.to_dict(),
        minds=minds.to_dict(),
        quests=quest_data,
        active_quest_id=quests.active_quest_id,
        event_log=event_log.to_dict(),
        player_x=player_x,
        player_z=player_z,
        clock_hour=clock_hour,
        clock_minute=clock_minute,
        clock_weather=clock_weather,
        agents=agents or {},
        mystery=mystery or {},
        economy=economy or {},
    )


def apply_save(
    save: GameSave,
    *,
    player: PlayerProfile,
    relationships: RelationshipStore,
    minds: NPCMindRegistry,
    quests: QuestManager,
    event_log: EventLog,
    city,
) -> tuple[float, float]:
    """Restore save into live objects. Returns (player_x, player_z)."""
    loaded_player = PlayerProfile.from_dict(save.player)
    player.money = loaded_player.money
    player.xp = loaded_player.xp
    player.items = dict(loaded_player.items)
    player.quests_completed = list(loaded_player.quests_completed)
    player.relationships = dict(loaded_player.relationships)

    relationships._relations = RelationshipStore.from_dict(save.relationships)._relations

    minds.load_dict(save.minds)
    minds.relationships = relationships

    for qid, qdata in save.quests.items():
        quest = quests.quests.get(qid)
        if not quest:
            quest = Quest(
                id=qid,
                title=qdata.get("title", qid),
                emoji=qdata.get("emoji", "📋"),
                objectives=[
                    QuestObjective(
                        o["id"],
                        o.get("description", o["id"]),
                        ObjectiveType(o.get("type", "talk_npc")),
                        o.get("target_id", ""),
                        completed=o.get("completed", False),
                    )
                    for o in qdata.get("objectives", [])
                ],
                giver_npc_id=qdata.get("giver_npc_id", ""),
                generated=qdata.get("generated", False),
                intro_key=qdata.get("intro_key", ""),
                complete_key=qdata.get("complete_key", ""),
            )
            quests.quests[qid] = quest
        quest.state = QuestState(qdata.get("state", quest.state.value))
        saved_objs = {o["id"]: o for o in qdata.get("objectives", [])}
        for obj in quest.objectives:
            if obj.id in saved_objs:
                obj.completed = saved_objs[obj.id].get("completed", obj.completed)

    quests.active_quest_id = save.active_quest_id

    event_log.entries.clear()
    loaded_log = EventLog.from_dict(save.event_log)
    event_log.entries.extend(loaded_log.entries)

    city.clock.hour = save.clock_hour
    city.clock.minute = save.clock_minute
    from nyc_world.city.world_clock import Weather

    try:
        city.clock.weather = Weather(save.clock_weather)
    except ValueError:
        city.clock.weather = Weather.CLEAR
    city.clock.day = save.game_day

    if save.agents and hasattr(city, "agent_controller"):
        city.agent_controller.load_dict(save.agents)

    if save.economy and hasattr(city, "economy"):
        from nyc_world.simulation.economy import CityEconomy

        city.economy = CityEconomy.from_dict(save.economy)

    return save.player_x, save.player_z
