# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import os
import importlib.util

from ultralytics import YOLO


def export_tensorrt(model_path: str):
    model = YOLO(model_path)
    model.export(format="engine")


def export_openvino(model_path: str):
    model = YOLO(model_path)
    model.export(format="openvino")


def main():
    model_path = os.environ.get("WVAB_MODEL", "yolov8n.pt")
    export_trt = os.environ.get("WVAB_EXPORT_TRT", "auto").strip().lower()
    if export_trt in ("1", "true", "yes", "on", "auto"):
        if importlib.util.find_spec("tensorrt") is not None or export_trt != "auto":
            export_tensorrt(model_path)
    export_openvino(model_path)


if __name__ == "__main__":
    main()
