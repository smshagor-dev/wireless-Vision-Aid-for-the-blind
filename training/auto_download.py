import argparse
import os
import sys
import shutil
import zipfile
from urllib.request import urlretrieve

COCO_BASE = "http://images.cocodataset.org"
COCO_FILES = {
    "annotations_trainval2017.zip": f"{COCO_BASE}/annotations/annotations_trainval2017.zip",
    "train2017.zip": f"{COCO_BASE}/zips/train2017.zip",
    "val2017.zip": f"{COCO_BASE}/zips/val2017.zip",
}


def _download(url, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        print(f"[skip] exists: {dst}")
        return
    print(f"[down] {url}")
    urlretrieve(url, dst)
    print(f"[ok ] {dst}")


def _unzip(path, out_dir):
    print(f"[unzip] {path} -> {out_dir}")
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(path, "r") as zf:
        zf.extractall(out_dir)


def download_coco(raw_dir, unzip):
    coco_dir = os.path.join(raw_dir, "coco2017")
    os.makedirs(coco_dir, exist_ok=True)
    for name, url in COCO_FILES.items():
        dst = os.path.join(coco_dir, name)
        _download(url, dst)
        if unzip:
            _unzip(dst, coco_dir)


def main():
    ap = argparse.ArgumentParser(description="Auto-download public datasets (no-login only)")
    ap.add_argument("--raw-dir", default=os.path.join("data", "raw"), help="Raw dataset cache dir")
    ap.add_argument("--no-unzip", action="store_true", help="Skip unzip (keep zips only)")
    args = ap.parse_args()

    raw_dir = args.raw_dir
    unzip = not args.no_unzip

    print("== WVAB Auto Download ==")
    print("This will download COCO 2017 train/val + annotations (public, no-login).")
    print("Other datasets (BDD100K/Cityscapes/ADE20K/RDD/OpenImages) require registration or large tooling.")

    download_coco(raw_dir, unzip)

    print("\nDone.")
    print("COCO path:", os.path.join(raw_dir, "coco2017"))
    print("Next: run a conversion script to filter your 27 classes into YOLO format.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
