import gradio as gr

from plants_manager import count_plants
from ui.plants_ui import plants_screen
from ui.sensors_ui import sensors_screen
from ui.search_ui import search_screen
from ui.upload_ui import upload_screen
from ui.dashboard_ui import dashboard_screen
from ui.auth_ui import auth_screen

CSS = r"""
:root{
  --bg: #f6faf6;
  --topbar: #eaf7ea;
  --border: #cfe8cf;
  --text: #0f172a;
  --muted: #475569;

  --btn-bg: #bfecc9;
  --btn-bg-hover: #a9e6b8;
  --btn-text: #0b2a16;
}

.gradio-container{
  max-width: 100% !important;
  width: 100% !important;
  padding: 0 !important;
}

html, body, .gradio-container {
  background: var(--bg) !important;
  color: var(--text) !important;
}

.gradio-container p,
.gradio-container .prose p,
.gradio-container .markdown p,
.gradio-container .prose,
.gradio-container .markdown {
  color: #334155 !important;
}

.gradio-container h1, .gradio-container h2, .gradio-container h3, .gradio-container h4 {
  color: #0f172a !important;
}

/* Topbar full width */
#topbar{
  background: var(--topbar) !important;
  border-bottom: 1px solid var(--border) !important;
  padding: 14px 18px !important;
  margin: 0 !important;
  border-radius: 0 !important;
  align-items: center !important;
  width: 100vw !important;
  margin-left: calc(50% - 50vw) !important;
  margin-right: calc(50% - 50vw) !important;
}

#brandWrap{ display:flex; align-items:center; gap:10px; }
#brandIcon{ font-size: 26px; }
#brandText{ font-size: 34px; font-weight: 900; letter-spacing: -0.02em; }
#brandText .garden{ color:#15803d; }

.navrow{
  display:flex !important;
  flex-wrap: nowrap !important;
  gap: 10px !important;
  overflow-x: auto !important;
  padding-bottom: 6px !important;
  justify-content: flex-end !important;
  align-items: center !important;
}
.navrow > *{ flex: 0 0 auto !important; }

.navbtn, button.navbtn, .navbtn > button{
  min-width: 90px !important;
  height: 42px !important;
  padding: 10px 14px !important;
  font-size: 0.98rem !important;
  border-radius: 999px !important;
  border: none !important;
  background: var(--btn-bg) !important;
  color: var(--btn-text) !important;
  font-weight: 800 !important;
  white-space: nowrap !important;
  box-shadow: 0 8px 18px rgba(16, 185, 129, 0.12) !important;
}
.navbtn:hover, button.navbtn:hover, .navbtn > button:hover{
  background: var(--btn-bg-hover) !important;
}

#pagePad{ padding: 18px 18px 0 !important; }

.card{
  background:#fff !important;
  border:1px solid #e5e7eb !important;
  border-radius:16px !important;
  padding:16px !important;
  box-shadow:0 10px 22px rgba(15,23,42,.06) !important;
}

.cardbtn, button.cardbtn, .cardbtn > button{
  width: 100% !important;
  text-align: left !important;
  border: 1px solid #e5e7eb !important;
  background: #fff !important;
  border-radius: 16px !important;
  padding: 16px !important;
  box-shadow: 0 10px 22px rgba(15,23,42,.06) !important;
  height: auto !important;
  white-space: normal !important;

  /* FORCE DARK TEXT */
  color: #0f172a !important;
  opacity: 1 !important;
}

.cardbtn *{
  color: #0f172a !important;
}

.cardbtn:hover, button.cardbtn:hover, .cardbtn > button:hover{
  background: #f8fafc !important;
}

.smallmuted{ color:#475569 !important; font-size: .95rem; }
.bigNum{ font-size: 1.7rem; font-weight: 900; color:#0f172a !important; }

.metric{
  background:#fff !important;
  border:1px solid #e5e7eb !important;
  border-radius:14px !important;
  padding:14px !important;
  box-shadow:0 8px 18px rgba(15,23,42,.06) !important;
  text-align: left;
}

.metric .label{
  font-size: .85rem;
  color:#475569 !important;
}

.metric .value{
  font-size: 1.4rem;
  font-weight: 900;
  color:#0f172a !important;
}

.gr-gallery .thumbnail-item,
.gr-gallery .thumbnail-item img{
  width: 180px !important;
  height: 180px !important;
  object-fit: cover !important;
  border-radius: 14px !important;
}

.gr-gallery .gallery{
  justify-content: flex-start !important;
  gap: 12px !important;
}
.resWrap{ display:flex; flex-direction:column; gap:12px; }

.resCard{ padding:14px !important; }

.resTitle{
  font-weight: 900;
  font-size: 1.05rem;
  color:#0f172a !important;
  margin-bottom: 6px;
  overflow-wrap:anywhere;
  word-break: break-word;
}

.resTitle a{
  color:#0f172a !important;
  text-decoration: none;
}

.resTitle a:hover{ text-decoration: underline; }

.resSnippet{
  color:#334155 !important;
  line-height: 1.35;
  margin-bottom: 8px;
  overflow-wrap:anywhere;
  word-break: break-word;
}

.resLink{
  font-size: .92rem;
  overflow-wrap:anywhere;
  word-break: break-word;
}

.resLink a{ color:#15803d !important; font-weight: 700; }
.resLink.muted{ color:#64748b !important; }




"""

