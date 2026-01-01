import threading
import time
from config import get_db
from ui.home_ui import home_screen
import data_manager
import plants_manager

# ==========================================
# BACKGROUND AUTO-FETCHER
# ==========================================

AUTO_FETCH_INTERVAL_SECONDS = 600  # 10 minutes

def _get_all_plant_ids():
    """Returns all plant_id strings from all users."""
    db = get_db()
    plant_ids = []
    
    try:
        # Get all users
        users = db.collection("users").stream()
        for user_doc in users:
            username = user_doc.id
            # Get all plants for this user
            plants = db.collection("users").document(username).collection("plants").stream()
            user_plants = plants_manager.list_plants(username)
            for plant in user_plants:
                pid = plant.get("plant_id")
                if pid:
                    plant_ids.append(pid)
    except Exception as e:
        print(f"[AutoFetch] Error fetching plant IDs: {e}")
    
    return plant_ids


def _auto_fetch_loop():
    """Background loop - syncs IoT data every 10 minutes."""
    print("[AutoFetch] Background scheduler started (10-minute interval)")
    
    while True:
        # Sleep first to allow app to fully initialize
        time.sleep(AUTO_FETCH_INTERVAL_SECONDS)
        
        print("[AutoFetch] Waking up... syncing IoT data for all plants")
        
        try:
            plant_ids = _get_all_plant_ids()
            
            if not plant_ids:
                print("[AutoFetch] No plants found in database")
                continue
            
            print(f"[AutoFetch] Found {len(plant_ids)} plants. Syncing...")
            
            for plant_id in plant_ids:
                try:
                    data_manager.sync_iot_data(plant_id)
                except Exception as e:
                    print(f"[AutoFetch] Error syncing plant {plant_id}: {e}")
            
            print(f"[AutoFetch] Sync complete. Next sync in {AUTO_FETCH_INTERVAL_SECONDS // 60} minutes.")
            
        except Exception as e:
            print(f"[AutoFetch] Error in sync cycle: {e}")


def start_background_scheduler():
    """Starts daemon thread for auto-fetching."""
    thread = threading.Thread(target=_auto_fetch_loop, daemon=True)
    thread.start()
    print("[AutoFetch] Background thread initialized")
    return thread


# ==========================================
# MAIN APPLICATION
# ==========================================

def main():
    print("--- SHARK TEAM CLOUD SYSTEM - GUI MODE ---")
    
    # 1. Initialize Infrastructure
    try:
        db = get_db()
        print("[OK] Database Connected")
        
        # 2. Setup/Seed Data (Critical for RAG/Search)
        try:
            data_manager.seed_database_with_articles()
            print("[OK] Knowledge Base Ready")
        except Exception as seed_err:
            print(f"[WARNING] Knowledge Base seeding failed (likely quota/rate limit): {seed_err}")
            print("[SYSTEM] Continuing launch... RAG search might use existing index.")


    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        return

    # 3. Start Background Auto-Fetcher
    start_background_scheduler()

    # 4. Launch the Graphical Interface
    print("[SYSTEM] Launching User Interface...")
    app = home_screen()
    app.launch()

if __name__ == "__main__":
    main()