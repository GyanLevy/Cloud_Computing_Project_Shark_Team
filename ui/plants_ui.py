import gradio as gr
from plants_manager import list_plants, delete_plant


def _get_username(user_state):
    return user_state.strip() if isinstance(user_state, str) else ""


PLANTS_CSS = r"""
/* Make Gallery look like a clean grid of cards */
#plants_grid .grid-wrap,
#plants_grid .gallery{
  gap: 12px !important;
}

#plants_grid .thumbnail-item,
#plants_grid .gallery-item{
  border-radius: 14px !important;
  overflow: hidden !important;
  border: 1px solid rgba(148, 163, 184, 0.35) !important;
  box-shadow: 0 6px 18px rgba(0,0,0,0.18) !important;
}

/* image */
#plants_grid img{
  width: 100% !important;
  height: 170px !important;
  object-fit: cover !important;
  display: block !important;
}

/* caption (plant name) */
#plants_grid figcaption,
#plants_grid .caption{
  padding: 10px 12px !important;
  font-weight: 800 !important;
  line-height: 1.1 !important;
}

/* hide the big empty label spacing sometimes */
#plants_grid .label{
  margin-bottom: 0 !important;
}
"""


def plants_screen(user_state: gr.State):
    # Inject small CSS only for this screen
    gr.HTML(f"<style>{PLANTS_CSS}</style>")

    gr.Markdown("## 🌿 My Plants")
    info = gr.Markdown()
    refresh_btn = gr.Button("Load Plants", variant="primary")

    empty_state = gr.HTML()

    # Keep Gallery (so local paths still work), but style it to look like cards/grid
    gallery = gr.Gallery(
        label="",
        columns=4,
        rows=2,
        height=420,
        object_fit="cover",
        allow_preview=False,
        show_label=False,
        visible=False,
        elem_id="plants_grid",
    )

    with gr.Row(visible=False) as delete_row:
        plant_to_delete = gr.Dropdown(label="Delete plant (by name)", choices=[], value=None)
        del_btn = gr.Button("Delete", variant="stop")

    del_status = gr.Markdown()

    def load(u):
        username = _get_username(u)

        # --- Not logged in ---
        if not username:
            return (
                "⚠️ Please login to see your plants.",
                '<div class="card"><h3>🔒 Login required</h3><p>Please login, then press <b>Load Plants</b>.</p></div>',
                gr.update(visible=False, value=[]),
                gr.update(visible=False),
                gr.update(choices=[], value=None),
                ""
            )

        plants = list_plants(username) or []

        # --- Logged in but no plants ---
        if not plants:
            return (
                f"Logged in as **{username}**",
                '<div class="card"><h3>🌱 No plants yet</h3><p>Go to <b>Upload</b> to add your first plant, then come back and press <b>Load Plants</b>.</p></div>',
                gr.update(visible=False, value=[]),
                gr.update(visible=False),
                gr.update(choices=[], value=None),
                ""
            )

        # --- Have plants ---
        items = []
        delete_choices = []

        for p in plants:
            pid = p.get("plant_id") or p.get("id") or ""
            name = (p.get("name") or p.get("species") or "").strip() or "Plant"
            img = p.get("image_url") or p.get("image_path")

            # Gallery can display local server paths OR real URLs
            if img:
                items.append((img, name))

            # Show NAME to user, but keep pid as value
            if pid:
                delete_choices.append((name, pid))

        if not items:
            return (
                f"Logged in as **{username}**",
                '<div class="card"><h3>🖼️ No images found</h3><p>Your plants exist, but they don’t have images/URLs yet.</p></div>',
                gr.update(visible=False, value=[]),
                gr.update(visible=True),
                gr.update(choices=delete_choices, value=None),
                ""
            )

        return (
            f"✅ Loaded **{len(items)}** plants.",
            "",
            gr.update(visible=True, value=items),
            gr.update(visible=True),
            gr.update(choices=delete_choices, value=None),
            ""
        )

    def on_delete(u, pid):
        username = _get_username(u)
        if not username:
            return load(u)

        if not pid:
            msg, empty_html, gal_upd, delrow_upd, dd_upd, _ = load(u)
            return msg, empty_html, gal_upd, delrow_upd, dd_upd, "⚠️ Please select a plant to delete."

        ok, msg_del = delete_plant(username, pid)
        msg, empty_html, gal_upd, delrow_upd, dd_upd, _ = load(u)
        return msg, empty_html, gal_upd, delrow_upd, dd_upd, ("✅ Deleted." if ok else f"❌ {msg_del}")

    refresh_btn.click(
        fn=load,
        inputs=[user_state],
        outputs=[info, empty_state, gallery, delete_row, plant_to_delete, del_status]
    )

    del_btn.click(
        fn=on_delete,
        inputs=[user_state, plant_to_delete],
        outputs=[info, empty_state, gallery, delete_row, plant_to_delete, del_status]
    )
