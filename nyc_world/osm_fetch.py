"""Download OpenStreetMap data via the Overpass API."""

from __future__ import annotations

import json
from pathlib import Path

import requests

from nyc_world.areas import Area
from nyc_world.paths import DATA_DIR

OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]
USER_AGENT = "nyc-tiny-world/1.0 (local game map generator)"


def _overpass_query(area: Area) -> str:
    south, west, north, east = area.bbox
    bbox = f"{south},{west},{north},{east}"
    return f"""[out:json][timeout:90];
(
  way["building"]({bbox});
  relation["building"]({bbox});
  way["highway"]({bbox});
  way["leisure"="park"]({bbox});
  relation["leisure"="park"]({bbox});
  way["leisure"="garden"]({bbox});
  way["landuse"~"grass|recreation_ground|forest|meadow"]({bbox});
  relation["landuse"~"grass|recreation_ground|forest|meadow"]({bbox});
  node["amenity"]({bbox});
  node["shop"]({bbox});
  node["tourism"]({bbox});
  node["highway"="traffic_signals"]({bbox});
  node["railway"="station"]({bbox});
  node["railway"="subway_entrance"]({bbox});
  node["amenity"="subway_entrance"]({bbox});
);
out body;
>;
out skel qt;"""


def cache_path(area: Area) -> Path:
    return DATA_DIR / f"{area.slug}_osm.json"


def fetch_osm(area: Area, *, refresh: bool = False) -> dict:
    path = cache_path(area)
    if path.exists() and not refresh:
        return json.loads(path.read_text())

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    query = _overpass_query(area)
    headers = {"User-Agent": USER_AGENT}
    last_error: Exception | None = None

    for url in OVERPASS_URLS:
        try:
            response = requests.post(
                url,
                data=query.encode("utf-8"),
                headers=headers,
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            path.write_text(json.dumps(data))
            return data
        except Exception as exc:
            last_error = exc
            continue

    raise RuntimeError("Failed to fetch OSM data from all Overpass mirrors") from last_error
