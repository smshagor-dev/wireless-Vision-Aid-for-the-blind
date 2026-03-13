# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import numpy as np


def detections_to_points(detections, depth_map, intrinsics, depth_scale_m=5.0):
    fx = float(intrinsics["fx"])
    fy = float(intrinsics["fy"])
    cx = float(intrinsics["cx"])
    cy = float(intrinsics["cy"])

    points_xy = []
    h, w = depth_map.shape[:2]
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        u = int((x1 + x2) * 0.5)
        v = int((y1 + y2) * 0.5)
        if u < 0 or v < 0 or u >= w or v >= h:
            continue
        z = float(depth_map[v, u]) * depth_scale_m
        if z <= 0.0:
            continue
        x = (u - cx) * z / fx
        y = (v - cy) * z / fy
        points_xy.append((z, x))
    return points_xy


def update_grid_from_frame(detections, depth_map, grid, intrinsics, depth_scale_m=5.0, sensor_origin=(0.0, 0.0)):
    points = detections_to_points(detections, depth_map, intrinsics, depth_scale_m=depth_scale_m)
    if points:
        grid.update_from_points(points, sensor_origin=sensor_origin)
    return points
