"""Utility-based agent brains for all NPCs."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nyc_world.feeds.effects import SimulationModifiers, apply_score_modifiers

if TYPE_CHECKING:
    from nyc_world.city.landmarks import Landmark3D
    from nyc_world.city.npcs import NPC
    from nyc_world.city.streets import StreetNetwork
    from nyc_world.city.world_clock import WorldClock
    from nyc_world.simulation.npc_mind import NPCMindRegistry


DECISION_INTERVAL_S = 3.0


@dataclass
class Personality:
    extroversion: float
    curiosity: float
    kindness: float
    risk_tolerance: float
    ambition: float

    def summary(self) -> str:
        return (
            f"curious {self.curiosity:.1f} · kind {self.kindness:.1f} · "
            f"risk {self.risk_tolerance:.1f}"
        )

    def to_dict(self) -> dict:
        return {
            "extroversion": self.extroversion,
            "curiosity": self.curiosity,
            "kindness": self.kindness,
            "risk_tolerance": self.risk_tolerance,
            "ambition": self.ambition,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Personality:
        return cls(
            extroversion=data.get("extroversion", 0.5),
            curiosity=data.get("curiosity", 0.5),
            kindness=data.get("kindness", 0.5),
            risk_tolerance=data.get("risk_tolerance", 0.5),
            ambition=data.get("ambition", 0.5),
        )


@dataclass
class AgentNeeds:
    hunger: float = 0.3
    energy: float = 0.5
    social: float = 0.4
    money: float = 0.4

    def drift(self, dt: float) -> None:
        self.hunger = min(1.0, self.hunger + 0.004 * dt)
        self.energy = max(0.0, self.energy - 0.002 * dt)
        self.social = min(1.0, self.social + 0.003 * dt)

    def bars_summary(self) -> str:
        def bar(v: float) -> str:
            filled = int(round(v * 5))
            return "▓" * filled + "░" * (5 - filled)

        return (
            f"hunger {bar(self.hunger)}  energy {bar(self.energy)}  "
            f"social {bar(self.social)}  money {bar(self.money)}"
        )

    def to_dict(self) -> dict:
        return {
            "hunger": self.hunger,
            "energy": self.energy,
            "social": self.social,
            "money": self.money,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentNeeds:
        return cls(
            hunger=data.get("hunger", 0.3),
            energy=data.get("energy", 0.5),
            social=data.get("social", 0.4),
            money=data.get("money", 0.4),
        )


@dataclass
class AgentBrain:
    npc_id: str
    display_name: str
    personality: Personality
    needs: AgentNeeds
    home: tuple[float, float] = (0.0, 0.0)
    workplace: tuple[float, float] = (0.0, 0.0)
    cafe: tuple[float, float] = (0.0, 0.0)
    park: tuple[float, float] = (0.0, 0.0)
    home_hour: int = 18
    current_action: str = "wander"
    plan_summary: str = "walking around"
    goal_text: str = ""
    _decision_timer: float = field(default=0.0, repr=False)
    _agent_enabled: bool = True

    def to_dict(self) -> dict:
        return {
            "npc_id": self.npc_id,
            "display_name": self.display_name,
            "personality": self.personality.to_dict(),
            "needs": self.needs.to_dict(),
            "home": list(self.home),
            "workplace": list(self.workplace),
            "cafe": list(self.cafe),
            "park": list(self.park),
            "home_hour": self.home_hour,
            "current_action": self.current_action,
            "plan_summary": self.plan_summary,
            "goal_text": self.goal_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AgentBrain:
        return cls(
            npc_id=data["npc_id"],
            display_name=data.get("display_name", data["npc_id"]),
            personality=Personality.from_dict(data.get("personality", {})),
            needs=AgentNeeds.from_dict(data.get("needs", {})),
            home=tuple(data.get("home", (0.0, 0.0))),
            workplace=tuple(data.get("workplace", (0.0, 0.0))),
            cafe=tuple(data.get("cafe", (0.0, 0.0))),
            park=tuple(data.get("park", (0.0, 0.0))),
            home_hour=data.get("home_hour", 18),
            current_action=data.get("current_action", "wander"),
            plan_summary=data.get("plan_summary", ""),
            goal_text=data.get("goal_text", ""),
        )

    def hud_lines(self) -> list[str]:
        lines = [
            f"{self.display_name}",
            f"Personality: {self.personality.summary()}",
            f"Needs:  {self.needs.bars_summary()}",
            f"Goal:   {self.goal_text or self.plan_summary}",
            f"Plan:   {self.plan_summary}",
        ]
        return lines


def _personality_for(npc_id: str, archetype: str) -> Personality:
    seed = sum(ord(c) for c in npc_id) + sum(ord(c) for c in archetype)
    rng = random.Random(seed)
    base = {
        "commuter": (0.4, 0.3, 0.5, 0.3, 0.6),
        "tourist": (0.7, 0.9, 0.6, 0.5, 0.3),
        "local": (0.5, 0.4, 0.7, 0.4, 0.4),
        "pedestrian": (0.5, 0.5, 0.5, 0.4, 0.3),
    }.get(archetype, (0.5, 0.5, 0.5, 0.4, 0.4))
    return Personality(
        extroversion=base[0] + rng.uniform(-0.15, 0.15),
        curiosity=base[1] + rng.uniform(-0.15, 0.15),
        kindness=base[2] + rng.uniform(-0.15, 0.15),
        risk_tolerance=base[3] + rng.uniform(-0.15, 0.15),
        ambition=base[4] + rng.uniform(-0.15, 0.15),
    )


def score_actions(
    brain: AgentBrain,
    *,
    hour: int,
    is_raining: bool,
    game_minutes: float,
    nearby_npc_count: int = 0,
    quest_goal_boost: str | None = None,
) -> dict[str, float]:
    """Score candidate actions — higher is better."""
    p = brain.personality
    n = brain.needs
    scores: dict[str, float] = {}

    scores["eat"] = n.hunger * 0.55 + (1.0 - n.energy) * 0.1 + p.kindness * 0.05
    scores["work"] = (
        p.ambition * 0.35
        + (0.25 if 9 <= hour <= 17 else 0.0)
        + n.money * 0.2
    )
    scores["socialize"] = (
        n.social * 0.45
        + p.extroversion * 0.35
        + min(nearby_npc_count, 5) * 0.04
    )
    scores["rest"] = (1.0 - n.energy) * 0.5 + (0.3 if hour >= brain.home_hour else 0.0)
    scores["go_home"] = (
        (0.55 if game_minutes >= brain.home_hour * 60 else 0.0)
        + (1.0 - n.energy) * 0.35
        + (0.25 if is_raining else 0.0)
    )
    scores["seek_shelter"] = (
        (0.85 if is_raining else 0.0)
        * (1.0 - p.risk_tolerance)
        + n.hunger * 0.1
    )
    scores["explore"] = p.curiosity * 0.45 + p.extroversion * 0.15 + (0.1 if not is_raining else 0.0)
    scores["wander"] = 0.15 + p.curiosity * 0.1

    if quest_goal_boost:
        scores[quest_goal_boost] = scores.get(quest_goal_boost, 0.0) + 0.9

    return scores


def pick_action(scores: dict[str, float]) -> str:
    return max(scores, key=lambda k: scores[k])


def action_target(brain: AgentBrain, action: str) -> tuple[float, float]:
    if action == "eat":
        return brain.cafe
    if action in ("work",):
        return brain.workplace
    if action in ("go_home", "rest"):
        return brain.home
    if action == "seek_shelter":
        return brain.cafe if brain.cafe != (0.0, 0.0) else brain.home
    if action == "socialize":
        return brain.park if brain.park != (0.0, 0.0) else brain.cafe
    if action == "explore":
        return brain.park if brain.park != (0.0, 0.0) else brain.workplace
    return brain.home


def plan_text_for(action: str) -> str:
    return {
        "eat": "walk → cafe → eat",
        "work": "walk → workplace",
        "socialize": "walk → park → mingle",
        "rest": "walk → home → rest",
        "go_home": "walk → home",
        "seek_shelter": "walk → shelter",
        "explore": "walk → explore sights",
        "wander": "wander sidewalks",
    }.get(action, "walking around")


def apply_action_effects(brain: AgentBrain, action: str) -> None:
    if action == "eat":
        brain.needs.hunger = max(0.0, brain.needs.hunger - 0.35)
        brain.needs.money = max(0.0, brain.needs.money - 0.05)
    elif action == "rest" or action == "go_home":
        brain.needs.energy = min(1.0, brain.needs.energy + 0.25)
    elif action == "socialize":
        brain.needs.social = max(0.0, brain.needs.social - 0.3)
    elif action == "work":
        brain.needs.money = min(1.0, brain.needs.money + 0.08)
        brain.needs.energy = max(0.0, brain.needs.energy - 0.08)
    elif action == "seek_shelter":
        brain.needs.energy = min(1.0, brain.needs.energy + 0.05)


class AgentController:
    """Utility AI for all NPCs — full brain within simulation radius."""

    def __init__(self) -> None:
        self.brains: dict[str, AgentBrain] = {}

    def register(self, brain: AgentBrain) -> None:
        self.brains[brain.npc_id] = brain

    def get(self, npc_id: str) -> AgentBrain | None:
        return self.brains.get(npc_id)

    @classmethod
    def from_npcs(
        cls,
        npcs: list[NPC],
        landmarks: list[Landmark3D],
        *,
        spawn_x: float,
        spawn_z: float,
        minds: NPCMindRegistry | None = None,
    ) -> AgentController:
        from nyc_world.city.landmarks import CAFE, PARK, STORE, LANDMARK

        controller = cls()

        def pick_lm(kind: str, fallback: tuple[float, float]) -> tuple[float, float]:
            matches = [lm for lm in landmarks if lm.kind == kind]
            if matches:
                lm = matches[hash(kind) % len(matches)]
                return lm.x, lm.z
            return fallback

        cafe = pick_lm(CAFE, (spawn_x + 30, spawn_z - 20))
        park = pick_lm(PARK, (spawn_x - 20, spawn_z + 10))
        work = pick_lm(LANDMARK, (spawn_x + 80, spawn_z - 60))
        store = pick_lm(STORE, cafe)

        for npc in npcs:
            display = npc.name.title() if npc.name in ("maya", "alex") else npc.name.replace("_", " ").title()
            brain = AgentBrain(
                npc_id=npc.name,
                display_name=display,
                personality=_personality_for(npc.name, npc.personality),
                needs=AgentNeeds(),
                home=(npc.x, npc.z),
                workplace=work,
                cafe=cafe,
                park=park,
            )
            if npc.personality == "commuter":
                brain.home_hour = 18
                brain.needs.money = 0.55
            elif npc.personality == "tourist":
                brain.personality.curiosity = 0.85
            controller.register(brain)

        if minds:
            for npc_id in ("maya", "alex"):
                mind = minds.get(npc_id)
                brain = controller.get(npc_id)
                if mind and brain:
                    brain.goal_text = mind.current_goal_text()
                    brain.home_hour = mind.home_hour
                    if mind.workplace_id:
                        brain.workplace = cafe if "cafe" in mind.workplace_id else work
                    if npc_id == "maya":
                        brain.needs.money = mind.needs.get("money", 0.72)

        return controller

    def sync_quest_goals(self, minds: NPCMindRegistry) -> None:
        for npc_id, brain in self.brains.items():
            mind = minds.get(npc_id)
            if mind:
                brain.goal_text = mind.current_goal_text()

    def update_npc(
        self,
        npc: NPC,
        streets: StreetNetwork,
        clock: WorldClock,
        dt: float,
        *,
        nearby_npc_count: int = 0,
        minds: NPCMindRegistry | None = None,
        feed_modifiers: SimulationModifiers | None = None,
        near_subway: bool = False,
        near_cafe: bool = False,
    ) -> None:
        brain = self.brains.get(npc.name)
        if not brain or not brain._agent_enabled:
            return

        brain.needs.drift(dt)
        brain._decision_timer += dt

        game_minutes = clock.hour * 60 + clock.minute
        quest_boost: str | None = None
        if minds:
            mind = minds.get(npc.name)
            if mind:
                brain.goal_text = mind.current_goal_text()
                goal = mind.current_goal_text().lower()
                if "camera" in goal or "favor" in goal:
                    quest_boost = "explore"
                elif "cafe" in goal or "work" in goal:
                    quest_boost = "work"
                elif "home" in goal or "dry" in goal:
                    quest_boost = "go_home" if "home" in goal else "seek_shelter"

        idle = not npc.path or npc.path_index >= len(npc.path)
        waiting = game_minutes < npc.wait_until

        if idle and not waiting and brain._decision_timer >= DECISION_INTERVAL_S:
            brain._decision_timer = 0.0
            scores = score_actions(
                brain,
                hour=clock.hour,
                is_raining=clock.is_raining,
                game_minutes=game_minutes,
                nearby_npc_count=nearby_npc_count,
                quest_goal_boost=quest_boost,
            )
            if feed_modifiers:
                scores = apply_score_modifiers(
                    scores,
                    feed_modifiers,
                    near_subway=near_subway,
                    near_cafe=near_cafe,
                )
            action = pick_action(scores)
            brain.current_action = action
            brain.plan_summary = plan_text_for(action)
            tx, tz = action_target(brain, action)
            npc._route_to(streets, tx, tz)
            npc.agent_action = action

        if idle and waiting and brain._decision_timer >= DECISION_INTERVAL_S * 0.5:
            apply_action_effects(brain, brain.current_action)
            brain._decision_timer = 0.0

    def to_dict(self) -> dict:
        return {npc_id: brain.to_dict() for npc_id, brain in self.brains.items()}

    def load_dict(self, data: dict) -> None:
        for npc_id, brain_data in data.items():
            self.brains[npc_id] = AgentBrain.from_dict(brain_data)

    def summary_for(self, npc_id: str) -> str | None:
        brain = self.get(npc_id)
        if not brain:
            return None
        return (
            f"{brain.display_name}: {brain.current_action} · "
            f"{brain.goal_text or brain.plan_summary}"
        )
