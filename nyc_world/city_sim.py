"""Backward-compatible import path. Prefer: from nyc_world.city import CitySimulation."""

from nyc_world.city.city_sim import CitySimulation

__all__ = ["CitySimulation"]
