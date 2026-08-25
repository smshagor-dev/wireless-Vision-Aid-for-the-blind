from core.object_policy import CriticalObjectPolicy, label_candidates, normalize_class_name
from udp_streaming import UDPVisionServer


def test_class_normalization_unifies_coco_and_custom_names():
    assert normalize_class_name("traffic light") == "traffic_light"
    assert normalize_class_name("traffic_light") == "traffic_light"
    assert normalize_class_name("stop-sign") == "stop_sign"
    assert normalize_class_name("road cone") == "road_cone"


def test_custom_mobility_hazards_are_not_filtered_out():
    policy = CriticalObjectPolicy()
    for name in (
        "traffic_light",
        "stop_sign",
        "crosswalk",
        "curb",
        "pothole",
        "pole",
        "road_cone",
        "stairs",
        "door",
    ):
        assert name in policy
        assert isinstance(policy.get(name), int)


def test_coco_space_names_use_same_priority_as_custom_names():
    policy = CriticalObjectPolicy()
    assert policy["traffic light"] == policy["traffic_light"]
    assert policy["stop sign"] == policy["stop_sign"]
    assert policy["potted plant"] == policy["potted_plant"]


def test_label_candidates_allow_existing_coco_translation_for_custom_name():
    assert label_candidates("traffic_light") == ["traffic_light", "traffic light"]


def test_udp_wrapper_translates_custom_alias_using_existing_label_table():
    server = UDPVisionServer.__new__(UDPVisionServer)
    server.language = "bn"
    server.multilingual_labels = {
        "traffic light": {"en": "Traffic light", "bn": "ট্রাফিক লাইট"}
    }
    assert server._translate("traffic_light") == "ট্রাফিক লাইট"
