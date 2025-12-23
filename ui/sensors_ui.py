import gradio as gr

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


def sensors_screen(user_state: gr.State):
    gr.Markdown("## 🌱 IoT Sensors")
    info = gr.Markdown()

    with gr.Row():
        plant_dd = gr.Dropdown(label="Choose a plant", choices=[], value=None, interactive=True)
        refresh_btn = gr.Button("🔄 Refresh", variant="secondary", scale=0)

    # Latest metrics (NO light)
    with gr.Row():
        m_temp = gr.HTML()
        m_hum = gr.HTML()
        m_soil = gr.HTML()

    history = gr.Dataframe(
        headers=["timestamp", "temp", "humidity", "soil"],
        datatype=["str", "number", "number", "number"],
        interactive=False,
        row_count=10,
        col_count=(4, "fixed"),
        label="Latest history (most recent first)",
    )

    def _metric_html(label: str, value):
        v = "N/A" if value is None else value
        return f"""
        <div class="metric">
          <div class="label">{label}</div>
          <div class="value">{v}</div>
        </div>
        """

    def load(u, chosen_pid):
        username = _get_username(u)

        if not username:
            return (
                "⚠️ Please login to view sensors data.",
                gr.update(choices=[], value=None),
                _metric_html("Temp (°C)", None),
                _metric_html("Humidity (%)", None),
                _metric_html("Soil", None),
                [],
            )

        plants = list_plants(username) or []
        choices = []
        for p in plants:
            pid = p.get("plant_id") or p.get("id")
            if pid:
                choices.append((_plant_label(p), pid))

        if not choices:
            return (
                f"🌱 No plants found. Add a plant in **Upload**, then come back.",
                gr.update(choices=[], value=None),
                _metric_html("Temp (°C)", None),
                _metric_html("Humidity (%)", None),
                _metric_html("Soil", None),
                [],
            )

        pid = chosen_pid or choices[0][1]

        # pull 1 fresh sample and store in Firestore
        sync_iot_data(pid)

        latest = get_latest_reading(pid)
        temp = latest.get("temp") if latest else None
        hum = latest.get("humidity") if latest else None
        soil = latest.get("soil") if latest else None

        hist = get_sensor_history(pid, limit=10) or []
        rows = []
        for r in hist:
            rows.append([
                r.get("timestamp"),
                r.get("temp"),
                r.get("humidity"),
                r.get("soil"),
            ])

        return (
            f"✅ Showing sensors for selected plant",
            gr.update(choices=choices, value=pid),
            _metric_html("Temp (°C)", temp),
            _metric_html("Humidity (%)", hum),
            _metric_html("Soil", soil),
            rows,
        )

    # Reactive: update when dropdown selection changes
    plant_dd.change(
        fn=load,
        inputs=[user_state, plant_dd],
        outputs=[info, plant_dd, m_temp, m_hum, m_soil, history],
    )

    # Manual refresh button (for syncing new IoT data)
    refresh_btn.click(
        fn=load,
        inputs=[user_state, plant_dd],
        outputs=[info, plant_dd, m_temp, m_hum, m_soil, history],
    )

    # Return components for external wiring (auto-load on navigation)
    return refresh_btn, load, [user_state, plant_dd], [info, plant_dd, m_temp, m_hum, m_soil, history]
