# Dataset and Model Downloads

## Runtime model provisioning

The large MiDaS depth weight is intentionally not committed to the source repository. After installing `requirements.txt`, provision it once while online:

```bash
python tools/download_models.py midas
```

The provisioner downloads the official MiDaS v2.1 small weight, verifies SHA256 `70d6b9c891758c67f974a6097fb0c608c7ee67fb81ac3e5588847d5596d56fca`, and prepares the Torch Hub source cache used by offline depth startup.

For weights only:

```bash
python tools/download_models.py midas --weights-only
```

The downloaded file is stored at `data/models/midas_v21_small_256.pt` and ignored by Git.

## Dataset downloads: automatic

```bash
python training/auto_download.py
```

This downloads COCO 2017 train/val + annotations into `data/raw/coco2017`.

## Dataset downloads: manual

These datasets require registration or license acceptance. Download manually, then place under `data/raw`:

- BDD100K: `data/raw/bdd100k`
- Cityscapes: `data/raw/cityscapes`
- ADE20K: `data/raw/ade20k`
- RDD2022 Road Damage: `data/raw/rdd2022`
- Open Images V7: `data/raw/openimages`

After download, use the merge/conversion utilities to produce:

- `data/custom_wvab/images/train|val`
- `data/custom_wvab/labels/train|val`
