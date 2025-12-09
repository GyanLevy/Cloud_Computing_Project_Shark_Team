import firebase_admin
from firebase_admin import credentials, firestore
import hashlib

# ==========================================
# FIREBASE INITIALIZATION
# ==========================================

def init_firebase():
    if not firebase_admin._apps:
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
        print("[System] Firebase connected successfully.")
    return firestore.client()

db = init_firebase()

# ==========================================
# HELPER FUNCTION: SECURITY
# ==========================================

def _hash_password(password):
    """
    Converts a plain text password into a secure hash (SHA-256).
    Example: "123456" -> "8d969eef6ecad3c29a3a629280e686cf..."
    """
    # 1. Encode the string to bytes
    password_bytes = password.encode('utf-8')
    # 2. Use SHA-256 hashing algorithm
    hash_object = hashlib.sha256(password_bytes)
    # 3. Return the hexadecimal representation
    return hash_object.hexdigest()

# ==========================================
# AUTHENTICATION FUNCTIONS
# ==========================================

def register_user(username, display_name, password, email):
    """
    Registers a new user in Firestore.
    
    Args:
        username (str): Unique ID (No spaces allowed!).
        display_name (str): Full name (e.g., "Zohar Levy").
        password (str): User password.
        email (str): User email.
    """
    try:
       
        # Validation: Ensure fields are not empty 
        if not username or not password or not email or not display_name:
            return False, "Error: All fields are required."

        # Check for spaces in usrename
        if " " in username:
            return False, "Error: Username cannot contain spaces (use 'carmel12' not 'carmel 12')."

        if len(password) < 6:
            return False, "Error: Password must be at least 6 characters long."

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
    Includes input validation to save API calls.
    
    Returns:
        tuple: (bool, dict/str) -> (Success Status, User Data or Error Message)
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