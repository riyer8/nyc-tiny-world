# Gameplay

## Controls

| Action | Keys |
|--------|------|
| Move forward | **W** or **↑** |
| Move backward | **S** or **↓** |
| Strafe left / right | **A** / **D** or **←** / **→** |
| Sprint | **F** (hold) |
| Jump | **Space** |
| Look around | **Click** to unlock, move mouse, **click** again to lock |
| Interact | **E** |
| Toggle geo debug | **G** |
| Record trajectories | `--record` flag |
| Quit | **Esc** |

Controls also appear in the HUD at the bottom of the screen while playing.

**Third-person view:** You see your character on the street — blue jacket, walking animation when you move. The camera sits behind and slightly to the right, looking at your chest (not stuck to your back). Click + mouse to orbit the view.

## Interactions & quests

Walk up to subway entrances, cafes, buildings, NPCs, and objects. When you're close enough, a prompt appears — press **E** to interact.

**Example quest: The Missing Camera**
1. Talk to **Maya** (pink NPC near Washington Square spawn)
2. Visit the **Village Cafe** (nearest cafe landmark)
3. Talk to **Alex** for a clue
4. Enter the **Jefferson Market Library**
5. Find the camera inside
6. Return to Maya

Quest progress shows in the top-left HUD. Dialogue appears at the bottom. A few buildings have simple interiors (cafe, library, photo shop).

## Inventory & progression

Your **player profile** tracks everything that makes exploration meaningful:

| Stat | Starting value |
|------|----------------|
| Money | $37 |
| XP / Level | 0 XP · Level 1 |
| Items | MetroCard |

The profile panel (top-right, below the mini-map) shows level, money, inventory, and relationships.

**Completing "The Missing Camera" rewards:**
- +75 XP
- +$15
- ☕ Coffee + coffee token
- Maya likes you more (+50%)

Items have display names and emojis (`MetroCard`, `Camera`, `Coffee`, `Mysterious Key`). Relationships with NPCs persist — talk to Maya again after the quest and she remembers you helped.

**Testing without the 3D window:**
```bash
pytest tests/test_profile.py tests/test_interactions.py tests/test_quests.py -v
```
