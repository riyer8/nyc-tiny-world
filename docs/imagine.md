# What-If / Imagine Mode

Rule-based world-model predictions inside twin mode.

## Modules

- `nyc_world/modes/imagine.py` — scenario UI
- `nyc_world/simulation/model/imagination.py` — `run_what_if()`, side-by-side diff
- `nyc_world/simulation/model/world_patch.py` — weather, transit, relationship patches

## Controls (twin mode active)

| Key | Action |
|-----|--------|
| I | Toggle / cycle scenario |
| R | Run prediction |

CLI: `python3 scripts/imagine_future.py --what-if rain_at_5pm`

## Tests

`tests/test_imagine.py`
