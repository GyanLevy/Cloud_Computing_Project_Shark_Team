import html
import datetime as dt
import gradio as gr
import matplotlib.pyplot as plt

from plants_manager import list_plants
from data_manager import get_latest_reading, get_sensor_history, sync_iot_data


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
    """Same logic as _health_eval, but returns ONLY a score (for trend chart)."""
    if not reading:
        return 0

    temp = reading.get("temp")
    hum = reading.get("humidity")
    soil = reading.get("soil")

    score = 100

    # Soil
    if soil is not None:
        try:
            soil_v = float(soil)
            if soil_v < 30:
                score -= 25
            elif soil_v > 70:
                score -= 20
        except Exception:
            pass

    # Temp
    if temp is not None:
        try:
            t = float(temp)
            if t < 15 or t > 30:
                score -= 15
        except Exception:
            pass

    # Humidity
    if hum is not None:
        try:
            h = float(hum)
            if h < 35 or h > 75:
                score -= 10
        except Exception:
            pass

    return max(0, min(100, int(round(score))))


def _style_axes(ax):
    ax.set_facecolor("white")
    for side in ["top", "right"]:
        ax.spines[side].set_visible(False)
    for side in ["left", "bottom"]:
        ax.spines[side].set_color("#e5e7eb")
        ax.spines[side].set_linewidth(1.0)

    ax.tick_params(colors="#0f172a")
    ax.yaxis.label.set_color("#0f172a")
    ax.xaxis.label.set_color("#0f172a")
    ax.title.set_color("#0f172a")
    ax.grid(True, alpha=0.18)


def _line_plot(points, title, y_label):
    fig = plt.figure(figsize=(7.0, 3.2))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)

    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Time")
    ax.set_ylabel(y_label)

    if not points:
        _style_axes(ax)
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color="#0f172a")
        fig.tight_layout()
        return fig

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    ax.plot(xs, ys, linewidth=2.4)
    fig.autofmt_xdate()
    _style_axes(ax)
    fig.tight_layout()
    return fig


def _hist_plot(values, title, x_label):
    fig = plt.figure(figsize=(7.0, 3.2))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)

    ax.set_title(title, fontweight="bold")
    ax.set_xlabel(x_label)
    ax.set_ylabel("Count")

    if not values:
        _style_axes(ax)
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color="#0f172a")
        fig.tight_layout()
        return fig

    ax.hist(values, bins=10, edgecolor="#ffffff", linewidth=1.0)
    _style_axes(ax)
    fig.tight_layout()
    return fig


def _scatter_plot(xs, ys, title, x_label, y_label):
    fig = plt.figure(figsize=(7.0, 3.2))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)

    ax.set_title(title, fontweight="bold")
    ax.set_xlabel(x_label)
    ax.set_ylabel(y_label)

    if not xs or not ys:
        _style_axes(ax)
        ax.text(0.5, 0.5, "No data", ha="center", va="center",
                transform=ax.transAxes, color="#0f172a")
        fig.tight_layout()
        return fig

    ax.scatter(xs, ys, s=45, alpha=0.85)
    _style_axes(ax)
    fig.tight_layout()
    return fig

def _delta_plot(points_temp, points_hum, points_soil, title="Change between samples (Δ)"):
    """
    Builds a delta chart: difference between consecutive samples for each sensor.
    X-axis = time of the current sample
    """
    fig = plt.figure(figsize=(7.0, 3.2))
    fig.patch.set_facecolor("white")
    ax = fig.add_subplot(111)

    ax.set_title(title, fontweight="bold")
    ax.set_xlabel("Time")
    ax.set_ylabel("Δ value")

    def to_deltas(points):
        
        if len(points) < 2:
            return []
        out = []
        for i in range(1, len(points)):
            t_prev, v_prev = points[i - 1]
            t_cur, v_cur = points[i]
            try:
                out.append((t_cur, float(v_cur) - float(v_prev)))
            except Exception:
                pass
        return out

    dT = to_deltas(points_temp)
    dH = to_deltas(points_hum)
    dS = to_deltas(points_soil)

    if not dT and not dH and not dS:
        _style_axes(ax)
        ax.text(0.5, 0.5, "Not enough data (need at least 2 samples)", ha="center", va="center",
                transform=ax.transAxes, color="#0f172a")
        fig.tight_layout()
        return fig

    # plot each delta series if exists
    if dT:
        ax.plot([t for t, _ in dT], [v for _, v in dT], linewidth=2.2, label="Δ Temp (°C)")
    if dH:
        ax.plot([t for t, _ in dH], [v for _, v in dH], linewidth=2.2, label="Δ Humidity (%)")
    if dS:
        ax.plot([t for t, _ in dS], [v for _, v in dS], linewidth=2.2, label="Δ Soil")

    fig.autofmt_xdate()
    _style_axes(ax)
    ax.legend(loc="upper right", frameon=False)
    fig.tight_layout()
    return fig


def _status_badge(status: str):
    s = (status or "").lower()
    if "healthy" in s:
        return ("#ecfdf5", "#bbf7d0", "#065f46")
    if "unhealthy" in s:
        return ("#fef2f2", "#fecaca", "#991b1b")
    return ("#fff7ed", "#fed7aa", "#9a3412")


