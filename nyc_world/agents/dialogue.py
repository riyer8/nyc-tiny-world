"""Dialogue pack registration for mod NPCs."""

from __future__ import annotations

PACKS: dict[str, list[str]] = {}


def register_dialogue_pack(pack_id: str, lines: list[str]) -> None:
    PACKS[pack_id] = list(lines)


def greeting_key(npc_id: str, pack_id: str) -> str:
    if pack_id:
        return pack_id
    return f"{npc_id}_greeting"


def merge_into_game_dialogue() -> None:
    from nyc_world.game.dialogue_lines import DIALOGUE

    for pack_id, lines in PACKS.items():
        DIALOGUE.setdefault(pack_id, lines)
