"""Clue discovery and investigation HUD helpers."""

from __future__ import annotations

from nyc_world.simulation.event_log import EventLogEntry
from nyc_world.simulation.mystery.case import MysteryInvestigation
from nyc_world.simulation.relationships import RelationshipStore


TRUST_TO_TALK = 25.0


def _format_entry(entry: EventLogEntry) -> str:
    actor = entry.actor_id.replace("_", " ").title()
    action_labels = {
        "enter": "entered",
        "leave": "left",
        "take": "took something from",
        "report": "reported theft at",
        "depart": "departed",
        "witness": "witnessed activity at",
    }
    verb = action_labels.get(entry.action, entry.action)
    loc = entry.location_id.replace("_", " ")
    detail = f" ({entry.details})" if entry.details else ""
    return f"{entry.game_time}  {actor} {verb} {loc}{detail}"


def discover_clues_from_npc(
    investigation: MysteryInvestigation,
    npc_id: str,
    relationships: RelationshipStore,
) -> list[str]:
    """Reveal witness events if NPC trusts player enough."""
    rel = relationships.get(npc_id)
    if rel.trust < TRUST_TO_TALK and not rel.has_fact("helped"):
        return []

    lines: list[str] = []
    for entry in investigation.case.backstory_log.entries:
        if entry.visibility == "hidden":
            continue
        if entry.actor_id != npc_id and entry.action != "witness":
            continue
        if investigation.discover(entry):
            lines.append(f"Clue: {_format_entry(entry)}")
    return lines


def discover_clues_at_location(
    investigation: MysteryInvestigation,
    location_id: str,
) -> list[str]:
    """Reveal public events that happened at a location."""
    lines: list[str] = []
    for entry in investigation.case.backstory_log.entries:
        if entry.visibility != "public":
            continue
        if entry.location_id != location_id:
            continue
        if investigation.discover(entry):
            lines.append(f"Clue: {_format_entry(entry)}")
    return lines


def investigation_hud_lines(investigation: MysteryInvestigation | None) -> list[str]:
    if not investigation:
        return []
    case = investigation.case
    lines = [
        case.title,
        f"Something happened at {case.crime_time}.",
        "",
        "TIMELINE (discovered)",
    ]
    discovered = investigation.discovered_entries()
    if discovered:
        for entry in discovered:
            lines.append(_format_entry(entry))
    else:
        lines.append(" (talk to witnesses · visit locations)")
    if investigation.solved:
        lines.extend(["", "✓ CASE SOLVED"])
    else:
        lines.extend(["", "Press M to toggle · talk to NPCs · visit cafes"])
    return lines
