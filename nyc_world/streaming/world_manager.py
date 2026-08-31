"""Streaming world manager — ties loader, LOD, and city simulation."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.city.city_sim import CitySimulation
from nyc_world.core.projection import GeoProjection
from nyc_world.geo.coords import world_xz_to_gps
from nyc_world.map.buildings import Building3D, load_buildings
from nyc_world.streaming.loader import TileDataLoader
from nyc_world.streaming.lod import (
    lod_buildings,
    lod_landmarks,
    lod_npcs,
    lod_vehicles,
)
from nyc_world.streaming.radii import DEFAULT_RADII, StreamRadii
from nyc_world.streaming.state import StreamingState
from nyc_world.streaming.tiles import gps_to_tile


class StreamingWorldManager:
    """Orchestrate tile loading and level-of-detail around the player."""

    def __init__(
        self,
        projection: GeoProjection,
        meters_per_tile: float,
        spawn_x: float,
        spawn_z: float,
        all_buildings: list[Building3D],
        *,
        radii: StreamRadii | None = None,
        loader: TileDataLoader | None = None,
        npc_count: int = 48,
        vehicle_count: int = 32,
    ) -> None:
        self.projection = projection
        self.meters_per_tile = meters_per_tile
        self.radii = radii or DEFAULT_RADII
        self.loader = loader or TileDataLoader(network=False)
        self.all_buildings = all_buildings
        self.city = CitySimulation(
            projection, spawn_x, spawn_z, npc_count=npc_count, vehicle_count=vehicle_count
        )
        self.state = StreamingState(
            data_radius_m=self.radii.data_m,
            render_radius_m=self.radii.render_3d_m,
            simulation_radius_m=self.radii.simulation_m,
        )
        self.render_buildings: list[Building3D] = []
        self.render_landmarks = self.city.landmarks
        self.render_npcs = self.city.npcs
        self.render_vehicles = self.city.vehicles

    def update_player(self, player_x: float, player_z: float) -> StreamingState:
        lat, lon = world_xz_to_gps(player_x, player_z, self.projection, self.meters_per_tile)
        tile = gps_to_tile(lat, lon)

        self.state.player_lat = lat
        self.state.player_lon = lon
        self.state.player_tile = tile.tile_id
        self.state.loaded_tile_ids = self.loader.load_around(lat, lon, self.radii.data_m)
        self.loader.unload_outside(lat, lon, self.radii.data_m)

        detailed, markers = lod_buildings(
            self.all_buildings, player_x, player_z, self.radii
        )
        self.render_buildings = detailed
        self.state.far_building_markers = markers
        self.state.buildings_in_render = len(detailed)
        self.state.buildings_in_data = len(detailed) + len(markers)

        self.render_landmarks = lod_landmarks(
            self.city.landmarks, player_x, player_z, self.radii.render_3d_m
        )
        self.render_npcs = lod_npcs(
            self.city.npcs, player_x, player_z, self.radii.simulation_m
        )
        self.render_vehicles = lod_vehicles(
            self.city.vehicles, player_x, player_z, self.radii.simulation_m
        )
        return self.state

    def update(self, dt: float, player_x: float, player_z: float, *, speed_multiplier: float = 1.0, tick_city: bool = True) -> None:
        self.update_player(player_x, player_z)
        if tick_city:
            self.city.update(
                dt,
                speed_multiplier=speed_multiplier,
                player_x=player_x,
                player_z=player_z,
            )

    @property
    def street_scene(self):
        return self.city.street_scene

    @property
    def clock(self):
        return self.city.clock

    @property
    def streets(self):
        return self.city.streets

    def summary(self) -> str:
        return (
            f"{len(self.state.loaded_tile_ids)} tiles, "
            f"{self.state.buildings_in_render} 3D buildings, "
            f"{len(self.render_npcs)} NPCs, "
            f"{len(self.render_vehicles)} vehicles"
        )

    def try_load_streamed_buildings(self) -> list[Building3D]:
        """Build 3D models from merged tile OSM (when tiles are cached)."""
        if not self.state.loaded_tile_ids:
            return []
        merged = self.loader.merge_elements(self.state.loaded_tile_ids)
        if not merged.get("elements"):
            return []
        return load_buildings(self.projection, merged)
