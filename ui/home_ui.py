import gradio as gr
from datetime import datetime, timezone

from plants_manager import count_plants
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


def _compute_overview_metrics():
    try:
        plants_n = int(count_plants() or 0)
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
    with gr.Blocks(title="My Garden Care", theme=gr.themes.Soft()) as app:
        user_state = gr.State(value=None)

        # ---------- TOP BAR ----------
        with gr.Row():
            gr.Markdown("## 🌿 My Garden Care")
            with gr.Row():
                btn_home = gr.Button("Home", variant="secondary")
                btn_sensors = gr.Button("Sensors", variant="secondary")
                btn_search = gr.Button("Search", variant="secondary")
                btn_dashboard = gr.Button("Plant Dashboard", variant="secondary")
                btn_upload = gr.Button("Upload a Photo", variant="secondary")
                btn_auth = gr.Button("Login / Register", variant="primary")

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

                vacation_table = gr.Dataframe(
                    headers=["Plant", "Current Soil", "Status", "Message"],
                    interactive=False,
                    wrap=True
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
            sensors_screen(user_state)

        with gr.Column(visible=False) as search:
            search_screen()

        with gr.Column(visible=False) as dashboard:
            dashboard_screen(user_state)

        with gr.Column(visible=False) as upload:
            upload_screen(user_state)

        with gr.Column(visible=False) as auth:
            auth_screen(user_state)

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
        btn_sensors.click(lambda: go("sensors"), outputs=pages)
        btn_search.click(lambda: go("search"), outputs=pages)
        btn_dashboard.click(lambda: go("dashboard"), outputs=pages)
        btn_upload.click(lambda: go("upload"), outputs=pages)
        btn_auth.click(lambda: go("auth"), outputs=pages)

        btn_open_plants.click(lambda: go("plants"), outputs=pages)
        qa_sensors.click(lambda: go("sensors"), outputs=pages)
        qa_upload.click(lambda: go("upload"), outputs=pages)

        # ---------- METRICS ----------
        def refresh_metrics():
            plants_n, last_reading, avg_soil = _compute_overview_metrics()
            return plants_n, last_reading, avg_soil

        btn_refresh.click(refresh_metrics, outputs=[m_plants, m_last, m_avg_soil])
        app.load(refresh_metrics, outputs=[m_plants, m_last, m_avg_soil])

    return app
