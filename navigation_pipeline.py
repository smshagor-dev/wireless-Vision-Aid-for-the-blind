import json
import os
import signal
import threading
import time

import cv2

from offline_utils import configure_offline_env, ensure_local_model

OFFLINE_MODE = configure_offline_env()
from ultralytics import YOLO

from core.config import load_config, validate_navigation_config
from core.logger import setup_json_logger
from core.safety import SafetyStatePublisher
from mapping.occupancy_grid import OccupancyGrid
from mapping.orbslam3_bridge import ORBSLAM3Bridge
from mapping.slam import VisualOdometry
from metrics import Metrics
from navigation.planner import PathPlanner
from perception.depth_estimator import DepthEstimator
from perception.perception_mapping import update_grid_from_frame


def _env_bool(name, default=False):
    raw = os.environ.get(name)
    if raw is None:
        return bool(default)
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _extract_detections(results, conf_thres=0.5):
    detections = []
    for result in results:
        for box in result.boxes:
            confidence = float(box.conf[0])
            if confidence < conf_thres:
                continue
            class_id = int(box.cls[0])
            detections.append(
                {
                    "class_name": result.names[class_id],
                    "bbox": box.xyxy[0].cpu().numpy(),
                    "confidence": confidence,
                }
            )
    return detections


def _load_goal_from_file(path, last_goal):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        goal = data.get("goal", {})
        return {
            "x": float(goal.get("x")),
            "y": float(goal.get("y")),
            "frame": data.get("frame", "local"),
        }
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return last_goal


def _get_goal(cfg, last_goal):
    nav_cfg = cfg["navigation"]
    if nav_cfg.get("goal_source", "file") == "file":
        return _load_goal_from_file(nav_cfg.get("goal_file", "config/goal.json"), last_goal)
    return last_goal


def _goal_world(pose, goal, fallback_relative):
    if goal is None:
        return pose[0] + fallback_relative[0], pose[1] + fallback_relative[1]
    if goal.get("frame") == "world":
        return goal["x"], goal["y"]
    return pose[0] + goal["x"], pose[1] + goal["y"]


