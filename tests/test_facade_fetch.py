"""Tests for facade fetch helpers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from nyc_world.map.facade_fetch import (
    _clean_url,
    _sort_targets,
    batch_wikidata_images,
)


def test_clean_url_strips_query() -> None:
    url = "https://upload.wikimedia.org/foo.jpg?utm_source=test"
    assert _clean_url(url) == "https://upload.wikimedia.org/foo.jpg"


def test_sort_targets_prioritizes_quest_buildings() -> None:
    targets = [
        ("Q999", {"wikidata": "Q999", "name": "Other"}),
        ("Q502505", {"wikidata": "Q502505", "name": "Jefferson Market Library"}),
    ]
    ordered = _sort_targets(targets)
    assert ordered[0][0] == "Q502505"


def test_batch_wikidata_images_parses_response() -> None:
    payload = {
        "entities": {
            "Q502505": {
                "claims": {
                    "P18": [
                        {
                            "mainsnak": {
                                "datavalue": {"value": "Jefferson market crop.jpg"},
                            }
                        }
                    ]
                }
            }
        }
    }
    session = MagicMock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = payload
    titles = batch_wikidata_images(["Q502505"], session)
    assert titles["Q502505"] == "Jefferson market crop.jpg"
