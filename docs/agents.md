# Agents

Spawned NPCs use utility AI: needs drift, scored actions, and pathfinding goals.
The default graphics profile spawns 20 NPCs; `--graphics normal` spawns 48.

## Modules

- `nyc_world/simulation/agent.py` — `AgentBrain`, `AgentController`, `score_actions()`
- Wired in `nyc_world/city/city_sim.py` for every spawned NPC

## Behaviors

Hungry NPCs seek food (café), rain drives shelter-seeking, evening pushes homeward. Quest NPCs (Maya, Alex) share the same framework with quest goal boosts.

## WorldState

Each `NPCState` includes personality summary, needs bars, current action, and plan summary.

## Tests

`tests/test_agent.py`, `tests/test_agents.py`
