# NYC Tiny World — Vision Goal

> **North star:** A tiny, walkable, GPS-grounded NYC that *remembers you*, *thinks*, *generates stories*, and can be observed, manipulated, and predicted — like a living digital twin with a game on top.

This document defines what “done” looks like for the next era of the project. It is written against the **current codebase** (not vaporware) and specifies systems, UX, data models, milestones, and acceptance criteria for all twelve vision pillars.

---

## Principles (non‑negotiable)

1. **Simulation first, renderer second.** Every feature must serialize into `WorldState` JSON. Pygame/OpenGL today; Godot tomorrow.
2. **No fake memory.** If the HUD says an NPC remembers something, it must be stored, queryable, and behavior-changing.
3. **Procedural ≠ random.** Generated quests and mysteries must be *causally reconstructable* from simulation logs.
4. **Real NYC when possible.** External feeds (weather, MTA, events) are optional inputs with graceful offline fallback.
5. **Inspectable.** Every mode (game, twin, god, photo) is a lens on the same simulation — not a separate hack.
6. **Incremental shipping.** Each pillar ships a vertical slice that is playable and testable before the next pillar starts.

---

## What exists today (foundation)

| Layer | Status | Key files |
|-------|--------|-----------|
| OSM map + 3D city | ✅ | `map/`, `render/`, `city/streets.py` |
| Third-person play | ✅ | `scripts/play_3d.py`, `render/camera.py`, `game/player_avatar.py` |
| Living city (48 NPCs, 32 vehicles) | ✅ | `city/city_sim.py`, `city/npcs.py`, `city/vehicles.py` |
| Quest: *The Missing Camera* | ✅ | `game/quests.py` |
| Player profile (money, XP, items) | ✅ | `game/profile.py` |
| Player ↔ NPC relationships (profile) | ✅ partial | `PlayerProfile.relationships` |
| NPC minds (needs, goals, memory) | ✅ partial | `simulation/npc_mind.py` — Maya & Alex only |
| `WorldState` snapshots | ✅ | `simulation/state.py` |
| Trajectory recording + world model | ✅ prototype | `simulation/trajectory.py`, `simulation/model/` |
| Streaming LOD | ✅ | `streaming/` |
| Geo HUD + mini-map | ✅ | `geo/`, `render/gl_hud.py` |

### Known gaps to close first

- **Dual relationship systems:** `PlayerProfile.relationships` and `NPCMind.player_affinity` are not unified.
- **Memory is shallow:** 32 string events, no structured facts, no visit counts, no opinion synthesis.
- **NPC brains are scripted:** time-of-day rules (`home_hour`, rain) — not utility-based decisions.
- **Quests are hand-authored:** one quest, fixed dialogue keys in `DIALOGUE`.
- **No persistence across sessions:** profile/minds reset on quit.
- **No event log / replay:** cannot reconstruct “what happened at 11:42 PM.”
- **Subway = landmark mesh**, not a transport simulation.
- **World model is CLI-only**, not in-game.

**Phase 0 (prerequisite)** addresses these before pillar features land.

---

## Architecture target

```
                    ┌─────────────────────────────────────┐
                    │           PLAYER LENSES             │
                    │  Game · Twin · God · Photo · What-If │
                    └─────────────────┬───────────────────┘
                                      │
                    ┌─────────────────▼───────────────────┐
                    │         GameSession / HUD           │
                    │  quests · dialogue · interactions   │
                    └─────────────────┬───────────────────┘
                                      │
        ┌─────────────────────────────▼─────────────────────────────┐
        │                    SIMULATION CORE                         │
        │  WorldState · EventLog · Simulation.step() · Schedulers   │
        └─────────┬───────────────────────┬─────────────────────────┘
                  │                       │
     ┌────────────▼────────────┐ ┌────────▼────────────┐
     │   AGENT LAYER           │ │  STORY LAYER        │
     │  Personality · Needs    │ │  QuestGen · Mystery │
     │  Goals · Memory · Plans │ │  LLM narrator (opt)│
     └────────────┬────────────┘ └────────┬────────────┘
                  │                       │
     ┌────────────▼───────────────────────▼────────────┐
     │              CITY SYSTEMS                        │
     │  Streets · Buildings · Subway · Weather · Feeds  │
     └──────────────────────────────────────────────────┘
```

