"""Example: register a custom NPC without forking core game code."""

from nyc_world.agents import NPC, NPCRegistry, Needs, Personality, Schedule


def build_example_npc() -> NPC:
    return NPC(
        id="river",
        name="River",
        personality=Personality(curiosity=0.9, kindness=0.6),
        needs=Needs(money=0.5, social=0.7),
        schedule=Schedule.workplace("library_building", hour=8),
        dialogue_pack="river_default",
    )


def register(registry: NPCRegistry) -> None:
    registry.register(build_example_npc())


if __name__ == "__main__":
    from nyc_world.city.city_sim import CitySimulation
    from nyc_world.core.projection import GeoProjection
    from nyc_world.paths import DEFAULT_META_PATH

    projection = GeoProjection.from_file(DEFAULT_META_PATH)
    city = CitySimulation(projection, 100.0, 100.0, npc_count=4, vehicle_count=0)
    city.register_npc(build_example_npc())
    print(f"Spawned mod NPCs: {[n.name for n in city.npcs if n.personality == 'mod']}")
