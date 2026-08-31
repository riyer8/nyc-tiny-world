"""Tests for procedural mystery generation and investigation."""

from nyc_world.simulation.mystery import (
    MysteryInvestigation,
    discover_clues_at_location,
    discover_clues_from_npc,
    generate_mystery,
    investigation_hud_lines,
)
from nyc_world.simulation.relationships import RelationshipStore


def test_generate_mystery_is_seeded():
    a = generate_mystery(42)
    b = generate_mystery(42)
    c = generate_mystery(99)
    assert a.culprit_id == b.culprit_id
    assert a.crime_location == b.crime_location
    assert len(a.backstory_log.entries) == len(b.backstory_log.entries)
    assert a.culprit_id != c.culprit_id or a.crime_location != c.crime_location


def test_discover_public_clues_at_location():
    case = generate_mystery(7)
    inv = MysteryInvestigation(case=case)
    lines = discover_clues_at_location(inv, case.crime_location)
    assert lines
    assert len(inv.discovered_entry_ids) >= 1


def test_discover_witness_clues_requires_trust():
    case = generate_mystery(3, suspect_pool=["alex"])
    inv = MysteryInvestigation(case=case)
    rels = RelationshipStore()
    rels.get("alex").trust = 10.0
    low_trust = discover_clues_from_npc(inv, "alex", rels)
    assert low_trust == []

    rels.get("alex").trust = 30.0
    high_trust = discover_clues_from_npc(inv, "alex", rels)
    assert high_trust


def test_accuse_correct_culprit():
    case = generate_mystery(5, suspect_pool=["alex"])
    inv = MysteryInvestigation(case=case)
    for entry in case.backstory_log.entries:
        inv.discover(entry)
    ok, msg = inv.try_accuse(case.culprit_id)
    assert ok
    assert inv.solved
    assert "Correct" in msg


def test_accuse_wrong_suspect():
    case = generate_mystery(5, suspect_pool=["alex", "npc_3"])
    inv = MysteryInvestigation(case=case)
    wrong = "alex" if case.culprit_id != "alex" else "npc_3"
    ok, msg = inv.try_accuse(wrong)
    if wrong == case.culprit_id:
        assert ok
    else:
        assert not ok
        assert not inv.solved
        assert "wasn't the thief" in msg


def test_investigation_serializes():
    case = generate_mystery(11)
    inv = MysteryInvestigation(case=case)
    discover_clues_at_location(inv, case.crime_location)
    restored = MysteryInvestigation.from_dict(inv.to_dict())
    assert restored.case.culprit_id == case.culprit_id
    assert restored.discovered_entry_ids == inv.discovered_entry_ids


def test_investigation_hud_lines():
    case = generate_mystery(1)
    inv = MysteryInvestigation(case=case)
    lines = investigation_hud_lines(inv)
    assert case.title in lines[0]
    assert "TIMELINE" in "\n".join(lines)
