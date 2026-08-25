import math

import cv2
import numpy as np


class VisualOdometry:
    """Lightweight monocular visual odometry with optional metric depth scaling."""

    def __init__(self, fx, fy, cx, cy):
        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = float(cx)
        self.cy = float(cy)
        self.K = np.array(
            [[self.fx, 0.0, self.cx], [0.0, self.fy, self.cy], [0.0, 0.0, 1.0]],
            dtype=np.float32,
        )
        self.orb = cv2.ORB_create(2000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.prev_kp = None
        self.prev_des = None
        self.prev_gray = None
        self.pose = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def update(self, frame_bgr, depth_map=None, require_metric_depth=False):
        """
        Update the planar pose estimate.

        `depth_map` must already be in the desired translation unit. When
        `require_metric_depth=True`, translation is not integrated unless a
        finite positive scale can be estimated from that depth map. This keeps
        a previously metric trajectory from being contaminated by arbitrary
        monocular unit translations during depth dropouts.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        kp, des = self.orb.detectAndCompute(gray, None)
        if des is None or self.prev_des is None:
            self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
            return self.pose.copy(), None

        matches = self.bf.match(self.prev_des, des)
        if len(matches) < 20:
            self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
            return self.pose.copy(), None

        pts_prev = np.float32([self.prev_kp[m.queryIdx].pt for m in matches])
        pts_curr = np.float32([kp[m.trainIdx].pt for m in matches])

        essential, _ = cv2.findEssentialMat(
            pts_prev,
            pts_curr,
            self.K,
            method=cv2.RANSAC,
            prob=0.999,
            threshold=1.0,
        )
        if essential is None:
            self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
            return self.pose.copy(), None

        _, rotation, translation, _ = cv2.recoverPose(essential, pts_prev, pts_curr, self.K)
        scale = self._estimate_scale(depth_map, pts_curr, translation) if depth_map is not None else None

        if scale is None and require_metric_depth:
            dx = 0.0
            dy = 0.0
        else:
            applied_scale = 1.0 if scale is None else scale
            dx, dy = self._translation_to_xy(translation, applied_scale)

        self.pose[0] += dx
        self.pose[1] += dy
        self.pose[2] += self._rotation_to_yaw(rotation)

        self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
        return self.pose.copy(), scale

    def _estimate_scale(self, depth_map, pts_curr, translation):
        depths = []
        height, width = depth_map.shape[:2]
        for u, v in pts_curr.astype(int):
            if 0 <= v < height and 0 <= u < width:
                value = float(depth_map[v, u])
                if np.isfinite(value) and value > 0:
                    depths.append(value)
        if not depths:
            return None

        median_depth = float(np.median(depths))
        translation_norm = float(np.linalg.norm(translation))
        if not np.isfinite(median_depth) or median_depth <= 0 or translation_norm <= 1e-6:
            return None
        return median_depth / translation_norm

    @staticmethod
    def _rotation_to_yaw(rotation):
        return float(math.atan2(rotation[1, 0], rotation[0, 0]))

    @staticmethod
    def _translation_to_xy(translation, scale):
        scaled = translation.flatten() * float(scale)
        return float(scaled[0]), float(scaled[2])
