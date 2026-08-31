"""Tests for procedural quest generation."""

from nyc_world.game.profile import PlayerProfile
from nyc_world.game.quests import QuestManager, QuestState
from nyc_world.simulation.agent import AgentBrain, AgentController, AgentNeeds, Personality
from nyc_world.simulation.npc_mind import NPCMindRegistry, create_alex_mind, create_maya_mind
from nyc_world.simulation.quest_gen import QuestGenContext, scan_generated_quests, try_generate_maya_favor


def _make_alex_brain() -> AgentBrain:
    return AgentBrain(
        npc_id="alex",
        display_name="Alex",
        personality=Personality(
            extroversion=0.8,
            curiosity=0.5,
            kindness=0.5,
            risk_tolerance=0.5,
            ambition=0.5,
        ),
        needs=AgentNeeds(social=0.7),
    )


def test_maya_favor_generates_after_camera_quest():
    minds = NPCMindRegistry()
    maya = create_maya_mind()
    maya.needs["money"] = 0.8
    minds.register(maya)
    player = PlayerProfile()
    player.complete_quest("missing_camera")
    ctx = QuestGenContext(game_day=2, tick=100)

    quest = try_generate_maya_favor(
        minds,
        ctx,
        completed_quests=set(player.quests_completed),
        active_quest_id=None,
    )
    assert quest is not None
    assert quest.id == "maya_favor"
    assert quest.title == "A Favor for Maya"


def test_quest_manager_registers_generated_quest():
    minds = NPCMindRegistry()
    minds.register(create_maya_mind())
    player = PlayerProfile()
    player.complete_quest("missing_camera")
    qm = QuestManager(player, minds=minds)
    qm.refresh_generated_quests()
    assert "maya_favor" in qm.quests
    assert qm.quests["maya_favor"].state == QuestState.AVAILABLE


def test_scan_generates_delivery_quest():
    minds = NPCMindRegistry()
    minds.register(create_alex_mind())
    agents = AgentController()
    agents.register(_make_alex_brain())
    player = PlayerProfile()
    player.complete_quest("missing_camera")
    ctx = QuestGenContext(game_day=2, tick=50)
    quests = scan_generated_quests(
        minds,
        agents,
        ctx,
        completed_quests=set(player.quests_completed),
        active_quest_id=None,
        prerequisite_completed=set(player.quests_completed),
    )
    delivery = [q for q in quests if q.id == "alex_delivery"]
    assert delivery
    assert delivery[0].title == "Coffee for Maya"


def test_scan_generates_investigate_quest():
    minds = NPCMindRegistry()
    maya = create_maya_mind()
    minds.register(maya)
    agents = AgentController()
    brain = AgentBrain(
        npc_id="maya",
        display_name="Maya",
        personality=Personality(
            extroversion=0.5,
            curiosity=0.9,
            kindness=0.5,
            risk_tolerance=0.5,
            ambition=0.5,
        ),
        needs=AgentNeeds(),
    )
    agents.register(brain)
    player = PlayerProfile()
    player.complete_quest("missing_camera")
    ctx = QuestGenContext(game_day=3, tick=80)
    quests = scan_generated_quests(
        minds,
        agents,
        ctx,
        completed_quests=set(player.quests_completed),
        active_quest_id=None,
        prerequisite_completed=set(player.quests_completed),
    )
    investigate = [q for q in quests if q.id.endswith("_investigate")]
    assert investigate
    assert "Library" in investigate[0].title

