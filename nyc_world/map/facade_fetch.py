"""Download facade photos from Wikimedia Commons via Wikidata/OSM."""

from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.parse import quote

import requests

from nyc_world.core.areas import GREENWICH_VILLAGE, WASHINGTON_SQUARE
from nyc_world.map.buildings import facade_key_from_tags
from nyc_world.map.osm_fetch import cache_path, fetch_osm
from nyc_world.paths import DATA_DIR, FACADES_DIR

USER_AGENT = "nyc-tiny-world/1.0 (facade texture fetcher)"
COMMONS_WIDTH = 512
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DOWNLOAD_DELAY_S = 4.0

# Quest / landmark buildings — fetched first.
PRIORITY_QIDS = [
    "Q502505",   # Jefferson Market Library
    "Q3306353",  # Merchant's House Museum
    "Q3051566",  # Bobst Library
    "Q1261362",  # Stonewall Inn
    "Q3637062",  # Bayard-Condict Building
    "Q131382414",  # Public Theater
    "Q7587109",  # St. Anthony of Padua Church
    "Q5117267",  # St. Joseph Church
    "Q5453598",  # First Presbyterian Church
    "Q6651525",  # Little Red School House
]


def collect_facade_targets(osm_data: dict) -> dict[str, dict]:
    """Map facade_key -> {wikidata, name}."""
    targets: dict[str, dict] = {}
    for element in osm_data.get("elements", []):
        tags = element.get("tags", {})
        if "building" not in tags:
            continue
        key, wikidata = facade_key_from_tags(tags)
        if not key:
            continue
        targets[key] = {
            "wikidata": wikidata,
            "name": tags.get("name", ""),
        }
    return targets


def _session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})
    return session


def _sleep_backoff(attempt: int, base: float = 3.0) -> None:
    time.sleep(min(90.0, base * (2**attempt)))


def _clean_url(url: str) -> str:
    return url.split("?")[0]


