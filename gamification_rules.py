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
    "USE_SEARCH": {
        "points": 5,
        "description": "Using the RAG Knowledge Base"
    },
    "ADD_PLANT": {
        "points": 25,
        "description": "Adding a new plant to the garden"
    }
}

# ==========================================
# 2. RANKS (TAGS) DEFINITION
# ==========================================
# Based on Total Score (Lifetime)

RANKS = [
    {"name": "Fresh Sprout",      "min_score": 0},    # 0 - 200
    {"name": "Diligent Gardener", "min_score": 201},  # 201 - 500
    {"name": "Growth Expert",     "min_score": 501},  # 501 - 1000
    {"name": "Garden Master",     "min_score": 1001}  # 1001+
]

# ==========================================
# 3. WEEKLY CHALLENGES (LEGACY / OPTIONAL)
# ==========================================
# Kept for future use, currently we focus on the "Garden Race" daily tasks.

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
# 4. HELPER FUNCTIONS
# ==========================================

def get_points_for_action(action_key):
    """
    Returns the points for a specific action.
    """
    if action_key in ACTIONS:
        return ACTIONS[action_key]["points"]
    return 0

def get_user_rank(total_score):
    """
    Calculates the rank based on cumulative total score.
    Iterates through RANKS to find the highest matching tier.
    """
    # Default to the lowest rank
    current_rank = RANKS[0]["name"]
    
    # Check against thresholds
    for rank in RANKS:
        if total_score >= rank["min_score"]:
            current_rank = rank["name"]
            
    return current_rank

# --- Helper for Weekly Challenge (Legacy Support) ---
_FORCED_CHALLENGE_ID = None

def get_current_weekly_challenge():
    """
    Returns the current active challenge.
    Currently defaults to the first one if used.
    """
    if _FORCED_CHALLENGE_ID:
        for c in WEEKLY_CHALLENGES:
            if c['id'] == _FORCED_CHALLENGE_ID: return c
            
    # Simple logic: Just return the first one for now to avoid errors
    return WEEKLY_CHALLENGES[0]