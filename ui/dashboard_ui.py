
import html
import datetime as dt
import gradio as gr
import matplotlib.pyplot as plt

from plants_manager import list_plants
from data_manager import get_latest_reading, get_sensor_history, sync_iot_data


# =========================
# Helpers
# =========================

def _get_username(user_state):
    return user_state.strip() if isinstance(user_state, str) else ""

def _plant_label(p: dict) -> str:
    pid = p.get("plant_id", "") or p.get("id", "")
    name = p.get("name") or ""
    species = p.get("species") or ""
    title = name or species or "Plant"
    return f"{title} ({pid})" if pid else title


def _parse_ts(x):
    if x is None:
        return None
    if isinstance(x, dt.datetime):
        return x
    s = str(x).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s[:19], fmt)
        except Exception:
            pass
    return None


# =========================
# Health logic
# =========================

def _health_eval(latest: dict):
    if not latest:
        return 0, "No data", ["No sensor data found for this plant yet."]

    temp = latest.get("temp")
    hum = latest.get("humidity")
    soil = latest.get("soil")

    issues = []
    score = 100

    if soil is not None:
        try:
            soil_v = float(soil)
            if soil_v < 30:
                issues.append("Soil is dry → consider watering")
                score -= 25
            elif soil_v > 70:
                issues.append("Soil is very wet → overwatering risk")
                score -= 20
        except Exception:
            pass

    if temp is not None:
        try:
            t = float(temp)
            if t < 15:
                issues.append("Temperature is low")
                score -= 15
            elif t > 30:
                issues.append("Temperature is high")
                score -= 15
        except Exception:
            pass

    if hum is not None:
        try:
            h = float(hum)
            if h < 35:
                issues.append("Humidity is low")
                score -= 10
            elif h > 75:
                issues.append("Humidity is high")
                score -= 10
        except Exception:
            pass

    score = max(0, min(100, score))

    if score >= 85:
        status = "Healthy"
    elif score >= 65:
        status = "Needs attention"
    else:
        status = "Unhealthy"

    if not issues:
        issues = ["Looks good based on the latest reading."]

    return score, status, issues


def _health_score_only(reading: dict) -> int:
    score, _, _ = _health_eval(reading)
    return score

# ======================================================
# Matplotlib  styling
# ======================================================
def _palette(is_dark: bool):
    """Color palette depending on current theme."""
    if is_dark:
        return {
            "bg": "#0b1220",
            "fg": "#e2e8f0",
            "grid": "#334155",
        }
    return {
        "bg": "#ffffff",
        "fg": "#0f172a",
        "grid": "#cbd5e1",
    }

def _styled_fig(is_dark: bool, size=(7, 3.2)):
    pal = _palette(is_dark)
    fig = plt.figure(figsize=size)
    fig.patch.set_facecolor(pal["bg"])
    ax = fig.add_subplot(111)

    ax.set_facecolor(pal["bg"])
    ax.tick_params(colors=pal["fg"])
    ax.xaxis.label.set_color(pal["fg"])
    ax.yaxis.label.set_color(pal["fg"])
    ax.title.set_color(pal["fg"])

    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    for spine in ["left", "bottom"]:
        ax.spines[spine].set_color(pal["grid"])

    ax.grid(True, alpha=0.3, color=pal["grid"])
    return fig, ax

# def _style_axes(ax):
#     ax.set_facecolor("#0b1220")
#     for side in ["top", "right"]:
#         ax.spines[side].set_visible(False)
#     for side in ["left", "bottom"]:
#         ax.spines[side].set_color("#334155")

#     ax.tick_params(colors="#e2e8f0")
#     ax.yaxis.label.set_color("#e2e8f0")
#     ax.xaxis.label.set_color("#e2e8f0")
#     ax.title.set_color("#e2e8f0")
#     ax.grid(True, alpha=0.25)

# =========================
# Plot builders (Light-only / default matplotlib)
# =========================
def _line_plot(points, title, ylabel):
    fig = plt.figure(figsize=(7, 3.2))
    ax = fig.add_subplot(111)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Time")
    ax.set_ylabel(ylabel)
    if points:
        xs, ys = zip(*points)
        ax.plot(xs, ys, linewidth=2.4)
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def _hist_plot(values, title, xlabel):
    fig = plt.figure(figsize=(7, 3.2))
    ax = fig.add_subplot(111)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel("Count")
    if values:
        ax.hist(values, bins=10, alpha=0.9)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def _scatter_plot(xs, ys, title, xlabel, ylabel):
    fig = plt.figure(figsize=(7, 3.2))
    ax = fig.add_subplot(111)
    ax.set_title(title, fontweight="bold")
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    if xs and ys:
        ax.scatter(xs, ys, s=45, alpha=0.85)
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    return fig


def _delta_plot(t, h, s):
    fig = plt.figure(figsize=(7, 3.2))
    ax = fig.add_subplot(111)

    ax.set_title("Change between samples (Δ)", fontweight="bold")
    ax.set_xlabel("Time")
    ax.set_ylabel("Δ value")

    def delta(points):
        return [(points[i][0], points[i][1] - points[i - 1][1]) for i in range(1, len(points))]

    if len(t) > 1:
        xs, ys = zip(*delta(t))
        ax.plot(xs, ys, label="Δ Temp")
    if len(h) > 1:
        xs, ys = zip(*delta(h))
        ax.plot(xs, ys, label="Δ Humidity")
    if len(s) > 1:
        xs, ys = zip(*delta(s))
        ax.plot(xs, ys, label="Δ Soil")

    ax.legend(frameon=False)
    ax.grid(True, alpha=0.25)
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig

