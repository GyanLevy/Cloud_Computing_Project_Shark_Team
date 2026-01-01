import hashlib
import datetime
import re
from firebase_admin import firestore  
from config import get_db
import gamification_rules
from plants_manager import clear_plants_cache

db = get_db()

# ==========================================
# HELPER: WEEKLY RESET LOGIC
# ==========================================
def _check_and_reset_weekly_score(user_ref, user_data):
    """Checks if it's a new week. If so, resets 'weekly_score'."""
    try:
        current_week = datetime.date.today().isocalendar()[1]
        saved_week = user_data.get('last_week_number', 0)
        
        if current_week != saved_week:
            user_ref.update({
                'weekly_score': 0,
                'last_week_number': current_week,
                'maintenance_log': {} 
            })
    except Exception as e:
        print(f"Reset Check Error: {e}")

# ==========================================
# SECURITY
# ==========================================
def _hash_password(password):
    password_bytes = password.encode('utf-8')
    hash_object = hashlib.sha256(password_bytes)
    return hash_object.hexdigest()

# ==========================================
# AUTH
# ==========================================
def logout_user():
    clear_plants_cache()
    return True

def register_user(username, display_name, password, email):
    try:
        if not username or not password or not email or not display_name:
            return False, "Error: All fields are required."
        if " " in username:
            return False, "Error: Username cannot contain spaces."
        if len(password) < 6:
            return False, "Error: Password must be at least 6 characters."
        
        # Email check
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False, "Error: Invalid email address."

        users_ref = db.collection('users').document(username)
        if users_ref.get().exists:
            return False, "Error: Username already exists."

        new_user = {
            'username': username,
            'display_name': display_name,
            'password': _hash_password(password),
            'email': email,
            'score': 0,
            'weekly_score': 0,
            'tasks_completed': 0,
            'last_week_number': datetime.date.today().isocalendar()[1],
            'maintenance_log': {},
            'created_at': firestore.SERVER_TIMESTAMP
        }
        users_ref.set(new_user)
        return True, "Success: User registered successfully."
    except Exception as e:
        return False, f"System Error: {str(e)}"

def login_user(username, password):
    try:
        if not username or not password:
            return False, "Error: Fields cannot be empty."

        users_ref = db.collection('users').document(username)
        doc = users_ref.get()

        if not doc.exists:
            return False, "Error: User not found."

        user_data = doc.to_dict()
        if user_data.get('password') == _hash_password(password):
            _check_and_reset_weekly_score(users_ref, user_data)
            return True, user_data
        else:
            return False, "Error: Incorrect password."
    except Exception as e:
        return False, f"System Error: {str(e)}"

# ==========================================
# GAMIFICATION (Score & Leaderboard)
# ==========================================

def update_user_scores(username, action_key, plant_id=None):
    try:
        user_ref = db.collection('users').document(username)
        doc = user_ref.get()
        if not doc.exists: 
            return None, "User not found"
        
        user_data = doc.to_dict()
        _check_and_reset_weekly_score(user_ref, user_data)
        
        today_str = datetime.date.today().isoformat()
        if plant_id:
            action_id = f"{plant_id}_{action_key}"
            log = user_data.get('maintenance_log', {})
            if log.get(action_id) == today_str:
                return None, "Already done today!"

        points = gamification_rules.get_points_for_action(action_key)
        if points == 0: 
            return 0, "No points"

        update_data = {
            'score': firestore.Increment(points),
            'weekly_score': firestore.Increment(points),
            'tasks_completed': firestore.Increment(1)
        }
        if plant_id:
            update_data[f'maintenance_log.{action_id}'] = today_str

        user_ref.update(update_data)
        return points, "Success"
    except Exception as e:
        return None, f"Error: {e}"

def get_weekly_leaderboard():
    try:
        users_ref = db.collection('users')
        query = users_ref.order_by('weekly_score', direction=firestore.Query.DESCENDING).limit(5)
        
        leaderboard = []
        for doc in query.stream():
            d = doc.to_dict()
            leaderboard.append({
                'username': d.get('username', d.get('username')),
                'score': d.get('weekly_score', 0),
                'rank_title': gamification_rules.get_user_rank(d.get('score', 0))
            })
        return leaderboard
    except Exception as e:
        print(f"Error fetching leaderboard: {e}")
        return []

def get_user_details(username):
    try:
        doc = db.collection('users').document(username).get()
        return doc.to_dict() if doc.exists else None
    except Exception:
        return None
    