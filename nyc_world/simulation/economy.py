"""City economy — businesses, residences, and weekly evolution."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nyc_world.simulation.event_log import EventLog
    from nyc_world.simulation.npc_mind import NPCMindRegistry


@dataclass
class Business:
    id: str
    name: str
    location_id: str
    cash: float
    reputation: float
    staff: list[str]
    rent: float = 120.0
    base_revenue: float = 55.0
    open: bool = True

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "location_id": self.location_id,
            "cash": self.cash,
            "reputation": self.reputation,
            "staff": list(self.staff),
            "rent": self.rent,
            "base_revenue": self.base_revenue,
            "open": self.open,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Business:
        return cls(
            id=data["id"],
            name=data.get("name", data["id"]),
            location_id=data.get("location_id", ""),
            cash=data.get("cash", 0.0),
            reputation=data.get("reputation", 0.5),
            staff=list(data.get("staff", [])),
            rent=data.get("rent", 120.0),
            base_revenue=data.get("base_revenue", 55.0),
            open=data.get("open", True),
        )


@dataclass
class Residence:
    unit_id: str
    location_id: str
    occupants: list[str]
    rent: float
    for_rent: bool = False

    def to_dict(self) -> dict:
        return {
            "unit_id": self.unit_id,
            "location_id": self.location_id,
            "occupants": list(self.occupants),
            "rent": self.rent,
            "for_rent": self.for_rent,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Residence:
        return cls(
            unit_id=data["unit_id"],
            location_id=data.get("location_id", ""),
            occupants=list(data.get("occupants", [])),
            rent=data.get("rent", 1500.0),
            for_rent=data.get("for_rent", False),
        )


@dataclass
class EvolutionEntry:
    week: int
    line: str

    def to_dict(self) -> dict:
        return {"week": self.week, "line": self.line}

    @classmethod
    def from_dict(cls, data: dict) -> EvolutionEntry:
        return cls(week=data.get("week", 1), line=data.get("line", ""))


REPLACEMENT_NAMES: dict[str, list[str]] = {
    "photo_shop": ["Lens & Leaf", "Frame Forward", "Village Optics", "Silver Street Studio"],
    "cafe_village": ["The Daily Grind", "MacDougal Roasters", "Perk & Pour"],
}

SALARY_PER_STAFF = 65.0
WAGE_RENT_MULTIPLIER = 0.04


def seed_village_economy() -> CityEconomy:
    """Starter businesses and residences near Washington Square (12 trackable businesses)."""
    economy = CityEconomy()
    seeds = [
        ("joes_camera", "Joe's Camera", "photo_shop", 95.0, 0.42, [], 130.0, 38.0),
        ("village_cafe", "Village Cafe", "cafe_village", 240.0, 0.72, ["maya"], 150.0, 62.0),
        ("corner_books", "Corner Books", "library_building", 180.0, 0.65, ["alex"], 110.0, 48.0),
        ("west_4th_records", "West 4th Records", "west_4th_records", 140.0, 0.55, [], 105.0, 42.0),
        ("bleecker_boutique", "Bleecker Boutique", "bleecker_boutique", 120.0, 0.48, [], 125.0, 36.0),
        ("thompson_bar", "Thompson Bar", "thompson_bar", 200.0, 0.68, [], 140.0, 58.0),
        ("washington_cart", "Washington Cart", "washington_cart", 75.0, 0.5, [], 80.0, 28.0),
        ("macdougal_gallery", "MacDougal Gallery", "macdougal_gallery", 160.0, 0.6, [], 115.0, 44.0),
        ("sullivan_bakery", "Sullivan Bakery", "sullivan_bakery", 130.0, 0.57, [], 100.0, 40.0),
        ("laguardia_plants", "LaGuardia Plants", "laguardia_plants", 90.0, 0.45, [], 95.0, 32.0),
        ("perry_studio", "Perry Studio", "perry_studio", 110.0, 0.52, [], 108.0, 35.0),
        ("christopher_cuts", "Christopher Cuts", "christopher_cuts", 155.0, 0.63, [], 118.0, 46.0),
    ]
    economy.businesses = {
        bid: Business(
            id=bid,
            name=name,
            location_id=loc,
            cash=cash,
            reputation=rep,
            staff=staff,
            rent=rent,
            base_revenue=rev,
        )
        for bid, name, loc, cash, rep, staff, rent, rev in seeds
    }
    economy.residences = {
        "wsp_apt_4b": Residence(
            unit_id="wsp_apt_4b",
            location_id="library_building",
            occupants=["maya"],
            rent=1650.0,
        ),
        "macdougal_studio": Residence(
            unit_id="macdougal_studio",
            location_id="cafe_village",
            occupants=["alex"],
            rent=1420.0,
        ),
    }
    economy.npc_wallets = {"maya": 420.0, "alex": 380.0}
    return economy


@dataclass
class CityEconomy:
    businesses: dict[str, Business] = field(default_factory=dict)
    residences: dict[str, Residence] = field(default_factory=dict)
    journal: list[EvolutionEntry] = field(default_factory=list)
    npc_wallets: dict[str, float] = field(default_factory=dict)
    week: int = 1
    processed_week: int = -1
    village_rent_index: float = 1.0
    new_coworker_announced: bool = False
    _replacement_index: dict[str, int] = field(default_factory=dict)

    def business_at_location(self, location_id: str) -> Business | None:
        for biz in self.businesses.values():
            if biz.location_id == location_id and biz.open:
                return biz
        return None

    def facade_label(self, location_id: str, default: str) -> str:
        biz = self.business_at_location(location_id)
        if biz:
            return biz.name
        residence = next(
            (r for r in self.residences.values() if r.location_id == location_id),
            None,
        )
        if residence and residence.for_rent:
            return f"{default} — FOR RENT"
        return default

    def journal_lines(self, *, limit: int = 12) -> list[str]:
        lines = [f"WEEK {self.week}"]
        recent = self.journal[-limit:]
        if not recent:
            lines.append(" · No changes yet — fast-forward time to watch the city evolve.")
            return lines
        for entry in recent:
            lines.append(f" · {entry.line}")
        return lines

    def maybe_weekly_tick(
        self,
        game_day: int,
        *,
        minds: NPCMindRegistry | None = None,
        event_log: EventLog | None = None,
        rng: random.Random | None = None,
    ) -> list[str]:
        current_week = (game_day - 1) // 7
        if current_week <= self.processed_week:
            return []
        self.processed_week = current_week
        self.week = current_week + 1
        return self.weekly_tick(minds=minds, event_log=event_log, rng=rng)

    def weekly_tick(
        self,
        *,
        minds: NPCMindRegistry | None = None,
        event_log: EventLog | None = None,
        rng: random.Random | None = None,
    ) -> list[str]:
        rng = rng or random.Random(42 + self.week)
        lines: list[str] = []

        for biz in list(self.businesses.values()):
            if not biz.open:
                continue
            noise = rng.uniform(0.85, 1.15)
            revenue = biz.base_revenue * (0.4 + biz.reputation) * noise
            wages = SALARY_PER_STAFF * len(biz.staff)
            biz.cash += revenue - biz.rent - wages
            biz.reputation = max(0.1, min(1.0, biz.reputation + rng.uniform(-0.03, 0.05)))
            for staff_id in biz.staff:
                self.npc_wallets[staff_id] = self.npc_wallets.get(staff_id, 0.0) + SALARY_PER_STAFF

            if biz.cash < 0:
                line = f"{biz.name} closed (bankruptcy)"
                lines.append(line)
                self._record(line)
                self._close_and_replace(biz, minds=minds, lines=lines, rng=rng)
                if event_log:
                    event_log.append(
                        tick=0,
                        game_day=self.week * 7,
                        game_time="",
                        actor_id="economy",
                        action="business_closed",
                        location_id=biz.location_id,
                        details=biz.name,
                    )

        rent_bump = rng.uniform(0.01, 0.04)
        self.village_rent_index += rent_bump
        lines.append(f"Rent in Village +{rent_bump * 100:.0f}%")
        self._record(f"Rent in Village +{rent_bump * 100:.0f}%")

        for residence in self.residences.values():
            adjusted_rent = residence.rent * self.village_rent_index
            broke: list[str] = []
            for occupant in list(residence.occupants):
                wallet = self.npc_wallets.get(occupant, 0.0)
                payment = adjusted_rent * WAGE_RENT_MULTIPLIER
                if wallet >= payment:
                    self.npc_wallets[occupant] = wallet - payment
                else:
                    broke.append(occupant)
            for occupant in broke:
                residence.occupants.remove(occupant)
                residence.for_rent = True
                line = f"{occupant.title()} moved out of {residence.unit_id}"
                lines.append(line)
                self._record(line)

        if minds:
            self._drift_relationships(minds, lines)

        return lines

    def _drift_relationships(self, minds: NPCMindRegistry, lines: list[str]) -> None:
        maya = minds.get("maya")
        alex = minds.get("alex")
        if maya and alex:
            delta = 0.12
            maya.adjust_npc_relationship("alex", delta)
            alex.adjust_npc_relationship("maya", delta)
            line = f"Alex and Maya friendship +{int(delta * 100)}"
            if not any(e.line == line for e in self.journal[-3:]):
                lines.append(line)
                self._record(line)

        coworkers: dict[str, list[str]] = {}
        for biz in self.businesses.values():
            if biz.open and len(biz.staff) >= 2:
                for staff_id in biz.staff:
                    coworkers.setdefault(staff_id, []).extend(
                        s for s in biz.staff if s != staff_id
                    )
        for staff_id, others in coworkers.items():
            mind = minds.get(staff_id)
            if not mind:
                continue
            for other in others:
                mind.adjust_npc_relationship(other, 0.05)

    def _close_and_replace(
        self,
        biz: Business,
        *,
        minds: NPCMindRegistry | None,
        lines: list[str],
        rng: random.Random,
    ) -> None:
        location_id = biz.location_id
        old_name = biz.name
        biz.open = False
        options = REPLACEMENT_NAMES.get(location_id, [f"New {location_id.replace('_', ' ').title()}"])
        idx = self._replacement_index.get(location_id, 0) % len(options)
        self._replacement_index[location_id] = idx + 1
        new_name = options[idx]
        new_id = f"{location_id}_{idx}"
        new_staff: list[str] = []
        if location_id == "photo_shop":
            new_staff = ["jordan"]
            self.new_coworker_announced = True
            if minds:
                maya = minds.get("maya")
                if maya:
                    maya.remember("new_coworker", 0, "jordan at Lens & Leaf")

        replacement = Business(
            id=new_id,
            name=new_name,
            location_id=location_id,
            cash=rng.uniform(120, 200),
            reputation=rng.uniform(0.45, 0.7),
            staff=new_staff,
            rent=biz.rent * 0.95,
            base_revenue=biz.base_revenue * 1.05,
        )
        self.businesses[new_id] = replacement
        line = f'"{new_name}" opened in same unit'
        lines.append(line)
        self._record(line)
        if location_id == "photo_shop" and old_name:
            self._record(f"{old_name} → {new_name}")

    def _record(self, line: str) -> None:
        self.journal.append(EvolutionEntry(week=self.week, line=line))

    def apply_facades(self, interactables) -> None:
        for item in interactables:
            item.label = self.facade_label(item.id, item.label)

    def to_dict(self) -> dict:
        return {
            "businesses": {k: v.to_dict() for k, v in self.businesses.items()},
            "residences": {k: v.to_dict() for k, v in self.residences.items()},
            "journal": [e.to_dict() for e in self.journal],
            "npc_wallets": dict(self.npc_wallets),
            "week": self.week,
            "processed_week": self.processed_week,
            "village_rent_index": self.village_rent_index,
            "new_coworker_announced": self.new_coworker_announced,
            "replacement_index": dict(self._replacement_index),
        }

    @classmethod
    def from_dict(cls, data: dict) -> CityEconomy:
        economy = cls(
            businesses={
                k: Business.from_dict(v) for k, v in data.get("businesses", {}).items()
            },
            residences={
                k: Residence.from_dict(v) for k, v in data.get("residences", {}).items()
            },
            journal=[EvolutionEntry.from_dict(e) for e in data.get("journal", [])],
            npc_wallets=dict(data.get("npc_wallets", {})),
            week=data.get("week", 1),
            processed_week=data.get("processed_week", -1),
            village_rent_index=data.get("village_rent_index", 1.0),
            new_coworker_announced=data.get("new_coworker_announced", False),
        )
        economy._replacement_index = dict(data.get("replacement_index", {}))
        return economy
