
import gradio as gr
from plants_manager import list_plants, delete_plant


def _get_username(user_state):
    # Helper: Extract username from the shared user_state.
    # Args:
    #     user_state: expected to be a string username or None.
    # Returns:
    #     str: username if logged-in, else "".
    return user_state.strip() if isinstance(user_state, str) else ""


def plants_screen(user_state: gr.State):
  #   Plants gallery screen.
  #   The screen shows:
  #   - Gallery of plant images (previewable)
  #   - A delete dropdown + delete button (only visible when data exists)
  #   Args:
  #       user_state (gr.State): shared state holding username string or None.
  #   Returns:
  #       tuple:
  #           (refresh_btn, load_fn, inputs_list, outputs_list)

    gr.Markdown("## 🌿 My Plants")
    gr.Markdown("*Click on any plant image to view it in full size.*")
    info = gr.Markdown()
    # refresh_btn = gr.Button("Load Plants", variant="primary")
    # Manual fallback. We hide it visually by default (scale=0),
    # but keep it for resilience/debugging.
    refresh_btn = gr.Button("Load plants", variant="secondary", scale=0)

    empty_state = gr.HTML()

    # Elegant grid gallery with preview support
    gallery = gr.Gallery(
        label="",
        columns=3,
        rows=2,
        height=350,
        object_fit="scale-down",
        allow_preview=True,
        preview=True,
        show_label=False,
        visible=False,
    )

    with gr.Row(visible=False) as delete_row:
        plant_to_delete = gr.Dropdown(label="Delete plant (by name)", choices=[], value=None)
        del_btn = gr.Button("Delete", variant="stop")

    del_status = gr.Markdown()

    def load(u):
      #   Load plants for current user:
      #   - If not logged-in -> show 'login required'
      #   - If no plants -> show empty state
      #   - Else -> fill gallery + delete dropdown

        username = _get_username(u)

        # --- Not logged in ---
        if not username:
            return (
                "⚠️ Please login to see your plants.",
                '<div class="card"><h3>🔒 Login required</h3><p>Please login.</p></div>',
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
      #   Delete selected plant (by id), then reload UI state.

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
    
    # Return wiring for auto-load on navigation
    return refresh_btn, load, [user_state], [info, empty_state, gallery, delete_row, plant_to_delete, del_status]

