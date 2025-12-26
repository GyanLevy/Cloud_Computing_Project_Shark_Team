import os
import sys
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ==========================================
# PART 1: ENVIRONMENT & PATH CONFIGURATION
# ==========================================

IN_COLAB = 'google.colab' in sys.modules

if IN_COLAB:
    # Specific path for Colab environment
    PROJECT_ROOT = "/content/Cloud_Computing_Project_Shark_Team"
else:
    # Local path (dynamic based on file location)
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# Check for environment variable first, then fall back to default
KEY_FILENAME = "serviceAccountKey.json"
DEFAULT_CRED_PATH = os.path.join(PROJECT_ROOT, KEY_FILENAME)

# Priority: ENV variable > Default path > Current directory
FIREBASE_CRED_PATH = os.getenv("FIREBASE_CREDENTIALS_PATH", DEFAULT_CRED_PATH)

# Validate key existence
if not os.path.exists(FIREBASE_CRED_PATH):
    # Fallback: check current directory if configured path fails
    if os.path.exists(KEY_FILENAME):
        FIREBASE_CRED_PATH = KEY_FILENAME
    else:
        print(f"Warning: Firebase key not found at {FIREBASE_CRED_PATH}")

# ==========================================
# PART 2: DATABASE INITIALIZATION (SINGLETON)
# ==========================================

import json

# Global variable to hold the DB instance
_DB_CLIENT = None

def get_db():
    """Returns singleton Firestore client. Initializes Firebase if needed."""
    global _DB_CLIENT
    
    # Return existing instance if available
    if _DB_CLIENT is not None:
        return _DB_CLIENT

    # Check if Firebase is already initialized internally
    if not firebase_admin._apps:
        try:
            # 1. Read the JSON key to get project_id (for storageBucket)
            bucket_name = None
            if os.path.exists(FIREBASE_CRED_PATH):
                with open(FIREBASE_CRED_PATH, "r") as f:
                    key_data = json.load(f)
                    pid = key_data.get("project_id")
                    if pid:
                        # Newer Firebase projects use .firebasestorage.app
                        bucket_name = f"{pid}.firebasestorage.app"
            
            # 2. Initialize App with Storage Bucket
            cred = credentials.Certificate(FIREBASE_CRED_PATH)
            options = {"storageBucket": bucket_name} if bucket_name else None
            
            firebase_admin.initialize_app(cred, options=options)
            
            print(f"[System] Firebase initialized using {FIREBASE_CRED_PATH}")
            if bucket_name:
                print(f"[System] Cloud Storage Bucket: {bucket_name}")
                
        except Exception as e:
            print(f"[Critical Error] Failed to init Firebase: {e}")
            raise e
    
    _DB_CLIENT = firestore.client()
    return _DB_CLIENT