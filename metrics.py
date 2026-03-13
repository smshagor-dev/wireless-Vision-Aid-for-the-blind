# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import time
from prometheus_client import Summary, Gauge, start_http_server


class Metrics:
    def __init__(self, port=8000):
        self.start_time = time.time()
        self.port = int(port)

        self.vision_inference_time = Summary("vision_inference_time_seconds", "Vision inference latency")
        self.navigation_planner_time = Summary("navigation_planner_time_seconds", "Planner latency")
        self.camera_fps = Gauge("camera_fps", "Camera FPS")
        self.uptime = Gauge("system_uptime_seconds", "System uptime seconds")

    def start(self):
        start_http_server(self.port)

    def observe_inference(self, seconds):
        self.vision_inference_time.observe(seconds)

    def observe_planner(self, seconds):
        self.navigation_planner_time.observe(seconds)

    def set_camera_fps(self, fps):
        self.camera_fps.set(fps)

    def update_uptime(self):
        self.uptime.set(time.time() - self.start_time)
