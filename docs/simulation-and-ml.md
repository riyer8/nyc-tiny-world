# Simulation & ML

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
