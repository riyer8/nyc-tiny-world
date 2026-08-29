# NYC Tiny World

An interactive **3D game across New York City**, built from real [OpenStreetMap](https://www.openstreetmap.org) data. Walk real neighborhoods with accurate streets, building footprints, landmarks, NPCs, and traffic.

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

## Quick start

```bash
pip install -r requirements.txt
python3 scripts/generate_map.py    # first time: download OSM + build map
python3 scripts/play_3d.py         # walk the living 3D city
python3 scripts/play_3d.py --record  # also save trajectories for ML
```

**Controls**

| Action | Keys |
|--------|------|
| Move forward | **W** or **↑** |
| Move backward | **S** or **↓** |
| Strafe left / right | **A** / **D** or **←** / **→** |
| Sprint | **F** (hold) |
| Jump | **Space** |
| Look around | **Click** to unlock, move mouse, **click** again to lock |
| Interact | **E** |
| Toggle geo debug | **G** |
| Record trajectories | `--record` flag |
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

## Inventory & progression

Your **player profile** tracks everything that makes exploration meaningful:

| Stat | Starting value |
|------|----------------|
| Money | $37 |
| XP / Level | 0 XP · Level 1 |
| Items | MetroCard |

The profile panel (top-right, below the mini-map) shows level, money, inventory, and relationships.

**Completing "The Missing Camera" rewards:**
- +75 XP
- +$15
- ☕ Coffee + coffee token
- Maya likes you more (+50%)

Items have display names and emojis (`MetroCard`, `Camera`, `Coffee`, `Mysterious Key`). Relationships with NPCs persist — talk to Maya again after the quest and she remembers you helped.

**Testing without the 3D window:**
```bash
pytest tests/test_profile.py tests/test_interactions.py tests/test_quests.py -v
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
| Progression | XP, money, inventory, NPC relationships |

## Living city (NPC minds)

Quest NPCs have **needs, goals, memory, and relationships**:

```
Maya
├── works at Village Cafe
├── likes Alex
├── hates rain
├── goes home at 6 PM
└── remembers if you help or steal
```

The HUD shows a **Living City** panel with Maya/Alex mood and goals. Help Maya find her camera and she remembers — steal from her and she remembers that too.

## Formal simulation

Every frame the game captures a serializable `WorldState`:

```
WorldState(t)
      ├── Player (position, inventory, relationships)
      ├── NPCs (position, mood, goals)
      ├── Vehicles
      ├── Weather + Time
      └── Quests
             ↓
        Simulation.step()
             ↓
      WorldState(t+1)
```

Press **G** to see simulation tick count and trajectory stats in the debug panel.

## World model pipeline

Record trajectories while playing, train a model, then imagine the future:

```bash
# Option A: record while playing
python3 scripts/play_3d.py --record

# Option B: generate synthetic trajectories offline
python3 scripts/generate_trajectories.py --steps 200

# Train a lightweight world model (pure Python, no PyTorch required)
python3 scripts/train_world_model.py

# Imagine walking north for 10 steps
python3 scripts/imagine_future.py --steps 10 --north
```

Each trajectory step stores `(state, action, next_state)` as JSONL in `data/trajectories/`. The model learns to predict the next world state from the current state plus player action.

## Architecture

```
🗽 NYC DATA (OSM)
        ↓
🌎 3D City Engine + Streaming LOD
        ↓
🎮 Simulation (WorldState, NPC minds, quests)
        ↓
📼 Trajectories (state, action, next_state)
        ↓
🧠 World Model → 🔮 Future Prediction
```

Python owns data + simulation + ML. The Pygame/OpenGL layer is the current renderer — swap for Godot later without touching the simulation package.

## Project layout

```
nyc_world/
  core/          world map, projection, 3D scene
  map/           OSM fetch, map generation, buildings
  city/          streets, landmarks, NPCs, vehicles
  game/          controls, interactions, quests, profile, session
  geo/           coordinates, mini-map, location context
  simulation/    WorldState, NPC minds, trajectories, world model
  streaming/     tile loader, LOD radii, world manager
  render/        OpenGL scene + HUD
scripts/         play_3d.py, train_world_model.py, imagine_future.py
tests/           pytest suite
data/            OSM cache, trajectories, trained models
maps/            generated map + projection metadata
```

## Tests

```bash
pytest
```

## Roadmap

- Godot renderer connected to `WorldState` JSON stream
- Richer landmark models and subway fast-travel
- Deeper NPC/vehicle AI with learned policies
- Train larger world models on millions of trajectories
