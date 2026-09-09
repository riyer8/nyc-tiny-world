# Memory & Relationships

NPCs remember player actions as structured facts and synthesize opinions for dialogue.

## Modules

- `nyc_world/simulation/memory.py` — `MemoryFact`, `synthesize_opinion()`
- `nyc_world/simulation/relationships.py` — `RelationshipStore`, `NPCPlayerRelationship`
- `nyc_world/game/dialogue.py` — tag-based greeting router

## Player experience

Press **E** near an NPC. The memory panel shows trust, friendship, visit count, facts, and opinion text. Greetings change based on history (helped, stole, returning visitor).

## Persistence

Memories serialize through `RelationshipStore` into save files and `WorldState.relationships`.

## Tests

`tests/test_memory.py`, `tests/test_npc_memory.py`, `tests/test_relationships.py`, `tests/test_dialogue.py`
