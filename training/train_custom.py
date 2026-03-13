# WVAB Custom Training (YOLOv8)
# 1) Install: pip install ultralytics
# 2) Put images + labels in data/custom_wvab (YOLO format)
# 3) Run: python training/train_custom.py

from ultralytics import YOLO

DATA_YAML = "training/wvab_custom.yaml"
# Best accuracy (heavier): yolov8x.pt. If VRAM is limited, drop to yolov8l.pt or yolov8m.pt.
MODEL = "yolov8x.pt"
EPOCHS = 200
IMGSZ = 960
BATCH = 8

if __name__ == "__main__":
    model = YOLO(MODEL)
    model.train(
        data=DATA_YAML,
        epochs=EPOCHS,
        imgsz=IMGSZ,
        batch=BATCH,
        patience=20,
        save=True,
        project="runs/wvab_custom",
        name="road_room_outside",
    )