---

# The twelve pillars

---

## 🥇 1. Make the city remember you

### Player experience

Walk up to Maya after several sessions. Press **E**. The interaction panel shows:

```
MAYA
────────────────────────────────────
Met you: Day 1, 8:14 AM
Trust: 72    Friendship: 48
Last seen: 2 hours ago · Visits: 3

MEMORIES
 ✓ You found her camera        (Day 1)
 ✓ You gave her $10            (Day 2)
 ✗ You stole her coffee ☕     (Day 3)
 ✓ You visited her twice

OPINION
 "Generally helpful.
  Slightly suspicious."
```

Dialogue changes:

| History | Greeting |
|---------|----------|
| Helped often | *"Hey! I was hoping you'd come by."* |
| Stole from them | *"Don't touch that."* |
| Neutral + first time today | *"Oh, hi again."* |
| Long absence | *"It's been a while…"* |

### System design

**New module:** `nyc_world/simulation/memory.py`

```python
@dataclass
class MemoryFact:
    id: str
    category: str          # "helped" | "stole" | "gave" | "visited" | "talked" | ...
    summary: str             # display string
    tick: int
    game_day: int
    game_time: str           # "08:14"
  # optional structured payload
    target_id: str = ""
    amount: int = 0
    sentiment: float = 0.0   # -1..1

@dataclass
class NPCPlayerRelationship:
    met_tick: int
    met_day: int
    visit_count: int
    last_seen_tick: int
    trust: float             # 0..100
    friendship: float        # 0..100
    facts: list[MemoryFact]
```

**Opinion synthesis** (`memory.py` → `synthesize_opinion(facts, trust, friendship) -> str`):
- Rule-based template for offline play (always works).
- Optional LLM polish layer later (pillar 3) — never required for correctness.

**Behavior hooks** (`npc_mind.py`, `game/interactions.py`):
- `on_player_enter_radius(npc_id)` → increment `visit_count`, record `visited`.
- `on_give_money`, `on_steal`, `on_quest_complete` → append `MemoryFact`, adjust trust/friendship.
- Dialogue router picks line set from memory tags, not just quest state.

**Persistence:** `data/saves/<slot>/world.json` containing `PlayerProfile`, all `NPCMind`s, `MemoryFact`s, quest state.

### HUD

New panel section when targeting an NPC (or in profile → Relationships → drill-down).

### Acceptance criteria

- [ ] Maya shows ≥4 memory lines after scripted play session (help, steal, visit, gift).
- [ ] Greeting dialogue differs for high-trust vs thief vs neutral.
- [ ] Save/load restores memories and opinion text exactly.
- [ ] `WorldState` includes summarized relationship per NPC for ML trajectories.
- [ ] Tests: `tests/test_npc_memory.py` — fact append, opinion strings, dialogue routing.

### Depends on

Phase 0 (unified relationship model, persistence, event recording).

---

## 🧠 2. Give every NPC an actual brain

### Player experience

Press **G** → Living City panel shows for *any* nearby NPC:

```
PEDESTRIAN #12 — "Jordan"
Personality: curious 0.8 · kind 0.6 · risk 0.3
Needs:  hunger ▓▓▓░░  energy ▓▓░░░  social ▓▓▓▓░  money ▓▓░░░
Goal:    "Get coffee before work"
Plan:    walk → cafe → wait → workplace
```

NPCs visibly change routes: hungry NPC walks to cafe; tired NPC sits on bench; social NPC seeks crowded corners.

### System design

**Extend** `NPCMind` → full `AgentMind` for all 48 NPCs (not just Maya/Alex):

