"""Game session — interactions, quests, simulation, persistence, and HUD state."""

from __future__ import annotations

from pathlib import Path

from nyc_world.city.city_sim import CitySimulation
from nyc_world.city.subway import SubwayRide, SubwaySimulation, build_subway_graph
from nyc_world.game.interactions import (
    InteractionSystem,
    assign_quest_npcs,
    build_world_interactables,
)
from nyc_world.game.interiors import INTERIORS, Interior
from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager
from nyc_world.game.save import apply_save, capture_save, default_save_path
from nyc_world.feeds import FeedManager
from nyc_world.modes.photo import PhotoMode
from nyc_world.modes.god import GodMode
from nyc_world.modes.imagine import ImagineMode
from nyc_world.modes.twin import TwinMode
from nyc_world.simulation import Simulation
from nyc_world.simulation.actions import InteractAction, PlayerMoveAction
from nyc_world.simulation.event_log import EventLog
from nyc_world.simulation.mystery import (
    MysteryInvestigation,
    discover_clues_at_location,
    discover_clues_from_npc,
    generate_mystery,
    investigation_hud_lines,
)
from nyc_world.simulation.npc_mind import NPCMindRegistry


INTERIOR_SPAWN = (6.0, 8.0)
SUBWAY_SPAWN = (7.0, 4.0)


from dataclasses import dataclass, field


@dataclass
class HudState:
    prompt: str | None = None
    dialogue_lines: list[str] = field(default_factory=list)
    quest_text: str | None = None
    profile_lines: list[str] = field(default_factory=list)
    npc_mind_lines: list[str] = field(default_factory=list)
    npc_memory_lines: list[str] = field(default_factory=list)
    npc_memory_title: str | None = None
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
    mystery_lines: list[str] = field(default_factory=list)
    show_mystery_journal: bool = False
    feed_banner_lines: list[str] = field(default_factory=list)
    subway_lines: list[str] = field(default_factory=list)
    subway_progress: float = 0.0
    twin_lines: list[str] = field(default_factory=list)
    twin_inspector_lines: list[str] = field(default_factory=list)
    imagine_lines: list[str] = field(default_factory=list)
    god_lines: list[str] = field(default_factory=list)
    evolution_lines: list[str] = field(default_factory=list)
    show_evolution_journal: bool = False
    photo_lines: list[str] = field(default_factory=list)
    hide_hud: bool = False


