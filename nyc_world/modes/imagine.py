"""What-if imagination UI state."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.simulation.model.world_patch import WorldPatch


@dataclass(frozen=True)
class ImagineScenario:
    scenario_id: str
    label: str
    patch: WorldPatch


SCENARIOS: list[ImagineScenario] = [
    ImagineScenario(
        "rain_at_5pm",
        "It starts raining at 5:00 PM",
        WorldPatch(weather_override="rain", weather_at_hour=17),
    ),
    ImagineScenario(
        "f_train_shutdown",
        "F train shuts down at rush hour",
        WorldPatch(transit_line="F", transit_shutdown=True),
    ),
    ImagineScenario(
        "never_met_maya",
        "Player never met Maya",
        WorldPatch(relationship_overrides={"maya": 0.0}),
    ),
]


@dataclass
class ImagineMode:
    active: bool = False
    scenario_index: int = 0
    horizon_minutes: int = 30
    diff_lines: list[str] = field(default_factory=list)
    menu_lines: list[str] = field(default_factory=list)

    @property
    def scenario(self) -> ImagineScenario:
        return SCENARIOS[self.scenario_index % len(SCENARIOS)]

    def toggle(self) -> bool:
        self.active = not self.active
        if self.active:
            self._refresh_menu()
        else:
            self.diff_lines = []
            self.menu_lines = []
        return self.active

    def cycle_scenario(self) -> ImagineScenario:
        self.scenario_index = (self.scenario_index + 1) % len(SCENARIOS)
        self._refresh_menu()
        return self.scenario

    def _refresh_menu(self) -> None:
        self.menu_lines = [
            "🔮 WHAT IF...",
            "",
        ]
        for i, sc in enumerate(SCENARIOS):
            marker = "●" if i == self.scenario_index else "○"
            self.menu_lines.append(f" {marker} {sc.label}")
        self.menu_lines.extend(["", "Press R to run prediction (30 min horizon)"])

    def set_result(self, lines: list[str]) -> None:
        self.diff_lines = lines
