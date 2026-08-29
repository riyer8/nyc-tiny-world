"""A* pathfinding on street graphs."""

from __future__ import annotations

import heapq
import math
from collections import defaultdict
def astar(
    graph: dict[int, list[tuple[int, float]]],
    start: int,
    goal: int,
    *,
    max_nodes: int = 50_000,
) -> list[int]:
    """Return node-id path from start to goal, or [] if unreachable."""
    if start == goal:
        return [start]
    if start not in graph or goal not in graph:
        return []

    positions: dict[int, tuple[float, float]] = getattr(astar, "_positions", {})

    def h(node: int) -> float:
        x0, z0 = positions[node]
        x1, z1 = positions[goal]
        return math.hypot(x1 - x0, z1 - z0)

    open_heap: list[tuple[float, int]] = [(h(start), start)]
    came_from: dict[int, int] = {}
    g_score: dict[int, float] = {start: 0.0}
    closed: set[int] = set()
    expanded = 0

    while open_heap and expanded < max_nodes:
        _, current = heapq.heappop(open_heap)
        if current in closed:
            continue
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        closed.add(current)
        expanded += 1
        for neighbor, cost in graph.get(current, []):
            if neighbor in closed:
                continue
            tentative = g_score[current] + cost
            if tentative < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative
                heapq.heappush(open_heap, (tentative + h(neighbor), neighbor))

    return []


def build_adjacency(
    edges: list[tuple[int, int, float]],
) -> dict[int, list[tuple[int, float]]]:
    graph: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for u, v, length in edges:
        graph[u].append((v, length))
        graph[v].append((u, length))
    return dict(graph)


def path_to_world(
    path: list[int],
    positions: dict[int, tuple[float, float]],
) -> list[tuple[float, float]]:
    return [positions[n] for n in path if n in positions]


def set_astar_positions(positions: dict[int, tuple[float, float]]) -> None:
    astar._positions = positions  # type: ignore[attr-defined]
