# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

import time
import json
import cv2

from ultralytics import YOLO

from core.config import load_config
from core.logger import setup_json_logger
from metrics import Metrics
from perception.depth_estimator import DepthEstimator
from perception.perception_mapping import update_grid_from_frame
from mapping.occupancy_grid import OccupancyGrid
from mapping.slam import VisualOdometry
from mapping.orbslam3_bridge import ORBSLAM3Bridge
from navigation.planner import PathPlanner


def _extract_detections(results, conf_thres=0.5):
    detections = []
    for result in results:
        boxes = result.boxes
        for box in boxes:
            confidence = float(box.conf[0])
            if confidence < conf_thres:
                continue
            class_id = int(box.cls[0])
            class_name = result.names[class_id]
            bbox = box.xyxy[0].cpu().numpy()
            detections.append({"class_name": class_name, "bbox": bbox})
    return detections


def _load_goal_from_file(path, last_goal):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        goal = data.get("goal", {})
        frame = data.get("frame", "local")
        gx = float(goal.get("x"))
        gy = float(goal.get("y"))
        return {"x": gx, "y": gy, "frame": frame}
    except Exception:
        return last_goal


def _get_goal(pose, cfg, last_goal):
    nav_cfg = cfg.get("navigation", {})
    source = nav_cfg.get("goal_source", "file")
    if source == "file":
        goal_file = nav_cfg.get("goal_file", "config/goal.json")
        return _load_goal_from_file(goal_file, last_goal)
    return last_goal


def _goal_world(pose, goal, fallback_relative):
    if goal is None:
        return pose[0] + fallback_relative[0], pose[1] + fallback_relative[1]
    if goal.get("frame") == "world":
        return goal["x"], goal["y"]
    return pose[0] + goal["x"], pose[1] + goal["y"]


def stop_robot():
    # Placeholder for integration with motor controller.
    return


def main():
    cfg = load_config("config/config.yaml")
    log_dir = cfg["system"]["log_dir"]
    logger = setup_json_logger("navigation_pipeline", f"{log_dir}/system.log", cfg["system"]["log_level"])

    cam_cfg = cfg["camera"]
    cap = cv2.VideoCapture(cam_cfg["source"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])
    cap.set(cv2.CAP_PROP_FPS, cam_cfg["fps"])

    model = YOLO(cfg["perception"]["yolo_model"])
    depth = DepthEstimator(
        model_name=cfg["perception"]["depth"]["backend"],
        device="auto",
        logger=logger,
    )

    intr = cam_cfg["intrinsics"]
    grid_cfg = cfg["mapping"]["occupancy_grid"]
    grid = OccupancyGrid(
        width_m=grid_cfg["width_m"],
        height_m=grid_cfg["height_m"],
        resolution=grid_cfg["resolution"],
        origin=(grid_cfg["origin_x"], grid_cfg["origin_y"]),
    )

    vo = VisualOdometry(intr["fx"], intr["fy"], intr["cx"], intr["cy"])
    slam_cfg = cfg.get("mapping", {}).get("slam", {})
    slam_backend = slam_cfg.get("backend", "vo")
    orbslam = None
    if slam_backend == "orbslam3":
        orbslam = ORBSLAM3Bridge(
            command=slam_cfg.get("command", []),
            pose_file=slam_cfg.get("pose_file"),
            map_points_file=slam_cfg.get("map_points_file"),
            logger=logger,
        )
        try:
            orbslam.start()
        except Exception as exc:
            logger.warning("ORB-SLAM3 start failed, falling back to VO: %s", exc)
            orbslam = None
    planner = PathPlanner(
        allow_diagonal=cfg["planning"]["allow_diagonal"],
        smooth=cfg["planning"]["smooth_path"],
    )

    metrics = Metrics(port=8000)
    metrics.start()

    last_fps_ts = time.time()
    frames = 0
    last_goal = None
    last_goal_check = 0.0

    while True:
        ok, frame = cap.read()
        if not ok:
            logger.warning("Camera frame missing")
            time.sleep(0.1)
            continue

        t0 = time.time()
        results = model(frame, verbose=False)
        detections = _extract_detections(results, cfg["perception"]["confidence"])
        depth_map = depth.predict(frame)
        update_grid_from_frame(
            detections,
            depth_map,
            grid,
            intrinsics=intr,
            depth_scale_m=cfg["perception"]["depth"]["scale_m"],
        )
        pose = None
        if orbslam is not None:
            pose = orbslam.read_pose()
        if pose is None:
            pose, _ = vo.update(frame, depth_map=depth_map)
        if orbslam is not None and slam_cfg.get("use_map_points", True):
            points = orbslam.read_map_points()
            if points:
                grid.update_from_points(points, sensor_origin=(pose[0], pose[1]) if pose else (0.0, 0.0))
        t1 = time.time()
        metrics.observe_inference(t1 - t0)

        if time.time() - last_goal_check > 0.5:
            last_goal = _get_goal(pose, cfg, last_goal)
            last_goal_check = time.time()
        goal_world = _goal_world(pose, last_goal, cfg["navigation"]["fallback_goal_relative"])

        start = grid.world_to_grid(pose[0], pose[1])
        goal = grid.world_to_grid(goal_world[0], goal_world[1])
        p0 = time.time()
        path = planner.plan(grid, start, goal)
        metrics.observe_planner(time.time() - p0)
        if not path:
            logger.warning("Path not found")
            stop_robot()

        frames += 1
        if time.time() - last_fps_ts >= 1.0:
            metrics.set_camera_fps(frames / (time.time() - last_fps_ts))
            metrics.update_uptime()
            frames = 0
            last_fps_ts = time.time()

        # Optional visualization
        cv2.imshow("Navigation Pipeline", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    if orbslam is not None:
        orbslam.stop()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
