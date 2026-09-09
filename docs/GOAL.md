# Roadmap

NYC Tiny World is a small, walkable, GPS-grounded city demo. The public build
should make one idea clear quickly: this is not just a renderer, it is a place
where NPCs remember, move, ask for help, and react to the same simulation state.

## Current State

- Real OpenStreetMap streets, sidewalks, parks, landmarks, and building
  footprints around Washington Square / Greenwich Village.
- Third-person 3D play with streaming LOD, minimaps, traffic, NPCs, interiors,
  photo mode, and a day/night sky.
- NYC-style building facades: varied brick, brownstone, limestone, glass,
  per-story windows, facade photo textures, and simple grounding shadows.
- A first-run opening beat: the player spawns facing Maya as she asks for help
  finding her stolen camera.
- Persistent player profile, inventory, money, XP, relationships, memories,
  quests, mystery state, and economy state.
- Simulation snapshots through `WorldState`, trajectory recording, and small
  what-if prediction tools.
- Utility-style NPC behavior, quest NPC minds, subway travel, optional live
  feeds, digital twin mode, god mode, economy events, and a mod NPC API.

## Public Demo Goal

The portfolio path is:

1. Launch with `pip install -r requirements.txt && python3 scripts/play_3d.py`.
2. See Maya immediately and understand the camera quest.
3. Walk through a recognizable Village street with varied buildings and NPCs.
4. Visit the cafe / Alex / library loop.
5. Show that the city remembers actions and can be inspected through debug,
   twin, photo, or what-if modes.

The README should stay focused on this path. Detailed system notes live in the
individual docs.

## Next Best Work

- Record and link a 30-second walkthrough from Maya to the cafe.
- Improve renderer performance beyond the current immediate-mode OpenGL path.
- Add richer landmark silhouettes for the cafe, library, and subway entrances.
- Expand memory and utility AI beyond Maya/Alex so more pedestrians feel
  individually motivated.
- Add more facade attribution detail where Commons author/license metadata is
  worth preserving locally.

## Non-Goals For This Repo

- A full NYC-scale renderer.
- A generic habit tracker, dashboard, or productivity app.
- Online-only infrastructure.
- LLM-generated gameplay as a requirement for the core demo.
