"""Generate procedural mysteries with reproducible backstory timelines."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from nyc_world.simulation.event_log import EventLog
from nyc_world.simulation.mystery.case import MysteryCase

if TYPE_CHECKING:
    from nyc_world.city.landmarks import Landmark3D


MYSTERY_TITLES = [
    "The Midnight Disappearance",
    "The Village Cafe Theft",
    "The Case of the Missing Camera",
]


def _time_to_minutes(time_str: str) -> int:
    parts = time_str.replace(" AM", "").replace(" PM", "").split(":")
    hour = int(parts[0])
    minute = int(parts[1]) if len(parts) > 1 else 0
    if "PM" in time_str and hour != 12:
        hour += 12
    if "AM" in time_str and hour == 12:
        hour = 0
    return hour * 60 + minute


def generate_mystery(
    seed: int,
    *,
    victim_id: str = "maya",
    suspect_pool: list[str] | None = None,
    locations: list[str] | None = None,
    landmarks: list[Landmark3D] | None = None,
) -> MysteryCase:
    """Build a theft mystery with a seeded backstory event log."""
    rng = random.Random(seed)
    suspects = suspect_pool or ["alex", "npc_3", "npc_7", "npc_12"]
    culprit = rng.choice(suspects)
    locs = locations or ["cafe_village", "library_interior", "photo_shop"]
    crime_location = rng.choice(locs)
    title = rng.choice(MYSTERY_TITLES)
    crime_time = "11:42 PM"
    crime_day = 1

    log = EventLog()
    tick = 0

    def add(
        actor: str,
        action: str,
        location: str,
        time: str,
        *,
        visibility: str = "public",
        details: str = "",
    ) -> None:
        nonlocal tick
        tick += 1
        log.append(
            tick=tick,
            game_day=crime_day,
            game_time=time,
            actor_id=actor,
            action=action,
            location_id=location,
            details=details,
            visibility=visibility,
        )

    add(victim_id, "enter", "cafe_village", "11:35 PM")
    if culprit != victim_id:
        add(culprit, "enter", "cafe_village", "11:38 PM", visibility="witness_only")
    add("alex", "enter", "cafe_village", "11:39 PM")
    add("alex", "leave", "cafe_village", "11:41 PM")
    add(
        culprit,
        "take",
        crime_location,
        crime_time,
        visibility="hidden",
        details="camera",
    )
    add("vehicle_7", "depart", "cafe_village", "11:48 PM", details="eastbound taxi")
    add(victim_id, "report", crime_location, "12:03 AM", details="theft reported")

    if landmarks:
        for lm in landmarks[:3]:
            if lm.kind == "cafe":
                add("barista", "witness", "cafe_village", "11:40 PM", visibility="witness_only",
                    details=f"saw someone near {lm.name}")

    return MysteryCase(
        mystery_id=f"mystery_{seed}",
        title=title,
        seed=seed,
        crime_type="theft",
        victim_id=victim_id,
        culprit_id=culprit,
        stolen_item="camera",
        crime_location=crime_location,
        crime_time=crime_time,
        crime_day=crime_day,
        backstory_log=log,
    )
