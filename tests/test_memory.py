"""Tests for NPC memory and opinions."""

from nyc_world.simulation.memory import make_fact, synthesize_opinion


def test_synthesize_opinion_helpful():
    facts = [
        make_fact("helped", "You found her camera", tick=1, game_day=1, game_time="08:00 AM", sentiment=0.8),
    ]
    opinion = synthesize_opinion(75, 55, facts)
    assert "helpful" in opinion.lower()


def test_synthesize_opinion_suspicious():
    facts = [
        make_fact("helped", "You found her camera", tick=1, game_day=1, game_time="08:00 AM"),
        make_fact("stole", "You stole her coffee", tick=2, game_day=1, game_time="09:00 AM", sentiment=-0.9),
    ]
    opinion = synthesize_opinion(55, 40, facts)
    assert "suspicious" in opinion.lower()