```python
@dataclass
class Personality:
    extroversion: float
    curiosity: float
    kindness: float
    risk_tolerance: float
    ambition: float

@dataclass
class Needs:
    hunger: float
    energy: float
    social: float
    money: float

@dataclass
class AgentMind(NPCMind):
    personality: Personality
    needs: Needs
    schedule: WorkSchedule | None
    current_plan: list[PlanStep]
```

**Decision loop** (`simulation/agent.py`):

```
each tick (or every N ticks for distant NPCs):
  1. perceive (location, time, weather, nearby entities)
  2. score candidate actions (utility function)
  3. pick highest utility → update plan
  4. execute next plan step (pathfind via streets.walk_graph)
```

Utility example:

```
U(get_food) = 0.4*hunger + 0.2*(1-energy) + personality.kindness*0.1
U(go_home)  = 0.5*(time > home_hour) + 0.3*energy + 0.2*weather_penalty
```

Replace hard-coded `if game_minutes >= home_hour` in `npc_mind.py` with scored decisions. Keep schedule as *soft bias*, not a script.

**Procedural personality** for generic pedestrians: seeded from `npc_id` for consistency.

### Performance

- Full brain for NPCs within `simulation_m` (300 m).
- Simplified wander for distant NPCs (current behavior).
- LOD in `streaming/lod.py`.

### Acceptance criteria

- [ ] All 48 NPCs have `Personality` + `Needs` in `WorldState`.
- [ ] At least 3 distinct emergent behaviors observable in 10-min session (food-seeking, homeward, shelter-from-rain).
- [ ] Maya/Alex retain quest-specific goals but use same decision framework.
- [ ] Tests: utility scoring, plan selection, need drift.

### Depends on

Pillar 1 (memory informs utility — e.g. avoid player if stolen from).

---

## 🤯 3. Let NPCs create their own quests

### Player experience

Maya approaches you (notification + map marker):

```
📷 A FAVOR FOR MAYA

"I'm short on rent. Alex mentioned a camera in the
 library — could you check if it's still there?"

Reward: friendship +$20 · trust
```

Quest was not hand-written. It was generated from:

```
Maya.needs.money ↑  +  knows(Alex)  +  Alex.inventory(camera)
  →  goal: acquire_camera  →  quest template: fetch_item
```

### System design

**New module:** `nyc_world/simulation/quest_gen.py`

```python
@dataclass
class QuestTemplate:
    id: str
    title_pattern: str
    objective_generators: list[Callable]
    preconditions: Callable[[WorldState, AgentMind], bool]
    reward_fn: Callable
```

**Pipeline:**

1. **Scan** NPCs with urgent needs + social graph.
2. **Match** to template library (fetch, deliver, escort, investigate, talk).
3. **Instantiate** objectives with real entity IDs from world.
4. **Register** with `QuestManager` (extend `game/quests.py`).
5. **Optional narration:** LLM rewrites title/dialogue from structured quest JSON (offline templates if no API key).

**LLM contract (when enabled):**

```json
{
  "quest_id": "maya_fetch_camera_42",
  "giver": "maya",
  "title": "A Favor for Maya",
  "objectives": [{"type": "collect", "target": "camera", "location": "library"}],
  "tone": "anxious, friendly"
}
```

LLM may only *phrase* — not invent targets that don't exist in JSON.

### Acceptance criteria

- [ ] ≥3 quest templates work without LLM.
- [ ] Generated quest completable end-to-end in-game.
- [ ] Failed quests (timeout, theft) update NPC memory (pillar 1).
- [ ] `WorldState.quests` reflects generated quest metadata for ML.
- [ ] Tests: precondition matching, objective binding, no orphan targets.

### Depends on

Pillars 1–2 (needs, relationships, social graph).

---

## 🕵️ 4. Procedural mystery generator

### Player experience

New game → loading screen:

```
THE MIDNIGHT DISAPPEARANCE

Something happened last night at 11:42 PM.
Interview witnesses. Inspect locations. Reconstruct the truth.
```

**Investigation journal** (HUD tab):

