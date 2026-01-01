import gradio as gr
import auth_service
import logic_handler
import plants_manager
import gamification_rules

# ==========================================
# 1. UI HELPERS
# ==========================================

def get_race_status_md(username):
    if not username: return "Please log in."
    
    user_data = auth_service.get_user_details(username)
    if not user_data: return "User data not found"
    
    weekly = user_data.get('weekly_score', 0)
    rank = gamification_rules.get_user_rank(user_data.get('score', 0))
    
    return f"###  🏆 Weekly Score: {weekly} | Rank: {rank}"

def get_plant_choices(username):
    if not username: return []
    plants = plants_manager.list_plants(username)
    return [(p.get('name', 'Unknown'), p.get('plant_id')) for p in plants]

def refresh_all_data(username):
    """Refreshes status, plant list, and leaderboard."""
    if not username:
        return "Please Login", gr.update(choices=[]), []
    
    # 1. Status Text
    md_status = get_race_status_md(username)
    
    # 2. Plant Dropdown
    plants = get_plant_choices(username)
    
    # 3. Leaderboard Table
    leaderboard = [[u['username'], u['score'], u['rank_title']] for u in auth_service.get_weekly_leaderboard()]
    
    return md_status, gr.update(choices=plants), leaderboard

# ==========================================
# 3. LOGIC WRAPPER (THE FIX)
# ==========================================
def safe_gamified_action(user, plant_id, action_type):
    """
    Validates that a plant is selected BEFORE calling the logic.
    Prevents the 'free points' bug.
    """
    if not user:
        return "Please log in first."
    
    if not plant_id:
        return "⚠️ Error: You must select a plant from the list first!"
    
    return logic_handler.handle_gamified_action(user, action_type, plant_id)

# ==========================================
# 3. MAIN TAB UI
# ==========================================
def create_gamification_tab(user_state):
    # 1. Status (Simple Markdown)
    status_box = gr.Markdown(value="Loading...")
    
    gr.Markdown("---")
    
    # 2. Action Area
    gr.Markdown("###  📅 Daily Missions")
    with gr.Group():
        with gr.Row(variant="panel", equal_height=True):
            # Dropdown
            dd_plants = gr.Dropdown(label="Select Plant", choices=[], interactive=True, scale=3)
            
            # Water Button
            btn_water = gr.Button("💧 Water (+10)", variant="primary", scale=1)
            
            # Spacer
            with gr.Column(scale=0.2, min_width=20):
                pass
            
            # Fertilize Button
            btn_fert = gr.Button("🧪 Fertilize (+10)", variant="primary", scale=1)
        
        lbl_result = gr.Textbox(label="Result", interactive=False, lines=1)

        gr.Markdown("---")

        # 3. Leaderboard
        gr.Markdown("###  🏆 Weekly Leaderboard")
        leaderboard = gr.Dataframe(
            headers=["Nickname", "Weekly Score", "Rank"],
            interactive=False
        )

        # =======================================
        # EVENTS
        # =======================================
        btn_water.click(
            fn=lambda u, pid: safe_gamified_action(u, pid, "WATER_PLANT"),
            inputs=[user_state, dd_plants], 
            outputs=[lbl_result]
        ).success(
            fn=refresh_all_data, 
            inputs=[user_state],
            outputs=[status_box, dd_plants, leaderboard]
        )

     
        btn_fert.click(
            fn=lambda u, pid: safe_gamified_action(u, pid, "FERTILIZE_PLANT"),
            inputs=[user_state, dd_plants],
            outputs=[lbl_result]
        ).success(
            fn=refresh_all_data,
            inputs=[user_state],
            outputs=[status_box, dd_plants, leaderboard]
        )
        
    
        return status_box, dd_plants, leaderboard, lbl_result