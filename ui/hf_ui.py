from __future__ import annotations

from typing import List, Tuple
from PIL import Image
import gradio as gr

from hf_plant_disease_service import predict_plant_disease


def _ui_predict(image: Image.Image, top_k: int):
    preds = predict_plant_disease(image, top_k=top_k)
    if not preds:
        return "Please upload an image.", []

    top_label, top_score = preds[0]
    table = [[lbl, f"{score*100:.2f}%"] for (lbl, score) in preds]
    return f"{top_label} ({top_score*100:.2f}%)", table


def build_hf_tab():
    """
    Call this inside your main gradio Blocks app to add the Plant Disease feature.
    """
    with gr.Tab("Plant Disease (HF)"):
        gr.Markdown(
            "### 🌿 Plant Disease Detection\n"
            "Upload a leaf image and get top predictions"
        )

        img = gr.Image(type="pil", label="Upload plant leaf image")
        k = gr.Slider(1, 10, value=5, step=1, label="Top-K results")
        btn = gr.Button("Analyze")

        out_top = gr.Textbox(label="Top prediction")
        out_table = gr.Dataframe(headers=["Label", "Confidence"], interactive=False, label="Top-K results")

        btn.click(_ui_predict, inputs=[img, k], outputs=[out_top, out_table])
