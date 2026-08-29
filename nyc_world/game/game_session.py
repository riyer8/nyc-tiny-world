"""Game session — interactions, quests, simulation, and HUD state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nyc_world.city.city_sim import CitySimulation
from nyc_world.game.interactions import (
    InteractionSystem,
    assign_quest_npcs,
    build_world_interactables,
)
from nyc_world.game.interiors import INTERIORS, Interior
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.simulation import Simulation
from nyc_world.simulation.actions import InteractAction, PlayerMoveAction
from nyc_world.simulation.npc_mind import NPCMindRegistry


INTERIOR_SPAWN = (6.0, 8.0)


@dataclass
class HudState:
    prompt: str | None = None
    dialogue_lines: list[str] = field(default_factory=list)
    quest_text: str | None = None
    profile_lines: list[str] = field(default_factory=list)
    npc_mind_lines: list[str] = field(default_factory=list)
    simulation_lines: list[str] = field(default_factory=list)
    mode: str = "exterior"
    controls_hint: str = ""
    sprinting: bool = False
    adjusting_view: bool = False
    show_geo_debug: bool = False
    player_lat: float = 0.0
    player_lon: float = 0.0
    nearest_street: str = ""
    nearest_poi: str = ""
    neighborhood: str = ""
    borough: str = ""
    streaming_tiles: int = 0
    streaming_buildings: int = 0
    trajectory_steps: int = 0
    minimap: object | None = None


class GameSession:
    """Orchestrates interactions, quests, and formal simulation for the 3D game."""

    def __init__(
        self,
        city: CitySimulation,
        spawn_x: float,
        spawn_z: float,
        player: PlayerProfile | None = None,
        *,
        record_trajectories: bool = False,
        trajectory_dir: Path | None = None,
    ) -> None:
        self.city = city
        self.spawn_x = spawn_x
        self.spawn_z = spawn_z
        self.player = player or PlayerProfile()
        minds = getattr(city, "mind_registry", None)
        self.quests = QuestManager(self.player, minds=minds)
        assign_quest_npcs(city.npcs, spawn_x, spawn_z)
        interactables = build_world_interactables(
            city.landmarks, city.npcs, spawn_x, spawn_z
        )
        self.interaction = InteractionSystem(interactables, self.quests)
        self.simulation = Simulation(
            city,
            self.player,
            self.quests,
            minds=minds or NPCMindRegistry(),
            record_trajectories=record_trajectories,
            trajectory_dir=trajectory_dir,
        )
        self.hud = HudState()
        self.exterior_pos = (spawn_x, spawn_z)
        self._last_state = None
        self._pending_interact = ""

    @property
    def in_interior(self) -> bool:
        return self.interaction.mode == "interior"

    @property
    def current_interior(self) -> Interior | None:
        iid = self.interaction.current_interior_id
        return INTERIORS.get(iid) if iid else None

    def begin_frame(self, x: float, z: float, *, yaw: float = 0.0, building_count: int = 0) -> None:
        """Capture WorldState before player movement."""
        self._last_state = self.simulation.observe(
            x,
            z,
            player_yaw=yaw,
            in_interior=self.in_interior,
            building_count=building_count,
        )

    def end_frame(
        self,
        x: float,
        z: float,
        *,
        yaw: float = 0.0,
        dx: float = 0.0,
        dz: float = 0.0,
        sprint: bool = False,
        jumped: bool = False,
        interacted: bool = False,
        interact_target: str = "",
        building_count: int = 0,
    ) -> None:
        """Record trajectory after movement and update HUD."""
        if self._last_state is None:
            self.update(x, z, building_count=building_count)
            return

        interact_target = interact_target or self._pending_interact
        if interacted or interact_target:
            action = InteractAction(target_id=interact_target)
        elif dx or dz or sprint or jumped:
            action = PlayerMoveAction(dx=dx, dz=dz, sprint=sprint, jump=jumped)
        else:
            from nyc_world.simulation.actions import WaitAction

            action = WaitAction()

        next_state = self.simulation.observe(
            x,
            z,
            player_yaw=yaw,
            in_interior=self.in_interior,
            building_count=building_count,
        )
        self.simulation.tick = next_state.tick
        self.simulation.record_transition(self._last_state, action, next_state)
        self._last_state = None
        self._pending_interact = ""
        self.update(x, z, building_count=building_count)

    def update(self, x: float, z: float, *, building_count: int = 0) -> None:
        self.interaction.update_player(x, z)
        self.hud.prompt = self.interaction.prompt()
        self.hud.quest_text = self.quests.hud_objective_text()
        self.hud.profile_lines = self.player.profile_lines()
        self.hud.mode = self.interaction.mode

        mind_lines: list[str] = []
        for npc_id in ("maya", "alex"):
            summary = self.simulation.npc_summary(npc_id)
            if summary:
                mind_lines.append(summary)
        self.hud.npc_mind_lines = mind_lines

        sim = self.simulation
        recorder = sim.recorder
        self.hud.simulation_lines = [
            f"tick {sim.tick}",
            f"trajectories: {recorder.step_count if recorder else 0}",
            f"NPCs: {len(getattr(self.city, 'npcs', []))} · vehicles: {len(getattr(self.city, 'vehicles', []))}",
            f"weather: {getattr(getattr(self.city, 'clock', None), 'weather', 'clear')}",
        ]
        weather = getattr(getattr(self.city, "clock", None), "weather", None)
        if hasattr(weather, "value"):
            self.hud.simulation_lines[-1] = f"weather: {weather.value}"
        self.hud.trajectory_steps = recorder.step_count if recorder else 0

    def press_interact(self, x: float, z: float) -> tuple[float, float] | None:
        """Try to interact. Returns new (x, z) if player teleported."""
        if self.interaction.nearest:
            self._pending_interact = self.interaction.nearest.id
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

    def close(self) -> None:
        self.simulation.close()