# =========================
# UI
# =========================

def dashboard_screen(user_state: gr.State):

    gr.Markdown("## 🌿 Plant Dashboard")
    gr.Markdown("Visual overview based on **real IoT data**.")

    info = gr.Markdown()

    with gr.Row():
        plant_dd = gr.Dropdown(label="Choose a plant", interactive=True)
        days_dd = gr.Dropdown(
            choices=[("Last 7 days", 7), ("Last 14 days", 14), ("Last 30 days", 30)],
            value=14,
            label="Range",
            interactive=True,
        )
        refresh_btn = gr.Button("Refresh", variant="secondary", scale=0)

    summary_html = gr.HTML()

    # -------- PLOTS (hidden by default) --------
    plots = gr.Column(visible=False)
    with plots:
        with gr.Row():
            p_soil_hist = gr.Plot()
            p_temp = gr.Plot()

        with gr.Row():
            p_hum = gr.Plot()
            p_soil = gr.Plot()

        with gr.Row():
            p_health = gr.Plot()
            p_scatter = gr.Plot()

    def load(u, pid, days):
        username = _get_username(u)

        if not username:
            return (
                "⚠️ Please login to view the dashboard.",
                gr.update(choices=[], value=None),
                "<b>Login required</b>",
                gr.update(visible=False),
                None, None, None, None, None, None
            )

        plants = list_plants(username) or []
        choices = [(_plant_label(p), p.get("plant_id") or p.get("id")) for p in plants if p.get("plant_id") or p.get("id")]

        if not choices:
            return (
                "No plants found.",
                gr.update(choices=[], value=None),
                "<b>No plants yet</b>",
                gr.update(visible=False),
                None, None, None, None, None, None
            )

        pid = pid or choices[0][1]
        sync_iot_data(pid)

        since = dt.datetime.utcnow() - dt.timedelta(days=int(days))
        hist = get_sensor_history(pid, limit=500) or []

        pts_t, pts_h, pts_s, pts_health = [], [], [], []
        xs_s, ys_h = [], []

        for r in hist:
            ts = _parse_ts(r.get("timestamp"))
            if not ts or ts < since:
                continue

            if r.get("temp") is not None:
                pts_t.append((ts, float(r["temp"])))
            if r.get("humidity") is not None:
                pts_h.append((ts, float(r["humidity"])))
            if r.get("soil") is not None:
                pts_s.append((ts, float(r["soil"])))

            pts_health.append((ts, _health_score_only(r)))

            if r.get("soil") is not None and r.get("humidity") is not None:
                xs_s.append(float(r["soil"]))
                ys_h.append(float(r["humidity"]))

        latest = get_latest_reading(pid)
        score, status, insights = _health_eval(latest)

        summary = f"<b>Status:</b> {status}<br><b>Score:</b> {score}<ul>"
        summary += "".join(f"<li>{html.escape(i)}</li>" for i in insights)
        summary += "</ul>"

        return (
            "Dashboard loaded.",
            gr.update(choices=choices, value=pid),
            summary,
            gr.update(visible=True),
            _hist_plot([v for _, v in pts_s], "Soil moisture distribution", "Soil"),
            _line_plot(pts_t, "Temperature (°C)", "°C"),
            _line_plot(pts_h, "Humidity (%)", "%"),
            _line_plot(pts_s, "Soil moisture trend", "Soil"),
            _delta_plot(pts_t, pts_h, pts_s),
            _scatter_plot(xs_s, ys_h, "Soil vs Humidity", "Soil", "Humidity")
        )


    for c in (plant_dd, days_dd):
        c.change(
            load,
            inputs=[user_state, plant_dd, days_dd],
            outputs=[info, plant_dd, summary_html, plots,p_soil_hist, p_temp, p_hum, p_soil,
            p_health, p_scatter],
        )
    # # Reactive: update when plant dropdown selection changes
    # plant_dd.change(
    #     load,
    #     inputs=[user_state, plant_dd, days_dd],
    #     outputs=[
    #         info, plant_dd, summary_html,
    #         plots_wrap,
    #         p_soil_hist, p_temp, p_hum, p_soil,
    #         p_health, p_scatter
    #     ],
    # )

    # # Reactive: update when days range changes
    # days_dd.change(
    #     load,
    #     inputs=[user_state, plant_dd, days_dd],
    #     outputs=[
    #         info, plant_dd, summary_html,
    #         plots_wrap,
    #         p_soil_hist, p_temp, p_hum, p_soil,
    #         p_health, p_scatter
    #     ],
    # )

    # Manual refresh button
    refresh_btn.click(
        load,
        inputs=[user_state, plant_dd, days_dd],
        outputs=[
            info, plant_dd, summary_html,
            plots,
            p_soil_hist, p_temp, p_hum, p_soil,
            p_health, p_scatter
        ],
    )

    # Return components for external wiring (auto-load on navigation)
    return refresh_btn, load, [user_state, plant_dd, days_dd], [
        info, plant_dd, summary_html,
        plots,
        p_soil_hist, p_temp, p_hum, p_soil,
        p_health, p_scatter
    ]
