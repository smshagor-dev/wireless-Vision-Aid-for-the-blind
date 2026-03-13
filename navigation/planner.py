# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 


from navigation.a_star import a_star
from navigation.trajectory import shortcut_path, smooth_path


class PathPlanner:
    def __init__(self, allow_diagonal=True, smooth=True):
        self.allow_diagonal = allow_diagonal
        self.smooth = smooth

    def plan(self, grid, start, goal):
        raw = a_star(grid, start, goal, allow_diagonal=self.allow_diagonal)
        if not raw:
            return []
        if self.smooth:
            raw = shortcut_path(grid, raw)
            raw = smooth_path(raw, window=2)
        return raw
