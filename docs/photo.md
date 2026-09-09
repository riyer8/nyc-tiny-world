# Photo Mode

Free-fly camera with visual-only time/weather overrides and screenshots.

## Modules

- `nyc_world/modes/photo.py` — `PhotoMode`, `FreeFlyCamera`
- Screenshots saved to `data/screenshots/`

## Controls

| Key | Action |
|-----|--------|
| P | Toggle photo mode |
| WASD + mouse | Fly camera |
| Mouse wheel | Scrub time of day |
| [ / ] | Time step |
| - / + | FOV |
| , / . | Vignette |
| N | Cycle weather |
| Tab | Pause / resume sim |
| Enter | Save PNG |

Visual sliders appear in the HUD. Vignette provides cheap edge darkening.

## Tests

`tests/test_photo.py`
