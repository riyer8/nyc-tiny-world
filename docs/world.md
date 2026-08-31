# World

**Current area:** ~500 m × 500 m around Washington Square Park (Greenwich Village, Manhattan).

## Geographic grounding

The game maps your 3D position to **real GPS coordinates** using a reversible projection:

```
3D position → game pixels → latitude/longitude → mini-map
```

While playing you'll see:
- **Top-right mini-map** — NYC → Manhattan → neighborhood, with your position as a blue dot
- **Facing arrow** on the neighborhood map (yellow line from the dot)
- **North indicators** on each map panel
- **Debug panel** (press **G**) — lat/lon, street, POI, simulation tick

Buildings use **real OSM footprints** (not generic rectangles), extruded to estimated height.

To regenerate the focused play area:
```bash
python3 scripts/generate_map.py --area washington_square
```

## Streaming world

The game uses **concentric radii** around your real GPS position — not all of Manhattan at once:

| Radius | Distance | What's loaded |
|--------|----------|-----------------|
| Data | 5 miles | OSM tiles fetched/cached (`data/tiles/`) |
| 3D render | 1 mile | Detailed building footprints |
| Simulation | 300 m | NPCs, vehicles, traffic |
| Interaction | 100 m | Quest objects, interiors |

```
Player 🔵
   ↓ lat/lon
Tile loader (500 m grid)
   ↓
LOD filter → 3D + simulation
```

The mini-map shows **loaded data radius** circles on Manhattan. As you walk, new tiles load and distant ones unload.

Prefetch tiles around spawn (requires network):
```bash
python3 scripts/prefetch_tiles.py
```

Or from Python:

```python
from nyc_world.streaming import TileDataLoader
from nyc_world.core.areas import WASHINGTON_SQUARE

loader = TileDataLoader(network=True)
loader.load_around(WASHINGTON_SQUARE.spawn_lat, WASHINGTON_SQUARE.spawn_lon, 8046)
```

## What's in the world

| System | Source |
|--------|--------|
| Streets | OSM highways → roads, sidewalks, crosswalks, lane markings, traffic lights |
| Buildings | Real OSM footprints — brick brownstones, glass towers, window grids |
| Landmarks | Cafes, stores, parks, named buildings from OSM |
| NPCs | 48 pedestrians with schedules — humanoid models on sidewalks |
| Vehicles | 32 cars, taxis, buses, bikes — oriented meshes with wheels & lights |
| Time & weather | Clock (starts 8:00 AM), sunrise/sunset, rain, fog, clouds |
| Interactions | E to interact with landmarks, NPCs, objects |
| Quests | Adventure system with objectives, dialogue, rewards |
| Progression | XP, money, inventory, NPC relationships |

## Realistic graphics

Buildings use **OpenStreetMap tags** to pick NYC-like appearances:

| OSM signal | Visual result |
|------------|----------------|
| `building=terrace` / brownstone | Brick walls, cornice, storefront |
| `building:material=brick` | Warm masonry colors |
| `building=office` + tall | Glass curtain wall + reflective windows |
| `building:colour` | Custom facade tint |
| `start_date` before 1940 | Pre-war stone + trim bands |
| `shop` / `amenity` on ground | Storefront glazing |

Facades get **per-story window grids**, directional shading, pitched or parapet roofs, and ground-floor retail glass.

Vehicles are **oriented meshes** (body, cabin, wheels, headlights) that turn with traffic. Pedestrians are **humanoid** (head, torso, legs) with varied jacket colors — 48 NPCs including sidewalk wanderers.

**More realism later:** NYC Open Data building footprints (1M+ buildings with roof heights) and Mapillary/street-level imagery can be layered on without changing the simulation architecture.

Regenerate after OSM updates:
```bash
python3 scripts/generate_map.py --area washington_square
```
