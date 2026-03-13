# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

import os
from pathlib import Path

def configure_offline_env():
    """
    Enable offline behavior for Ultralytics unless explicitly disabled.
    Set WVAB_OFFLINE=0 to allow online downloads.
    """
    offline = os.environ.get("WVAB_OFFLINE", "1") != "0"
    if offline:
        os.environ.setdefault("ULTRALYTICS_OFFLINE", "1")
        os.environ.setdefault("WANDB_DISABLED", "true")
    return offline


def ensure_local_model(model_path, offline=True):
    """
    Resolve and validate the local model path.
    Supports YOLO .pt and exported OpenVINO directories (or .xml files).
    In offline mode, raise if missing.
    """
    prefer_openvino = os.environ.get("WVAB_OPENVINO", "0") != "0"
    path = Path(model_path)
    if not path.is_absolute():
        base_dir = Path(__file__).resolve().parent
        path = (base_dir / path).resolve()

    if prefer_openvino:
        if path.exists() and (path.is_dir() or path.suffix.lower() == ".xml"):
            return str(path)
        base_name = path.stem
        ov_dir = path.with_name(f"{base_name}_openvino_model")
        if ov_dir.exists():
            return str(ov_dir)

    if path.exists():
        return str(path)

    if offline:
        raise FileNotFoundError(
            "Offline mode: model not found at "
            f"{path}. Provide a local YOLO .pt file (e.g., yolov8n.pt) "
            "or an OpenVINO export directory (e.g., yolov8n_openvino_model)."
        )
    return model_path