def main():
    cfg = validate_navigation_config(load_config("config/config.yaml"))
    os.makedirs(cfg["system"]["log_dir"], exist_ok=True)
    logger = setup_json_logger(
        "navigation_pipeline",
        os.path.join(cfg["system"]["log_dir"], "system.log"),
        cfg["system"]["log_level"],
    )
    safety = SafetyStatePublisher(cfg["navigation"]["safety_state_file"])
    safety.stop("initializing")

    stop_event = threading.Event()

    def handle_signal(signum, _frame):
        logger.info("Signal %s received; stopping navigation pipeline", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    try:
        signal.signal(signal.SIGTERM, handle_signal)
    except (AttributeError, ValueError):
        pass

    headless = _env_bool("WVAB_NAV_HEADLESS", cfg["system"].get("headless", False))
    metrics_enabled = _env_bool("WVAB_METRICS_ENABLED", cfg["system"].get("metrics_enabled", True))
    metrics_port = int(os.environ.get("WVAB_METRICS_PORT", cfg["system"].get("metrics_port", 8000)))

    cam_cfg = cfg["camera"]
    cap = cv2.VideoCapture(cam_cfg["source"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])
    cap.set(cv2.CAP_PROP_FPS, cam_cfg["fps"])
    if not cap.isOpened():
        safety.stop("camera_open_failed")
        raise RuntimeError("Camera could not be opened")

    model_path = ensure_local_model(cfg["perception"]["yolo_model"], offline=OFFLINE_MODE)
    model = YOLO(model_path)
    depth_cfg = cfg["perception"]["depth"]
    depth = DepthEstimator(model_name=depth_cfg["backend"], device="auto", logger=logger)

    intr = cam_cfg["intrinsics"]
    metric_depth_ready = bool(depth_cfg.get("metric_calibrated", False)) and bool(intr.get("calibrated", False))
    if not metric_depth_ready:
        logger.warning(
            "Metric depth mapping disabled: camera/depth scale is not calibrated. "
            "Guidance will remain DEGRADED unless another calibrated map source is available."
        )

    grid_cfg = cfg["mapping"]["occupancy_grid"]
    grid = OccupancyGrid(
        width_m=grid_cfg["width_m"],
        height_m=grid_cfg["height_m"],
        resolution=grid_cfg["resolution"],
        origin=(grid_cfg["origin_x"], grid_cfg["origin_y"]),
    )

    vo = VisualOdometry(intr["fx"], intr["fy"], intr["cx"], intr["cy"])
    slam_cfg = cfg["mapping"].get("slam", {})
    orbslam = None
    if slam_cfg.get("backend", "vo") == "orbslam3":
        orbslam = ORBSLAM3Bridge(
            command=slam_cfg.get("command", []),
            pose_file=slam_cfg.get("pose_file"),
            map_points_file=slam_cfg.get("map_points_file"),
            logger=logger,
        )
        try:
            orbslam.start()
        except Exception as exc:
            logger.warning("ORB-SLAM3 start failed; falling back to VO: %s", exc)
            orbslam = None

    planner = PathPlanner(
        allow_diagonal=cfg["planning"]["allow_diagonal"],
        smooth=cfg["planning"]["smooth_path"],
    )
    metrics = None
    if metrics_enabled:
        try:
            metrics = Metrics(port=metrics_port)
            metrics.start()
            logger.info("Prometheus metrics listening on port %s", metrics_port)
        except Exception as exc:
            metrics = None
            logger.warning("Metrics server unavailable; continuing without Prometheus: %s", exc)

    frames = 0
    last_fps_ts = time.time()
    last_goal = None
    last_goal_check = 0.0
    last_frame_ok = time.time()

    try:
        while not stop_event.is_set():
            ok, frame = cap.read()
            if not ok:
                if time.time() - last_frame_ok > 1.0:
                    safety.stop("camera_frame_missing")
                logger.warning("Camera frame missing")
                stop_event.wait(0.1)
                continue
            last_frame_ok = time.time()

            t0 = time.time()
            results = model(frame, verbose=False)
            detections = _extract_detections(results, cfg["perception"]["confidence"])
            depth_map = depth.predict(frame)

            pose = orbslam.read_pose() if orbslam is not None else None
            if pose is None:
                pose, _ = vo.update(frame, depth_map=depth_map)
            if pose is None:
                safety.stop("localization_unavailable")
                continue

            map_is_metric = False
            if metric_depth_ready and depth_map is not None:
                update_grid_from_frame(
                    detections,
                    depth_map,
                    grid,
                    intrinsics=intr,
                    depth_scale=float(depth_cfg["scale_m"]),
                    sensor_origin=(pose[0], pose[1]),
                )
                map_is_metric = True

            if (
                orbslam is not None
                and slam_cfg.get("use_map_points", True)
                and bool(slam_cfg.get("metric_scale_calibrated", False))
            ):
                points = orbslam.read_map_points()
                if points:
                    grid.update_from_points(points, sensor_origin=(pose[0], pose[1]))
                    map_is_metric = True

            if metrics is not None:
                metrics.observe_inference(time.time() - t0)

            if time.time() - last_goal_check > 0.5:
                last_goal = _get_goal(cfg, last_goal)
                last_goal_check = time.time()
            goal_world = _goal_world(pose, last_goal, cfg["navigation"]["fallback_goal_relative"])
            start = grid.world_to_grid(pose[0], pose[1])
            goal = grid.world_to_grid(goal_world[0], goal_world[1])

            p0 = time.time()
            path = planner.plan(grid, start, goal)
            if metrics is not None:
                metrics.observe_planner(time.time() - p0)
            if not path:
                safety.stop("path_not_found", pose=[pose[0], pose[1]])
            elif map_is_metric:
                safety.guidance(path_points=len(path), pose=[pose[0], pose[1]])
            else:
                safety.degraded(
                    "uncalibrated_metric_geometry",
                    path_points=len(path),
                    pose=[pose[0], pose[1]],
                )

            frames += 1
            if time.time() - last_fps_ts >= 1.0:
                if metrics is not None:
                    metrics.set_camera_fps(frames / (time.time() - last_fps_ts))
                    metrics.update_uptime()
                frames = 0
                last_fps_ts = time.time()

            if not headless:
                cv2.imshow("Navigation Pipeline", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    stop_event.set()
    finally:
        safety.stop("pipeline_stopped")
        if orbslam is not None:
            orbslam.stop()
        cap.release()
        if not headless:
            cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
