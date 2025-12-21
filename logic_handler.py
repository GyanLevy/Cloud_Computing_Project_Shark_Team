
import config
import auth_service
import gamification_rules
import data_manager

def handle_gamified_action(username, action_key, plant_id=None):
    """
    Executes a gamified action, updates scores, triggers IoT/sync if needed,
    and returns a summary string of what happened.
    """
    messages = []
    
    # 1. Score Update
    points = gamification_rules.get_points_for_action(action_key)
    if points > 0:
        new_score = auth_service.update_user_score(username, points)
        messages.append(f"Action recorded! You earned {points} points. New Score: {new_score}")
    
    # 2. IoT Sync for physical actions
    physical_actions = ["WATER_PLANT", "FERTILIZE_PLANT"]
    if action_key in physical_actions and plant_id:
        # Trigger IoT sync
        success = data_manager.sync_iot_data(plant_id)
        if success:
            messages.append("Plant environment updated with REAL data (IoT Synced).")
        else:
            messages.append("Failed to fetch real data (IoT Sync failed).")
            
    # 3. Weekly Challenge Update
    status = auth_service.update_weekly_challenge_progress(username, action_key)
    if status and status.get('relevant'):
        progress_str = f"Challenge Progress: {status['progress']}/{status['target']}"
        messages.append(progress_str)
        
        if status.get('completed'):
            bonus = status['bonus_awarded']
            if bonus > 0:
                messages.append(f"CHALLENGE COMPLETED! Bonus {bonus} points awarded!")
            else:
                messages.append("Challenge already completed previously.")
                
    return "\n".join(messages)
