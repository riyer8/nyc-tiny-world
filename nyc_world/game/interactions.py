"""Player interaction system — proximity detection and E to interact."""

from __future__ import annotations

from dataclasses import dataclass, field

from nyc_world.game.interactables import Interactable, InteractableKind
from nyc_world.game.interiors import INTERIORS, Interior
from nyc_world.city.landmarks import CAFE, LANDMARK, STORE, SUBWAY, Landmark3D
from nyc_world.city.npcs import NPC
from nyc_world.game.dialogue_lines import DIALOGUE
from nyc_world.game.quests import QuestManager


@dataclass
class InteractionResult:
    success: bool
    lines: list[str] = field(default_factory=list)
    entered_interior: str | None = None
    exited_interior: bool = False
    open_subway: bool = False


class InteractionSystem:
    def __init__(
        self,
        interactables: list[Interactable],
        quest_manager: QuestManager,
    ) -> None:
        self.interactables = interactables
        self.quests = quest_manager
        self.nearest: Interactable | None = None
        self.mode: str = "exterior"
        self.current_interior_id: str | None = None
        self.current_subway_station: str | None = None
        self._interior_interactables: list[Interactable] = []

    @property
    def active_interactables(self) -> list[Interactable]:
        if self.mode == "interior":
            return self._interior_interactables
        return self.interactables

    def update_player(self, x: float, z: float) -> None:
        self.nearest = None
        best_dist = float("inf")
        for item in self.active_interactables:
            d = item.distance_to(x, z)
            if d <= item.radius and d < best_dist:
                best_dist = d
                self.nearest = item

    def try_interact(self, x: float, z: float) -> InteractionResult:
        self.update_player(x, z)
        if not self.nearest:
            return InteractionResult(False)

        target = self.nearest
        lines: list[str] = []

        if self.mode == "interior":
            return self._interact_interior(target)

        if target.kind == InteractableKind.NPC:
            lines.extend(self.quests.on_talk_npc(target.id))
            return InteractionResult(True, lines)

        if target.kind == InteractableKind.CAFE:
            lines.extend(self.quests.on_visit(target.id))
            if target.interior_id:
                lines.extend(self.quests.on_enter_building(target.interior_id))
                self._enter_interior(target.interior_id)
                return InteractionResult(True, lines, entered_interior=target.interior_id)
            return InteractionResult(True, lines)

        if target.kind == InteractableKind.BUILDING and target.interior_id:
            lines.extend(self.quests.on_enter_building(target.interior_id))
            self._enter_interior(target.interior_id)
            return InteractionResult(True, lines, entered_interior=target.interior_id)

        if target.kind == InteractableKind.SUBWAY:
            if not self.quests.player.has_item("metro_card"):
                lines.extend(DIALOGUE.get("subway_no_card", ["You need a MetroCard."]))
                return InteractionResult(True, lines)
            return InteractionResult(True, [], open_subway=True)

        if target.kind == InteractableKind.OBJECT and target.item_id:
            lines.extend(self.quests.on_collect(target.item_id))
            return InteractionResult(True, lines)

        if target.dialogue_id and target.dialogue_id in DIALOGUE:
            lines.extend(DIALOGUE[target.dialogue_id])
            return InteractionResult(True, lines)

        lines.append(f"You interact with {target.label}.")
        return InteractionResult(True, lines)

    def _interact_interior(self, target: Interactable) -> InteractionResult:
        if target.id.startswith("exit_"):
            self._exit_interior()
            return InteractionResult(True, ["You step back outside."], exited_interior=True)

        lines: list[str] = []
        if target.kind == InteractableKind.OBJECT and target.item_id:
            lines.extend(self.quests.on_collect(target.item_id))
            return InteractionResult(True, lines)
        if target.dialogue_id and target.dialogue_id in DIALOGUE:
            lines.extend(DIALOGUE[target.dialogue_id])
            return InteractionResult(True, lines)
        return InteractionResult(True, [f"You look at {target.label}."])

    def _enter_interior(self, interior_id: str) -> None:
        interior = INTERIORS.get(interior_id)
        if not interior:
            return
        self.mode = "interior"
        self.current_interior_id = interior_id
        self._interior_interactables = list(interior.interactables)

    def _exit_interior(self) -> None:
        self.mode = "exterior"
        self.current_interior_id = None
        self._interior_interactables = []

    def enter_subway(self, station_id: str) -> None:
        self.mode = "subway"
        self.current_subway_station = station_id

    def exit_subway(self) -> None:
        if self.mode == "subway":
            self.mode = "exterior"
        self.current_subway_station = None

    @property
    def in_subway(self) -> bool:
        return self.mode == "subway"

    def prompt(self) -> str | None:
        if self.nearest:
            return self.nearest.prompt_text()
        return None


