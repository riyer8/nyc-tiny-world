"""World model training utilities."""

from __future__ import annotations

from pathlib import Path

from nyc_world.simulation.model.simple_model import WorldModel
from nyc_world.simulation.trajectory import TrajectoryRecorder


def train_from_directory(
    trajectory_dir: Path,
    *,
    model_path: Path | None = None,
    epochs: int = 80,
    learning_rate: float = 0.02,
    val_fraction: float = 0.2,
) -> tuple[WorldModel, float, float]:
    """Load trajectories, train model, save weights. Returns (model, train_mse, val_mse)."""
    steps = TrajectoryRecorder.load_all(trajectory_dir)
    if len(steps) < 4:
        raise ValueError(f"Need at least 4 trajectory steps, found {len(steps)} in {trajectory_dir}")

    split = max(1, int(len(steps) * (1 - val_fraction)))
    train_steps = steps[:split]
    val_steps = steps[split:] or steps[-2:]

    model = WorldModel()
    train_mse = model.train(train_steps, epochs=epochs, learning_rate=learning_rate)
    val_mse = model.evaluate(val_steps)

    if model_path:
        model.save(model_path)

    return model, train_mse, val_mse
