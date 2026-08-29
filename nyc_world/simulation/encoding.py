"""Feature encoding for world-model training."""

from __future__ import annotations

from nyc_world.simulation.actions import Action, InteractAction, PlayerMoveAction, WaitAction
from nyc_world.simulation.state import WorldState

# Fixed feature layout for a lightweight world model.
FEATURE_SIZE = 24
TARGET_SIZE = 9

WEATHER_INDEX = {"clear": 0, "cloudy": 1, "rain": 2, "fog": 3}
KEY_NPCS = ("maya", "alex")


def _norm(value: float, scale: float = 500.0) -> float:
    return max(-1.0, min(1.0, value / scale))


def encode_state(state: WorldState) -> list[float]:
    """Flatten WorldState into a fixed-size vector."""
    features = [0.0] * FEATURE_SIZE
    features[0] = _norm(state.player.x)
    features[1] = _norm(state.player.z)
    features[2] = state.player.yaw / 3.14159
    features[3] = state.clock.hour / 24.0
    features[4] = state.clock.minute / 60.0
    weather_idx = WEATHER_INDEX.get(state.clock.weather, 0)
    features[5 + weather_idx] = 1.0
    features[9] = 1.0 if state.player.in_interior else 0.0
    features[10] = min(state.player.money / 200.0, 1.0)
    features[11] = min(state.player.xp / 500.0, 1.0)
    features[12] = 1.0 if state.quests.active_quest_id else 0.0
    features[13] = len(state.quests.completed) / 5.0

    for i, npc_id in enumerate(KEY_NPCS):
        npc = state.npc_by_id(npc_id)
        base = 14 + i * 4
        if npc:
            features[base] = _norm(npc.x)
            features[base + 1] = _norm(npc.z)
            features[base + 2] = npc.mood
            features[base + 3] = npc.player_affinity

    return features


def encode_action(action: Action) -> list[float]:
    """Encode action as a small vector."""
    if isinstance(action, PlayerMoveAction):
        return [_norm(action.dx, 10.0), _norm(action.dz, 10.0), 1.0 if action.sprint else 0.0, 1.0 if action.jump else 0.0, 1.0, 0.0]
    if isinstance(action, InteractAction):
        return [0.0, 0.0, 0.0, 0.0, 0.0, 1.0]
    return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def encode_input(state: WorldState, action: Action) -> list[float]:
    return encode_state(state) + encode_action(action)


def encode_target(next_state: WorldState) -> list[float]:
    """Target vector: player + key NPC positions, time, weather."""
    target = [0.0] * TARGET_SIZE
    target[0] = _norm(next_state.player.x)
    target[1] = _norm(next_state.player.z)
    target[2] = next_state.clock.hour / 24.0
    target[3] = next_state.clock.minute / 60.0
    weather_idx = WEATHER_INDEX.get(next_state.clock.weather, 0)
    target[4] = weather_idx / 3.0

    for i, npc_id in enumerate(KEY_NPCS):
        npc = next_state.npc_by_id(npc_id)
        if npc:
            target[5 + i] = _norm(npc.x)
            target[6 + i] = _norm(npc.z)
    return target
