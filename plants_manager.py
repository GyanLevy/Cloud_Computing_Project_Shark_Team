"""
plants_manager.py

Plants belong to a specific user.

Firestore data model:
  users/{username}/plants/{plant_id}

Each plant document can store:
- name (display name)
- species (optional)
- image_url (recommended when using cloud storage)
- image_path (optional local fallback)
"""

from __future__ import annotations

from datetime import datetime, timezone
import uuid
from typing import Any
import os
import re
import time

# --- New Imports for AI ---
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from config import get_db


# ==========================================
# CACHING LAYER (TTL-based)
# ==========================================

_plants_cache: dict[str, tuple[list, float]] = {}  # {username: (plants_list, timestamp)}
_CACHE_TTL_SECONDS = 60  # Cache expires after 60 seconds


def clear_plants_cache(username: str = None):
    """
    Clear the plants cache.
    If username is provided, clears only that user's cache.
    If None, clears entire cache.
    """
    global _plants_cache
    if username:
        _plants_cache.pop(username, None)
    else:
        _plants_cache.clear()


def _utc_now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _clean(s: Any) -> str:
    """Convert input to a trimmed string safely."""
    return str(s).strip() if s is not None else ""

def get_optimal_soil(species_name: str) -> int:
    """
    Consults Gemini AI to determine the optimal minimum soil moisture percentage.
    
    Args:
        species_name: The type of plant (e.g., 'Basil', 'Cactus').
        
    Returns:
        int: The minimum soil threshold (0-100). Defaults to 30 if AI fails.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    
    # Safety check: If no API key is found, return default immediately
    if not api_key:
        print("[AI Warning] No GOOGLE_API_KEY found in .env. Using default 30%.")
        return 30

   # List of models to try in order (Fallback mechanism)
    models_to_try = [
        'gemini-2.0-flash',       # First priority
        'gemini-2.5-flash',       # Second priority
        'gemini-flash-latest',    # Fallback generic name
        'models/gemini-2.0-flash' # Explicit path just in case
    ]
    
    genai.configure(api_key=api_key)

    # Clean the input
    species_name = species_name.strip()

    prompt = f"""
    You are an expert agronomist. 
    I am growing a plant of type: "{species_name}".
    What is the critical minimum soil moisture percentage (0-100%) this plant needs to survive before it starts wilting?
    Note: I am measuring soil moisture, NOT air humidity.
    Return ONLY the number (integer). No text.
    Example response: 30
    """
    # This loop was causing the indentation error - now fixed:
    for model_name in models_to_try:
        try:
            print(f"[AI Agent] Connecting to model: {model_name} for '{species_name}'...")
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            numbers = re.findall(r'\d+', text)
            if numbers:
                val = int(numbers[0])
                if 5 <= val <= 90:
                    return val
            
        except Exception as e:
            print(f"[AI Log] Model {model_name} failed: {e}")
            continue

    print("[AI Error] All models failed. Using fallback 30%.")
    return 30

def add_plant(
    username: str,
    name: str,
    species: str = "",
    image_url: str = "",
    image_path: str = "",
) -> tuple[bool, str]:
    """
    Create a new plant document for a user.
    Now includes AI-powered humidity threshold detection.

    Args:
        username: Owner username (from user_state)
        name: Display name (required)
        species: Optional (used for AI detection)
        image_url: Public URL
        image_path: Local path fallback

    Returns:
        (ok, plant_id_or_error)
    """
    username = _clean(username)
    name = _clean(name)
    species = _clean(species)
    image_url = _clean(image_url)
    image_path = _clean(image_path)

    if not username:
        return False, "Missing username (please login)."
    if not name:
        return False, "Plant name is required."

    # --- AI Integration Start ---
    # Determine minimum humidity based on species
    optimal_min = 30 # Default value

    # Logic: If species is provided, use it. Otherwise, try to infer from the name.
    ai_search_term = species if species else name

    if ai_search_term:
        # Call the helper function to get the SOIL threshold
        optimal_min = get_optimal_soil(ai_search_term)
        print(f"[Success] AI set soil threshold for '{name}' to {optimal_min}% (Term: '{ai_search_term}')")
    # --- AI Integration End ---

    plant_id = uuid.uuid4().hex[:8]
    doc = {
        "plant_id": plant_id,
        "name": name,
        "species": species,
        "min_soil": optimal_min, # <--- Storing the AI result in DB
        "image_url": image_url,
        "image_path": image_path,
        "created_at": _utc_now_iso(),
    }

    db = get_db()
    try:
        db.collection("users").document(username).collection("plants").document(plant_id).set(doc)
        return True, plant_id
    except Exception as e:
        return False, f"Failed to add plant: {e}"


import json
import os
import google.generativeai as genai

import json
import os
import re
import google.generativeai as genai

def get_vacation_advice_ai(plant_name, current_soil, min_threshold, current_temp, days_away):
    """
    Uses Gemini AI to analyze vacation risk based on real-time temperature and plant type.
    Includes a fallback mechanism to try multiple models if one fails.

    Args:
        plant_name (str): The species or name of the plant.
        current_soil (float): Current soil moisture percentage from sensors.
        min_threshold (int): The minimum soil moisture required for survival.
        current_temp (float): Real-time temperature from sensors.
        days_away (int): Duration of the vacation in days.

    Returns:
        dict: A dictionary with status, message, and recommendation, or None if all models fail.
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("[System] Missing API Key.")
        return None

    genai.configure(api_key=api_key)

    # List of models to try in order (Fallback mechanism), same as in get_optimal_soil
    models_to_try = [
        'gemini-2.0-flash',       # First priority
        'gemini-2.5-flash',       # Second priority
        'gemini-flash-latest',    # Fallback generic name
        'models/gemini-2.0-flash' # Explicit path just in case
    ]

    # Construct the prompt
    prompt = f"""
    You are an expert botanist.
    I am going on vacation for {days_away} days.
    
    Plant Details:
    - Type: {plant_name}
    - Current Soil Moisture: {current_soil}%
    - Minimum Survival Threshold: {min_threshold}%
    
    Environment Conditions (Real-time Sensor):
    - Indoor Temperature: {current_temp}°C
    
    Task:
    1. Analyze if the temperature indicates fast evaporation (Summer/Hot) or slow (Winter/Cold).
    2. Estimate the daily soil moisture loss % for this specific plant at this temperature.
    3. Determine if the plant will survive without intervention.
    4. Recommend action: "Water heavily now" OR "Must install automatic irrigation system".
    
    Return ONLY a valid JSON object in this format:
    {{
        "status": "SAFE" or "NEEDS WATER" or "CRITICAL",
        "message": "Short explanation mentioning temp effect (e.g., 'High heat (30C) increases drying rate')",
        "recommendation": "The specific action to take"
    }}
    """

    # Retry Loop: Try each model until one succeeds
    for model_name in models_to_try:
        try:
            print(f"[AI Agent] Connecting to model: {model_name} for vacation advice...")
            model = genai.GenerativeModel(model_name)
            
            response = model.generate_content(prompt)
            text = response.text.strip()
            
            # Clean up Markdown formatting if present (```json ... ```)
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()
            
            # Try to parse JSON
            result = json.loads(text)
            
            # If successful, return the result immediately
            return result

        except Exception as e:
            print(f"[AI Log] Model {model_name} failed: {e}")
            # Continue to the next model in the list
            continue

    print("[AI Error] All models failed. Returning None (fallback to math logic).")
    return None

