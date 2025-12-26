"""
GAMIFICATION RULES MODULE
-------------------------
This file defines the points system and weekly challenges.
It serves as the "Rule Book" for the Main Application.

KEY RULES:
1. Points are PER PLANT. If a user waters 5 plants, they get points 5 times.
2. Weekly Challenge Counters must reset every week (Sunday).
3. Total Score NEVER resets.
"""

import datetime

# ==========================================
# 1. POINTS SYSTEM (The "Price List")
# ==========================================
# Simple Logic: Action Performed -> Points Awarded immediately.

ACTIONS = {
    "WATER_PLANT": {
        "points": 10,
        "description": "Watering a single plant"
    },
    "FERTILIZE_PLANT": {
        "points": 10,
        "description": "Fertilizing a single plant"
    },
    "UPLOAD_PHOTO": {
        "points": 20,
        "description": "Scanning a plant with AI"
    },
    "EARLY_DETECTION": {
        "points": 40,
        "description": "System detected an issue early"
    },
    "PREVENTIVE_ACTION": {
        "points": 25,
        "description": "User completed a maintenance task"
    },
    "USE_SEARCH": {
        "points": 0,
        "description": "Using the RAG Knowledge Base"
    },
    "ADD_PLANT": {
        "points": 15,
        "description": "Adding a new plant to the garden"
    }
}

# ==========================================
# 2. WEEKLY CHALLENGES
# ==========================================
# Cycle through these challenges (one per week).

WEEKLY_CHALLENGES = [
    {
        "id": 1,
        "title": "Photo Marathon",
        "description": "Scan 3 different plants to update their status.",
        "action_type": "UPLOAD_PHOTO",
        "target": 3, 
        "reward_points": 150
    },
    {
        "id": 2,
        "title": "Garden Expansion",
        "description": "Add a new plant to your garden collection.",
        "action_type": "ADD_PLANT",
        "target": 1,
        "reward_points": 100
    },
    {
        "id": 3,
        "title": "The Scholar",
        "description": "Use the Smart Search (RAG) to ask a question about plants.",
        "action_type": "USE_SEARCH",
        "target": 1, 
        "reward_points": 50
    }
]

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================

# Global variable to store the forced challenge ID (None = Auto/Calendar Mode)
_FORCED_CHALLENGE_ID = None

def set_challenge_mode(mode_id):
    """
    Sets the challenge mode.
    None = Use Real Calendar.
    1, 2, 3 = Force specific challenge ID.
    """
    global _FORCED_CHALLENGE_ID
    _FORCED_CHALLENGE_ID = mode_id

def get_points_for_action(action_key):
    """
    Returns the points for a specific action.
    """
    if action_key in ACTIONS:
        return ACTIONS[action_key]["points"]
    return 0

def get_current_weekly_challenge():
    # 1. Check if a specific challenge is forced (Manual Mode)
    if _FORCED_CHALLENGE_ID is not None:
        # Find the challenge with the specific ID
        for challenge in WEEKLY_CHALLENGES:
            if challenge['id'] == _FORCED_CHALLENGE_ID:
                return challenge
    
    # 2. If no force (Auto Mode), use the Real Calendar logic
    # Calculate week number (1-52)
    current_week = datetime.date.today().isocalendar()[1]
    
    # Cycle through challenges
    challenge_index = current_week % len(WEEKLY_CHALLENGES)
    return WEEKLY_CHALLENGES[challenge_index]

def get_user_rank(current_score):
    """
    Simple rank calculation based on total score.
    """
    if current_score < 100:
        return "Beginner"
    elif current_score < 500:
        return "Advanced"
    elif current_score < 1000:
        return "Pro"
    else:
        return "Master"

# ==========================================
# TEST BLOCK
# ==========================================
if __name__ == "__main__":
    print("--- GAMIFICATION RULES CHECK ---")
    print(f"Adding Plant Points: {get_points_for_action('ADD_PLANT')}")
    print(f"Current Challenge: {get_current_weekly_challenge()['title']}")
    print("Rules are valid.")