#!/usr/bin/env python3
import argparse
import hashlib
import os
from pathlib import Path
from urllib.request import Request, urlopen


MIDAS_URL = "https://github.com/isl-org/MiDaS/releases/download/v2_1/midas_v21_small_256.pt"
MIDAS_SHA256 = "70d6b9c891758c67f974a6097fb0c608c7ee67fb81ac3e5588847d5596d56fca"
MIDAS_RELATIVE_PATH = Path("data/models/midas_v21_small_256.pt")


def sha256_file(path, chunk_size=1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def download_verified(url, destination, expected_sha256):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destination.with_suffix(destination.suffix + ".part")
    request = Request(url, headers={"User-Agent": "WVAB-model-provisioner/1.0"})
    digest = hashlib.sha256()
    try:
        with urlopen(request, timeout=60) as response, open(tmp_path, "wb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
        actual = digest.hexdigest()
        if actual.lower() != expected_sha256.lower():
            raise RuntimeError(
                f"checksum mismatch for {destination.name}: expected {expected_sha256}, got {actual}"
            )
        os.replace(tmp_path, destination)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return destination


def prepare_midas_hub_cache():
    try:
        import torch
    except Exception as exc:
        raise RuntimeError("PyTorch must be installed before preparing the MiDaS hub cache") from exc
    # This downloads/caches the official MiDaS source needed to instantiate the
    # legacy v2.1 small model later while WVAB is offline.
    torch.hub.load("isl-org/MiDaS", "transforms", source="github", trust_repo=True)


def provision_midas(project_root, prepare_hub=True):
    destination = Path(project_root) / MIDAS_RELATIVE_PATH
    if destination.exists() and sha256_file(destination) == MIDAS_SHA256:
        print(f"MiDaS weights already verified: {destination}")
    else:
        print(f"Downloading MiDaS v2.1 small weights to {destination}")
        download_verified(MIDAS_URL, destination, MIDAS_SHA256)
        print(f"Verified SHA256: {MIDAS_SHA256}")
    if prepare_hub:
        print("Preparing MiDaS Torch Hub source cache for offline depth startup")
        prepare_midas_hub_cache()
    print("MiDaS provisioning complete")


def main():
    parser = argparse.ArgumentParser(description="Provision WVAB runtime model assets with integrity checks")
    parser.add_argument("model", choices=["midas"], help="Model asset to provision")
    parser.add_argument(
        "--weights-only",
        action="store_true",
        help="Download/verify weights without preparing the Torch Hub source cache",
    )
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parent.parent
    if args.model == "midas":
        provision_midas(project_root, prepare_hub=not args.weights_only)


if __name__ == "__main__":
    main()
