"""Simulation engine — WorldState(t) + action → WorldState(t+1)."""

from __future__ import annotations

from pathlib import Path

from nyc_world.simulation.actions import Action, InteractAction, PlayerMoveAction, WaitAction
from nyc_world.simulation.adapters import capture_world_state
from nyc_world.simulation.event_log import EventLog
from nyc_world.simulation.npc_mind import NPCMindRegistry
from nyc_world.simulation.state import WorldState
from nyc_world.simulation.trajectory import TrajectoryRecorder


class Simulation:
    """Formal simulation loop wrapping the living city."""

    def __init__(
        self,
        city,
        player_profile,
        quest_manager,
        *,
        minds: NPCMindRegistry | None = None,
        event_log: EventLog | None = None,
        record_trajectories: bool = False,
        trajectory_dir: Path | None = None,
    ) -> None:
        self.city = city
        self.player = player_profile
        self.quests = quest_manager
        self.minds = minds or getattr(city, "mind_registry", None) or NPCMindRegistry()
        self.event_log = event_log or EventLog()
        self.tick = 0
        self._building_count = 0
        self.mystery = None
        self.recorder = TrajectoryRecorder(trajectory_dir) if record_trajectories else None
        if record_trajectories and self.recorder:
            self.recorder.open()

    def observe(
        self,
        player_x: float,
        player_z: float,
        *,
        player_yaw: float = 0.0,
        in_interior: bool = False,
        building_count: int = 0,
    ) -> WorldState:
        self._building_count = building_count
        return capture_world_state(
            self.city,
            self.player,
            self.quests,
            self.minds,
            tick=self.tick,
            player_x=player_x,
            player_z=player_z,
            player_yaw=player_yaw,
            in_interior=in_interior,
            building_count=building_count,
            event_count=len(self.event_log.entries),
            mystery=self.mystery,
        )

    def advance_world(
        self,
        dt: float,
        *,
        speed_multiplier: float = 1.0,
        time_scale: float = 1.0,
    ) -> None:
        """Tick city clock, NPC movement, vehicles, and NPC minds."""
        if time_scale <= 0.0:
            return
        mult = speed_multiplier * time_scale
        self.city.update(dt, speed_multiplier=mult)
        economy = getattr(self.city, "economy", None)
        if economy:
            economy.maybe_weekly_tick(
                self.city.clock.day,
                minds=self.minds,
                event_log=self.event_log,
            )
        positions = {npc.name: (npc.x, npc.z) for npc in self.city.npcs}
        self.minds.update(
            self.city.clock.hour,
            self.city.clock.minute,
            self.city.clock.is_raining,
            positions,
        )

    def apply_action_to_state(self, state: WorldState, action: Action) -> WorldState:
        """Pure transition for recorded trajectories (lightweight prediction helper)."""
        next_state = WorldState.from_dict(state.to_dict())
        next_state.tick = state.tick + 1
        next_state.clock.tick = next_state.tick

        if isinstance(action, PlayerMoveAction):
            next_state.player.x += action.dx
            next_state.player.z += action.dz
            # Advance game clock slightly on movement frames.
            total_min = next_state.clock.hour * 60 + next_state.clock.minute + 0.05
            next_state.clock.hour = int(total_min // 60) % 24
            next_state.clock.minute = int(total_min % 60)
        elif isinstance(action, InteractAction):
            mind = self.minds.get(action.target_id)
            if mind:
                mind.remember("player_interacted", next_state.tick, action.target_id)
            clock = self.city.clock
            self.event_log.append(
                tick=next_state.tick,
                game_day=clock.day,
                game_time=clock.time_str,
                actor_id="player",
                action="interact",
                location_id=action.target_id,
            )
        return next_state

    def step(
        self,
        state: WorldState,
        action: Action,
        dt: float,
        *,
        speed_multiplier: float = 1.0,
        building_count: int = 0,
    ) -> WorldState:
        """Advance simulation: apply action, tick world, return new snapshot."""
        if isinstance(action, PlayerMoveAction):
            px = state.player.x + action.dx
            pz = state.player.z + action.dz
        else:
            px, pz = state.player.x, state.player.z

        self.advance_world(dt, speed_multiplier=speed_multiplier)
        self.tick += 1

        next_state = self.observe(
            px,
            pz,
            player_yaw=state.player.yaw,
            in_interior=state.player.in_interior,
            building_count=building_count or self._building_count,
        )

        if self.recorder:
            self.recorder.record(state, action, next_state)

        return next_state

    def record_transition(self, state: WorldState, action: Action, next_state: WorldState) -> None:
        if self.recorder:
            self.recorder.record(state, action, next_state)

    def close(self) -> None:
        if self.recorder:
            self.recorder.close()

    def npc_summary(self, npc_id: str) -> str | None:
        return self.minds.summary_for(npc_id)
