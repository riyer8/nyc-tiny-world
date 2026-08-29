# NYC Tiny World

An interactive **3D game across New York City**, built from real [OpenStreetMap](https://www.openstreetmap.org) data. Walk real neighborhoods with accurate streets, building footprints, landmarks, NPCs, and traffic.

**Current area:** ~1 km² of Greenwich Village (Washington Square Park).

## Quick start

```bash
pip install -r requirements.txt
python3 scripts/generate_map.py    # first time: download OSM + build map
python3 scripts/play_3d.py         # walk the living 3D city
```

**Controls:** WASD move · mouse look · Esc quit

## What's in the world

| System | Source |
|--------|--------|
| Streets | OSM highways → roads, sidewalks, crosswalks, lane markings, traffic lights |
| Buildings | Real footprints extruded with OSM height data |
| Landmarks | Cafes, stores, parks, named buildings from OSM |
| NPCs | 24 pedestrians with daily schedules (A* on street graph) |
| Vehicles | Taxis, cars, buses, bikes on the road network |
| Time & weather | Clock (starts 8:00 AM), sunrise/sunset, rain, fog, clouds |

## Project layout

```
nyc_world/       game engine
  streets.py     road graph + 3D street geometry
  buildings.py   extruded OSM footprints
  landmarks.py   recognizable POI models
  npcs.py        scheduled pedestrians
  vehicles.py    road-following traffic
  world_clock.py time + weather
  city_sim.py    ties it all together
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
