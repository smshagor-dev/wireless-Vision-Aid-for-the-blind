import time

from mapping.orbslam3_bridge import ORBSLAM3Bridge


def _write_pose(path, line="0.0 1.0 2.0 3.0 0.0 0.0 0.0 1.0\n"):
    path.write_text(line, encoding="utf-8")


def test_orbslam_pose_parsing_and_freshness(tmp_path):
    pose_file = tmp_path / "pose.txt"
    _write_pose(pose_file)
    bridge = ORBSLAM3Bridge([], str(pose_file), pose_max_age_s=1.0)
    pose = bridge.read_pose()
    assert pose == (1.0, 3.0, 0.0)

    bridge._last_pose_monotonic = time.monotonic() - 2.0
    assert bridge.read_pose() is None


def test_orbslam_malformed_new_pose_fails_closed(tmp_path):
    pose_file = tmp_path / "pose.txt"
    _write_pose(pose_file)
    bridge = ORBSLAM3Bridge([], str(pose_file), pose_max_age_s=5.0)
    assert bridge.read_pose() is not None

    pose_file.write_text("malformed pose\n", encoding="utf-8")
    assert bridge.read_pose() is None


def test_orbslam_map_points_reject_nonfinite_values(tmp_path):
    map_file = tmp_path / "map.txt"
    map_file.write_text("1 0 2\nnan 0 3\n4 0 inf\n", encoding="utf-8")
    bridge = ORBSLAM3Bridge([], None, str(map_file))
    assert bridge.read_map_points() == [(1.0, 2.0)]
