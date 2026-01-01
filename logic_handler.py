import config
import auth_service
import gamification_rules
import data_manager

def handle_gamified_action(username, action_key, plant_id=None):
    """
    Executes a gamified action (Garden Race Logic).
    1. Updates Scores (Total + Weekly) with Daily Limit check.
    2. Triggers IoT Sync if it's a physical action.
    3. Returns a user-friendly status message.
    """
    messages = []
    
    # 1. Attempt to Update Scores (Check limits logic is inside auth_service)
    result = auth_service.update_user_scores(username, action_key, plant_id)
    
    # result is a tuple: (points_awarded, message)
    # If points is None, it means error or limit reached.
    
    if result is None:
        return "⚠️ Error: Could not update score. User not found?"
        
    points, status_msg = result
    
    if points is None:
        # This happens if Daily Limit is reached
        return f"🛑 Limit Reached: {status_msg}"
        
    # If we got here, points were awarded!
    messages.append(f"✅ Action recorded! +{points} points to your Garden Race!")
    
    # 2. IoT Sync for physical actions (Water/Fertilize)
    physical_actions = ["WATER_PLANT", "FERTILIZE_PLANT"]
    if action_key in physical_actions and plant_id:
        success = data_manager.sync_iot_data(plant_id)
        if success:
            messages.append("📡 IoT Sensor synced successfully with real-time data.")
        else:
            messages.append("⚠️ IoT Sync skipped (Simulation mode or connection error).")
            
    return "\n".join(messages)

import auth_service

def handle_search_gamification(username, query):
    if not username: return 0
    
    if not query or len(str(query).strip()) < 2:
        return 0
        
    return auth_service.update_user_scores(username, 'SEARCH_QUERY', plant_id=None)


def handle_add_plant_gamification(username, is_success):
    if not username: return 0

    if is_success:
        return auth_service.update_user_scores(username, 'ADD_PLANT', plant_id=None)
    
    return 0