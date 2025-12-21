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

from config import get_db


def _utc_now_iso() -> str:
    """Return current UTC time as ISO string."""
    return datetime.now(timezone.utc).isoformat()


def _clean(s: Any) -> str:
    """Convert input to a trimmed string safely."""
    return str(s).strip() if s is not None else ""


def add_plant(
    username: str,
    name: str,
    species: str = "",
    image_url: str = "",
    image_path: str = "",
) -> tuple[bool, str]:
    """
    Create a new plant document for a user.

    Args:
        username: Owner username (from user_state)
        name: Display name (required)
        species: Optional
        image_url: Public URL (preferred, e.g., Firebase Storage)
        image_path: Local path fallback (optional)

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

    plant_id = uuid.uuid4().hex[:8]
    doc = {
        "plant_id": plant_id,
        "name": name,
        "species": species,
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
