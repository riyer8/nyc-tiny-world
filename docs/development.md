# Development

## Architecture

```
OSM / feeds / saves
        |
3D city engine + streaming LOD
        |
Simulation (WorldState, NPC minds, quests)
        |
Trajectories (state, action, next_state)
        |
World model / what-if prediction
```

Python owns data, simulation, and rendering for the current build. The
simulation state stays serializable so another renderer could consume it later.

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

- Record and link a short public walkthrough.
- Improve immediate-mode OpenGL performance.
- Add richer landmark silhouettes for the cafe, library, and subway entrances.
- Expand NPC individuality beyond the key quest characters.
- Train larger world models from recorded trajectories.
