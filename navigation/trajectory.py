# --------------------------------------------------------------------------------------------- # 
# | Name: Md. Shahanur Islam Shagor                                                           | # 
# | Autonomous Systems & UAV Researcher | Cybersecurity    | Specialist | Software Engineer   | #
# | Voronezh State University of Forestry and Technologies                                    | # 
# | Build for Blind people within 15$                                                         | # 
# --------------------------------------------------------------------------------------------- # 

def _bresenham(x0, y0, x1, y1):
    points = []
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x += sx
        if e2 <= dx:
            err += dx
            y += sy
    return points


def _line_of_sight(grid, a, b):
    for x, y in _bresenham(a[0], a[1], b[0], b[1]):
        if grid.is_occupied(x, y):
            return False
    return True


def shortcut_path(grid, path):
    if len(path) < 3:
        return path
    out = [path[0]]
    i = 0
    while i < len(path) - 1:
        j = len(path) - 1
        while j > i + 1:
            if _line_of_sight(grid, path[i], path[j]):
                break
            j -= 1
        out.append(path[j])
        i = j
    return out


def smooth_path(path, window=3):
    if len(path) < 3:
        return path
    out = []
    for i in range(len(path)):
        x_sum = 0.0
        y_sum = 0.0
        count = 0
        for j in range(max(0, i - window), min(len(path), i + window + 1)):
            x_sum += path[j][0]
            y_sum += path[j][1]
            count += 1
        out.append((int(round(x_sum / count)), int(round(y_sum / count))))
    return out
