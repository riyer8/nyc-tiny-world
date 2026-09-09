# Digital Twin Mode

Elevated fly camera to observe the living simulation.

## Modules

- `nyc_world/modes/twin.py` — pause, time scale, heatmap, click-to-inspect
- `nyc_world/render/camera.py` — `apply_twin_camera()`

## Controls

| Key | Action |
|-----|--------|
| T | Toggle twin |
| Space | Pause / resume |
| 1/2/3 | Time scale 1× / 10× / 30× |
| H | Cycle heatmap |
| Click | Inspect NPC or vehicle |

## Tests

`tests/test_twin.py`
