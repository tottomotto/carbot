"""YOLO runner stub using Ultralytics for basic detections (body style, car presence).

This is a lightweight wrapper; it attempts to load a small pre-trained model.
We keep it optional so the POC runs even if Ultralytics isn't installed.
"""
from typing import Dict, Optional


def infer_body_style(image_path: str) -> Dict[str, Optional[float]]:
    """Return a simple body-style guess with confidence.

    If Ultralytics is available, run a small detection and map classes to
    coarse body styles; otherwise return unknown.
    """
    try:
        from ultralytics import YOLO  # type: ignore
        import cv2

        # Use YOLO11m by default (can be swapped to a car-specific model later)
        model = YOLO("yolo11m.pt")

        results = model.predict(image_path, imgsz=640, conf=0.25, verbose=False)
        # Very naive mapping: presence of 'car'/'truck'/'bus' → sedan/suv hints
        # In production, use a fine-tuned classifier or detection head for body styles
        best_conf = 0.0
        body_style = None
        for r in results:
            for b in r.boxes:
                cls_id = int(b.cls.item())
                conf = float(b.conf.item())
                name = r.names.get(cls_id, "")
                if name in {"car", "truck", "bus", "van"} and conf > best_conf:
                    best_conf = conf
                    if name == "car":
                        body_style = "sedan"
                    elif name in {"truck", "van"}:
                        body_style = "suv"
                    elif name == "bus":
                        body_style = "suv"

        if body_style:
            return {"body_style": body_style, "confidence": round(best_conf, 3)}
        return {"body_style": None, "confidence": 0.0}
    except Exception:
        return {"body_style": None, "confidence": 0.0}


