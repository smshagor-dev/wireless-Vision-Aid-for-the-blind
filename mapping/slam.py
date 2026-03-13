# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import math
import numpy as np
import cv2


class VisualOdometry:
    """Lightweight monocular visual odometry."""

    def __init__(self, fx, fy, cx, cy):
        self.fx = float(fx)
        self.fy = float(fy)
        self.cx = float(cx)
        self.cy = float(cy)
        self.K = np.array([[self.fx, 0.0, self.cx],
                           [0.0, self.fy, self.cy],
                           [0.0, 0.0, 1.0]], dtype=np.float32)
        self.orb = cv2.ORB_create(2000)
        self.bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        self.prev_kp = None
        self.prev_des = None
        self.prev_gray = None
        self.pose = np.array([0.0, 0.0, 0.0], dtype=np.float32)

    def update(self, frame_bgr, depth_map=None):
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        kp, des = self.orb.detectAndCompute(gray, None)
        if des is None or self.prev_des is None:
            self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
            return self.pose.copy(), 0.0

        matches = self.bf.match(self.prev_des, des)
        if len(matches) < 20:
            self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
            return self.pose.copy(), 0.0

        pts_prev = np.float32([self.prev_kp[m.queryIdx].pt for m in matches])
        pts_curr = np.float32([kp[m.trainIdx].pt for m in matches])

        E, mask = cv2.findEssentialMat(pts_prev, pts_curr, self.K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
        if E is None:
            self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
            return self.pose.copy(), 0.0

        _, R, t, mask_pose = cv2.recoverPose(E, pts_prev, pts_curr, self.K)
        scale = 1.0
        if depth_map is not None:
            scale = self._estimate_scale(depth_map, pts_curr, t)
        dx, dy = self._translation_to_xy(R, t, scale)
        self.pose[0] += dx
        self.pose[1] += dy
        self.pose[2] += self._rotation_to_yaw(R)

        self.prev_kp, self.prev_des, self.prev_gray = kp, des, gray
        return self.pose.copy(), scale

    def _estimate_scale(self, depth_map, pts_curr, t):
        depths = []
        h, w = depth_map.shape[:2]
        for (u, v) in pts_curr.astype(int):
            if 0 <= v < h and 0 <= u < w:
                d = float(depth_map[v, u])
                if d > 0:
                    depths.append(d)
        if not depths:
            return 1.0
        median_depth = float(np.median(depths))
        t_norm = float(np.linalg.norm(t))
        if t_norm <= 1e-6:
            return 1.0
        return median_depth / max(t_norm, 1e-6)

    def _rotation_to_yaw(self, R):
        yaw = math.atan2(R[1, 0], R[0, 0])
        return float(yaw)

    def _translation_to_xy(self, R, t, scale):
        t_scaled = t.flatten() * scale
        dx = float(t_scaled[0])
        dy = float(t_scaled[2])
        return dx, dy
