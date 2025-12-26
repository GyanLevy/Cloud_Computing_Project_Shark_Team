import hashlib
import datetime
from firebase_admin import firestore  
from config import get_db
import gamification_rules
from plants_manager import clear_plants_cache

db = get_db()

# ==========================================
# HELPER FUNCTION: SECURITY
# ==========================================

def _hash_password(password):
    """SHA-256 hash of password."""
    password_bytes = password.encode('utf-8')
    hash_object = hashlib.sha256(password_bytes)
    return hash_object.hexdigest()

# ==========================================
# AUTHENTICATION FUNCTIONS
# ==========================================

def logout_user():
    """Clears cached user data on logout."""
    clear_plants_cache()
    return True

def register_user(username, display_name, password, email):
    try:
        # Validation: Ensure fields are not empty 
        if not username or not password or not email or not display_name:
            return False, "Error: All fields are required."

        # Check for spaces in usrename
        if " " in username:
            return False, "Error: Username cannot contain spaces (use 'carmel12' not 'carmel 12')."

        if len(password) < 6:
            return False, "Error: Password must be at least 6 characters long."

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return False, "Error: Please enter a valid email address (e.g., user@example.com)."

        # 1. Check if user already exists
        users_ref = db.collection('users').document(username)
        doc = users_ref.get()
        
        if doc.exists:
            return False, "Error: Username already exists."

        hashed_password = _hash_password(password)
        
        # 2. Create user data object
        new_user = {
            'username': username,      # The technical ID (e.g. 'zohar_l')
            'display_name': display_name, # The real name (e.g. 'Zohar Levy')
            'password': hashed_password,
            'email': email,
            'score': 0,
            'tasks_completed': 0,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        # 3. Save to Firestore
        users_ref.set(new_user)
        return True, "Success: User registered successfully."
        
    except Exception as e:
        return False, f"System Error: {str(e)}"

def login_user(username, password):
    """
    Authenticates a user by comparing password hashes.
    """
    try:
        # Validation: Ensure fields are not empty 
        if not username or not password:
            return False, "Error: Username and Password fields cannot be empty."

        # Step 1: Fetch user from Firestore 
        users_ref = db.collection('users').document(username)
        doc = users_ref.get()

        # Step 2: Check if user exists 
        if not doc.exists:
            return False, "Error: User not found. Please register first."

        # Step 3: Verify Password 
        user_data = doc.to_dict()
        stored_hash = user_data.get('password')
        
        # Security: Hash the input password to compare with the stored hash
        input_hash = _hash_password(password)
        
        if stored_hash == input_hash:
            return True, user_data  # Login Success
        else:
            return False, "Error: Incorrect password."
            
    except Exception as e:
        return False, f"System Error: {str(e)}"

# ==========================================
# GAMIFICATION FUNCTIONS
# ==========================================

def update_user_score(username, points):
    try:
        user_ref = db.collection('users').document(username)
        doc = user_ref.get()
        if doc.exists:
            user_ref.update({
                'score': firestore.Increment(points),
                'tasks_completed': firestore.Increment(1)
            })
            updated_doc = user_ref.get()
            return updated_doc.to_dict().get('score')
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None

def get_leaderboard():
    try:
        users_ref = db.collection('users')
        query = users_ref.order_by('score', direction=firestore.Query.DESCENDING).limit(5)
        results = query.stream()
        
        leaderboard_data = []
        for doc in results:
            data = doc.to_dict()
            leaderboard_data.append({
                'username': data.get('username'),
                'score': data.get('score')
            })
        return leaderboard_data
    except Exception as e:
        print(f"Error: {e}")
        return []

def update_weekly_challenge_progress(username, action_type):
    """
    Updates the user's progress for the current weekly challenge.
    Handles weekly resets logic automatically.
    """
    try:
        user_ref = db.collection('users').document(username)
        doc = user_ref.get()
        
        if not doc.exists:
            return None

        user_data = doc.to_dict()
        
        # 1. Identify the current active challenge
        current_challenge = gamification_rules.get_current_weekly_challenge()
        challenge_id = str(current_challenge['id'])
        target_action = current_challenge['action_type']
        
        # 2. Check if the action is relevant to the current challenge
        if action_type != target_action:
            return {
                "relevant": False,
                "msg": "Action does not match weekly challenge."
            }

        # 3. Get User's challenge state (or initialize it)
        challenge_state = user_data.get('challenge_state', {})
        
        # Check if we need to reset (if the stored challenge ID is old)
        stored_id = challenge_state.get('challenge_id')
        
        if stored_id != challenge_id:
            # New week detected! Reset counters.
            challenge_state = {
                'challenge_id': challenge_id,
                'progress': 0,
                'is_completed': False,
                'last_updated': firestore.SERVER_TIMESTAMP
            }

        # If already completed, return full data structure to prevent KeyErrors
        if challenge_state.get('is_completed'):
             return {
                "relevant": True,
                "completed": True,
                "progress": challenge_state.get('progress', current_challenge['target']), 
                "target": current_challenge['target'],
                "bonus_awarded": 0,
                "msg": "Challenge already completed for this week."
            }

        # 5. Update Progress
        new_progress = challenge_state['progress'] + 1
        challenge_target = current_challenge['target']
        bonus_points = 0
        is_finished = False

        if new_progress >= challenge_target:
            is_finished = True
            bonus_points = current_challenge['reward_points']
            challenge_state['is_completed'] = True
            
            # Grant the Bonus Points!
            update_user_score(username, bonus_points)

        challenge_state['progress'] = new_progress
        
        # 6. Save back to Firestore
        user_ref.update({
            'challenge_state': challenge_state
        })

        return {
            "relevant": True,
            "progress": new_progress,
            "target": challenge_target,
            "completed": is_finished,
            "bonus_awarded": bonus_points
        }

    except Exception as e:
        print(f"Error in challenge update: {e}")
        return None
    
    
def get_user_details(username):
    """
    Fetches user data without requiring a password.
    Used for refreshing the dashboard after an action.
    """
    try:
        users_ref = db.collection('users').document(username)
        doc = users_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error fetching user details: {e}")
        return None