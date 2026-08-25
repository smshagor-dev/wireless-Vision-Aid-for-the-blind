import os
import sys
import numpy as np


class DepthEstimator:
    def __init__(self, model_name="MiDaS_small", device="auto", logger=None, trust_repo=True):
        self.model_name = model_name
        self.device = device
        self.logger = logger
        self.trust_repo = trust_repo
        self.model = None
        self.transform = None
        self.last_error = None
        self.debug = {}
        self._load()

    def _log(self, level, msg, *args):
        if self.logger:
            getattr(self.logger, level)(msg, *args)

    @staticmethod
    def _find_local_hub_repo():
        cache_root = os.path.join(os.path.expanduser("~"), ".cache", "torch", "hub")
        candidates = [
            os.path.join(cache_root, "isl-org_MiDaS_master"),
            os.path.join(cache_root, "intel-isl_MiDaS_master"),
        ]
        return next((path for path in candidates if os.path.isdir(path)), None), candidates

    def _load(self):
        try:
            import importlib.util
            import torch

            name_map = {
                "midas_small": "MiDaS_small",
                "midas": "MiDaS",
                "dpt_hybrid": "DPT_Hybrid",
                "dpt_large": "DPT_Large",
            }
            self.model_name = name_map.get(str(self.model_name).strip().lower(), self.model_name)
            if self.device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"

            offline = os.environ.get("WVAB_OFFLINE", "1").strip() != "0"
            weights_path = os.environ.get("WVAB_MIDAS_WEIGHTS", "").strip()
            if not weights_path:
                repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                candidate = os.path.join(repo_root, "data", "models", "midas_v21_small_256.pt")
                if os.path.exists(candidate):
                    weights_path = candidate

            local_repo, cache_candidates = self._find_local_hub_repo()
            self.debug = {
                "weights_path": weights_path or None,
                "hub_cache_candidates": cache_candidates,
                "local_repo": local_repo,
                "offline": offline,
            }

            if offline and not weights_path:
                raise FileNotFoundError(
                    "MiDaS weights are not provisioned. Run 'python tools/download_models.py midas' while online."
                )
            if offline and not local_repo:
                raise FileNotFoundError(
                    "MiDaS Torch Hub source cache is missing. Run 'python tools/download_models.py midas' while online."
                )

            repo_ref = local_repo or "isl-org/MiDaS"
            repo_source = "local" if local_repo else "github"

            if weights_path:
                if not os.path.exists(weights_path):
                    raise FileNotFoundError(f"MiDaS weights not found: {weights_path}")

                if local_repo:
                    if local_repo not in sys.path:
                        sys.path.insert(0, local_repo)
                    from midas.midas_net_custom import MidasNet_small
                    import timm
                    import torch.nn as nn

                    hubconf_path = os.path.join(local_repo, "hubconf.py")
                    spec = importlib.util.spec_from_file_location("midas_hubconf", hubconf_path)
                    if spec is None or spec.loader is None:
                        raise RuntimeError("Unable to load cached MiDaS hub configuration")
                    hubconf = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(hubconf)

                    if self.model_name == "MiDaS_small":
                        original_hub_load = torch.hub.load

                        def _hub_load_stub(repo_or_dir, model, *args, **kwargs):
                            if repo_or_dir == "rwightman/gen-efficientnet-pytorch" and model == "tf_efficientnet_lite3":
                                efficientnet = timm.create_model("tf_efficientnet_lite3", pretrained=False)
                                if not hasattr(efficientnet, "act1"):
                                    efficientnet.act1 = nn.Identity()
                                return efficientnet
                            return original_hub_load(repo_or_dir, model, *args, **kwargs)

                        torch.hub.load = _hub_load_stub
                        try:
                            self.model = MidasNet_small(
                                path=weights_path,
                                features=64,
                                backbone="efficientnet_lite3",
                                exportable=True,
                                non_negative=True,
                                blocks={"expand": True},
                            )
                        finally:
                            torch.hub.load = original_hub_load
                    else:
                        self.model = getattr(hubconf, self.model_name)(pretrained=False)
                        state = torch.load(weights_path, map_location=self.device)
                        if isinstance(state, dict) and "state_dict" in state:
                            state = state["state_dict"]
                        self.model.load_state_dict(state, strict=False)
                    transforms = hubconf.transforms()
                    self.debug["mode"] = "hubconf_local"
                else:
                    self.model = torch.hub.load(
                        repo_ref,
                        self.model_name,
                        pretrained=False,
                        source=repo_source,
                        trust_repo=self.trust_repo,
                    )
                    transforms = torch.hub.load(
                        repo_ref,
                        "transforms",
                        source=repo_source,
                        trust_repo=self.trust_repo,
                    )
                    state = torch.load(weights_path, map_location=self.device)
                    if isinstance(state, dict) and "state_dict" in state:
                        state = state["state_dict"]
                    self.model.load_state_dict(state, strict=False)
                    self.debug["mode"] = "torchhub_weights"
            else:
                self.model = torch.hub.load(
                    repo_ref,
                    self.model_name,
                    source=repo_source,
                    trust_repo=self.trust_repo,
                )
                transforms = torch.hub.load(
                    repo_ref,
                    "transforms",
                    source=repo_source,
                    trust_repo=self.trust_repo,
                )
                self.debug["mode"] = "torchhub_default"

            self.model.to(self.device)
            self.model.eval()
            if self.model_name in ("DPT_Large", "DPT_Hybrid"):
                self.transform = transforms.dpt_transform
            else:
                self.transform = transforms.small_transform
            self._log("info", "Depth model loaded: %s on %s", self.model_name, self.device)
        except Exception as exc:
            self.model = None
            self.transform = None
            message = str(exc)
            if "No module named" in message and "torch" in message:
                message = "PyTorch not installed. Install runtime dependencies to enable depth."
            elif "HTTPError" in message or "URLError" in message:
                message = "Model provisioning failed. Run tools/download_models.py while online."
            self.last_error = message
            self._log("warning", "Depth model unavailable; depth mapping disabled. %s", message)

    def diagnostics(self):
        return {
            "ready": self.model is not None and self.transform is not None,
            "model_name": self.model_name,
            "device": self.device,
            "weights": self.debug.get("weights_path") or os.environ.get("WVAB_MIDAS_WEIGHTS", "").strip() or None,
            "error": self.last_error,
            "debug": self.debug,
        }

    def predict(self, frame_bgr):
        if self.model is None or self.transform is None:
            return None

        import torch

        input_batch = self.transform(frame_bgr).to(self.device)
        with torch.no_grad():
            prediction = self.model(input_batch)
            prediction = torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=frame_bgr.shape[:2],
                mode="bicubic",
                align_corners=False,
            ).squeeze()
        depth = prediction.cpu().numpy().astype(np.float32)
        minimum, maximum = float(depth.min()), float(depth.max())
        if maximum - minimum > 1e-6:
            depth = (depth - minimum) / (maximum - minimum)
        else:
            depth = np.ones_like(depth, dtype=np.float32)
        return depth
