"""Simple linear world model — predicts next-state features from state + action."""

from __future__ import annotations

import json
import random
from pathlib import Path

from nyc_world.simulation.encoding import FEATURE_SIZE, TARGET_SIZE, encode_input, encode_target
from nyc_world.simulation.state import WorldState
from nyc_world.simulation.trajectory import TrajectoryStep


class WorldModel:
    """Lightweight linear model: y = W·x + b (pure Python, no ML deps required)."""

    def __init__(self, input_size: int | None = None, output_size: int | None = None) -> None:
        self.input_size = input_size or (FEATURE_SIZE + 6)
        self.output_size = output_size or TARGET_SIZE
        self.weights: list[list[float]] = [
            [random.uniform(-0.01, 0.01) for _ in range(self.input_size)]
            for _ in range(self.output_size)
        ]
        self.bias: list[float] = [0.0] * self.output_size

    def predict(self, features: list[float]) -> list[float]:
        if len(features) < self.input_size:
            features = features + [0.0] * (self.input_size - len(features))
        out: list[float] = []
        for row, b in zip(self.weights, self.bias):
            out.append(sum(w * x for w, x in zip(row, features)) + b)
        return out

    def train(
        self,
        steps: list[TrajectoryStep],
        *,
        epochs: int = 50,
        learning_rate: float = 0.01,
    ) -> float:
        """Train on trajectory steps. Returns final mean squared error."""
        if not steps:
            return 0.0

        pairs = [
            (encode_input(s.state, s.action), encode_target(s.next_state))
            for s in steps
        ]
        mse = 0.0
        for _ in range(epochs):
            total_error = 0.0
            for x, y in pairs:
                pred = self.predict(x)
                errors = [pred[i] - y[i] for i in range(self.output_size)]
                total_error += sum(e * e for e in errors) / self.output_size
                for i in range(self.output_size):
                    for j in range(self.input_size):
                        self.weights[i][j] -= learning_rate * errors[i] * x[j]
                    self.bias[i] -= learning_rate * errors[i]
            mse = total_error / len(pairs)
        return mse

    def evaluate(self, steps: list[TrajectoryStep]) -> float:
        if not steps:
            return 0.0
        total = 0.0
        for step in steps:
            pred = self.predict(encode_input(step.state, step.action))
            target = encode_target(step.next_state)
            total += sum((p - t) ** 2 for p, t in zip(pred, target)) / len(target)
        return total / len(steps)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "input_size": self.input_size,
                    "output_size": self.output_size,
                    "weights": self.weights,
                    "bias": self.bias,
                }
            ),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: Path) -> WorldModel:
        data = json.loads(path.read_text(encoding="utf-8"))
        model = cls(data["input_size"], data["output_size"])
        model.weights = data["weights"]
        model.bias = data["bias"]
        return model


def apply_prediction(state: WorldState, prediction: list[float], scale: float = 500.0) -> WorldState:
    """Convert model output back into a WorldState snapshot."""
    next_state = WorldState.from_dict(state.to_dict())
    next_state.tick = state.tick + 1
    next_state.clock.tick = next_state.tick

    next_state.player.x = max(-scale, min(scale, prediction[0] * scale))
    next_state.player.z = max(-scale, min(scale, prediction[1] * scale))
    next_state.clock.hour = int(prediction[2] * 24) % 24
    next_state.clock.minute = int(prediction[3] * 60) % 60

    weather_choices = ["clear", "cloudy", "rain", "fog"]
    weather_idx = int(round(prediction[4] * 3))
    next_state.clock.weather = weather_choices[max(0, min(3, weather_idx))]

    maya = next_state.npc_by_id("maya")
    if maya and len(prediction) > 5:
        maya.x = prediction[5] * scale
        maya.z = prediction[6] * scale
    alex = next_state.npc_by_id("alex")
    if alex and len(prediction) > 7:
        alex.x = prediction[7] * scale
        alex.z = prediction[8] * scale if len(prediction) > 8 else alex.z

    return next_state
