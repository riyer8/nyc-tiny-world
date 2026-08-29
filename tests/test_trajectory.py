"""Tests for trajectory recording (Chunk 18)."""

from __future__ import annotations

import json
from pathlib import Path

from nyc_world.simulation.actions import PlayerMoveAction
from nyc_world.simulation.state import WorldState
from nyc_world.simulation.trajectory import TrajectoryRecorder, TrajectoryStep


def test_trajectory_step_round_trip():
    state = WorldState(tick=1)
    nxt = WorldState(tick=2)
    action = PlayerMoveAction(dx=1.0, dz=0.0)
    step = TrajectoryStep(state, action, nxt)
    restored = TrajectoryStep.from_dict(step.to_dict())
    assert restored.state.tick == 1
    assert restored.next_state.tick == 2
    assert restored.action.dx == 1.0


def test_trajectory_recorder_writes_jsonl(tmp_path: Path):
    recorder = TrajectoryRecorder(tmp_path)
    recorder.open("test.jsonl")
    s0 = WorldState(tick=0)
    s1 = WorldState(tick=1)
    recorder.record(s0, PlayerMoveAction(dx=2.0), s1)
    recorder.close()
    lines = (tmp_path / "test.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["next_state"]["tick"] == 1


def test_load_all_trajectories(tmp_path: Path):
    recorder = TrajectoryRecorder(tmp_path)
    recorder.open("a.jsonl")
    recorder.record(WorldState(tick=0), PlayerMoveAction(), WorldState(tick=1))
    recorder.close()
    steps = TrajectoryRecorder.load_all(tmp_path)
    assert len(steps) == 1
