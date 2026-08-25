import math
import os
import subprocess
import time


class ORBSLAM3Bridge:
    """
    Bridge to an external ORB-SLAM3 process.

    Expected outputs:
      - pose_file: lines ``ts x y z qx qy qz qw``
      - map_points_file: lines ``x y z``

    Pose reads fail closed when the process has exited, the pose file becomes
    malformed, or no fresh pose has been observed within ``pose_max_age_s``.
    """

    def __init__(
        self,
        command,
        pose_file,
        map_points_file=None,
        logger=None,
        pose_max_age_s=1.0,
    ):
        self.command = command
        self.pose_file = pose_file
        self.map_points_file = map_points_file
        self.logger = logger
        self.pose_max_age_s = max(float(pose_max_age_s), 0.05)
        self.proc = None
        self._pose_mtime = None
        self._last_pose = None
        self._last_pose_monotonic = None

    def _log(self, level, msg, *args):
        if self.logger:
            getattr(self.logger, level)(msg, *args)

    def start(self):
        if self.proc is not None and self.proc.poll() is None:
            return
        if not self.command:
            raise RuntimeError("ORB-SLAM3 command is not configured.")
        self._log("info", "Starting ORB-SLAM3: %s", " ".join(self.command))
        self.proc = subprocess.Popen(self.command)

    def stop(self):
        if self.proc is None:
            return
        try:
            if self.proc.poll() is None:
                self.proc.terminate()
                self.proc.wait(timeout=5)
        except Exception:
            try:
                self.proc.kill()
            except Exception:
                pass
        self.proc = None

    def _pose_is_fresh(self):
        if self._last_pose is None or self._last_pose_monotonic is None:
            return False
        return (time.monotonic() - self._last_pose_monotonic) <= self.pose_max_age_s

    def read_pose(self):
        if self.proc is not None and self.proc.poll() is not None:
            self._log("warning", "ORB-SLAM3 process exited with code %s", self.proc.returncode)
            return None
        if not self.pose_file or not os.path.exists(self.pose_file):
            return self._last_pose if self._pose_is_fresh() else None

        try:
            mtime = os.path.getmtime(self.pose_file)
            if self._pose_mtime is not None and mtime == self._pose_mtime:
                return self._last_pose if self._pose_is_fresh() else None

            with open(self.pose_file, "r", encoding="utf-8") as handle:
                lines = [line.strip() for line in handle if line.strip()]
            if not lines:
                return None

            parts = lines[-1].split()
            if len(parts) < 8:
                return None

            _, x, _y, z, qx, qy, qz, qw = parts[:8]
            values = [float(x), float(z), float(qx), float(qy), float(qz), float(qw)]
            if not all(math.isfinite(value) for value in values):
                return None

            yaw = self._quat_to_yaw(values[2], values[3], values[4], values[5])
            pose = (values[0], values[1], yaw)
            if not all(math.isfinite(value) for value in pose):
                return None

            self._pose_mtime = mtime
            self._last_pose = pose
            self._last_pose_monotonic = time.monotonic()
            return pose
        except (OSError, ValueError):
            return None

    def read_map_points(self, limit=5000):
        if not self.map_points_file or not os.path.exists(self.map_points_file):
            return []
        points = []
        try:
            with open(self.map_points_file, "r", encoding="utf-8") as handle:
                for line in handle:
                    if len(points) >= limit:
                        break
                    parts = line.strip().split()
                    if len(parts) < 3:
                        continue
                    x, _y, z = map(float, parts[:3])
                    if math.isfinite(x) and math.isfinite(z):
                        points.append((x, z))
        except (OSError, ValueError):
            return []
        return points

    @staticmethod
    def _quat_to_yaw(qx, qy, qz, qw):
        siny = 2.0 * (qw * qz + qx * qy)
        cosy = 1.0 - 2.0 * (qy * qy + qz * qz)
        return math.atan2(siny, cosy)
