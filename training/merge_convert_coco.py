import argparse
import json
import os
import shutil
from pathlib import Path


TARGET_CLASSES = [
    "person",
    "car",
    "bus",
    "truck",
    "bicycle",
    "motorcycle",
    "traffic_light",
    "stop_sign",
    "crosswalk",
    "curb",
    "pothole",
    "pole",
    "road_cone",
    "fan",
    "door",
    "chair",
    "table",
    "bed",
    "sofa",
    "bottle",
    "cup",
    "laptop",
    "tv",
    "stairs",
    "window",
    "wall",
    "floor",
]

# COCO category name -> WVAB class name
COCO_TO_WVAB = {
    "person": "person",
    "car": "car",
    "bus": "bus",
    "truck": "truck",
    "bicycle": "bicycle",
    "motorcycle": "motorcycle",
    "traffic light": "traffic_light",
    "stop sign": "stop_sign",
    "chair": "chair",
    "bed": "bed",
    "couch": "sofa",
    "dining table": "table",
    "bottle": "bottle",
    "cup": "cup",
    "laptop": "laptop",
    "tv": "tv",
}


def _load_coco(ann_path):
    with open(ann_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_yolo_label(out_path, items):
    if not items:
        return
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for cls_id, xc, yc, w, h in items:
            f.write(f"{cls_id} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}\n")


def _convert_split(
    coco_root,
    ann_file,
    image_subdir,
    out_images_dir,
    out_labels_dir,
    class_to_id,
    limit,
):
    data = _load_coco(ann_file)

    coco_cat_id_to_name = {c["id"]: c["name"] for c in data["categories"]}
    target_cat_ids = {
        cid for cid, name in coco_cat_id_to_name.items() if name in COCO_TO_WVAB
    }

    images = {img["id"]: img for img in data["images"]}
    anns_by_img = {}
    for ann in data["annotations"]:
        if ann.get("iscrowd", 0):
            continue
        if ann["category_id"] not in target_cat_ids:
            continue
        anns_by_img.setdefault(ann["image_id"], []).append(ann)

    copied = 0
    for image_id, anns in anns_by_img.items():
        if limit and copied >= limit:
            break
        img = images.get(image_id)
        if not img:
            continue
        width = img["width"]
        height = img["height"]
        if width <= 0 or height <= 0:
            continue

        label_items = []
        for ann in anns:
            coco_name = coco_cat_id_to_name.get(ann["category_id"], "")
            wvab_name = COCO_TO_WVAB.get(coco_name)
            if not wvab_name:
                continue
            cls_id = class_to_id[wvab_name]
            x, y, w, h = ann["bbox"]
            if w <= 1 or h <= 1:
                continue
            xc = (x + w / 2.0) / width
            yc = (y + h / 2.0) / height
            wn = w / width
            hn = h / height
            if xc <= 0 or yc <= 0 or wn <= 0 or hn <= 0:
                continue
            if xc > 1 or yc > 1 or wn > 1 or hn > 1:
                continue
            label_items.append((cls_id, xc, yc, wn, hn))

        if not label_items:
            continue

        src_img = Path(coco_root) / image_subdir / img["file_name"]
        if not src_img.exists():
            continue
        dst_img = Path(out_images_dir) / img["file_name"]
        dst_img.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_img, dst_img)

        out_label = Path(out_labels_dir) / (Path(img["file_name"]).stem + ".txt")
        _write_yolo_label(out_label, label_items)

        copied += 1

    return copied


def main():
    ap = argparse.ArgumentParser(description="Convert COCO to WVAB YOLO format")
    ap.add_argument("--raw-dir", default=os.path.join("data", "raw"), help="Raw datasets root")
    ap.add_argument("--out-dir", default=os.path.join("data", "custom_wvab"), help="Output YOLO root")
    ap.add_argument("--limit", type=int, default=0, help="Limit images per split (0 = no limit)")
    args = ap.parse_args()

    raw_dir = args.raw_dir
    out_dir = args.out_dir
    limit = args.limit or 0

    class_to_id = {name: i for i, name in enumerate(TARGET_CLASSES)}

    coco_root = os.path.join(raw_dir, "coco2017")
    ann_train = os.path.join(coco_root, "annotations", "instances_train2017.json")
    ann_val = os.path.join(coco_root, "annotations", "instances_val2017.json")

    if not os.path.exists(ann_train) or not os.path.exists(ann_val):
        raise SystemExit(
            "COCO annotations not found. Run: python training/auto_download.py"
        )

    out_images_train = os.path.join(out_dir, "images", "train")
    out_images_val = os.path.join(out_dir, "images", "val")
    out_labels_train = os.path.join(out_dir, "labels", "train")
    out_labels_val = os.path.join(out_dir, "labels", "val")

    print("[COCO] Converting train...")
    n_train = _convert_split(
        coco_root,
        ann_train,
        "train2017",
        out_images_train,
        out_labels_train,
        class_to_id,
        limit,
    )
    print(f"[COCO] train images written: {n_train}")

    print("[COCO] Converting val...")
    n_val = _convert_split(
        coco_root,
        ann_val,
        "val2017",
        out_images_val,
        out_labels_val,
        class_to_id,
        limit,
    )
    print(f"[COCO] val images written: {n_val}")

    print("\nDone. Output:", out_dir)
    print("Note: COCO does NOT contain fan/door/crosswalk/curb/pothole/road_cone/wall/floor/etc.")
    print("Add those from other datasets later and re-run merge script.")


if __name__ == "__main__":
    main()
