"""Unified player ↔ NPC relationship store."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.simulation.memory import MemoryFact, make_fact, synthesize_opinion


@dataclass
class NPCPlayerRelationship:
    npc_id: str
    met_tick: int = 0
    met_day: int = 1
    met_time: str = ""
    visit_count: int = 0
    last_seen_tick: int = 0
    last_seen_time: str = ""
    trust: float = 50.0
    friendship: float = 30.0
    facts: list[MemoryFact] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "met_tick": self.met_tick,
            "met_day": self.met_day,
            "met_time": self.met_time,
            "visit_count": self.visit_count,
            "last_seen_tick": self.last_seen_tick,
            "last_seen_time": self.last_seen_time,
            "trust": self.trust,
            "friendship": self.friendship,
            "facts": [f.to_dict() for f in self.facts],
        }

    @classmethod
    def from_dict(cls, data: dict) -> NPCPlayerRelationship:
        return cls(
            npc_id=data["npc_id"],
            met_tick=data.get("met_tick", 0),
            met_day=data.get("met_day", 1),
            met_time=data.get("met_time", ""),
            visit_count=data.get("visit_count", 0),
            last_seen_tick=data.get("last_seen_tick", 0),
            last_seen_time=data.get("last_seen_time", ""),
            trust=data.get("trust", 50.0),
            friendship=data.get("friendship", 30.0),
            facts=[MemoryFact.from_dict(f) for f in data.get("facts", [])],
        )

    @property
    def opinion(self) -> str:
        return synthesize_opinion(self.trust, self.friendship, self.facts)

    @property
    def affinity(self) -> float:
        """Backward-compatible -1..1 score used by legacy systems."""
        score = self.trust / 100.0 * 0.6 + self.friendship / 100.0 * 0.4
        return max(-1.0, min(1.0, score * 2.0 - 1.0))

    def has_fact(self, category: str) -> bool:
        return any(f.category == category for f in self.facts)


class RelationshipStore:
    """Single source of truth for how NPCs feel about the player."""

    def __init__(self) -> None:
        self._relations: dict[str, NPCPlayerRelationship] = {}

    def get(self, npc_id: str) -> NPCPlayerRelationship:
        if npc_id not in self._relations:
            self._relations[npc_id] = NPCPlayerRelationship(npc_id=npc_id)
        return self._relations[npc_id]

    def all_relations(self) -> dict[str, NPCPlayerRelationship]:
        return dict(self._relations)

    def record_fact(
        self,
        npc_id: str,
        category: str,
        summary: str,
        *,
        tick: int,
        game_day: int,
        game_time: str,
        target_id: str = "",
        amount: int = 0,
        sentiment: float = 0.0,
        trust_delta: float = 0.0,
        friendship_delta: float = 0.0,
    ) -> MemoryFact:
        rel = self.get(npc_id)
        if rel.met_tick == 0:
            rel.met_tick = tick
            rel.met_day = game_day
            rel.met_time = game_time
        fact = make_fact(
            category,
            summary,
            tick=tick,
            game_day=game_day,
            game_time=game_time,
            target_id=target_id,
            amount=amount,
            sentiment=sentiment,
        )
        rel.facts.append(fact)
        if len(rel.facts) > 64:
            rel.facts.pop(0)
        rel.trust = max(0.0, min(100.0, rel.trust + trust_delta))
        rel.friendship = max(0.0, min(100.0, rel.friendship + friendship_delta))
        return fact

    def record_visit(
        self,
        npc_id: str,
        *,
        tick: int,
        game_day: int,
        game_time: str,
    ) -> None:
        rel = self.get(npc_id)
        rel.visit_count += 1
        rel.last_seen_tick = tick
        rel.last_seen_time = game_time
        if rel.met_tick == 0:
            rel.met_tick = tick
            rel.met_day = game_day
            rel.met_time = game_time
            self.record_fact(
                npc_id,
                "met",
                "First meeting",
                tick=tick,
                game_day=game_day,
                game_time=game_time,
                sentiment=0.1,
                friendship_delta=2.0,
            )
        else:
            self.record_fact(
                npc_id,
                "visited",
                f"You visited {npc_id.title()}",
                tick=tick,
                game_day=game_day,
                game_time=game_time,
                sentiment=0.05,
                friendship_delta=1.0,
            )

    def sync_to_profile(self, profile) -> None:
        """Push affinity scores into PlayerProfile.relationships."""
        for npc_id, rel in self._relations.items():
            profile.relationships[npc_id] = rel.affinity

    def import_from_profile(self, profile) -> None:
        """Migrate legacy -1..1 relationship values into trust/friendship."""
        for npc_id, value in profile.relationships.items():
            rel = self.get(npc_id)
            if rel.met_tick == 0 and not rel.facts:
                rel.trust = max(0.0, min(100.0, 50.0 + value * 50.0))
                rel.friendship = max(0.0, min(100.0, 30.0 + value * 40.0))

    def to_dict(self) -> dict:
        return {npc_id: rel.to_dict() for npc_id, rel in self._relations.items()}

    @classmethod
    def from_dict(cls, data: dict) -> RelationshipStore:
        store = cls()
        for npc_id, rel_data in data.items():
            store._relations[npc_id] = NPCPlayerRelationship.from_dict(rel_data)
        return store
