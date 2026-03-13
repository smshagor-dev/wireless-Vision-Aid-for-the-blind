# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

def test_imports():
    import camera_gui  # noqa: F401
    import vision_server  # noqa: F401
    import udp_streaming  # noqa: F401
    import navigation_pipeline  # noqa: F401
    import metrics  # noqa: F401
    import offline_utils  # noqa: F401
    import export_accelerated_models  # noqa: F401
    import smartphone_camera  # noqa: F401
    import train_navigation_model  # noqa: F401
    import core.config  # noqa: F401
    import core.logger  # noqa: F401
    import mapping.occupancy_grid  # noqa: F401
    import mapping.slam  # noqa: F401
    import mapping.orbslam3_bridge  # noqa: F401
    import navigation.a_star  # noqa: F401
    import navigation.trajectory  # noqa: F401
    import navigation.planner  # noqa: F401
    import perception.depth_estimator  # noqa: F401
    import perception.perception_mapping  # noqa: F401
