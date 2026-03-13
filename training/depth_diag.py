import os
import sys
import traceback

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def main():
    print("== WVAB Depth Diagnostics ==")
    try:
        import torch

        print("torch", torch.__version__)
        print("cuda_available", torch.cuda.is_available())
    except Exception as exc:
        print("torch_import_error", exc)
        return 1

    try:
        from perception.depth_estimator import DepthEstimator

        est = DepthEstimator(model_name="midas_small", device="auto", logger=None, trust_repo=True)
        diag = est.diagnostics()
        print("depth_ready", diag.get("ready"))
        print("depth_model", diag.get("model_name"))
        print("depth_device", diag.get("device"))
        print("depth_debug", diag.get("debug"))
        if diag.get("error"):
            print("depth_error", diag.get("error"))
            return 2
    except Exception as exc:
        print("depth_init_error", exc)
        traceback.print_exc()
        return 3

    print("Depth model loaded successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
