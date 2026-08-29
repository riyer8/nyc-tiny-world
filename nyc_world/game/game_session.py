"""Game session — interactions, quests, and HUD state."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.city.city_sim import CitySimulation
from nyc_world.game.interactions import (
    InteractionSystem,
    assign_quest_npcs,
    build_world_interactables,
)
from nyc_world.game.interiors import INTERIORS, Interior
from nyc_world.game.quests import QuestManager


INTERIOR_SPAWN = (6.0, 8.0)


@dataclass
class HudState:
    prompt: str | None = None
    dialogue_lines: list[str] = field(default_factory=list)
    quest_text: str | None = None
    inventory: list[str] = field(default_factory=list)
    mode: str = "exterior"
    controls_hint: str = ""
    sprinting: bool = False


class GameSession:
    """Orchestrates interactions and quests for the 3D game."""

    def __init__(
        self,
        city: CitySimulation,
        spawn_x: float,
        spawn_z: float,
    ) -> None:
        self.city = city
        self.spawn_x = spawn_x
        self.spawn_z = spawn_z
        self.quests = QuestManager()
        assign_quest_npcs(city.npcs, spawn_x, spawn_z)
        interactables = build_world_interactables(
            city.landmarks, city.npcs, spawn_x, spawn_z
        )
        self.interaction = InteractionSystem(interactables, self.quests)
        self.hud = HudState()
        self.exterior_pos = (spawn_x, spawn_z)

    @property
    def in_interior(self) -> bool:
        return self.interaction.mode == "interior"

    @property
    def current_interior(self) -> Interior | None:
        iid = self.interaction.current_interior_id
        return INTERIORS.get(iid) if iid else None

    def update(self, x: float, z: float) -> None:
        self.interaction.update_player(x, z)
        self.hud.prompt = self.interaction.prompt()
        self.hud.quest_text = self.quests.hud_objective_text()
        self.hud.inventory = sorted(self.quests.inventory)
        self.hud.mode = self.interaction.mode

    def press_interact(self, x: float, z: float) -> tuple[float, float] | None:
        """Try to interact. Returns new (x, z) if player teleported."""
        result = self.interaction.try_interact(x, z)
        if result.lines:
            self.hud.dialogue_lines = result.lines
        self.update(x, z)

        if result.entered_interior:
            self.exterior_pos = (x, z)
            return INTERIOR_SPAWN
        if result.exited_interior:
            return self.exterior_pos
        return None

    def clamp_interior(self, x: float, z: float) -> tuple[float, float]:
        interior = self.current_interior
        if not interior:
            return x, z
        margin = 0.6
        x = max(margin, min(interior.width - margin, x))
        z = max(margin, min(interior.depth - margin, z))
        return x, z

    def quest_summary(self) -> str:
        q = self.quests.active_quest
        if not q:
            return "no active quest"
        obj = q.current_objective
        if obj:
            return f"{q.title}: {obj.description}"
        return f"{q.title}: complete"
