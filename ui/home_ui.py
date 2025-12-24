import gradio as gr
from datetime import datetime, timezone

from plants_manager import count_plants
from auth_service import logout_user
from data_manager import get_all_readings

from ui.plants_ui import plants_screen
from ui.sensors_ui import sensors_screen
from ui.search_ui import search_screen
from ui.upload_ui import upload_screen
from ui.dashboard_ui import dashboard_screen
from ui.auth_ui import auth_screen


# =========================
# Vacation mode bridge
# =========================
def run_vacation_check(days, current_username):
    if days is None:
        return []

    if not current_username:
        return [["Error", "-", "❌", "No user logged in"]]

    from data_manager import generate_vacation_report
    return generate_vacation_report(current_username, days)


# =========================
# Helpers for metrics
# =========================
def _parse_iso(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts)
    except Exception:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except Exception:
            return None


def _time_ago(dt: datetime | None) -> str:
    if not dt:
        return "n/a"

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    now = datetime.now(timezone.utc)
    diff = now - dt
    mins = int(diff.total_seconds() // 60)

    if mins < 1:
        return "just now"
    if mins < 60:
        return f"{mins}m ago"

    hrs = mins // 60
    if hrs < 24:
        return f"{hrs}h ago"

    return f"{hrs // 24}d ago"


def _compute_overview_metrics(username=None):
    try:
        plants_n = int(count_plants(username) if username else 0)
    except Exception:
        plants_n = 0

    try:
        latest = get_all_readings(limit=1) or []
        latest_ts = _parse_iso(latest[0].get("timestamp")) if latest else None
        last_reading = _time_ago(latest_ts)

        recent = get_all_readings(limit=50) or []
        soils = [r.get("soil") for r in recent if r.get("soil") is not None]
        avg_soil = round(sum(soils) / len(soils), 1) if soils else 0.0

    except Exception:
        last_reading, avg_soil = "n/a", 0.0

    return plants_n, last_reading, avg_soil

# =========================
# HOME SCREEN
# =========================
def home_screen():
    """
    Builds the main dashboard UI.
    Includes custom CSS to fix table formatting for the Vacation Mode report.
    """
    
    # Custom CSS to control the table layout:
    # 1. Enforces 'nowrap' on the 3rd column (Status) to keep the icon and text on one line.
    # 2. Sets a minimum width for readability.
    custom_css = """
    .vacation-table td:nth-child(3) { 
        white-space: nowrap !important; 
        min-width: 140px;
    }
    """

    # Initialize Blocks with the custom CSS
    with gr.Blocks(title="My Garden Care", theme=gr.themes.Soft(), css=custom_css) as app:
        user_state = gr.State(value=None)

        # ---------- TOP BAR ----------
        with gr.Row():
            gr.Markdown("## 🌿 My Garden Care")
            user_status_label = gr.Markdown("")
        with gr.Row(equal_height=True):
            btn_home = gr.Button("Home", variant="secondary", scale=1, min_width=140)
            btn_sensors = gr.Button("Sensors", variant="secondary", scale=1, min_width=140)
            btn_search = gr.Button("Search", variant="secondary", scale=1, min_width=140)
            btn_dashboard = gr.Button("Plant Dashboard", variant="secondary", scale=1, min_width=140)
            btn_upload = gr.Button("Upload a Photo", variant="secondary", scale=1, min_width=140)
            btn_auth = gr.Button("Login / Register", variant="primary", scale=1, min_width=140)
            logout_btn = gr.Button("Logout", visible=False, scale=1, min_width=140)

        gr.Markdown("---")

        # ---------- HOME ----------
        with gr.Column(visible=True) as home:
            gr.Markdown("## Overview")

            btn_open_plants = gr.Button("View My Plants", variant="primary")

            with gr.Row():
                m_plants = gr.Number(label="My plants", interactive=False)
                m_last = gr.Textbox(label="Last sensor reading", interactive=False)
                m_avg_soil = gr.Number(label="Avg soil (last 50)", interactive=False)

            btn_refresh = gr.Button("Refresh", variant="secondary")

            gr.Markdown("### Quick actions")
            with gr.Row():
                qa_sensors = gr.Button("🌱 Check sensors", variant="secondary")
                qa_upload = gr.Button("📷 Upload a plant photo", variant="secondary")

            # ---------- VACATION MODE ----------
            with gr.Accordion("✈️ Planning a vacation? Check your plants", open=False):
                gr.Markdown(
                    "Estimate whether your plants will survive while you're away, "
                    "based on real soil moisture data."
                )

                with gr.Row():
                    days_input = gr.Number(
                        label="Days Away",
                        value=None,
                        precision=0,
                        placeholder="e.g. 5"
                    )
                    check_btn = gr.Button("Check", variant="primary")

                # Table configuration:
                # - 'column_widths': Allocates 50% width to the Message column to prevent cramping.
                # - 'elem_classes': Links this component to the 'vacation-table' CSS class defined above.
                vacation_table = gr.Dataframe(
                    headers=["Plant", "Current Soil", "Status", "Message"],
                    interactive=False,
                    wrap=True,
                    column_widths=["15%", "10%", "15%", "60%"], 
                    elem_classes="vacation-table"
                )

                check_btn.click(
                    fn=run_vacation_check,
                    inputs=[days_input, user_state],
                    outputs=[vacation_table]
                )

        # ---------- OTHER PAGES ----------
        with gr.Column(visible=False) as plants:
            plants_screen(user_state)

        with gr.Column(visible=False) as sensors:
            sensors_btn, sensors_load, sensors_inputs, sensors_outputs = sensors_screen(user_state)

        with gr.Column(visible=False) as search:
            search_screen()

        with gr.Column(visible=False) as dashboard:
            dashboard_btn, dashboard_load, dashboard_inputs, dashboard_outputs = dashboard_screen(user_state)

        with gr.Column(visible=False) as upload:
            upload_screen(user_state)

        with gr.Column(visible=False) as auth:
            login_event = auth_screen(user_state)

        # ---------- NAV ----------
        def go(target):
            return [
                gr.update(visible=(target == "home")),
                gr.update(visible=(target == "plants")),
                gr.update(visible=(target == "sensors")),
                gr.update(visible=(target == "search")),
                gr.update(visible=(target == "dashboard")),
                gr.update(visible=(target == "upload")),
                gr.update(visible=(target == "auth")),
            ]

        pages = [home, plants, sensors, search, dashboard, upload, auth]

        btn_home.click(lambda: go("home"), outputs=pages)
        btn_sensors.click(lambda: go("sensors"), outputs=pages).then(
            fn=sensors_load, inputs=sensors_inputs, outputs=sensors_outputs
        )
        btn_search.click(lambda: go("search"), outputs=pages)
        btn_dashboard.click(lambda: go("dashboard"), outputs=pages).then(
            fn=dashboard_load, inputs=dashboard_inputs, outputs=dashboard_outputs
        )
        btn_upload.click(lambda: go("upload"), outputs=pages)
        btn_auth.click(lambda: go("auth"), outputs=pages)

        btn_open_plants.click(lambda: go("plants"), outputs=pages)
        qa_sensors.click(lambda: go("sensors"), outputs=pages).then(
            fn=sensors_load, inputs=sensors_inputs, outputs=sensors_outputs
        )
        qa_upload.click(lambda: go("upload"), outputs=pages)

        # ---------- METRICS ----------
        def refresh_metrics(u):
            username = u.strip() if isinstance(u, str) else None
            plants_n, last_reading, avg_soil = _compute_overview_metrics(username)
            return plants_n, last_reading, avg_soil

        btn_refresh.click(refresh_metrics, inputs=[user_state], outputs=[m_plants, m_last, m_avg_soil])
        app.load(refresh_metrics, inputs=[user_state], outputs=[m_plants, m_last, m_avg_soil])

        # ---------- LOGOUT LOGIC ----------
        def do_logout():
            # Delegate cleanup to auth service
            logout_user()
            return (
                None,  # user_state - clear session
                gr.update(visible=False),  # home - hide
                gr.update(visible=False),  # plants - hide
                gr.update(visible=False),  # sensors - hide
                gr.update(visible=False),  # search - hide
                gr.update(visible=False),  # dashboard - hide
                gr.update(visible=False),  # upload - hide
                gr.update(visible=True),   # auth - SHOW login screen
                gr.update(visible=False),  # logout_btn - hide
                "",  # user_status_label - clear
                gr.update(visible=True),   # btn_auth - show Login/Register button
            )

        logout_btn.click(
            fn=do_logout,
            outputs=[user_state, home, plants, sensors, search, dashboard, upload, auth, logout_btn, user_status_label, btn_auth]
        )

        # ---------- LOGIN SUCCESS -> SHOW LOGOUT BTN + REFRESH METRICS ----------
        def on_login_success(username):
            if username:
                # Refresh metrics on login
                plants_n, last_reading, avg_soil = _compute_overview_metrics(username)
                return (
                    gr.update(visible=True),  # logout_btn
                    f"👤 Logged in as: **{username}**",  # user_status_label
                    plants_n,  # m_plants
                    last_reading,  # m_last
                    avg_soil,  # m_avg_soil
                )
            return gr.update(visible=False), "", 0, "n/a", 0.0

        login_event.then(
            fn=on_login_success,
            inputs=[user_state],
            outputs=[logout_btn, user_status_label, m_plants, m_last, m_avg_soil]
        )

    return app