# Pillar 3 — Procedural quest generation

Quests spawn from NPC needs and the social graph — no LLM required.

## Modules

- `nyc_world/simulation/quest_gen.py` — templates: Maya favor, Alex coffee delivery, library investigate
- `nyc_world/game/quests.py` — `QuestManager.refresh_generated_quests()`

## Flow

Complete *The Missing Camera* → Maya's money need spikes → `maya_favor` becomes available. Alex social need → delivery quest. Library investigate when Maya is worried.

## Persistence

Generated quests save/load with full metadata (`generated`, `giver_npc_id`, objectives).

## Tests

`tests/test_quest_gen.py`, `tests/test_mvp_vertical_slice.py`