```
TIMELINE (discovered)
 11:35  Maya entered Village Cafe
 11:41  Alex left cafe
 11:42  ??? Camera removed from shelf
 11:48  Taxi #7 departed east
 12:03  Maya reported theft
```

Player talks to NPCs → new timeline entries unlock if NPC `willingness_to_talk(trust)` passes. Player inspects locations → physical evidence. Final accusation UI → scored against ground truth.

### System design

**New modules:**
- `simulation/mystery/gen.py` — crime scenario generator
- `simulation/mystery/simulate.py` — run unseen backstory simulation
- `simulation/event_log.py` — append-only canonical timeline

**Generation algorithm:**

1. Pick crime type (theft, disappearance, vandalism).
2. Pick victim, suspect pool, location from real landmarks.
3. **Fast-forward simulate** 6pm–midnight with agent brains (pillar 2) + seeded RNG.
4. Record ground truth in `MysteryCase` (not shown to player).
5. Player-facing clues = noisy subset of `EventLog`.

```python
@dataclass
class EventLogEntry:
    tick: int
    game_time: str
    actor_id: str
    action: str
    location_id: str
    visibility: str   # "public" | "witness_only" | "hidden"
```

**Interview system:** dialogue choices extract facts if player asks right questions and NPC trust sufficient. Lying possible if `personality.risk_tolerance` high.

### Acceptance criteria

- [ ] Each new game produces different culprit + timeline (seeded).
- [ ] Player can solve without dev console; solution matches `MysteryCase.truth`.
- [ ] Event log replayable for debugging (`scripts/replay_mystery.py`).
- [ ] Tests: generation reproducibility (same seed → same truth), clue coverage.

### Depends on

Pillars 1–2, EventLog (Phase 0), landmark/interior IDs.

---

## 🗽 5. Make the city react to real-world data

### Player experience

Banner at top of HUD:

```
🚇 F train delayed 15 min — crowds shifting to buses
🌧️  Rain expected at 5 PM (live forecast)
```

Observable effects:
- More NPCs on sidewalks near subway entrances, fewer boarding.
- Cafe occupancy +15% during delay.
- Umbrellas appear at 5 PM if rain feed says so.

### System design

**New module:** `nyc_world/feeds/`

| Feed | Source | Fallback |
|------|--------|----------|
| Weather | NWS / Open-Meteo | `WorldClock` procedural weather |
| MTA alerts | GTFS-RT / MTA API | none (silent) |
| Events | NYC Open Data / Eventbrite | none |
| Construction | 511NY / OSM changes | static OSM |

```python
@dataclass
class CityFeedState:
    weather: WeatherAlert | None
    transit: list[TransitAlert]
    events: list[CityEvent]
    last_updated: datetime

class FeedManager:
    def poll(self) -> CityFeedState: ...
    def apply_to_sim(self, city: CitySimulation) -> list[Effect]:
```

**Effects** translate alerts → simulation parameters:

```python
TransitDelay(line="F", minutes=15) → {
  subway_boarding_rate: -0.4,
  bus_route_weight: +0.3,
  sidewalk_density_near_station: +0.2,
}
```

Poll every 5–15 min; cache to `data/feeds/`.

### Acceptance criteria

- [ ] Weather feed overrides `WorldClock.weather` when online.
- [ ] MTA delay injects measurable NPC route change (count metric in debug).
- [ ] Offline mode: game runs identically to today.
- [ ] Tests: effect application with mock feed JSON.

### Depends on

Pillar 2 (agents respond to effects), subway scaffold (pillar 6 helps).

---

## 🚇 6. Actually simulate the subway

### Player experience

Approach subway entrance → **E**:

```
ENTER SUBWAY — West 4th St
────────────────────────────
 ●───●───●───●
 W4  14  Union Sq  Astor Pl

[Select destination]
```

Cut to interior train car (simple geometry). Train moves along graph; travel time real-time or skippable. Exit at chosen station → spawn at surface entrance GPS.

NPCs board/alight based on goals (home, work, flee rain).

### System design

**New module:** `nyc_world/city/subway.py`