def batch_wikidata_images(qids: list[str], session: requests.Session | None = None) -> dict[str, str]:
    """Resolve P18 image filenames for many Wikidata IDs in one API call."""
    session = session or _session()
    titles: dict[str, str] = {}
    unique = list(dict.fromkeys(qids))
    for i in range(0, len(unique), 50):
        chunk = unique[i : i + 50]
        params = {
            "action": "wbgetentities",
            "ids": "|".join(chunk),
            "props": "claims",
            "format": "json",
        }
        for attempt in range(6):
            response = session.get(WIKIDATA_API, params=params, timeout=45)
            if response.status_code == 429:
                _sleep_backoff(attempt, base=5.0)
                continue
            response.raise_for_status()
            entities = response.json().get("entities", {})
            for qid, entity in entities.items():
                claims = entity.get("claims", {}).get("P18", [])
                if not claims:
                    continue
                value = claims[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                if isinstance(value, str):
                    titles[qid] = value
            break
        time.sleep(1.5)
    return titles


def wikidata_image_title(qid: str, session: requests.Session | None = None) -> str | None:
    return batch_wikidata_images([qid], session).get(qid)


def commons_thumbnail_url(
    filename: str,
    *,
    width: int = COMMONS_WIDTH,
    session: requests.Session | None = None,
) -> str | None:
    """Resolve a direct thumbnail URL via the Commons API."""
    session = session or _session()
    title = filename if filename.startswith("File:") else f"File:{filename}"
    params = {
        "action": "query",
        "titles": title,
        "prop": "imageinfo",
        "iiprop": "url",
        "iiurlwidth": width,
        "format": "json",
    }
    for attempt in range(6):
        response = session.get(COMMONS_API, params=params, timeout=45)
        if response.status_code == 429:
            _sleep_backoff(attempt, base=4.0)
            continue
        if response.status_code != 200:
            return None
        pages = response.json().get("query", {}).get("pages", {})
        for page in pages.values():
            if page.get("missing") is not None:
                return None
            info = page.get("imageinfo", [])
            if info:
                return info[0].get("thumburl") or info[0].get("url")
        return None
    return None


def _fallback_file_path(filename: str, *, width: int = COMMONS_WIDTH) -> str:
    safe = quote(filename.replace(" ", "_"))
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{safe}?width={width}"


def _download_bytes(session: requests.Session, url: str) -> bytes | None:
    clean = _clean_url(url)
    for attempt in range(8):
        response = session.get(clean, timeout=90, allow_redirects=True)
        if response.status_code == 429:
            _sleep_backoff(attempt, base=5.0)
            continue
        if response.status_code != 200:
            return None
        data = response.content
        if data.startswith(b"\xff\xd8") or data.startswith(b"\x89PNG") or data.startswith(b"RIFF"):
            return data
        content_type = response.headers.get("content-type", "")
        if "image" in content_type and len(data) > 1024:
            return data
        return None
    return None


def download_facade_image(
    filename: str,
    dest: Path,
    session: requests.Session | None = None,
) -> bool:
    session = session or _session()
    candidates: list[str] = []
    api_url = commons_thumbnail_url(filename, session=session)
    if api_url:
        candidates.append(api_url)
    candidates.append(_fallback_file_path(filename))

    for url in candidates:
        data = _download_bytes(session, url)
        if data:
            dest.write_bytes(data)
            return dest.stat().st_size > 1024
    return False


def _sort_targets(targets: list[tuple[str, dict]]) -> list[tuple[str, dict]]:
    def priority(item: tuple[str, dict]) -> tuple[int, str]:
        key, meta = item
        qid = meta.get("wikidata", "")
        if qid in PRIORITY_QIDS:
            return (PRIORITY_QIDS.index(qid), key)
        return (len(PRIORITY_QIDS), key)

    return sorted(targets, key=priority)


def rebuild_manifest(out_dir: Path | None = None) -> dict[str, str]:
    out_dir = out_dir or FACADES_DIR
    manifest = {
        p.stem: p.name
        for p in out_dir.glob("*.jpg")
        if p.stat().st_size > 1024
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(dict(sorted(manifest.items())), indent=2) + "\n"
    )
    return manifest


def fetch_facades(
    *,
    osm_path: Path | None = None,
    out_dir: Path | None = None,
    refresh_osm: bool = False,
    limit: int | None = None,
    missing_only: bool = True,
) -> dict[str, str]:
    """Download facade images and write manifest.json. Returns manifest."""
    out_dir = out_dir or FACADES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if refresh_osm or not (DATA_DIR / "greenwich_village_osm.json").exists():
        print("Fetching Greenwich Village OSM data (broader NYC coverage)...")
        fetch_osm(GREENWICH_VILLAGE, refresh=refresh_osm)

    osm_path = osm_path or DATA_DIR / "greenwich_village_osm.json"
    if not osm_path.exists():
        osm_path = cache_path(WASHINGTON_SQUARE)
    osm_data = json.loads(osm_path.read_text())
    targets = collect_facade_targets(osm_data)

    manifest_path = out_dir / "manifest.json"
    manifest: dict[str, str] = {}
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())

    wikidata_targets = [(k, v) for k, v in targets.items() if v.get("wikidata")]
    wikidata_targets = _sort_targets(wikidata_targets)

    if missing_only:
        wikidata_targets = [
            (k, v) for k, v in wikidata_targets if k not in manifest or not (out_dir / f"{k}.jpg").exists()
        ]

    if limit is not None:
        wikidata_targets = wikidata_targets[:limit]

    print(
        f"Found {len(targets)} textured building candidates "
        f"({len([v for v in targets.values() if v.get('wikidata')])} with Wikidata); "
        f"fetching {len(wikidata_targets)}"
    )

    session = _session()
    titles_path = out_dir / "image_titles.json"
    titles_cache: dict[str, str] = {}
    if titles_path.exists():
        titles_cache = json.loads(titles_path.read_text())

    pending_qids = [v["wikidata"] for _, v in wikidata_targets if v["wikidata"] not in titles_cache]
    if pending_qids:
        print(f"Resolving {len(pending_qids)} Wikidata image titles (batched)...")
        titles_cache.update(batch_wikidata_images(pending_qids, session))
        titles_path.write_text(json.dumps(titles_cache, indent=2, sort_keys=True) + "\n")

    fetched = 0
    failed = 0
    for key, meta in wikidata_targets:
        rel = f"{key}.jpg"
        dest = out_dir / rel
        if dest.exists() and dest.stat().st_size > 1024:
            manifest[key] = rel
            continue

        qid = meta["wikidata"]
        title = titles_cache.get(qid)
        if not title:
            print(f"  skip {key} ({meta.get('name') or qid}) — no Wikidata image")
            continue

        print(f"  fetch {key} — {meta.get('name') or title}")
        if download_facade_image(title, dest, session=session):
            manifest[key] = rel
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
            fetched += 1
            print(f"    saved {dest.stat().st_size // 1024} KB")
        else:
            failed += 1
            print(f"    failed ({title})")
        time.sleep(DOWNLOAD_DELAY_S)

    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Done — {len(manifest)} facades in manifest ({fetched} new, {failed} failed)")
    return manifest