class GameSession:
    """Orchestrates interactions, quests, simulation, and persistence."""

    def __init__(
        self,
        city: CitySimulation,
        spawn_x: float,
        spawn_z: float,
        player: PlayerProfile | None = None,
        *,
        record_trajectories: bool = False,
        trajectory_dir: Path | None = None,
        save_slot: str = "default",
        load_save: bool = True,
        mystery_seed: int = 42,
        live_feeds: bool = False,
        feed_fixture: Path | None = None,
    ) -> None:
        self.city = city
        self.spawn_x = spawn_x
        self.spawn_z = spawn_z
        self.save_slot = save_slot
        self.save_path = default_save_path(save_slot)
        self.player = player or PlayerProfile()
        self.event_log = EventLog()
        minds = getattr(city, "mind_registry", None) or NPCMindRegistry()
        minds.relationships.import_from_profile(self.player)
        self.quests = QuestManager(self.player, minds=minds)
        self.quests.set_agents(getattr(city, "agent_controller", None))
        assign_quest_npcs(city.npcs, spawn_x, spawn_z)
        interactables = build_world_interactables(
            city.landmarks, city.npcs, spawn_x, spawn_z
        )
        self.interaction = InteractionSystem(interactables, self.quests)
        from nyc_world.agents.loader import load_mods_into_city

        load_mods_into_city(city, interactables=self.interaction.interactables)
        self.simulation = Simulation(
            city,
            self.player,
            self.quests,
            minds=minds,
            event_log=self.event_log,
            record_trajectories=record_trajectories,
            trajectory_dir=trajectory_dir,
        )
        self.hud = HudState()
        self.exterior_pos = (spawn_x, spawn_z)
        self._last_state = None
        self._pending_interact = ""
        self.mystery: MysteryInvestigation | None = None
        self._mystery_seed = mystery_seed
        self._loaded_position = None
        self.feeds = FeedManager(offline=not live_feeds, live_weather=live_feeds)
        if feed_fixture and feed_fixture.exists():
            self.feeds.load_from_file(feed_fixture)
            self.feeds.apply_to_sim(city)
        elif live_feeds:
            self.feeds.poll(force=True)
            self.feeds.apply_to_sim(city)
        self._feed_poll_timer = 0.0
        projection = getattr(city, "projection", None)
        self.subway_graph = getattr(city, "subway_graph", None) or build_subway_graph(projection)
        self.subway_sim = getattr(city, "subway_sim", None) or SubwaySimulation(
            graph=self.subway_graph
        )
        if not hasattr(city, "subway_sim"):
            city.subway_sim = self.subway_sim
        if not hasattr(city, "subway_graph"):
            city.subway_graph = self.subway_graph
        self.subway_menu_station: str | None = None
        self.subway_ride: SubwayRide | None = None
        self._pending_teleport: tuple[float, float] | None = None
        self.twin = TwinMode()
        self.imagine = ImagineMode()
        self.god = GodMode()
        self.photo = PhotoMode()
        economy = getattr(city, "economy", None)
        if economy:
            economy.apply_facades(self.interaction.interactables)
        self._last_journal_len = len(economy.journal) if economy else 0

        if load_save and self.save_path.exists():
            from nyc_world.game.save import GameSave

            save = GameSave.load(self.save_path)
            px, pz = apply_save(
                save,
                player=self.player,
                relationships=minds.relationships,
                minds=minds,
                quests=self.quests,
                event_log=self.event_log,
                city=city,
            )
            self.exterior_pos = (px, pz)
            self.simulation.tick = save.tick
            minds.set_time_context(
                tick=save.tick,
                game_day=save.game_day,
                game_time=city.clock.time_str,
            )
            self._loaded_position = (px, pz)
            if save.mystery:
                self.mystery = MysteryInvestigation.from_dict(save.mystery)
            else:
                case = generate_mystery(mystery_seed, landmarks=city.landmarks)
                self.mystery = MysteryInvestigation(case=case)
            economy = getattr(city, "economy", None)
            if economy:
                economy.apply_facades(self.interaction.interactables)
                self._last_journal_len = len(economy.journal)
        else:
            self._loaded_position = None
            case = generate_mystery(mystery_seed, landmarks=city.landmarks)
            self.mystery = MysteryInvestigation(case=case)
            print(f"Mystery: {case.title} — something happened at {case.crime_time}.")

    @property
    def in_interior(self) -> bool:
        return self.interaction.mode == "interior"

    @property
    def in_subway(self) -> bool:
        return self.interaction.in_subway

    @property
    def in_twin(self) -> bool:
        return self.twin.active

    @property
    def in_subway_menu(self) -> bool:
        return self.subway_menu_station is not None

    @property
    def in_god(self) -> bool:
        return self.god.active

    @property
    def in_photo(self) -> bool:
        return self.photo.active

    def toggle_photo(self, x: float, y: float, z: float, *, yaw: float, pitch: float) -> bool:
        clock = self.city.clock
        active = self.photo.toggle(
            px=x, py=y, pz=z, yaw=yaw, pitch=pitch,
            sim_hour=clock.hour, sim_minute=clock.minute,
        )
        self.hud.hide_hud = active
        self.hud.photo_lines = self.photo.hud_lines() if active else []
        return active

    def take_photo(self, width: int, height: int) -> Path:
        from pathlib import Path

        path = self.photo.capture_frame(width, height)
        self.hud.photo_lines = self.photo.hud_lines() + [f"Saved {path.name}"]
        return path

    def toggle_evolution_journal(self) -> None:
        self.hud.show_evolution_journal = not self.hud.show_evolution_journal
        economy = getattr(self.city, "economy", None)
        if self.hud.show_evolution_journal and economy:
            self.hud.evolution_lines = economy.journal_lines()
        else:
            self.hud.evolution_lines = []

    def toggle_god(self) -> bool:
        active = self.god.toggle()
        if active:
            self.hud.god_lines = self.god.hud_lines(self.city)
        else:
            self.hud.god_lines = []
        return active

    def god_set_time(self, hour: int, minute: int = 0) -> None:
        self.god.apply_time(self.city, hour, minute, event_log=self.event_log)
        self.hud.god_lines = self.god.hud_lines(self.city)

    def god_set_weather(self, weather: str) -> None:
        self.god.apply_weather(self.city, weather, event_log=self.event_log)
        self.hud.god_lines = self.god.hud_lines(self.city)

    def god_spawn_festival(self, x: float, z: float) -> int:
        count = self.god.spawn_festival(self.city, x, z, event_log=self.event_log)
        self.hud.god_lines = self.god.hud_lines(self.city)
        return count

    def god_close_road(self) -> bool:
        ok = self.god.close_road(self.city, event_log=self.event_log)
        self.hud.god_lines = self.god.hud_lines(self.city)
        return ok

    def god_clear_closures(self) -> None:
        self.god.clear_road_closures(self.city, event_log=self.event_log)
        self.hud.god_lines = self.god.hud_lines(self.city)

    def toggle_twin(self) -> bool:
        active = self.twin.toggle()
        self.hud.mode = "twin" if active else self.interaction.mode
        if active:
            self.hud.twin_inspector_lines = []
        return active

    def twin_select_at(self, x: float, z: float) -> None:
        if not self.twin.active:
            return
        npcs = getattr(self.city, "npcs", [])
        vehicles = getattr(self.city, "vehicles", [])
        if self.twin.select_nearest(npcs, vehicles, x, z):
            if self.twin.selected_kind == "npc" and self.twin.selected_id:
                self.hud.twin_inspector_lines = self.twin.inspector_lines(
                    self.twin.selected_id,
                    minds=self.simulation.minds,
                    agents=getattr(self.city, "agent_controller", None),
                )
            else:
                self.hud.twin_inspector_lines = [
                    self.twin.selected_id or "entity",
                    "Vehicle — no brain data.",
                ]

    def toggle_imagine(self) -> bool:
        if not self.twin.active:
            return False
        return self.imagine.toggle()

    def cycle_imagine_scenario(self) -> None:
        if self.imagine.active:
            self.imagine.cycle_scenario()

    def run_imagination(self, x: float, z: float) -> None:
        if not self.imagine.active:
            return
        from nyc_world.simulation.model.imagination import run_what_if, seed_npc_positions

        state = self.simulation.observe(
            x,
            z,
            in_interior=self.in_interior,
            building_count=self._last_state.building_count if self._last_state else 0,
        )
        state = seed_npc_positions(state)
        patch = self.imagine.scenario.patch
        if patch.weather_at_hour is not None:
            state.clock.hour = max(0, patch.weather_at_hour - 1)
            state.clock.minute = 30
        elif state.clock.hour >= 17:
            state.clock.hour = 14
            state.clock.minute = 0
        result = run_what_if(
            state,
            patch,
            horizon_minutes=self.imagine.horizon_minutes,
            seed=42,
        )
        self.imagine.set_result(result.diff_lines)
        self.hud.imagine_lines = self.imagine.menu_lines + [""] + result.diff_lines

    @property
    def current_interior(self) -> Interior | None:
        if self.in_subway:
            return INTERIORS.get("subway_car_interior")
        iid = self.interaction.current_interior_id
        return INTERIORS.get(iid) if iid else None

    def _time_context(self) -> tuple[int, int, str]:
        clock = self.city.clock
        return clock.day, self.simulation.tick, clock.time_str

    def begin_frame(self, x: float, z: float, *, yaw: float = 0.0, building_count: int = 0) -> None:
        game_day, tick, game_time = self._time_context()
        self.simulation.mystery = self.mystery
        self.simulation.minds.set_time_context(tick=tick, game_day=game_day, game_time=game_time)
        self.quests.set_time_context(tick=tick, game_day=game_day)
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
        dt: float = 0.0,
    ) -> None:
        if self._last_state is None:
            self.update(x, z, building_count=building_count, dt=dt)
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
        self.update(x, z, building_count=building_count, dt=dt)

    def update(self, x: float, z: float, *, building_count: int = 0, dt: float = 0.0) -> tuple[float, float] | None:
        economy = getattr(self.city, "economy", None)
        if economy and len(economy.journal) != self._last_journal_len:
            economy.apply_facades(self.interaction.interactables)
            self._last_journal_len = len(economy.journal)
            if self.hud.show_evolution_journal:
                self.hud.evolution_lines = economy.journal_lines()

        new_pos = self._update_subway_ride(dt)

        self._feed_poll_timer += dt
        if self._feed_poll_timer >= self.feeds.poll_interval_s:
            self._feed_poll_timer = 0.0
            self.feeds.poll()
            self.feeds.apply_to_sim(self.city)

        self.interaction.update_player(x, z)
        self.hud.prompt = self.interaction.prompt()
        self.hud.quest_text = self.quests.hud_objective_text()
        self.quests.refresh_generated_quests()
        self.simulation.minds.relationships.sync_to_profile(self.player)
        self.hud.profile_lines = self.player.profile_lines()
        self.hud.mode = self.interaction.mode

        mind_lines: list[str] = []
        nearest = self.interaction.nearest
        if nearest and nearest.kind.name == "NPC":
            controller = getattr(self.city, "agent_controller", None)
            brain = controller.get(nearest.id) if controller else None
            if brain:
                mind_lines = brain.hud_lines()
            elif nearest.id in ("maya", "alex"):
                summary = self.simulation.npc_summary(nearest.id)
                if summary:
                    mind_lines = [summary]
        if not mind_lines:
            for npc_id in ("maya", "alex"):
                summary = self.simulation.npc_summary(npc_id)
                if summary:
                    mind_lines.append(summary)
        self.hud.npc_mind_lines = mind_lines

        nearest = self.interaction.nearest
        if nearest and nearest.kind.name == "NPC":
            panel = self.simulation.minds.memory_panel_lines(nearest.id)
            if panel:
                self.hud.npc_memory_lines = panel
                self.hud.npc_memory_title = nearest.label.upper()
            else:
                self.hud.npc_memory_lines = []
                self.hud.npc_memory_title = None
        else:
            self.hud.npc_memory_lines = []
            self.hud.npc_memory_title = None

        sim = self.simulation
        recorder = sim.recorder
        game_day, tick, _ = self._time_context()
        self.hud.simulation_lines = [
            f"Day {game_day} · tick {sim.tick}",
            f"trajectories: {recorder.step_count if recorder else 0}",
            f"events: {len(self.event_log.entries)}",
            f"NPCs: {len(getattr(self.city, 'npcs', []))} · vehicles: {len(getattr(self.city, 'vehicles', []))}",
            f"weather: {getattr(getattr(self.city, 'clock', None), 'weather', 'clear')}",
        ]
        weather = getattr(getattr(self.city, "clock", None), "weather", None)
        if hasattr(weather, "value"):
            self.hud.simulation_lines[-1] = f"weather: {weather.value}"
        self.hud.trajectory_steps = recorder.step_count if recorder else 0

        if self.mystery and self.hud.show_mystery_journal:
            self.hud.mystery_lines = investigation_hud_lines(self.mystery)
        else:
            self.hud.mystery_lines = []

        self.hud.feed_banner_lines = self.feeds.hud_banner()
        if self.feeds.modifiers.transit_affected_npcs and self.hud.show_geo_debug:
            self.hud.simulation_lines.append(
                f"feed: {self.feeds.modifiers.transit_affected_npcs} NPCs near subway (delay)"
            )
        if self.subway_sim.commuter_count and self.city.clock.is_raining:
            rate = self.subway_sim.commuter_subway_rate()
            if self.hud.show_geo_debug and rate > 0:
                self.hud.simulation_lines.append(
                    f"subway: {rate:.0%} commuters rode ({self.subway_sim.npc_ride_count})"
                )

        if self.subway_menu_station:
            self.hud.subway_lines = self.subway_graph.menu_lines(self.subway_menu_station)
        elif self.subway_ride:
            dest = self.subway_graph.stations[self.subway_ride.dest_id].name
            self.hud.subway_lines = [
                f"Riding to {dest}...",
                f"{'▓' * int(self.subway_ride.progress * 20)}{'░' * (20 - int(self.subway_ride.progress * 20))}",
            ]
            self.hud.subway_progress = self.subway_ride.progress
        else:
            self.hud.subway_lines = []
            self.hud.subway_progress = 0.0

        if self.twin.active:
            clock = self.city.clock
            self.hud.twin_lines = self.twin.hud_lines(
                npc_count=len(getattr(self.city, "npcs", [])),
                vehicle_count=len(getattr(self.city, "vehicles", [])),
                tick=self.simulation.tick,
                weather=clock.weather.value,
                time_str=clock.time_str,
            )
        else:
            self.hud.twin_lines = []
            self.hud.twin_inspector_lines = []

        if self.imagine.active:
            self.hud.imagine_lines = (
                self.imagine.menu_lines + ([""] + self.imagine.diff_lines if self.imagine.diff_lines else [])
            )
        else:
            self.hud.imagine_lines = []

        if self.god.active:
            self.hud.god_lines = self.god.hud_lines(self.city)
        else:
            self.hud.god_lines = []

        if self.hud.show_evolution_journal and economy:
            self.hud.evolution_lines = economy.journal_lines()
        elif not self.hud.show_evolution_journal:
            self.hud.evolution_lines = []

        self._pending_teleport = new_pos
        return new_pos

    def _discover_mystery_clues(self, target_id: str) -> list[str]:
        if not self.mystery or self.mystery.solved:
            return []
        lines: list[str] = []
        nearest = self.interaction.nearest
        if nearest and nearest.kind.name == "NPC":
            lines.extend(
                discover_clues_from_npc(
                    self.mystery,
                    target_id,
                    self.simulation.minds.relationships,
                )
            )
        location_id = target_id
        if nearest and getattr(nearest, "interior_id", None):
            location_id = nearest.interior_id
        lines.extend(discover_clues_at_location(self.mystery, location_id))
        return lines

    def try_accuse_nearest(self) -> list[str]:
        if not self.mystery or self.mystery.solved:
            return ["No active mystery."]
        nearest = self.interaction.nearest
        if not nearest or nearest.kind.name != "NPC":
            return ["Get closer to an NPC to accuse them."]
        if len(self.mystery.discovered_entry_ids) < 3:
            return ["Gather more clues before accusing anyone."]
        _ok, msg = self.mystery.try_accuse(nearest.id)
        return [msg]

    def open_subway_menu(self, x: float, z: float) -> None:
        station = self.subway_graph.nearest_station(x, z)
        if not station:
            self.hud.dialogue_lines = ["No subway station nearby."]
            return
        self.exterior_pos = (x, z)
        self.subway_menu_station = station
        self.hud.dialogue_lines = []

    def cancel_subway_menu(self) -> None:
        self.subway_menu_station = None
        self.hud.subway_lines = []

    def select_subway_destination(self, index: int) -> bool:
        if not self.subway_menu_station:
            return False
        dests = self.subway_graph.destination_ids(self.subway_menu_station)
        if index < 0 or index >= len(dests):
            return False
        dest_id = dests[index]
        origin = self.subway_menu_station
        ride = self.subway_sim.start_ride("player", origin, dest_id)
        if not ride:
            return False
        self.subway_ride = ride
        self.subway_menu_station = None
        self.interaction.enter_subway(origin)
        from nyc_world.game.dialogue_lines import DIALOGUE

        self.hud.dialogue_lines = list(DIALOGUE.get("subway_ride", []))
        return True

    def _update_subway_ride(self, dt: float) -> tuple[float, float] | None:
        if not self.subway_ride:
            return None
        finished = self.subway_sim.update(dt)
        for ride in finished:
            if ride.rider_id != "player":
                continue
            pos = self.subway_sim.exit_position(ride)
            self.subway_ride = None
            self.interaction.exit_subway()
            from nyc_world.game.dialogue_lines import DIALOGUE

            dest_name = self.subway_graph.stations[ride.dest_id].name
            self.hud.dialogue_lines = list(DIALOGUE.get("subway_arrive", [])) + [
                f"You arrive at {dest_name}."
            ]
            game_day, tick, game_time = self._time_context()
            self.event_log.append(
                tick=tick,
                game_day=game_day,
                game_time=game_time,
                actor_id="player",
                action="subway_exit",
                location_id=ride.dest_id,
                details=dest_name,
            )
            return pos
        return None

    def press_interact(self, x: float, z: float) -> tuple[float, float] | None:
        if self.interaction.nearest:
            self._pending_interact = self.interaction.nearest.id
        result = self.interaction.try_interact(x, z)
        if result.open_subway:
            self.open_subway_menu(x, z)
            self.update(x, z)
            return None
        if result.lines:
            self.hud.dialogue_lines = result.lines
        game_day, tick, game_time = self._time_context()
        target = self._pending_interact or (self.interaction.nearest.id if self.interaction.nearest else "")
        if target:
            clue_lines = self._discover_mystery_clues(target)
            if clue_lines:
                self.hud.dialogue_lines = list(self.hud.dialogue_lines) + clue_lines
            self.event_log.append(
                tick=tick,
                game_day=game_day,
                game_time=game_time,
                actor_id="player",
                action="interact",
                location_id=target,
            )
        self.update(x, z)

        if result.entered_interior:
            self.exterior_pos = (x, z)
            if self.mystery and result.entered_interior:
                interior_clues = discover_clues_at_location(self.mystery, result.entered_interior)
                if interior_clues:
                    self.hud.dialogue_lines = list(self.hud.dialogue_lines) + interior_clues
            return INTERIOR_SPAWN
        if result.exited_interior:
            return self.exterior_pos
        return None

    def subway_spawn(self) -> tuple[float, float]:
        return SUBWAY_SPAWN

    def save(self, x: float, z: float) -> Path:
        clock = self.city.clock
        controller = getattr(self.city, "agent_controller", None)
        game_save = capture_save(
            player=self.player,
            relationships=self.simulation.minds.relationships,
            minds=self.simulation.minds,
            quests=self.quests,
            event_log=self.event_log,
            tick=self.simulation.tick,
            game_day=clock.day,
            player_x=x,
            player_z=z,
            clock_hour=clock.hour,
            clock_minute=clock.minute,
            clock_weather=clock.weather.value,
            agents=controller.to_dict() if controller else {},
            mystery=self.mystery.to_dict() if self.mystery else {},
            economy=getattr(self.city, "economy", None).to_dict()
            if getattr(self.city, "economy", None)
            else {},
        )
        game_save.write(self.save_path)
        return self.save_path

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