```python
@dataclass
class Station:
    id: str
    name: str
    lines: list[str]
    entrance_xz: tuple[float, float]
    latlon: tuple[float, float]

@dataclass
class SubwayGraph:
    stations: dict[str, Station]
    edges: list[tuple[str, str, float]]  # travel time sec

class SubwaySimulation:
    trains: list[Train]
    def board(self, npc_or_player, station_id, dest_id): ...
```

**Phase 6a:** 4–6 stations around Washington Square (W4, 14 St, Union Sq, Astor, Canal, City Hall).

**Phase 6b:** NPC pathfinding uses multimodal graph (walk + subway).

**Rendering:** simple tunnel + car interior; map overlay shows line diagram in HUD.

### Acceptance criteria

- [ ] Player travels W4 → Union Sq in <60s gameplay.
- [ ] GPS position updates correctly on exit (pillar geo).
- [ ] ≥10% of commuter NPCs use subway during rain or long distances.
- [ ] Tests: graph connectivity, travel time, position projection round-trip.

### Depends on

Phase 0 geo accuracy, pillar 2 agent planning.

---

## 🏙️ 7. Build a "digital twin" mode

### Player experience

Press **T** → camera rises above neighborhood. HUD switches:

```
🌎 CITY SIMULATION          [⏸] [1×] [10×] [30×]
────────────────────────────────────────────────
NPCs: 48 active   Vehicles: 32   Tick: 18420
Weather: clear · 2:15 PM
```

Click entity → inspect panel (needs, goal, route). Scroll wheel zooms out toward Manhattan mini-map heat view.

### System design

**New module:** `nyc_world/modes/twin.py`

| Control | Action |
|---------|--------|
| T | Toggle game ↔ twin |
| Click | Select entity |
| Space | Pause/unpause |
| 1/2/3 | Time scale |
| H | Heatmap (density, traffic, mood) |

**Rendering:** reuse `render_gl.py` with orthographic/fly camera (`render/camera.py` extend). Entity icons as billboards / colored dots at altitude.

**Simulation continues** while twin mode active; player avatar frozen or AI-controlled optional.

### Acceptance criteria

- [ ] Toggle T without crash; state preserved.
- [ ] 10× speed runs stable for 5 sim-hours.
- [ ] Click NPC shows pillar-2 brain panel.
- [ ] Tests: mode switch, pause, time scale affects `Simulation.advance_world`.

### Depends on

Pillar 2, stable `WorldState`, HUD mode system (`HudState.mode` already has `"exterior"`).

---

## 🧠 8. World-model "what if?" machine

### Player experience

Press **I** (Imagine) in twin or god mode:

```
🔮 WHAT IF...
 ○ It starts raining at 5:00 PM
 ○ F train shuts down at rush hour
 ○ Player never met Maya

[Run prediction — 30 min horizon]
```

Split view:

```
REAL (left)          PREDICTED (right)
2:00 PM  clear       2:00 PM  clear
5:00 PM  clear       5:00 PM  🌧️
5:15 PM  12 in park   5:15 PM  2 in park
5:30 PM  cafe 40%    5:30 PM  cafe 78%
```

### System design

**Extend** `simulation/model/imagination.py` + new UI `modes/imagine.py`.

1. Capture current `WorldState` → `state_t`.
2. Inject hypothetical `Action` or `WorldPatch` (weather, transit, relationship).
3. Roll forward N steps with `simple_model` (upgrade path to larger model).
4. Diff metrics: NPC positions histogram, cafe occupancy, vehicle count, subway ridership.

**Visualization:** twin mode heatmaps overlay predicted vs actual.

### Acceptance criteria

- [ ] Rain what-if shows park occupancy drop in prediction.
- [ ] Side-by-side diff renders in HUD.
- [ ] CLI `imagine_future.py` and in-game use same code path.
- [ ] Tests: patch application, roll_forward determinism with seed.

### Depends on

Pillar 7 (visualization), existing world model, richer `WorldState` encoding.

---

