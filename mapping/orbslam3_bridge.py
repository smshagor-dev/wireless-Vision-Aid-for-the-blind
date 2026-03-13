# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import os
import math
import subprocess


class ORBSLAM3Bridge:
    """
    Bridge to external ORB-SLAM3 process.
    Expects ORB-SLAM3 (or a wrapper) to write:
      - pose_file: lines "ts x y z qx qy qz qw"
      - map_points_file: lines "x y z"
    """

    def __init__(self, command, pose_file, map_points_file=None, logger=None):
        self.command = command
        self.pose_file = pose_file
        self.map_points_file = map_points_file
        self.logger = logger
        self.proc = None
        self._pose_mtime = 0.0
        self._last_pose = None

    def _log(self, level, msg, *args):
        if self.logger:
            getattr(self.logger, level)(msg, *args)

    def start(self):
        if self.proc is not None:
            return
        if not self.command:
            raise RuntimeError("ORB-SLAM3 command is not configured.")
        self._log("info", "Starting ORB-SLAM3: %s", " ".join(self.command))
        self.proc = subprocess.Popen(self.command)

    def stop(self):
        if self.proc is None:
            return
        try:
            self.proc.terminate()
            self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    def read_pose(self):
        if not self.pose_file or not os.path.exists(self.pose_file):
            return self._last_pose
        try:
            mtime = os.path.getmtime(self.pose_file)
            if mtime == self._pose_mtime and self._last_pose is not None:
                return self._last_pose
            self._pose_mtime = mtime
            with open(self.pose_file, "r", encoding="utf-8") as f:
                lines = [ln.strip() for ln in f.readlines() if ln.strip()]
            if not lines:
                return self._last_pose
            parts = lines[-1].split()
            if len(parts) < 8:
                return self._last_pose
            _, x, y, z, qx, qy, qz, qw = parts[:8]
            yaw = self._quat_to_yaw(float(qx), float(qy), float(qz), float(qw))
            self._last_pose = (float(x), float(z), yaw)
            return self._last_pose
        except Exception:
            return self._last_pose

    def read_map_points(self, limit=5000):
        if not self.map_points_file or not os.path.exists(self.map_points_file):
            return []
        points = []
        try:
            with open(self.map_points_file, "r", encoding="utf-8") as f:
                for line in f:
                    if len(points) >= limit:
                        break
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    x, y, z = map(float, parts[:3])
                    points.append((x, z))
        except Exception:
            return []
        return points

    def _quat_to_yaw(self, qx, qy, qz, qw):
        siny = 2.0 * (qw * qz + qx * qy)
        cosy = 1.0 - 2.0 * (qy * qy + qz * qz)
        return math.atan2(siny, cosy)
