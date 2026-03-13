# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

import heapq
import math


def _heuristic(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])

def a_star(grid, start, goal, allow_diagonal=True):
    if start == goal:
        return [start]
    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    if allow_diagonal:
        neighbors += [(-1, -1), (-1, 1), (1, -1), (1, 1)]

    open_set = []
    heapq.heappush(open_set, (0.0, start))
    came_from = {}
    g_score = {start: 0.0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            return _reconstruct(came_from, current)

        for dx, dy in neighbors:
            nxt = (current[0] + dx, current[1] + dy)
            if not grid.in_bounds(nxt[0], nxt[1]) or grid.is_occupied(nxt[0], nxt[1]):
                continue
            step = math.hypot(dx, dy)
            tentative = g_score[current] + step
            if tentative < g_score.get(nxt, float("inf")):
                came_from[nxt] = current
                g_score[nxt] = tentative
                f = tentative + _heuristic(nxt, goal)
                heapq.heappush(open_set, (f, nxt))
    return []


def _reconstruct(came_from, current):
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path
