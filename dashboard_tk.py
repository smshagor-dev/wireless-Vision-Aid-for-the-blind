# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


import time
import tkinter as tk
from tkinter import ttk


COLORS = {
    "background": "#0B0F16",
    "panel": "#111827",
    "border": "#1F2937",
    "accent": "#22D3EE",
    "success": "#22C55E",
    "warning": "#FACC15",
    "danger": "#EF4444",
    "text": "#E5E7EB",
    "muted": "#94A3B8",
    "danger_dark": "#991B1B",
}


class DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("WVAB Autonomous Navigation Dashboard")
        self.geometry("1920x1080")
        self.configure(bg=COLORS["background"])
        self.minsize(1280, 720)

        self.start_time = time.time()
        self.status = {
            "online": True,
            "model": "YOLOv8",
            "gpu": "RTX",
        }

        self._build_layout()
        self._tick_uptime()

    def _build_layout(self):
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        TopBar(self, self.status).grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))

        main = tk.Frame(self, bg=COLORS["background"])
        main.grid(row=1, column=0, sticky="nsew", padx=16)
        main.grid_columnconfigure(0, weight=1)
        main.grid_columnconfigure(1, weight=3)
        main.grid_columnconfigure(2, weight=1)
        main.grid_rowconfigure(0, weight=1)

        left = tk.Frame(main, bg=COLORS["background"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        left.grid_rowconfigure(1, weight=1)

        ModelStatusPanel(left).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ObjectListPanel(left).grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        DepthPanel(left).grid(row=2, column=0, sticky="ew")

        center = tk.Frame(main, bg=COLORS["background"])
        center.grid(row=0, column=1, sticky="nsew", padx=(0, 12))
        center.grid_rowconfigure(0, weight=1)
        CameraPanel(center).grid(row=0, column=0, sticky="nsew")

        right = tk.Frame(main, bg=COLORS["background"])
        right.grid(row=0, column=2, sticky="nsew")
        right.grid_rowconfigure(2, weight=1)

        NavigationPanel(right).grid(row=0, column=0, sticky="ew", pady=(0, 10))
        MetricsPanel(right).grid(row=1, column=0, sticky="ew", pady=(0, 10))
        GoalPanel(right).grid(row=2, column=0, sticky="nsew")

        bottom = tk.Frame(self, bg=COLORS["background"])
        bottom.grid(row=2, column=0, sticky="ew", padx=16, pady=(10, 16))
        bottom.grid_columnconfigure(0, weight=3)
        bottom.grid_columnconfigure(1, weight=2)

        MapPanel(bottom).grid(row=0, column=0, sticky="ew")
        StatusBar(bottom).grid(row=0, column=1, sticky="ew", padx=(12, 0))

    def _tick_uptime(self):
        uptime = int(time.time() - self.start_time)
        h = uptime // 3600
        m = (uptime % 3600) // 60
        s = uptime % 60
        self.status["uptime"] = f"{h:02d}:{m:02d}:{s:02d}"
        self.after(1000, self._tick_uptime)

    def start_camera(self):
        print("Start camera")

    def pause_navigation(self):
        print("Pause navigation")

    def stop_camera(self):
        print("Stop camera")

    def emergency_stop(self):
        print("Emergency stop")


class Panel(tk.Frame):
    def __init__(self, parent, title):
        super().__init__(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        tk.Label(self, text=title, fg=COLORS["muted"], bg=COLORS["panel"], font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=12, pady=(8, 6)
        )


class TopBar(tk.Frame):
    def __init__(self, parent, status):
        super().__init__(parent, bg=COLORS["panel"], highlightbackground=COLORS["border"], highlightthickness=1)
        self.status = status
        self.uptime_var = tk.StringVar(value="00:00:00")

        tk.Label(self, text="WVAB Autonomous Navigation Dashboard",
                 fg=COLORS["text"], bg=COLORS["panel"],
                 font=("Segoe UI", 14, "bold")).pack(side=tk.LEFT, padx=12, pady=10)

        right = tk.Frame(self, bg=COLORS["panel"])
        right.pack(side=tk.RIGHT, padx=12)

        self._pill(right, "Status: ONLINE", COLORS["success"])
        self._pill(right, f"Model: {status['model']}", COLORS["accent"])
        self._pill(right, f"GPU: {status['gpu']}", COLORS["accent"])
        self.uptime_label = self._pill(right, "Uptime: 00:00:00", COLORS["accent"])
        self.after(1000, self._update_uptime)

    def _pill(self, parent, text, color):
        lbl = tk.Label(parent, text=text, fg=color, bg=COLORS["panel"],
                       font=("Segoe UI", 9, "bold"))
        lbl.pack(side=tk.LEFT, padx=6)
        return lbl

    def _update_uptime(self):
        uptime = self.master.status.get("uptime", "00:00:00")
        self.uptime_label.config(text=f"Uptime: {uptime}")
        self.after(1000, self._update_uptime)


class ModelStatusPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Model & Stream Status")
        for item in ["YOLO Model: Loaded", "Depth Model: MiDaS", "Streaming: READY"]:
            tk.Label(self, text=item, fg=COLORS["text"], bg=COLORS["panel"],
                     font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=4)


class ObjectListPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Detected Objects")
        self.listbox = tk.Listbox(self, bg=COLORS["panel"], fg=COLORS["text"],
                                  highlightthickness=0, relief="flat", height=12)
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        for item in ["Person 0.93 (High)", "Chair 0.78 (Medium)", "Bicycle 0.66 (High)"]:
            self.listbox.insert(tk.END, item)


class DepthPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Depth Map")
        tk.Label(self, text="Depth Visualization", fg=COLORS["muted"], bg=COLORS["panel"],
                 font=("Segoe UI", 10)).pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class CameraPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Live Camera Feed")
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        self.canvas.create_text(200, 100, text="Camera Stream Placeholder",
                                fill=COLORS["muted"], font=("Segoe UI", 14))


class NavigationPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Navigation Controls")
        btn_frame = tk.Frame(self, bg=COLORS["panel"])
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        for i in range(2):
            btn_frame.grid_columnconfigure(i, weight=1)

        self._btn(btn_frame, "START", COLORS["success"]).grid(row=0, column=0, padx=6, pady=6, sticky="ew")
        self._btn(btn_frame, "PAUSE", COLORS["warning"]).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        self._btn(btn_frame, "STOP", COLORS["danger"]).grid(row=1, column=0, padx=6, pady=6, sticky="ew")
        self._btn(btn_frame, "EMERGENCY STOP", COLORS["danger_dark"]).grid(row=1, column=1, padx=6, pady=6, sticky="ew")

    def _btn(self, parent, text, color):
        return tk.Button(parent, text=text, bg=color, fg="white",
                         font=("Segoe UI", 10, "bold"), relief="flat")


class MetricsPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Metrics")
        for item in ["Camera FPS: 24", "SLAM FPS: 27", "CPU: 42%", "GPU: 68%", "Memory: 58%"]:
            tk.Label(self, text=item, fg=COLORS["text"], bg=COLORS["panel"],
                     font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=4)


class GoalPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Goal Status")
        for item in ["Goal: (5.0, 0.0)", "Distance: 4.2m", "State: NAVIGATING"]:
            tk.Label(self, text=item, fg=COLORS["text"], bg=COLORS["panel"],
                     font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=4)


class MapPanel(Panel):
    def __init__(self, parent):
        super().__init__(parent, "Localization & Map")
        tk.Label(self, text="Occupancy Grid + Path Overlay", fg=COLORS["muted"], bg=COLORS["panel"],
                 font=("Segoe UI", 10)).pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))


class StatusBar(Panel):
    def __init__(self, parent):
        super().__init__(parent, "System Status")
        chips = ["AI ACTIVE", "SLAM ACTIVE", "DOCKER READY", "STREAMING ACTIVE"]
        for chip in chips:
            tk.Label(self, text=chip, fg=COLORS["success"], bg=COLORS["panel"],
                     font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=2)
        tk.Label(self, text='Audio: "Obstacle ahead, go right"', fg=COLORS["accent"], bg=COLORS["panel"],
                 font=("Segoe UI", 10)).pack(anchor="w", padx=12, pady=(8, 4))


if __name__ == "__main__":
    app = DashboardApp()
    app.mainloop()