## 👁️ 9. Let the player become the "god"

### Player experience

Press **`** (backtick) or **G+Shift** → God panel:

```
⚡ CITY LABORATORY
Time   [🌅 06:00] [☀️ 12:00] [🌙 00:00]  ───●────
Weather [☀️] [🌧️] [❄️] [🌫️]
Events  [+ Emergency] [+ Festival] [+ Road closure]
Spawn   [NPC] [Vehicle] [Quest]
```

Spawn festival → street crowd +20%, music POI, vendor NPCs. Close road → vehicles reroute, pedestrians detour.

### System design

**New module:** `nyc_world/modes/god.py`

```python
@dataclass
class WorldPatch:
    time_override: ClockState | None
    weather_override: str | None
    active_events: list[CityEvent]
    road_closures: list[str]  # way ids
```

God mode applies patches directly to `CitySimulation` + logs to `EventLog` for replay.

Uses pillar 5 effect system where possible (unify god injections with real feeds).

### Acceptance criteria

- [ ] Time scrub instantly updates sky + NPC schedules.
- [ ] Road closure changes vehicle paths within 30s sim time.
- [ ] Festival spawns measurable crowd increase.
- [ ] Tests: patch apply/remove, closure routing.

### Depends on

Pillars 2, 5, 7; EventLog.

---

## 🧬 10. Let the city evolve

### Player experience

Fast-forward 1 in-game week (twin mode 30×). Return on foot:

- Cafe has a new name on the facade.
- Apartment building shows "FOR RENT."
- Maya mentions new coworker.

**Evolution journal** in menu:

```
WEEK 2
 · Joe's Camera closed (bankruptcy)
 · "Lens & Leaf" opened in same unit
 · Alex and Maya friendship +12
 · Rent in Village +3%
```

### System design

**New module:** `nyc_world/simulation/economy.py`

```python
@dataclass
class Business:
    id: str
    name: str
    location_id: str
    cash: float
    reputation: float
    staff: list[str]  # npc ids

@dataclass
class Residence:
    unit_id: str
    occupants: list[str]
    rent: float
```

**Weekly tick:**
- Businesses: revenue − rent − wages → survive or fail.
- NPCs: salary, pay rent, move if broke.
- Relationships drift from co-location + events.
- Vacancies spawn new procedural businesses.

**Scope control:** start with 10–20 trackable businesses near Washington Square, not all of Manhattan.

### Acceptance criteria

- [ ] 7-day fast-forward produces ≥1 business state change in seed scenario.
- [ ] Changes persist in save file.
- [ ] Visual: facade sign updates (simple texture swap or HUD label).
- [ ] Tests: weekly tick accounting, bankruptcy trigger.

### Depends on

Pillars 1–2, 7 (fast-forward), persistence.

---

## 📸 11. Photo mode

### Player experience

Press **P**:

- UI chrome hidden.
- Free-fly camera (WASD + mouse, no collision).
- Sliders: time of day, weather, FOV, depth of field (fake bokeh via framebuffer if cheap, else FOV + vignette).
- **Enter** saves PNG to `screenshots/YYYY-MM-DD_HHMMSS.png`.

### System design

**New module:** `nyc_world/modes/photo.py`

Reuse `render/camera.py` → `FreeFlyCamera`. Pause simulation optional. Expose `WorldClock` hour override without affecting sim (visual-only) unless user toggles "sync."

Post-FX stack (phase 11b): vignette, letterbox, optional SSAO fake via gradient.

### Acceptance criteria

- [ ] P toggles mode; screenshot writes valid PNG.
- [ ] Time-of-day slider updates sky in real time.
- [ ] Tests: screenshot file created, camera detach/reattach.

### Depends on

Rendering stability; mostly independent — **can ship early** for marketing.

---

## 🧑‍💻 12. Let other developers create NPCs

### Player experience (developer)

```python
from nyc_world.agents import NPC, Personality, Needs, Schedule