def dashboard_screen(user_state: gr.State):
    gr.Markdown("## 🌿 Plant Dashboard")
    gr.Markdown("A visual overview of your plant health using real IoT samples (temp / humidity / soil).")

    info = gr.Markdown()

    with gr.Row():
        plant_dd = gr.Dropdown(label="Choose a plant", choices=[], value=None, scale=6)
        days_dd = gr.Dropdown(
            label="Range",
            choices=[("Last 7 days", 7), ("Last 14 days", 14), ("Last 30 days", 30)],
            value=14,
            scale=3,
        )
        refresh_btn = gr.Button("Apply", scale=2)

    summary_html = gr.HTML()

  
    with gr.Row():
        p_soil_hist = gr.Plot(elem_classes=["plotcard"])
        p_temp = gr.Plot(elem_classes=["plotcard"])

    with gr.Row():
        p_hum = gr.Plot(elem_classes=["plotcard"])
        p_soil = gr.Plot(elem_classes=["plotcard"])

    
    with gr.Row():
        p_health_trend = gr.Plot(elem_classes=["plotcard"])
        p_soil_hum_scatter = gr.Plot(elem_classes=["plotcard"])

    def load(u, chosen_pid, days):
        username = _get_username(u)

        empty_fig = _line_plot([], "No data", "")
        empty_hist = _hist_plot([], "No data", "")
        empty_scatter = _scatter_plot([], [], "No data", "", "")
        empty_health = _line_plot([], "No data", "")

        if not username:
            return (
                "⚠️ Please login to view the dashboard.",
                gr.update(choices=[], value=None),
                "<div class='card'><b style='color:#0f172a;'>Login required.</b></div>",
                empty_hist, empty_fig, empty_fig, empty_fig,
                empty_health, empty_scatter
            )

        plants = list_plants(username) or []
        choices = []
        for p in plants:
            pid = p.get("plant_id") or p.get("id")
            if pid:
                choices.append((_plant_label(p), pid))

        if not choices:
            return (
                "No plants found. Add a plant in Upload.",
                gr.update(choices=[], value=None),
                "<div class='card'><b style='color:#0f172a;'>No plants yet.</b></div>",
                empty_hist, empty_fig, empty_fig, empty_fig,
                empty_health, empty_scatter
            )

        pid = chosen_pid or choices[0][1]
        days = int(days or 14)

        # Pull 1 fresh sample from IoT server (temp/humidity/soil)
        sync_iot_data(pid)

        since = dt.datetime.utcnow() - dt.timedelta(days=days)
        hist = get_sensor_history(pid, limit=500) or []

        points_temp, points_hum, points_soil = [], [], []
        points_health = []          
        scatter_soil = []           
        scatter_hum = []            

        for r in hist:
            ts = _parse_ts(r.get("timestamp"))
            if not ts:
                continue
            try:
                ts_naive = ts.replace(tzinfo=None)
            except Exception:
                ts_naive = ts
            if ts_naive < since:
                continue

            def add_point(arr, key):
                v = r.get(key)
                if v is None:
                    return None
                try:
                    val = float(v)
                    arr.append((ts_naive, val))
                    return val
                except Exception:
                    return None

            t_val = add_point(points_temp, "temp")
            h_val = add_point(points_hum, "humidity")
            s_val = add_point(points_soil, "soil")

            
            score_here = _health_score_only(r)
            points_health.append((ts_naive, score_here))

            
            if s_val is not None and h_val is not None:
                scatter_soil.append(s_val)
                scatter_hum.append(h_val)

        points_temp.sort(key=lambda x: x[0])
        points_hum.sort(key=lambda x: x[0])
        points_soil.sort(key=lambda x: x[0])
        points_health.sort(key=lambda x: x[0])

        latest = get_latest_reading(pid) or {}
        score, status, insights = _health_eval(latest)
        bg, border, text = _status_badge(status)

        latest_txt = (
            f"<div style='margin-top:10px; color:#334155;'>"
            f"<b style='color:#0f172a;'>Latest reading:</b> "
            f"{latest.get('temp','N/A')}°C • {latest.get('humidity','N/A')}% • Soil {latest.get('soil','N/A')}"
            f"</div>"
        )

        insights_html = "".join([f"<li style='color:#0f172a;'>{html.escape(str(i))}</li>" for i in insights])

        summary = f"""
        <div class="card">
          <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
            <div style="font-weight:900; font-size:1.25rem; color:#0f172a;">{html.escape(status)}</div>
            <div style="background:{bg}; border:1px solid {border}; color:{text};
                        padding:6px 10px; border-radius:999px; font-weight:900;">
              Score: {score}
            </div>
            <div style="color:#64748b; font-weight:700;">(last {days} days)</div>
          </div>

          {latest_txt}

          <div style="margin-top:12px;">
            <div style="font-weight:900; color:#0f172a; margin-bottom:6px;">Insights</div>
            <ul style="margin:0; padding-left:18px;">
              {insights_html}
            </ul>
          </div>
        </div>
        """

   
        soil_values = [v for _, v in points_soil]
        fig_hist = _hist_plot(soil_values, "Soil moisture distribution", "Soil")
        fig_t = _line_plot(points_temp, "Temperature (°C)", "°C")
        fig_h = _line_plot(points_hum, "Humidity (%)", "%")
        fig_s = _line_plot(points_soil, "Soil moisture trend", "Soil")

        
        fig_health = _delta_plot(points_temp, points_hum, points_soil, "Delta chart: change between samples (Δ)")

        fig_scatter = _scatter_plot(
            scatter_soil, scatter_hum,
            "Correlation: Soil vs Humidity",
            "Soil moisture",
            "Humidity (%)"
        )

        return (
            "Dashboard loaded.",
            gr.update(choices=choices, value=pid),
            summary,
            fig_hist, fig_t, fig_h, fig_s,
            fig_health, fig_scatter
        )

    refresh_btn.click(
        fn=load,
        inputs=[user_state, plant_dd, days_dd],
        outputs=[
            info, plant_dd, summary_html,
            p_soil_hist, p_temp, p_hum, p_soil,
            p_health_trend, p_soil_hum_scatter
        ],
    )
