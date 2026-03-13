# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import math
import numpy as np


class OccupancyGrid:
    def __init__(self, width_m=20.0, height_m=20.0, resolution=0.1, origin=(0.0, 0.0)):
        self.resolution = float(resolution)
        self.width_m = float(width_m)
        self.height_m = float(height_m)
        self.origin = origin
        self.width = int(math.ceil(self.width_m / self.resolution))
        self.height = int(math.ceil(self.height_m / self.resolution))
        self.log_odds = np.zeros((self.height, self.width), dtype=np.float32)
        self.log_odds_occ = 0.85
        self.log_odds_free = -0.4
        self.log_odds_min = -5.0
        self.log_odds_max = 5.0

    def world_to_grid(self, x, y):
        gx = int((x - self.origin[0]) / self.resolution)
        gy = int((y - self.origin[1]) / self.resolution)
        return gx, gy

    def grid_to_world(self, gx, gy):
        x = gx * self.resolution + self.origin[0]
        y = gy * self.resolution + self.origin[1]
        return x, y

    def in_bounds(self, gx, gy):
        return 0 <= gx < self.width and 0 <= gy < self.height

    def _bresenham(self, x0, y0, x1, y1):
        points = []
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            points.append((x, y))
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy
        return points

    def update_from_points(self, points_xy, sensor_origin=(0.0, 0.0)):
        if points_xy is None or len(points_xy) == 0:
            return
        sx, sy = self.world_to_grid(sensor_origin[0], sensor_origin[1])
        for x, y in points_xy:
            gx, gy = self.world_to_grid(x, y)
            if not self.in_bounds(gx, gy):
                continue
            ray = self._bresenham(sx, sy, gx, gy)
            for rx, ry in ray[:-1]:
                if self.in_bounds(rx, ry):
                    self.log_odds[ry, rx] = np.clip(
                        self.log_odds[ry, rx] + self.log_odds_free,
                        self.log_odds_min,
                        self.log_odds_max,
                    )
            self.log_odds[gy, gx] = np.clip(
                self.log_odds[gy, gx] + self.log_odds_occ,
                self.log_odds_min,
                self.log_odds_max,
            )

    def to_prob(self):
        return 1.0 / (1.0 + np.exp(-self.log_odds))

    def is_occupied(self, gx, gy, threshold=0.65):
        if not self.in_bounds(gx, gy):
            return True
        return self.to_prob()[gy, gx] >= threshold
