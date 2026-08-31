"""Tests for unified relationship store."""

from nyc_world.simulation.relationships import RelationshipStore


def test_record_visit_increments_count():
    store = RelationshipStore()
    store.record_visit("maya", tick=1, game_day=1, game_time="08:00 AM")
    store.record_visit("maya", tick=2, game_day=1, game_time="09:00 AM")
    rel = store.get("maya")
    assert rel.visit_count == 2
    assert rel.met_day == 1


def test_record_fact_adjusts_trust():
    store = RelationshipStore()
    store.record_fact(
        "maya",
        "helped",
        "You found her camera",
        tick=5,
        game_day=1,
        game_time="10:00 AM",
        trust_delta=15,
        friendship_delta=10,
    )
    rel = store.get("maya")
    assert rel.trust == 65
    assert rel.friendship == 40
    assert rel.has_fact("helped")


def test_save_roundtrip():
    store = RelationshipStore()
    store.record_fact(
        "maya",
        "stole",
        "You stole her coffee",
        tick=3,
        game_day=2,
        game_time="11:00 AM",
        sentiment=-0.9,
        trust_delta=-20,
    )
    restored = RelationshipStore.from_dict(store.to_dict())
    rel = restored.get("maya")
    assert rel.has_fact("stole")
    assert rel.trust < 50
