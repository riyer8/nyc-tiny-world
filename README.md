# NYC Tiny World

An interactive **3D game across New York City**, built from real [OpenStreetMap](https://www.openstreetmap.org) data. Walk real neighborhoods with accurate streets, building footprints, landmarks, NPCs, and traffic.

**Current area:** ~1 km² of Greenwich Village (Washington Square Park).

## Quick start

```bash
pip install -r requirements.txt
python3 scripts/generate_map.py    # first time: download OSM + build map
python3 scripts/play_3d.py         # walk the living 3D city
```

**Controls**

| Action | Keys |
|--------|------|
| Move forward | **W** or **↑** |
| Move backward | **S** or **↓** |
| Strafe left / right | **A** / **D** or **←** / **→** |
| Sprint (you + city traffic) | **Space** (hold) |
| Look around | Mouse |
| Interact | **E** |
| Quit | **Esc** |

Controls also appear in the HUD at the bottom of the screen while playing.

## Interactions & quests

Walk up to subway entrances, cafes, buildings, NPCs, and objects. When you're close enough, a prompt appears — press **E** to interact.

**Example quest: The Missing Camera**
1. Talk to **Maya** (pink NPC near Washington Square spawn)
2. Visit the **Village Cafe** (nearest cafe landmark)
3. Talk to **Alex** for a clue
4. Enter the **Jefferson Market Library**
5. Find the camera inside
6. Return to Maya

Quest progress shows in the top-left HUD. Dialogue appears at the bottom. A few buildings have simple interiors (cafe, library, photo shop).

**Testing without the 3D window:**
```bash
pytest tests/test_interactions.py tests/test_quests.py -v
```

## What's in the world

| System | Source |
|--------|--------|
| Streets | OSM highways → roads, sidewalks, crosswalks, lane markings, traffic lights |
| Buildings | Real footprints extruded with OSM height data |
| Landmarks | Cafes, stores, parks, named buildings from OSM |
| NPCs | 24 pedestrians with daily schedules (A* on street graph) |
| Vehicles | Taxis, cars, buses, bikes on the road network |
| Time & weather | Clock (starts 8:00 AM), sunrise/sunset, rain, fog, clouds |
| Interactions | E to interact with landmarks, NPCs, objects |
| Quests | Adventure system with objectives, dialogue, rewards |

## Project layout

```
nyc_world/
  core/          world map, projection, 3D scene
  map/           OSM fetch, map generation, buildings
  city/          streets, landmarks, NPCs, vehicles, simulation
  game/          controls, interactions, quests, session
  render/        OpenGL scene + HUD
scripts/         play_3d.py, play_2d.py, generate_map.py
tests/           pytest suite
data/            cached OSM JSON
maps/            generated map + projection metadata
```

## Tests

```bash
pytest
```

## Roadmap

- More NYC neighborhoods tiled into a city-wide world
- Richer landmark models and subway entrances
- Deeper NPC/vehicle AI