alex = NPC(
    id="alex",
    name="Alex",
    personality=Personality(curiosity=0.9, kindness=0.7),
    needs=Needs(money=0.4),
    schedule=Schedule.workplace("nyu_library", hour=9),
    dialogue_pack="alex_default",
)

world.register_npc(alex)
```

Drop `mods/alex_npc.py` in folder → auto-loaded on start.

### System design

**New package:** `nyc_world/agents/` (public API)

| File | Purpose |
|------|---------|
| `api.py` | `NPC`, `Personality`, `Needs`, `Schedule` |
| `registry.py` | `NPCRegistry.register()` |
| `loader.py` | discover `mods/*.py` |
| `dialogue.py` | hook into interaction system |

**Stability contract:** versioned API (`AGENT_API_VERSION = 1`). Document breaking changes in `docs/agents-api.md`.

### Acceptance criteria

- [ ] Example mod NPC spawns and pathfinds without forking core.
- [ ] API docs + `examples/mod_npc.py`.
- [ ] Tests: load mod, interact, serialize to `WorldState`.

### Depends on

Pillar 2 (brain framework must be data-driven first).

---

# Implementation roadmap

## Phase 0 — Foundation (do first)

| Task | Output |
|------|--------|
| Unify relationships | Single `RelationshipStore` used by profile + minds |
| `EventLog` | Append-only `simulation/event_log.py` |
| Persistence | `data/saves/` save/load |
| Extend `WorldState` | memories, personalities, active mystery, feed state |
| Dialogue router | Tag-based, not quest-id-only |

**Exit:** save game, reload, Maya remembers; event log records player actions.

## Phase 1 — Social memory (Pillar 1)

Memory facts, opinion UI, behavioral greetings, tests.

## Phase 2 — Agent brains (Pillar 2)

Utility AI for all NPCs; replace schedule scripts.

## Phase 3 — Story systems (Pillars 3–4)

Quest generator + mystery generator sharing `EventLog`.

## Phase 4 — City systems (Pillars 5–6)

Real-world feeds + subway graph.

## Phase 5 — Lenses (Pillars 7–9, 11)

Twin mode, god mode, photo mode, imagine UI.

## Phase 6 — Long horizon (Pillars 8, 10, 12)

World-model diff viz, economy evolution, mod API.

### Recommended first vertical slice (MVP of the vision)

**"Maya remembers, thinks, and offers a generated favor quest"** — Pillars 1 + 2 + 3 partial in one playable demo:

1. Talk to Maya three times → memory panel populated.
2. Steal coffee → hostile greeting.
3. Her needs spike → she generates a fetch quest tied to a real object.
4. Save/load preserves everything.

Ship that before building subway or economy.

---

# Testing strategy

| Layer | Approach |
|-------|----------|
| Memory / relationships | Unit tests, golden opinion strings |
| Agent utility | Deterministic seeds, action choice snapshots |
| Quest/mystery gen | Property tests: solvable, no dangling ids |
| Feeds | Mock JSON fixtures |
| Subway | Graph + GPS round-trip |
| Modes | Headless mode toggle + state assertions |
| ML imagine | Compare roll_forward metrics thresholds |

Target: **120+ tests** by end of Phase 3.

---

# What "pristine" means for this repo

- No pillar merges without tests.
- No HUD feature without a `WorldState` field.
- No LLM-required paths — offline templates always work.
- Docs updated in `docs/` per pillar (`docs/memory.md`, `docs/agents.md`, …).
- README stays minimal; vision lives here.

---

# Success definition (project-level)

The vision is achieved when a player can:

1. **Be remembered** by nameless and named NPCs across sessions.
2. **Watch** the city think (needs, goals, plans) in twin mode.
3. **Receive** a quest no human wrote.
4. **Solve** a mystery reconstructed from simulation logs.
5. **See** real NYC weather/transit ripple through the streets.
6. **Ride** the subway and emerge at the correct GPS location.
7. **Ask "what if?"** and see prediction vs reality.
8. **Mod** a new NPC in 20 lines of Python.

And a developer can fork the repo and understand the full architecture from this document alone.