def home_screen():
    with gr.Blocks(title="My Garden Care", css=CSS) as app:
        user_state = gr.State(value=None)

        # ---------- TOP BAR ----------
        with gr.Row(elem_id="topbar"):
            with gr.Column(scale=4, min_width=280):
                gr.HTML("""
                <div id="brandWrap">
                  <div id="brandIcon">🌿</div>
                  <div id="brandText">
                    <span class="garden">My Garden Care</span>
                  </div>
                </div>
                """)

            with gr.Row(scale=8, elem_classes=["navrow"]):
                btn_home = gr.Button("Home", elem_classes=["navbtn"])
                btn_sensors = gr.Button("Sensors", elem_classes=["navbtn"])
                btn_search = gr.Button("Search", elem_classes=["navbtn"])
                btn_dashboard = gr.Button("Plant Dashboard", elem_classes=["navbtn"])
                btn_upload = gr.Button("Upload a Photo", elem_classes=["navbtn"])
                btn_auth = gr.Button("Login/Register", elem_classes=["navbtn"])

        with gr.Column(elem_id="pagePad"):

            # ---------- PAGES ----------
            with gr.Column(visible=True) as home:
                gr.Markdown("## Overview")
                # invisible button overlay for click
                btn_open_plants = gr.Button("View My Plants", elem_classes=["cardbtn"])


                                # --- Fake metrics row (UI placeholder) ---
                with gr.Row():
                    gr.HTML("""
                    <div class="metric">
                      <div class="label">Alerts today</div>
                      <div class="value">1</div>
                    </div>
                    """)
                    gr.HTML("""
                    <div class="metric">
                      <div class="label">Avg soil moisture</div>
                      <div class="value">42%</div>
                    </div>
                    """)
                    gr.HTML("""
                    <div class="metric">
                      <div class="label">Last scan</div>
                      <div class="value">2h ago</div>
                    </div>
                    """)
                    gr.HTML("""
                    <div class="metric">
                      <div class="label">Garden score</div>
                      <div class="value">87</div>
                    </div>
                    """)


                gr.Markdown("### Quick actions")
                with gr.Row():
                    qa_sensors = gr.Button(
                        "🌱 Check sensors! View latest readings >",
                        elem_classes=["cardbtn"]
                    )
                    qa_upload = gr.Button(
                        "📷 Upload a new plant photo >",
                        elem_classes=["cardbtn"]
                    )

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

        # ---------- HELPERS ----------
        def _get_username(u):
            return u.strip() if isinstance(u, str) else ""

        def render_plants_card(u):
            username = _get_username(u)
            n = count_plants(username) if username else 0
            return (
                '<div class="card">'
                '<div class="smallmuted">My Plants</div>'
                f'<div class="bigNum">{n}</div>'
                '<div class="smallmuted">Click to view your plant gallery</div>'
                '</div>'
            )

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

        outputs = [home, plants, sensors, search, dashboard, upload, auth]

        # ---------- NAVIGATION ----------
        btn_home.click(lambda: go("home"), outputs=outputs)
        btn_sensors.click(lambda: go("sensors"), outputs=outputs)
        btn_search.click(lambda: go("search"), outputs=outputs)
        btn_dashboard.click(lambda: go("dashboard"), outputs=outputs)
        btn_upload.click(lambda: go("upload"), outputs=outputs)
        btn_auth.click(lambda: go("auth"), outputs=outputs)

        # Home cards / quick actions
        btn_open_plants.click(lambda: go("plants"), outputs=outputs)
        qa_sensors.click(lambda: go("sensors"), outputs=outputs)
        qa_upload.click(lambda: go("upload"), outputs=outputs)


    return app
