"""NPC and world dialogue lines keyed by tag."""

DIALOGUE: dict[str, list[str]] = {
    "maya_intro": [
        "Maya: Hey! Someone stole my camera near the park.",
        "Maya: I need it back before my photo show tonight.",
        "Maya: Can you help me find it?",
    ],
    "maya_quest_accepted": [
        "Maya: Thank you! Start at the cafe on MacDougal.",
        "Maya: Someone there might have seen something.",
    ],
    "maya_no_camera": [
        "Maya: Any luck? Check the cafe, then follow the clues.",
    ],
    "maya_quest_complete": [
        "Maya: You found it! You're a lifesaver!",
        "Maya: Here's a coffee token for your trouble. ☕",
        "🎉 QUEST COMPLETE: The Missing Camera",
    ],
    "maya_friendly": [
        "Maya: Thanks again for finding my camera!",
        "Maya: I owe you one — seriously.",
    ],
    "maya_hoping_you_come_by": [
        "Maya: Hey! I was hoping you'd come by.",
        "Maya: Good to see a friendly face around here.",
    ],
    "maya_hostile": [
        "Maya: Don't touch that.",
        "Maya: I remember what you did. Keep your distance.",
    ],
    "maya_returning": [
        "Maya: Oh, hi again.",
    ],
    "maya_new_coworker": [
        "Maya: Have you met Jordan? They just opened Lens & Leaf where Joe's Camera was.",
        "Maya: Small world — we might grab coffee there after my shift.",
    ],
    "maya_favor_intro": [
        "Maya: I'm short on rent this week…",
        "Maya: Alex mentioned something at the library — could you check?",
        "Maya: I'd owe you big time.",
    ],
    "maya_favor_complete": [
        "Maya: You actually found Alex's note! Thank you.",
        "Maya: Maybe things will be okay after all.",
        "🎉 QUEST COMPLETE: A Favor for Maya",
    ],
    "npc_hostile_generic": [
        "They eye you suspiciously and step back.",
    ],
    "found_alex_note": [
        "You find a folded note from Alex tucked behind a shelf.",
        "It mentions helping Maya with rent — and a camera at the library.",
    ],
    "alex_delivery_intro": [
        "Alex: Maya's been stressed. Could you grab coffee from the cafe?",
        "Alex: She'd really appreciate it.",
    ],
    "alex_delivery_complete": [
        "Maya: You brought coffee! Alex told me you'd come.",
        "🎉 QUEST COMPLETE: Coffee for Maya",
    ],
    "investigate_intro": [
        "They heard strange noises at the library last night.",
        "Could you take a look inside?",
    ],
    "investigate_complete": [
        "You found scratch marks near the reading room shelf.",
        "🎉 QUEST COMPLETE: Strange Noises at the Library",
    ],
    "found_coffee_bag": [
        "You pick up a fresh bag of coffee beans from the counter.",
    ],
    "found_library_clue": [
        "Scratch marks on the shelf — someone was here recently.",
    ],
    "cafe_clue": [
        "Barista: Alex was here this morning, looked worried.",
        "Barista: Said something about the old library on 6th Avenue.",
    ],
    "alex_clue": [
        "Alex: I saw a camera near the library reading room.",
        "Alex: I didn't take it — honest! Check inside.",
    ],
    "alex_default": [
        "Alex: I'm late for class. Good luck finding that camera!",
    ],
    "found_camera": [
        "You pick up Maya's camera. It's still working!",
    ],
    "subway_ride": [
        "The train rattles through the tunnel...",
    ],
    "subway_no_card": [
        "The turnstile won't budge. You need a MetroCard.",
    ],
    "subway_arrive": [
        "Doors open. You step onto the platform.",
    ],
}
