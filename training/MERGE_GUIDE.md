# WVAB Dataset Merge/Convert

## Step 1: Auto-download COCO
python training/auto_download.py

## Step 2: Convert COCO -> YOLO (subset of WVAB classes)
python training/merge_convert_coco.py

This writes images/labels into:
- data/custom_wvab/images/train|val
- data/custom_wvab/labels/train|val

## Notes
- COCO does not include: fan, door, crosswalk, curb, pothole, road_cone, wall, floor, window, stairs.
- For those, add Open Images / Cityscapes / ADE20K / RDD2022 and we will merge next.

## Optional: Limit for quick test
python training/merge_convert_coco.py --limit 200
