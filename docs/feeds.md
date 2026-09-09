# Real-World NYC Feeds

Optional live or fixture-driven weather and MTA data affects the simulation.

## Modules

- `nyc_world/feeds/` — types, parsers, effects, manager, weather
- `FeedManager` wired in `GameSession`

## Effects

Weather overrides `WorldClock`. MTA delays boost subway boarding and sidewalk density near stations. Offline mode uses cached fixtures with no behavior change vs default.

## CLI

```bash
python3 scripts/play_3d.py --live-feeds
python3 scripts/play_3d.py --feed-fixture tests/fixtures/feeds/mta_delay.json
```

## Tests

`tests/test_feeds.py`
