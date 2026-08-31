# Development

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
