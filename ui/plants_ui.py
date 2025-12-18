import gradio as gr
from plants_manager import list_plants, delete_plant


def _get_username(user_state):
    return user_state.strip() if isinstance(user_state, str) else ""


def plants_screen(user_state: gr.State):
    gr.Markdown("## 🌿 My Plants")

    info = gr.Markdown()
    refresh_btn = gr.Button("Load Plants")

    empty_state = gr.HTML()
    gallery = gr.Gallery(
        label="Your plants",
        columns=4,
        rows=2,
        height=420,
        object_fit="cover",
        allow_preview=False,
        show_label=True,
        visible=False,
    )

    with gr.Row(visible=False) as delete_row:
        plant_to_delete = gr.Dropdown(label="Delete plant", choices=[], value=None)
        del_btn = gr.Button("Delete", variant="stop")

    del_status = gr.Markdown()

    def load(u):
        username = _get_username(u)

        # --- Not logged in ---
        if not username:
            return (
                " Please login to see your plants.",
                '<div class="card"><h3> Login required</h3><p>Please login, then press Load Plants.</p></div>',
                gr.update(visible=False, value=[]),
                gr.update(visible=False),
                gr.update(choices=[], value=None),
                ""
            )

        plants = list_plants(username)

        # --- Logged in but no plants ---
        if not plants:
            return (
                f"Logged in as {username}",
                '<div class="card"><h3>🌱 No plants yet</h3><p>Go to <b>Upload</b> to add your first plant (image + name), then come back and press Load Plants.</p></div>',
                gr.update(visible=False, value=[]),
                gr.update(visible=False),
                gr.update(choices=[], value=None),
                ""
            )

        # --- Have plants ---
        items = []
        ids = []
        for p in plants:
            pid = p.get("plant_id", "") or p.get("id", "")
            name = p.get("name") or p.get("species") or pid or "plant"
            img = p.get("image_url") or p.get("image_path")
            if img:
                items.append((img, name))
            if pid:
                ids.append(pid)

        
        if not items:
            return (
                f"Logged in as {username}",
                '<div class="card"><h3> No images found</h3><p>Your plants exist in the database, but they don’t have images yet. Add plants via Upload so images will appear here.</p></div>',
                gr.update(visible=False, value=[]),
                gr.update(visible=True),
                gr.update(choices=ids, value=None),
                ""
            )

        return (
            f"Loaded {len(items)} images.",
            "",  # empty_state hidden by empty HTML
            gr.update(visible=True, value=items),
            gr.update(visible=True),
            gr.update(choices=ids, value=None),
            ""
        )

    def on_delete(u, pid):
        username = _get_username(u)
        if not username:
            return load(u)

        if not pid:
            msg, empty_html, gal_upd, delrow_upd, dd_upd, _ = load(u)
            return msg, empty_html, gal_upd, delrow_upd, dd_upd, "Please select a plant to delete."

        ok, msg_del = delete_plant(username, pid)
        msg, empty_html, gal_upd, delrow_upd, dd_upd, _ = load(u)
        return msg, empty_html, gal_upd, delrow_upd, dd_upd, ("Deleted." if ok else f" {msg_del}")

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
