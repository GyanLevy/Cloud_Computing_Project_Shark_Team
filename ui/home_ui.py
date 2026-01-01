import gradio as gr
from datetime import datetime, timezone

import auth_service
import gamification_rules 
from plants_manager import count_plants
from auth_service import logout_user
from data_manager import get_all_readings

from ui.plants_ui import plants_screen
from ui.sensors_ui import sensors_screen
from ui.search_ui import search_screen
from ui.upload_ui import upload_screen
from ui.dashboard_ui import dashboard_screen
from ui.auth_ui import auth_screen
from ui.gamification_ui import create_gamification_tab, refresh_all_data

# =========================
# HELPER: HOME BANNER (Moved here correctly)
# =========================
def get_home_user_banner(username):
    """Creates the 'ID Card' for the Home Page."""
    user_data = auth_service.get_user_details(username)
    if not user_data: return ""
    
    score = user_data.get('score', 0)
    rank_title = gamification_rules.get_user_rank(score)
    progress = min((score / 1500) * 100, 100) if score else 0
    
    
    html = f"""
    <div style="display: flex; align-items: center; justify-content: space-between; 
        background: linear-gradient(90deg, #e0f2fe 0%, #f0fdf4 100%); 
        padding: 15px 25px; border-radius: 12px; border-left: 5px solid #0284c7; margin-bottom: 20px;">
        <div>
            <h2 style="margin:0; color: #0c4a6e; font-size: 24px;"> Welcome back, {user_data.get('username', username)}</h2>
            <p style="margin:5px 0 0 0; color: #0369a1; font-size: 16px;">
                Current Status: <span style="background-color:#0284c7; color:white; padding:2px 8px; border-radius:10px; font-weight:bold;">{rank_title}</span>
            </p>
        </div>
        <div style="text-align: right; min-width: 200px;">
            <span style="color: #0c4a6e; font-weight:bold; font-size: 14px;">Total Score: {score} XP</span>
            <div style="background-color: #cbd5e1; width: 100%; height: 10px; border-radius: 5px; margin-top: 5px;">
                <div style="background-color: #0284c7; width: {progress}%; height: 100%; border-radius: 5px;"></div>
            </div>
        </div>
    </div>
    """
    return html

# =========================
# Vacation mode bridge
# =========================
def run_vacation_check(days, current_username, progress=gr.Progress(track_tqdm=True)):
    if days is None: return []
    if not current_username: return [["Error", "-", "❌", "No user logged in"]]
    def gradio_callback(pct, desc=""): progress(pct, desc=desc)
    from data_manager import generate_vacation_report
    return generate_vacation_report(current_username, days, progress_callback=gradio_callback)

# =========================
# Helpers
# =========================
def _parse_iso(ts):
    if not ts: return None
    try: return datetime.fromisoformat(ts)
    except:
        try: return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except: return None

