# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import numpy as np


class DepthEstimator:
    def __init__(self, model_name="midas_small", device="auto", logger=None):
        self.model_name = model_name
        self.device = device
        self.logger = logger
        self.model = None
        self.transform = None
        self._load()

    def _log(self, level, msg, *args):
        if self.logger:
            getattr(self.logger, level)(msg, *args)

    def _load(self):
        try:
            import torch
            device = self.device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            self.device = device

            self.model = torch.hub.load("intel-isl/MiDaS", self.model_name)
            self.model.to(self.device)
            self.model.eval()

            transforms = torch.hub.load("intel-isl/MiDaS", "transforms")
            if self.model_name in ("DPT_Large", "DPT_Hybrid"):
                self.transform = transforms.dpt_transform
            else:
                self.transform = transforms.small_transform

            self._log("info", "Depth model loaded: %s on %s", self.model_name, self.device)
        except Exception as exc:
            self.model = None
            self.transform = None
            self._log("warning", "Depth model unavailable, using stub depth. %s", exc)

    def predict(self, frame_bgr):
        if self.model is None or self.transform is None:
            h, w = frame_bgr.shape[:2]
            return np.ones((h, w), dtype=np.float32)

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
        dmin, dmax = float(depth.min()), float(depth.max())
        if dmax - dmin > 1e-6:
            depth = (depth - dmin) / (dmax - dmin)
        else:
            depth = np.ones_like(depth, dtype=np.float32)
        return depth
