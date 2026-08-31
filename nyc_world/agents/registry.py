"""Register mod NPCs into the live city simulation."""

from __future__ import annotations

from nyc_world.agents.api import NPC, ScheduleStop
from nyc_world.agents.dialogue import greeting_key, register_dialogue_pack
from nyc_world.city.npcs import NPC as CityNPC
from nyc_world.city.npcs import ScheduleStop as CityScheduleStop
from nyc_world.game.interactables import Interactable, InteractableKind
from nyc_world.simulation.agent import AgentBrain, AgentNeeds, Personality as BrainPersonality

LOCATION_OFFSETS: dict[str, tuple[float, float]] = {
    "cafe_village": (30.0, -20.0),
    "library_building": (80.0, -50.0),
    "nyu_library": (80.0, -50.0),
    "photo_shop": (40.0, 0.0),
    "subway_wsp": (-40.0, 30.0),
    "west_4th_records": (55.0, -30.0),
    "bleecker_boutique": (20.0, 35.0),
    "thompson_bar": (-25.0, -15.0),
    "washington_cart": (-10.0, 45.0),
    "macdougal_gallery": (35.0, 25.0),
    "sullivan_bakery": (-45.0, -25.0),
    "laguardia_plants": (60.0, 15.0),
    "perry_studio": (-30.0, 40.0),
    "christopher_cuts": (15.0, -40.0),
}


def resolve_location(city, location_id: str) -> tuple[float, float]:
    for lm in getattr(city, "landmarks", []):
        name = (getattr(lm, "name", "") or "").lower()
        if location_id.replace("_", " ") in name or location_id in name:
            return lm.x, lm.z
    if location_id in LOCATION_OFFSETS:
        ox, oz = LOCATION_OFFSETS[location_id]
        return city.spawn_x + ox, city.spawn_z + oz
    return city.spawn_x, city.spawn_z


class NPCRegistry:
    """Collect mod NPCs and apply them to a running city."""

    def __init__(self) -> None:
        self._npcs: dict[str, NPC] = {}

    def register(self, npc: NPC) -> None:
        self._npcs[npc.id] = npc

    def all(self) -> list[NPC]:
        return list(self._npcs.values())

    def to_dict(self) -> dict:
        return {npc_id: npc.to_dict() for npc_id, npc in self._npcs.items()}

    @classmethod
    def from_dict(cls, data: dict) -> NPCRegistry:
        registry = cls()
        for npc_data in data.values():
            registry.register(NPC.from_dict(npc_data))
        return registry

    def apply_to_city(self, city, *, interactables: list | None = None) -> list[str]:
        spawned: list[str] = []
        streets = getattr(city, "streets", None)
        if not streets:
            return spawned

        minds = getattr(city, "mind_registry", None)
        controller = getattr(city, "agent_controller", None)
        existing = {n.name for n in city.npcs}

        for mod_npc in self._npcs.values():
            if mod_npc.id in existing:
                continue
            wx, wz = (
                (mod_npc.x, mod_npc.z)
                if mod_npc.x is not None and mod_npc.z is not None
                else resolve_location(city, mod_npc.schedule.stops[0].location_id if mod_npc.schedule.stops else "cafe_village")
            )
            schedule = self._build_schedule(city, mod_npc)
            city_npc = CityNPC(
                name=mod_npc.id,
                personality="mod",
                x=wx,
                z=wz,
                speed=mod_npc.speed,
                schedule=schedule,
                color=mod_npc.color,
            )
            city.npcs.append(city_npc)
            spawned.append(mod_npc.id)

            if controller:
                workplace = resolve_location(
                    city,
                    mod_npc.schedule.stops[0].location_id if mod_npc.schedule.stops else "cafe_village",
                )
                cafe = resolve_location(city, "cafe_village")
                park = (city.spawn_x - 20, city.spawn_z + 10)
                brain = AgentBrain(
                    npc_id=mod_npc.id,
                    display_name=mod_npc.name,
                    personality=BrainPersonality(
                        extroversion=mod_npc.personality.extroversion,
                        curiosity=mod_npc.personality.curiosity,
                        kindness=mod_npc.personality.kindness,
                        risk_tolerance=mod_npc.personality.risk_tolerance,
                        ambition=mod_npc.personality.ambition,
                    ),
                    needs=AgentNeeds(
                        hunger=mod_npc.needs.hunger,
                        energy=mod_npc.needs.energy,
                        social=mod_npc.needs.social,
                        money=mod_npc.needs.money,
                    ),
                    home=(wx, wz),
                    workplace=workplace,
                    cafe=cafe,
                    park=park,
                )
                controller.register(brain)

            if mod_npc.dialogue_pack:
                register_dialogue_pack(
                    greeting_key(mod_npc.id, mod_npc.dialogue_pack),
                    [f"{mod_npc.name}: Hi — I'm new in the neighborhood."],
                )

            if interactables is not None and mod_npc.interactable:
                interactables.append(
                    Interactable(
                        id=mod_npc.id,
                        kind=InteractableKind.NPC,
                        x=wx,
                        z=wz,
                        label=mod_npc.name,
                        dialogue_id=greeting_key(mod_npc.id, mod_npc.dialogue_pack),
                        quest_npc=False,
                        emoji="🧑",
                    )
                )

        return spawned

    def _build_schedule(self, city, mod_npc: NPC) -> list[CityScheduleStop]:
        if not mod_npc.schedule.stops:
            x, z = resolve_location(city, "cafe_village")
            return [CityScheduleStop(9, 0, x, z, "idle")]
        stops: list[CityScheduleStop] = []
        for stop in mod_npc.schedule.stops:
            x, z = resolve_location(city, stop.location_id)
            stops.append(
                CityScheduleStop(
                    stop.hour,
                    stop.minute,
                    x,
                    z,
                    stop.label or stop.location_id,
                )
            )
        return stops
