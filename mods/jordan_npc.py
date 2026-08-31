"""Example mod — Jordan, photo shop clerk."""

from nyc_world.agents import NPC, Needs, Personality, Schedule


def register(registry):
    registry.register(
        NPC(
            id="jordan",
            name="Jordan",
            personality=Personality(curiosity=0.85, kindness=0.75),
            needs=Needs(money=0.35),
            schedule=Schedule.workplace("photo_shop", hour=10),
            dialogue_pack="jordan_default",
            color=(0.55, 0.7, 0.9),
        )
    )