def list_plants(username: str) -> list[dict]:
    """
    List all plants for the given user.

    Returns:
        List of dicts: [{plant_id, name, species, image_url, image_path, created_at}, ...]
    """
    username = _clean(username)
    if not username:
        return []

    db = get_db()
    ref = db.collection("users").document(username).collection("plants")

    try:
        snap = ref.order_by("created_at").stream()
    except Exception:
        snap = ref.stream()

    return [d.to_dict() for d in snap]


def delete_plant(username: str, plant_id: str) -> tuple[bool, str]:
    """
    Delete a plant document for the user.

    Args:
        username: Owner username
        plant_id: Plant id

    Returns:
        (ok, message)
    """
    username = _clean(username)
    plant_id = _clean(plant_id)

    if not username:
        return False, "Missing username (please login)."
    if not plant_id:
        return False, "Missing plant_id."

    db = get_db()
    try:
        db.collection("users").document(username).collection("plants").document(plant_id).delete()
        return True, "Deleted."
    except Exception as e:
        return False, f"Failed to delete plant: {e}"


def count_plants(username: str) -> int:
    """
    Count how many plants a user has.
    Uses aggregation count() if available, otherwise streams and counts.
    """
    username = _clean(username)
    if not username:
        return 0

    db = get_db()
    ref = db.collection("users").document(username).collection("plants")

    try:
        agg = ref.count().get()
        return int(agg[0].value)
    except Exception:
        return sum(1 for _ in ref.stream())


import io
from firebase_admin import storage

def add_plant_with_image(
    username: str,
    name: str,
    species: str = "",
    pil_image=None,
) -> tuple[bool, str]:
    """
    Create a new plant AND upload the image to Firebase Storage.
    No local files are saved.
    
    Path: user_uploads/{username}/{timestamp}_{uuid}.png
    """
    username = _clean(username)
    name = _clean(name)
    species = _clean(species)

    if not username:
        return False, "Missing username (please login)."
    if not name:
        return False, "Plant name is required."
    if pil_image is None:
        return False, "Missing image."

    try:
        # 1. Convert PIL image to bytes
        img_byte_arr = io.BytesIO()
        pil_image.save(img_byte_arr, format='PNG')
        img_bytes = img_byte_arr.getvalue()
        
        # 2. Prepare Cloud Storage Path
        # Naming: user_uploads/alice/20231220-123045_a1b2c3d4.png
        ts_str = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        blob_path = f"user_uploads/{username}/{ts_str}_{unique_id}.png"
        
        # 3. Upload to Firebase Storage
        bucket = storage.bucket() # Uses the bucket configured in config.py
        blob = bucket.blob(blob_path)
        
        print(f"[Storage] Uploading to {blob_path}...")
        blob.upload_from_string(img_bytes, content_type="image/png")
        
        # 4. Make Public and Get URL
        blob.make_public()
        public_url = blob.public_url
        print(f"[Storage] Success! URL: {public_url}")

    except Exception as e:
        print(f"[Error] Storage upload failed: {e}")
        return False, f"Failed to upload image: {e}"

    # 5. Save metadata to Firestore (using existing add_plant)
    return add_plant(
        username=username,
        name=name,
        species=species,
        image_path="",      # No local path
        image_url=public_url,
    )
