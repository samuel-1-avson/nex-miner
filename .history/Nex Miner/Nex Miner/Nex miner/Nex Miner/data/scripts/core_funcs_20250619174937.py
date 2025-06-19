
import pygame, math

def load_img(path):
    img = pygame.image.load(path).convert()
    img.set_colorkey((0, 0, 0))
    return img

def normalize(val, amt):
    if val > amt: val -= amt
    elif val < -amt: val += amt
    else: val = 0
    return val

def read_f(path):
    with open(path, 'r') as f: return f.read()

def write_f(path, dat):
    with open(path, 'w') as f: f.write(dat)

def swap_color(img,old_c,new_c):
    img.set_colorkey(old_c)
    surf = img.copy(); surf.fill(new_c); surf.blit(img,(0,0))
    return surf

def clip(surf,x,y,x_size,y_size):
    handle_surf = surf.copy(); clipR = pygame.Rect(x,y,x_size,y_size)
    handle_surf.set_clip(clipR)
    return surf.subsurface(handle_surf.get_clip()).copy()

def rect_corners(points):
    p1, p2 = points
    return [ [min(p1[0],p2[0]), min(p1[1], p2[1])], [max(p1[0],p2[0]), max(p1[1], p2[1])] ]

def corner_rect(points):
    points = rect_corners(points)
    return pygame.Rect(points[0][0], points[0][1], points[1][0] - points[0][0], points[1][1] - points[0][1])

# --- NEW: Bresenham's Line Algorithm for Grid-based LoS ---
def get_line(start, end):
    """Bresenham's Line Algorithm to get grid cells between two points."""
    x1, y1 = start; x2, y2 = end
    dx, dy = x2 - x1, y2 - y1
    is_steep = abs(dy) > abs(dx)
    if is_steep: x1, y1, x2, y2 = y1, x1, y2, x2
    swapped = False
    if x1 > x2: x1, x2, y1, y2, swapped = x2, x1, y2, y1, True
    dx, dy = x2 - x1, y2 - y1
    error, ystep = int(dx / 2.0), 1 if y1 < y2 else -1
    y = y1
    points = []
    for x in range(x1, x2 + 1):
        coord = (y, x) if is_steep else (x, y)
        points.append(coord)
        error -= abs(dy)
        if error < 0: y += ystep; error += dx
    if swapped: points.reverse()
    return points