def _time_ago(dt: datetime | None) -> str:
    if not dt: return "n/a"
    if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    diff = now - dt
    mins = int(diff.total_seconds() // 60)
    if mins < 1: return "just now"
    if mins < 60: return f"{mins}m ago"
    hrs = mins // 60
    if hrs < 24: return f"{hrs}h ago"
    return f"{hrs // 24}d ago"

def _compute_overview_metrics(username=None):
    try: plants_n = int(count_plants(username) if username else 0)
    except: plants_n = 0
    try:
        latest = get_all_readings(limit=1) or []
        latest_ts = _parse_iso(latest[0].get("timestamp")) if latest else None
        last_reading = _time_ago(latest_ts)
        recent = get_all_readings(limit=50) or []
        soils = [r.get("soil") for r in recent if r.get("soil") is not None]
        avg_soil = round(sum(soils) / len(soils), 1) if soils else 0.0
    except: last_reading, avg_soil = "n/a", 0.0
    return plants_n, last_reading, avg_soil

def refresh_home_data(username):
    plants_n, last_reading, avg_soil = _compute_overview_metrics(username)
    banner_html = get_home_user_banner(username)
    return banner_html, plants_n, last_reading, avg_soil

# =========================
# HOME SCREEN
# =========================
def home_screen():
    custom_css = """
    .vacation-table td:nth-child(3) { white-space: nowrap !important; min-width: 140px; }
    """

    with gr.Blocks(title="My Garden Care", theme=gr.themes.Glass(), css=custom_css) as app:
        user_state = gr.State(value=None)

        # TOP BAR
        with gr.Row():
            gr.Markdown("## 🌿 My Garden Care")
            user_status_label = gr.Markdown("")
  
        # NAV BAR
        with gr.Row(equal_height=True, visible=False) as nav_row:
            btn_home = gr.Button("Home", variant="secondary", scale=1, min_width=120)
            btn_sensors = gr.Button("Sensors", variant="secondary", scale=1, min_width=120)
            btn_search = gr.Button("Search", variant="secondary", scale=1, min_width=120)
            btn_dashboard = gr.Button("Dashboard", variant="secondary", scale=1, min_width=120)
            btn_upload = gr.Button("Scan Plant", variant="secondary", scale=1, min_width=120)
            btn_race = gr.Button("🏆 Garden Race", variant="secondary", scale=1, min_width=120) 
            logout_btn = gr.Button("Logout", visible=False, scale=1, min_width=120)

        gr.Markdown("---")

        # PAGE 1: HOME
        with gr.Column(visible=False) as home:
            welcome_banner = gr.HTML(value="") 
            with gr.Row():
                qa_plants = gr.Button("🌿 View my plants", variant="secondary")
            with gr.Row():
                m_plants = gr.Number(label="My plants", interactive=False)
                m_last = gr.Textbox(label="Last sensor reading", interactive=False)
                m_avg_soil = gr.Number(label="Avg soil (last 50)", interactive=False)
            btn_refresh = gr.Button("Refresh", variant="secondary")
            
            with gr.Accordion("✈️ Planning a vacation?", open=False):
                gr.Markdown("Estimate survival time based on soil data.")
                with gr.Row():
                    days_input = gr.Number(label="Days Away", precision=0, placeholder="e.g. 5")
                    check_btn = gr.Button("Check", variant="primary")
                vacation_table = gr.Dataframe(headers=["Plant", "Current Soil", "Status", "Message"], interactive=False)
                check_btn.click(fn=run_vacation_check, inputs=[days_input, user_state], outputs=[vacation_table])

        # OTHER PAGES
        with gr.Column(visible=False) as plants:
            plants_btn, plants_load, plants_inputs, plants_outputs = plants_screen(user_state)
        with gr.Column(visible=False) as sensors:
            sensors_btn, sensors_load, sensors_inputs, sensors_outputs = sensors_screen(user_state)
        with gr.Column(visible=False) as search:
            search_screen(user_state)
        with gr.Column(visible=False) as dashboard:
            dashboard_btn, dashboard_load, dashboard_inputs, dashboard_outputs = dashboard_screen(user_state)
        with gr.Column(visible=False) as upload:
            upload_screen(user_state)

        # PAGE: RACE
        with gr.Column(visible=False) as race:
            race_status, race_dd, race_board, race_lbl = create_gamification_tab(user_state)

        with gr.Column(visible=True) as auth:
            login_event, auth_current_user, auth_login_msg, auth_reg_msg = auth_screen(user_state)

        # NAVIGATION
        def go(target):
            return [
                gr.update(visible=(target == "home")),
                gr.update(visible=(target == "plants")),
                gr.update(visible=(target == "sensors")),
                gr.update(visible=(target == "search")),
                gr.update(visible=(target == "dashboard")),
                gr.update(visible=(target == "upload")),
                gr.update(visible=(target == "race")),
                gr.update(visible=(target == "auth")),
            ]

        pages = [home, plants, sensors, search, dashboard, upload, race, auth]
        app.load(lambda: go("auth"), outputs=pages)

        # --- AUTO-LOAD LOGIC ---
        btn_home.click(lambda: go("home"), outputs=pages).then(
            fn=refresh_home_data,
            inputs=[user_state],
            outputs=[welcome_banner, m_plants, m_last, m_avg_soil]
        )
        
        btn_race.click(lambda: go("race"), outputs=pages).then(
            fn=refresh_all_data,
            inputs=[user_state],
            outputs=[race_status, race_dd, race_board]
        )

        btn_sensors.click(lambda: go("sensors"), outputs=pages).then(fn=sensors_load, inputs=sensors_inputs, outputs=sensors_outputs)
        btn_search.click(lambda: go("search"), outputs=pages)
        btn_dashboard.click(lambda: go("dashboard"), outputs=pages).then(fn=dashboard_load, inputs=dashboard_inputs, outputs=dashboard_outputs)
        btn_upload.click(lambda: go("upload"), outputs=pages)
        qa_plants.click(lambda: go("plants"), outputs=pages).then(fn=plants_load, inputs=plants_inputs, outputs=plants_outputs)

        btn_refresh.click(refresh_home_data, inputs=[user_state], outputs=[welcome_banner, m_plants, m_last, m_avg_soil])

        # Login Logic
        def on_login_success(username):
            if username:
                banner, p_n, last, avg = refresh_home_data(username)
                return (
                    gr.update(visible=True), gr.update(visible=True), 
                    f"👤 {username}", banner, p_n, last, avg
                )
            return (gr.update(visible=False), gr.update(visible=False), "", "", 0, "n/a", 0.0)

        login_event.then(
            fn=on_login_success,
            inputs=[user_state],
            outputs=[nav_row, logout_btn, user_status_label, welcome_banner, m_plants, m_last, m_avg_soil]
        ).then(lambda: go("home"), outputs=pages)

        # Logout Logic
        def do_logout():
            logout_user()
            return (None, gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
                    gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), gr.update(visible=False), 
                    gr.update(visible=True), gr.update(visible=True), "", "Not logged in.", "", "", "")

        logout_btn.click(
            fn=do_logout,
            outputs=[user_state, nav_row, home, plants, sensors, search, dashboard, upload, race, auth, logout_btn, 
                     user_status_label, auth_current_user, auth_login_msg, auth_reg_msg, welcome_banner]
        )

    return app