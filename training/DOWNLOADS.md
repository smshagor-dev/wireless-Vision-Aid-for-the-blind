# Dataset Downloads (Auto + Manual)

## Auto (no-login)
Run:
python training/auto_download.py

This downloads COCO 2017 train/val + annotations into:
- data/raw/coco2017

## Manual (login/license required)
These datasets require registration or license acceptance. Download manually, then place under `data/raw`:

- BDD100K (driving scenes, traffic signals)
  Place under: data/raw/bdd100k

- Cityscapes (urban scenes, poles/traffic lights)
  Place under: data/raw/cityscapes

- ADE20K (indoor scenes, wall/floor/window/stairs)
  Place under: data/raw/ade20k

- RDD2022 Road Damage (pothole)
  Place under: data/raw/rdd2022

- Open Images V7 (fan, cone, long-tail objects)
  Place under: data/raw/openimages

After manual download, we will run a merge/convert script to produce:
- data/custom_wvab/images/train|val
- data/custom_wvab/labels/train|val
