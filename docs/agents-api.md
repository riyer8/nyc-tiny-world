# Agents mod API

`AGENT_API_VERSION = 1`

## Quick start

```python
from nyc_world.agents import NPC, Personality, Needs, Schedule

npc = NPC(
    id="river",
    name="River",
    personality=Personality(curiosity=0.9, kindness=0.7),
    needs=Needs(money=0.4),
    schedule=Schedule.workplace("nyu_library", hour=9),
    dialogue_pack="river_default",
)

city.register_npc(npc)
```

Drop a file in `mods/` with a `register(registry)` function to auto-load on game start.

## Types

| Type | Purpose |
|------|---------|
| `NPC` | Mod NPC definition (id, name, schedule, dialogue) |
| `Personality` | curiosity, kindness, extroversion, risk, ambition |
| `Needs` | money, hunger, energy, social |
| `Schedule` | list of stops; `Schedule.workplace(location_id, hour)` helper |
| `NPCRegistry` | `register(npc)` then `apply_to_city(city)` |

## Location ids

Known anchors near Washington Square: `cafe_village`, `library_building`, `nyu_library`, `photo_shop`, `subway_wsp`.

## Dialogue

Set `dialogue_pack` to a key merged into `game/dialogue_lines.DIALOGUE` at load time.

## Stability

Breaking API changes increment `AGENT_API_VERSION` and are documented here.
