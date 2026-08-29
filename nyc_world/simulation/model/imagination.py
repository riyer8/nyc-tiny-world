"""Roll-forward imagination using a trained world model."""

from __future__ import annotations

from nyc_world.simulation.actions import Action, PlayerMoveAction, WaitAction
from nyc_world.simulation.encoding import encode_input
from nyc_world.simulation.model.simple_model import WorldModel, apply_prediction
from nyc_world.simulation.state import WorldState


def roll_forward(
    model: WorldModel,
    initial_state: WorldState,
    actions: list[Action],
) -> list[WorldState]:
    """Imagine a future trajectory without running the real simulation."""
    trajectory = [initial_state]
    current = initial_state
    for action in actions:
        features = encode_input(current, action)
        prediction = model.predict(features)
        current = apply_prediction(current, prediction)
        trajectory.append(current)
    return trajectory


def describe_trajectory(states: list[WorldState]) -> list[str]:
    """Human-readable summary of an imagined future."""
    lines: list[str] = []
    for i, state in enumerate(states):
        maya = state.npc_by_id("maya")
        alex = state.npc_by_id("alex")
        maya_pos = f"({maya.x:.0f},{maya.z:.0f})" if maya else "?"
        alex_pos = f"({alex.x:.0f},{alex.z:.0f})" if alex else "?"
        lines.append(
            f"t+{i}: player=({state.player.x:.0f},{state.player.z:.0f}) "
            f"time={state.clock.hour:02d}:{state.clock.minute:02d} "
            f"weather={state.clock.weather} "
            f"maya={maya_pos} alex={alex_pos}"
        )
    return lines


def default_explore_actions(steps: int, *, north: bool = True) -> list[Action]:
    """Generate a simple walk-north action sequence for demos."""
    dx, dz = (0.0, 2.0) if north else (2.0, 0.0)
    return [PlayerMoveAction(dx=dx, dz=dz) for _ in range(steps)] + [WaitAction()]
