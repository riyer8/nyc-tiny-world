"""Trajectory recording — (state, action, next_state) for world-model training."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nyc_world.simulation.actions import Action, action_from_dict
from nyc_world.simulation.state import WorldState


@dataclass
class TrajectoryStep:
    state: WorldState
    action: Action
    next_state: WorldState

    def to_dict(self) -> dict:
        action_dict = (
            self.action.to_dict()
            if hasattr(self.action, "to_dict")
            else {"type": "wait"}
        )
        return {
            "state": self.state.to_dict(),
            "action": action_dict,
            "next_state": self.next_state.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> TrajectoryStep:
        return cls(
            state=WorldState.from_dict(data["state"]),
            action=action_from_dict(data["action"]),
            next_state=WorldState.from_dict(data["next_state"]),
        )


class TrajectoryRecorder:
    """Append trajectory steps to JSONL for offline training."""

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or Path("data/trajectories")
        self._file = None
        self._path: Path | None = None
        self.step_count = 0

    def open(self, filename: str | None = None) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        if filename is None:
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"trajectory_{stamp}.jsonl"
        self._path = self.directory / filename
        self._file = self._path.open("a", encoding="utf-8")
        return self._path

    def record(self, state: WorldState, action: Action, next_state: WorldState) -> None:
        if self._file is None:
            self.open()
        step = TrajectoryStep(state, action, next_state)
        self._file.write(json.dumps(step.to_dict()) + "\n")
        self._file.flush()
        self.step_count += 1

    def close(self) -> None:
        if self._file:
            self._file.close()
            self._file = None

    @property
    def path(self) -> Path | None:
        return self._path

    @staticmethod
    def load_steps(path: Path) -> list[TrajectoryStep]:
        steps: list[TrajectoryStep] = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    steps.append(TrajectoryStep.from_dict(json.loads(line)))
        return steps

    @staticmethod
    def load_all(directory: Path) -> list[TrajectoryStep]:
        steps: list[TrajectoryStep] = []
        if not directory.exists():
            return steps
        for path in sorted(directory.glob("*.jsonl")):
            steps.extend(TrajectoryRecorder.load_steps(path))
        return steps
