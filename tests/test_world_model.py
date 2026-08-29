"""Tests for world model training and imagination (Chunks 19-20)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nyc_world.simulation.actions import PlayerMoveAction, WaitAction
from nyc_world.simulation.encoding import encode_input, encode_target
from nyc_world.simulation.model.imagination import default_explore_actions, roll_forward
from nyc_world.simulation.model.simple_model import WorldModel
from nyc_world.simulation.model.train import train_from_directory
from nyc_world.simulation.state import PlayerState, WorldState
from nyc_world.simulation.trajectory import TrajectoryRecorder, TrajectoryStep


def _make_steps(count: int = 20) -> list[TrajectoryStep]:
    steps: list[TrajectoryStep] = []
    state = WorldState(tick=0, player=PlayerState(x=10.0, z=20.0))
    for i in range(count):
        action = PlayerMoveAction(dx=1.0, dz=0.5)
        nxt = WorldState(
            tick=i + 1,
            player=PlayerState(x=10.0 + (i + 1), z=20.0 + (i + 1) * 0.5),
        )
        steps.append(TrajectoryStep(state, action, nxt))
        state = nxt
    return steps


def test_encode_state_has_fixed_size():
    state = WorldState(player=PlayerState(x=50, z=100))
    vec = encode_input(state, WaitAction())
    assert len(vec) > 20


def test_world_model_train_and_predict():
    model = WorldModel()
    steps = _make_steps(30)
    mse = model.train(steps, epochs=40, learning_rate=0.05)
    assert mse >= 0.0
    pred = model.predict(encode_input(steps[0].state, steps[0].action))
    assert len(pred) == model.output_size


def test_world_model_save_load(tmp_path: Path):
    model = WorldModel()
    model.train(_make_steps(10), epochs=5)
    path = tmp_path / "model.json"
    model.save(path)
    loaded = WorldModel.load(path)
    assert loaded.weights == model.weights


def test_train_from_directory(tmp_path: Path):
    recorder = TrajectoryRecorder(tmp_path)
    recorder.open("data.jsonl")
    for step in _make_steps(25):
        recorder.record(step.state, step.action, step.next_state)
    recorder.close()
    model_path = tmp_path / "trained.json"
    model, train_mse, val_mse = train_from_directory(
        tmp_path, model_path=model_path, epochs=30
    )
    assert model_path.exists()
    assert train_mse >= 0.0
    assert val_mse >= 0.0


def test_roll_forward_imagination():
    model = WorldModel()
    model.train(_make_steps(40), epochs=50, learning_rate=0.05)
    initial = WorldState(player=PlayerState(x=10.0, z=20.0))
    actions = default_explore_actions(5, north=True)
    trajectory = roll_forward(model, initial, actions)
    assert len(trajectory) == len(actions) + 1
    assert trajectory[-1].tick >= initial.tick


def test_train_requires_minimum_steps(tmp_path: Path):
    recorder = TrajectoryRecorder(tmp_path)
    recorder.open("tiny.jsonl")
    recorder.record(
        WorldState(tick=0),
        WaitAction(),
        WorldState(tick=1),
    )
    recorder.close()
    with pytest.raises(ValueError):
        train_from_directory(tmp_path)