def build_world_interactables(
    landmarks: list[Landmark3D],
    npcs: list[NPC],
    spawn_x: float,
    spawn_z: float,
) -> list[Interactable]:
    """Build interactables from OSM landmarks + quest-specific placements."""
    items: list[Interactable] = []

    cafe = _find_nearest_landmark(landmarks, CAFE, spawn_x, spawn_z)
    library = _find_named_landmark(landmarks, "Jefferson Market")
    if not library:
        library = _find_nearest_landmark(landmarks, LANDMARK, spawn_x + 80, spawn_z - 40)

    if cafe:
        items.append(
            Interactable(
                id="cafe_village",
                kind=InteractableKind.CAFE,
                x=cafe.x,
                z=cafe.z,
                label=cafe.name or "Village Cafe",
                interior_id="cafe_interior",
                emoji="☕",
            )
        )
    else:
        items.append(
            Interactable(
                id="cafe_village",
                kind=InteractableKind.CAFE,
                x=spawn_x + 30,
                z=spawn_z - 20,
                label="Village Cafe",
                interior_id="cafe_interior",
                emoji="☕",
            )
        )

    if library:
        items.append(
            Interactable(
                id="library_building",
                kind=InteractableKind.BUILDING,
                x=library.x,
                z=library.z,
                label=library.name or "Jefferson Market Library",
                interior_id="library_interior",
                radius=5.0,
                emoji="🏛️",
            )
        )
    else:
        items.append(
            Interactable(
                id="library_building",
                kind=InteractableKind.BUILDING,
                x=spawn_x + 60,
                z=spawn_z - 50,
                label="Jefferson Market Library",
                interior_id="library_interior",
                radius=5.0,
                emoji="🏛️",
            )
        )

    subway = _find_nearest_landmark(landmarks, SUBWAY, spawn_x, spawn_z)
    if subway:
        items.append(
            Interactable(
                id="subway_wsp",
                kind=InteractableKind.SUBWAY,
                x=subway.x,
                z=subway.z,
                label=subway.name or "Subway",
                radius=4.0,
            )
        )

    store = _find_nearest_landmark(landmarks, STORE, spawn_x + 40, spawn_z)
    if store:
        items.append(
            Interactable(
                id="photo_shop",
                kind=InteractableKind.BUILDING,
                x=store.x,
                z=store.z,
                label=store.name or "Photo Shop",
                interior_id="photo_shop_interior",
                emoji="🏪",
            )
        )

    for npc in npcs:
        if npc.name in ("maya", "alex"):
            items.append(
                Interactable(
                    id=npc.name,
                    kind=InteractableKind.NPC,
                    x=npc.x,
                    z=npc.z,
                    label=npc.name.title(),
                    radius=2.5,
                    quest_npc=True,
                )
            )

    return items


def assign_quest_npcs(npcs: list[NPC], spawn_x: float, spawn_z: float) -> None:
    """Pin quest NPCs to known locations near spawn."""
    if not npcs:
        return
    npcs[0].name = "maya"
    npcs[0].x = spawn_x + 5
    npcs[0].z = spawn_z + 3
    npcs[0].color = (0.85, 0.45, 0.55)
    if len(npcs) > 1:
        npcs[1].name = "alex"
        npcs[1].x = spawn_x + 35
        npcs[1].z = spawn_z - 15
        npcs[1].color = (0.35, 0.55, 0.85)


def _find_nearest_landmark(
    landmarks: list[Landmark3D],
    kind: str,
    x: float,
    z: float,
) -> Landmark3D | None:
    matches = [lm for lm in landmarks if lm.kind == kind]
    if not matches:
        return None
    return min(matches, key=lambda lm: (lm.x - x) ** 2 + (lm.z - z) ** 2)


def _find_named_landmark(landmarks: list[Landmark3D], substring: str) -> Landmark3D | None:
    for lm in landmarks:
        if substring.lower() in lm.name.lower():
            return lm
    return None
