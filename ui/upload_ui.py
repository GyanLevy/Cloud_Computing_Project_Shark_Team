import gradio as gr
from plants_manager import add_plant_with_image


def _get_username(user_state):
    """Extract username string from Gradio State (or empty string)."""
    return user_state.strip() if isinstance(user_state, str) else ""


def upload_screen(user_state: gr.State):
    """Upload UI: collects image + metadata and delegates saving to plants_manager."""
    gr.Markdown("## 📷 Upload Plant Image")

    with gr.Row():

        with gr.Column(scale=6):
            image_in = gr.Image(label="Upload a plant photo", type="pil")


        with gr.Column(scale=6):
            plant_name = gr.Textbox(label="Plant name", placeholder="e.g., My Basil")
            species = gr.Textbox(label="Species (optional)", placeholder="e.g., Basil / Monstera / Cactus")
            save_btn = gr.Button("Save to My Plants", variant="primary")
            status = gr.Markdown("")

    def on_save(u, img, name, sp, progress=gr.Progress(track_tqdm=True)):
        username = _get_username(u)

        if not username:
            return "⚠️ Please login first.", gr.update(), gr.update(), gr.update()
        if img is None:
            return "⚠️ Please upload an image.", gr.update(), gr.update(), gr.update()
        if not str(name).strip():
            return "⚠️ Please enter plant name.", gr.update(), gr.update(), gr.update()

        # Create a callback wrapper for Gradio progress
        def gradio_callback(pct, desc=""):
            progress(pct, desc=desc)

        ok, plant_id_or_err = add_plant_with_image(
            username=username,
            name=name,
            species=sp or "",
            pil_image=img,
            progress_callback=gradio_callback,
        )

        if not ok:
            return f"❌ {plant_id_or_err}", gr.update(), gr.update(), gr.update()

        # Success: clear the form for next upload
        return f"✅ Saved plant **{name}** (id: `{plant_id_or_err}`)", None, "", ""

    save_btn.click(
        fn=on_save,
        inputs=[user_state, image_in, plant_name, species],
        outputs=[status, image_in, plant_name, species],
    )

