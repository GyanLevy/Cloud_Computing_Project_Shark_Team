import time
from datetime import datetime

# --- Import Team Modules ---
import config            # Infrastructure & DB Connection
import auth_service      # Carmel: Auth & User Mgmt
import gamification_rules # Carmel: Rules definitions
import data_manager      # Shahed: IoT & RAG Logic

# Note: Since we don't have the final UI file yet, 
# I implemented a simple CLI (Command Line Interface) here 
# to test the logic of the entire system.

def print_header(text):
    print("\n" + "="*50)
    print(f"   {text}")
    print("="*50)

def handle_gamified_action(username, action_key, plant_id=None):
    # 1. חישוב ועדכון ניקוד (רק אם יש נקודות)
    points = gamification_rules.get_points_for_action(action_key)
    if points > 0:
        new_score = auth_service.update_user_score(username, points)
        print(f"\n[SUCCESS] Action recorded! You earned {points} points.")
        print(f"[SCORE] New Total Score: {new_score}")
    # יצרנו רשימה של פעולות "פיזיות" שצריכות לרענן את החיישנים
    physical_actions = ["WATER_PLANT", "FERTILIZE_PLANT"]
    
    # הבדיקה החדשה: האם הפעולה הנוכחית נמצאת בתוך הרשימה?
    if action_key in physical_actions and plant_id:
        print(f"\n[SYSTEM] Action '{action_key}' detected. Triggering IoT Device...")
        
        success = data_manager.sync_iot_data(plant_id)
        
        if success:
            print("[IOT] Plant environment updated with REAL data.")
        else:
            print("[IOT] Failed to fetch real data, check internet connection.")
    
    # 3. עדכון אתגר שבועי
    status = auth_service.update_weekly_challenge_progress(username, action_key)
    if status and status.get('relevant'):
        print(f"[CHALLENGE] Progress: {status['progress']}/{status['target']}")
        if status.get('completed'):
            bonus = status['bonus_awarded']
            if bonus > 0:
                print(f"[CHALLENGE] COMPLETED! Bonus {bonus} points awarded!")
            else:
                print(f"[CHALLENGE] COMPLETED! Bonus 0 points awarded! (already completed this weekly challenge)")

def show_dashboard(user_data):
    username = user_data['username']
    while True:
        # Refresh user data to show updated score
        refreshed_data = auth_service.get_user_details(username)
        if refreshed_data:
            user_data = refreshed_data
            
        print_header(f"DASHBOARD | User: {user_data['display_name']} | Score: {user_data.get('score', 0)}")
        
        latest = data_manager.get_latest_reading("plant_001")
        challenge = gamification_rules.get_current_weekly_challenge()
        
        # Safe handling if no sensor data exists yet
        temp = latest.get('temp') if latest else 'N/A'
        humidity = latest.get('humidity') if latest else 'N/A'
        
        print(f"Plant Status (plant_001):")
        print(f"   Temp: {temp}C | Humidity: {humidity}%")

        print(f"\nWeekly Challenge: {challenge['title']}")
        print(f"   Goal: {challenge['description']}")
        
        print("\nOPTIONS:")
        print("1. Water Plant")
        print("2. Fertilize Plant")       
        print("3. Upload Plant Photo")
        print("4. Ask AI Expert (RAG)")
        print("5. Leaderboard")
        print("6. Sync IoT Data (Manual)") 
        print("7. Logout")
        
        choice = input("\nSelect: ")
        
        if choice == "1":
            handle_gamified_action(username, "WATER_PLANT", "plant_001")
            # No need to re-login here, the loop will refresh data at the top
        elif choice == "2": # <-- חדש!
            handle_gamified_action(username, "FERTILIZE_PLANT", "plant_001")    
        elif choice == "3":
            handle_gamified_action(username, "UPLOAD_PHOTO")
            
        elif choice == "4":
            q = input("Question: ")
            res = data_manager.rag_search(q, top_k=2)
            print("\n--- AI SEARCH RESULTS ---")
            for r in res: 
                print(f"* {r['title']}\n  Snippet: {r['snippet']}\n")
            if res: 
                handle_gamified_action(username, "USE_SEARCH")
            input("Press Enter to continue...") # Pause to let user read
            
        elif choice == "5":
            print("\n--- LEADERBOARD ---")
            for i, p in enumerate(auth_service.get_leaderboard()):
                print(f"{i+1}. {p['username']} - {p['score']}")
            input("Press Enter to continue...")
        elif choice == "6":
            data_manager.sync_iot_data("plant_001")
            input("Press Enter to continue...")    
        elif choice == "7": 
            break
        else: 
            print("Invalid selection.")

def run_system():
    print_header("SHARK TEAM CLOUD SYSTEM - INITIALIZING")
    try:
        db = config.get_db()
        print("[OK] Database Connected")
        # Setup data
        data_manager.seed_database_with_articles()
    except Exception as e:
        print(f"[ERROR] Critical Error: {e}")
        return

    while True:
        print("\n1. Login\n2. Register\n3. Exit System")
        choice = input("Choose: ")
        
        if choice == "1":
            u = input("Username: ").strip()
            p = input("Password: ").strip()
            success, result = auth_service.login_user(u, p)
            
            if success:
                # --- NEW: Challenge Selection Menu ---
                print("\n--- SELECT CHALLENGE MODE ---")
                print("1. Real Calendar (Auto)")
                print("2. Photo Marathon (Force ID 1)")
                print("3. Garden Expansion (Force ID 2)")
                print("4. The Scholar (Force ID 3)")
                
                mode = input("Select Mode: ")
                if mode == "1":
                    gamification_rules.set_challenge_mode(None)
                    print("Mode set to: Real Calendar")
                elif mode == "2":
                    gamification_rules.set_challenge_mode(1)
                    print("Mode set to: Photo Marathon")
                elif mode == "3":
                    gamification_rules.set_challenge_mode(2)
                    print("Mode set to: Garden Expansion")
                elif mode == "4":
                    gamification_rules.set_challenge_mode(3)
                    print("Mode set to: The Scholar")
                else:
                    print("Invalid selection, defaulting to Calendar.")
                    gamification_rules.set_challenge_mode(None)
                
                # Continue to dashboard
                show_dashboard(result)
            else: 
                print(f"Login Failed: {result}")
                
        elif choice == "2":
            u = input("New Username: ").strip()
            d = input("Display Name: ").strip()
            p = input("Password: ").strip()
            e = input("Email: ").strip()
            
            success, msg = auth_service.register_user(u, d, p, e)
            print(msg)
            
        elif choice == "3":
            break

if __name__ == "__main__":
    run_system()