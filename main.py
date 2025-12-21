
import config
import data_manager
from ui.home_ui import home_screen

def main():
    print("--- SHARK TEAM CLOUD SYSTEM - GUI MODE ---")
    
    # 1. Initialize Infrastructure
    try:
        db = config.get_db()
        print("[OK] Database Connected")
        
        # 2. Setup/Seed Data (if needed)
        try:
            data_manager.seed_database_with_articles()
            print("[OK] Knowledge Base Ready")
        except Exception as seed_err:
            print(f"[WARNING] Knowledge Base seeding failed (likely quota/rate limit): {seed_err}")
            print("[SYSTEM] Continuing launch... RAG search might use existing index.")


    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        return

    # 3. Launch the Graphical Interface
    print("[SYSTEM] Launching User Interface...")
    app = home_screen()
    app.launch()

if __name__ == "__main__":
    main()