import numpy as np


def detections_to_points(detections, depth_map, intrinsics, depth_scale=1.0):
    """Project detections into a local grid.

    depth_scale is deliberately unit-neutral. A monocular normalized depth map is
    not metric unless the caller has completed an external scale calibration.
    """
    if depth_map is None:
        return []
    fx = float(intrinsics["fx"])
    fy = float(intrinsics["fy"])
    cx = float(intrinsics["cx"])
    cy = float(intrinsics["cy"])
    if fx <= 0 or fy <= 0:
        raise ValueError("camera intrinsics fx/fy must be positive")

    points_xy = []
    h, w = depth_map.shape[:2]
    for det in detections:
        x1, y1, x2, y2 = det["bbox"]
        u = int((x1 + x2) * 0.5)
        v = int((y1 + y2) * 0.5)
        if u < 0 or v < 0 or u >= w or v >= h:
            continue
        z = float(depth_map[v, u]) * float(depth_scale)
        if z <= 0.0 or not np.isfinite(z):
            continue
        x = (u - cx) * z / fx
        points_xy.append((z, x))
    return points_xy


def update_grid_from_frame(
    detections,
    depth_map,
    grid,
    intrinsics,
    depth_scale=1.0,
    sensor_origin=(0.0, 0.0),
):
    points = detections_to_points(
        detections,
        depth_map,
        intrinsics,
        depth_scale=depth_scale,
    )
    if points:
        grid.update_from_points(points, sensor_origin=sensor_origin)
    return points
