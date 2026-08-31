# Pillar 4 — Procedural mystery

Each playthrough generates a seeded mystery solvable from the EventLog.

## Modules

- `nyc_world/simulation/mystery/` — `case.py`, `gen.py`, `investigation.py`
- `scripts/replay_mystery.py` — CLI replay and reveal

## Player experience

**M** opens the journal. Talk to NPCs and visit locations to discover clues. **Y** accuses when enough evidence is gathered.

## Persistence

Mystery state saves with the game. `WorldState.mystery` captures title, clues, solved flag.

## Tests

`tests/test_mystery.py`
