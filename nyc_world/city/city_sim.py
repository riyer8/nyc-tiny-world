"""Orchestrates the living city simulation."""

from __future__ import annotations

from nyc_world.city.landmarks import load_landmarks_for_area
from nyc_world.city.npcs import spawn_npcs
from nyc_world.city.streets import StreetNetwork, load_street_network
from nyc_world.city.vehicles import spawn_vehicles
from nyc_world.city.world_clock import WorldClock
from nyc_world.core.projection import GeoProjection
from nyc_world.city.subway import SubwaySimulation, build_subway_graph
from nyc_world.feeds.effects import SimulationModifiers
from nyc_world.simulation.agent import AgentController
from nyc_world.simulation.economy import CityEconomy, seed_village_economy
from nyc_world.simulation.npc_mind import NPCMindRegistry

DEFAULT_SIMULATION_RADIUS_M = 300.0


class CitySimulation:
    """Streets, landmarks, NPCs, vehicles, time/weather, and NPC cognition."""

    def __init__(
        self,
        projection: GeoProjection,
        spawn_x: float,
        spawn_z: float,
        *,
        npc_count: int = 48,
        vehicle_count: int = 32,
        mind_registry: NPCMindRegistry | None = None,
        simulation_radius_m: float | None = None,
    ) -> None:
        self.projection = projection
        self.spawn_x = spawn_x
        self.spawn_z = spawn_z
        self.simulation_radius_m = simulation_radius_m or DEFAULT_SIMULATION_RADIUS_M
        self.clock = WorldClock(hour=8, minute=0)
        self.mind_registry = mind_registry or NPCMindRegistry()
        self.mind_registry.register_quest_npcs()
        self.streets: StreetNetwork | None = load_street_network(projection)
        self.landmarks = load_landmarks_for_area(projection)

        if self.streets:
            self.npcs = spawn_npcs(
                self.streets, self.landmarks, spawn_x, spawn_z, count=npc_count
            )
            self.vehicles = spawn_vehicles(self.streets, count=vehicle_count)
        else:
            self.npcs = []
            self.vehicles = []

        from nyc_world.game.interactions import assign_quest_npcs

        assign_quest_npcs(self.npcs, spawn_x, spawn_z)

        self.agent_controller = AgentController.from_npcs(
            self.npcs,
            self.landmarks,
            spawn_x=spawn_x,
            spawn_z=spawn_z,
            minds=self.mind_registry,
        )
        from nyc_world.city.landmarks import CAFE, SUBWAY

        self.subway_positions = [
            (lm.x, lm.z) for lm in self.landmarks if lm.kind == SUBWAY
        ]
        self.cafe_positions = [
            (lm.x, lm.z) for lm in self.landmarks if lm.kind == CAFE
        ]
        self.feed_modifiers = SimulationModifiers()
        self.subway_graph = build_subway_graph(projection)
        self.subway_sim = SubwaySimulation(graph=self.subway_graph)
        self.economy = seed_village_economy()
        self._tick = 0
        self.mod_registry = None

    def update(
        self,
        dt: float,
        *,
        speed_multiplier: float = 1.0,
        player_x: float | None = None,
        player_z: float | None = None,
    ) -> None:
        sim_dt = dt * speed_multiplier
        self.clock.advance(sim_dt)
        self._tick += 1
        if not self.streets:
            return
        game_minutes = self.clock.hour * 60 + self.clock.minute + self.clock.minute / 60.0
        radius_sq = self.simulation_radius_m * self.simulation_radius_m
        feed_mods = getattr(self, "feed_modifiers", SimulationModifiers())
        subway_sim = getattr(self, "subway_sim", None)
        commuter_total = 0

        self.agent_controller.sync_quest_goals(self.mind_registry)

        for npc in self.npcs:
            if npc.personality == "commuter":
                commuter_total += 1
            agent_mode = False
            if player_x is not None and player_z is not None:
                dx = npc.x - player_x
                dz = npc.z - player_z
                agent_mode = dx * dx + dz * dz <= radius_sq
            else:
                agent_mode = True

            if agent_mode:
                nearby = self._count_nearby_npcs(npc, radius_m=20.0)
                near_subway = self._near_any(npc.x, npc.z, self.subway_positions, 45.0)
                near_cafe = self._near_any(npc.x, npc.z, self.cafe_positions, 35.0)
                brain = self.agent_controller.get(npc.name)
                if (
                    subway_sim
                    and brain
                    and near_subway
                    and npc.personality == "commuter"
                    and self.clock.is_raining
                ):
                    tx, tz = action_target_for_npc(brain)
                    subway_sim.try_npc_ride(
                        npc,
                        target_x=tx,
                        target_z=tz,
                        is_raining=self.clock.is_raining,
                    )
                self.agent_controller.update_npc(
                    npc,
                    self.streets,
                    self.clock,
                    sim_dt,
                    nearby_npc_count=nearby,
                    minds=self.mind_registry,
                    feed_modifiers=feed_mods,
                    near_subway=near_subway,
                    near_cafe=near_cafe,
                )

            if self.clock.is_raining:
                mind = self.mind_registry.get(npc.name)
                if mind and mind.hates_rain:
                    npc.speed = max(0.9, npc.speed * 0.95)
            npc.update(
                sim_dt,
                self.clock,
                self.streets,
                game_minutes,
                agent_mode=agent_mode,
            )

        for vehicle in self.vehicles:
            vehicle.update(sim_dt, self.streets)

        positions = {npc.name: (npc.x, npc.z) for npc in self.npcs}
        self.mind_registry.set_time_context(
            tick=self._tick,
            game_day=self.clock.day,
            game_time=self.clock.time_str,
        )
        self.mind_registry.update(
            self.clock.hour,
            self.clock.minute,
            self.clock.is_raining,
            positions,
        )
        if subway_sim:
            subway_sim.commuter_count = max(subway_sim.commuter_count, commuter_total)

    def _count_nearby_npcs(self, npc, radius_m: float) -> int:
        radius_sq = radius_m * radius_m
        count = 0
        for other in self.npcs:
            if other.name == npc.name:
                continue
            dx = other.x - npc.x
            dz = other.z - npc.z
            if dx * dx + dz * dz <= radius_sq:
                count += 1
        return count

    @staticmethod
    def _near_any(x: float, z: float, positions: list[tuple[float, float]], radius_m: float) -> bool:
        radius_sq = radius_m * radius_m
        for px, pz in positions:
            dx, dz = x - px, z - pz
            if dx * dx + dz * dz <= radius_sq:
                return True
        return False

    @property
    def street_scene(self):
        return self.streets.scene if self.streets else None

    def register_npc(self, npc, *, interactables: list | None = None) -> str | None:
        from nyc_world.agents.registry import NPCRegistry

        registry = self.mod_registry or NPCRegistry()
        registry.register(npc)
        self.mod_registry = registry
        spawned = registry.apply_to_city(self, interactables=interactables)
        return spawned[0] if spawned else None

    def summary(self) -> str:
        parts = [
            f"{len(self.landmarks)} landmarks",
            f"{len(self.npcs)} NPCs",
            f"{len(self.vehicles)} vehicles",
            f"{len(self.agent_controller.brains)} agent brains",
        ]
        if self.streets:
            parts.insert(0, f"{len(self.streets.scene.road_quads)} road segments")
        return ", ".join(parts)


def action_target_for_npc(brain) -> tuple[float, float]:
    from nyc_world.simulation.agent import action_target

    return action_target(brain, brain.current_action or "work")
