from __future__ import annotations
from typing import List, Tuple
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

MODEL_ID = "linkanjarad/mobilenet_v2_1.0_224-plant-disease-identification"

_processor = None
_model = None


#Load processor + model once
def _load_once() -> None:
    global _processor, _model
    if _processor is None or _model is None:
        _processor = AutoImageProcessor.from_pretrained(MODEL_ID)
        _model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
        _model.eval()


def predict_plant_disease(image: Image.Image, top_k: int = 5) -> List[Tuple[str, float]]:
    _load_once()

    if image is None:
        return []

    if image.mode != "RGB":
        image = image.convert("RGB")

    inputs = _processor(images=image, return_tensors="pt")

    with torch.no_grad():
        logits = _model(**inputs).logits
        probs = torch.softmax(logits, dim=-1)[0]

    k = min(int(top_k), probs.shape[-1])
    top = torch.topk(probs, k=k)

    id2label = _model.config.id2label or {}
    results: List[Tuple[str, float]] = []
    for score, idx in zip(top.values.tolist(), top.indices.tolist()):
        label = id2label.get(int(idx), str(int(idx)))
        results.append((label, float(score)))

    return results
