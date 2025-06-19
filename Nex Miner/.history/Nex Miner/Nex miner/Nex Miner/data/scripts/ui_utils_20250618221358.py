
# data/scripts/ui_utils.py
import pygame

# Cache for generated glow surfaces to improve performance
GLOW_CACHE = {}

def glow_img(size, color):
    """
    Creates and caches a circular glow surface.
    """
    key = (int(size), color)
    if key not in GLOW_CACHE:
        surf = pygame.Surface((size * 2 + 2, size * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2), size)
        GLOW_CACHE[key] = surf
    return GLOW_CACHE[key]

def render_panel_9slice(surface, rect, panel_img, corner_size):
    """
    Renders a resizable panel using a 9-slice image.
    This is highly efficient for creating professional-looking UI.
    """
    # Corners (no scaling)
    # Top-left
    surface.blit(panel_img, rect.topleft, (0, 0, corner_size, corner_size))
    # Top-right
    surface.blit(panel_img, (rect.right - corner_size, rect.top), (panel_img.get_width() - corner_size, 0, corner_size, corner_size))
    # Bottom-left
    surface.blit(panel_img, (rect.left, rect.bottom - corner_size), (0, panel_img.get_height() - corner_size, corner_size, corner_size))
    # Bottom-right
    surface.blit(panel_img, (rect.right - corner_size, rect.bottom - corner_size), (panel_img.get_width() - corner_size, panel_img.get_height() - corner_size, corner_size, corner_size))

    # Edges (scaled on one axis)
    top_edge = pygame.transform.scale(panel_img.subsurface(corner_size, 0, panel_img.get_width() - corner_size * 2, corner_size), (rect.width - corner_size * 2, corner_size))
    bottom_edge = pygame.transform.scale(panel_img.subsurface(corner_size, panel_img.get_height() - corner_size, panel_img.get_width() - corner_size * 2, corner_size), (rect.width - corner_size * 2, corner_size))
    left_edge = pygame.transform.scale(panel_img.subsurface(0, corner_size, corner_size, panel_img.get_height() - corner_size * 2), (corner_size, rect.height - corner_size * 2))
    right_edge = pygame.transform.scale(panel_img.subsurface(panel_img.get_width() - corner_size, corner_size, corner_size, panel_img.get_height() - corner_size * 2), (corner_size, rect.height - corner_size * 2))
    
    surface.blit(top_edge, (rect.left + corner_size, rect.top))
    surface.blit(bottom_edge, (rect.left + corner_size, rect.bottom - corner_size))
    surface.blit(left_edge, (rect.left, rect.top + corner_size))
    surface.blit(right_edge, (rect.right - corner_size, rect.top + corner_size))
    

    
    # Center (scaled on both axes)
    center = pygame.transform.scale(panel_img.subsurface(corner_size, corner_size, panel_img.get_width() - corner_size * 2, panel_img.get_height() - corner_size * 2), (rect.width - corner_size * 2, rect.height - corner_size * 2))
    surface.blit(center, (rect.left + corner_size, rect.top + corner_size))