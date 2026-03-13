# WVAB Custom Dataset Guide

## Classes (27)
Road:
- person, car, bus, truck, bicycle, motorcycle, traffic_light, stop_sign, crosswalk, curb, pothole, pole, road_cone

Room:
- fan, door, chair, table, bed, sofa, bottle, cup, laptop, tv, stairs, window, wall, floor

## Folder Structure
- data/custom_wvab/images/train
- data/custom_wvab/images/val
- data/custom_wvab/labels/train
- data/custom_wvab/labels/val

## Label Format (YOLO)
Each image has a matching .txt label file with lines:
<class_id> <x_center> <y_center> <width> <height>
All normalized (0..1).

## Tips for Accuracy
- Use varied lighting, angles, distances, and backgrounds.
- Balance classes (avoid huge class imbalance).
- Include hard negatives (objects that look similar).
- Capture both indoor and outdoor scenes.

## Training
python training/train_custom.py
Default model is `yolov8x.pt` for best accuracy. If GPU memory is low, switch to `yolov8l.pt` or `yolov8m.pt` inside `training/train_custom.py`.

## Use Trained Model in GUI
After training, use the best model path (e.g. runs/wvab_custom/road_room_outside/weights/best.pt)
Run:
python camera_gui.py
and set WVAB_MODEL to your custom model path.
