import pygame
import math
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice

class PlayerHubState(State):
    def __init__(self, game):
        super().__init__(game)
        self.tabs = ["STATS", "COMPENDIUM"]
        self.current_tab = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.font_title = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        self.font_locked = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (80, 80, 80))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.game.pop_state()
                elif event.key in [pygame.K_RIGHT, pygame.K_d, pygame.K_TAB]: self.current_tab = (self.current_tab + 1) % len(self.tabs)
                elif event.key in [pygame.K_LEFT, pygame.K_a]: self.current_tab = (self.current_tab - 1 + len(self.tabs)) % len(self.tabs)
    
    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)
        
        tab_x = p_rect.left + 5
        for i, tab_name in enumerate(self.tabs):
            w = self.game.white_font.width(tab_name)
            font = self.font_title if i == self.current_tab else self.game.white_font
            font.render(tab_name, surface, (tab_x, p_rect.top + 5))
            tab_x += w + 15
        
        pygame.draw.line(surface, (200, 200, 220, 100), (p_rect.left+5, p_rect.top + 18), (p_rect.right - 5, p_rect.top + 18), 1)

        content_y = p_rect.top + 25
        if self.tabs[self.current_tab] == "STATS": self.render_stats(surface, p_rect.left + 15, content_y)
        elif self.tabs[self.current_tab] == "COMPENDIUM": self.render_compendium(surface, p_rect.left + 15, content_y)
            
        prompt = "Left/Right: Change Tab  -  Esc: Back"
        w = self.game.white_font.width(prompt); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1)); self.game.white_font.render(prompt, surface, pos)

    def render_stats(self, surface, x, y):
        stats = self.game.save_data['stats']
        hours = math.floor(stats['play_time'] / 3600)
        minutes = math.floor((stats['play_time'] % 3600) / 60)
        seconds = math.floor(stats['play_time'] % 60)
        play_time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        stats_lines = {
            "Play Time:": play_time_str,
            "Total Coins Collected:": f"{stats['total_coins']}",
            "Runs Started:": f"{stats['runs_started']}",
            "High Score:": f"{self.game.save_data['high_score']}",
        }
        
        y_offset = y
        for label, value in stats_lines.items():
            self.font_title.render(label, surface, (x, y_offset))
            w = self.font_title.width(label)
            self.game.white_font.render(value, surface, (x + w + 5, y_offset))
            y_offset += 14

    def render_compendium(self, surface, x, y):
        discovered = self.game.save_data['compendium']
        col1_y_offset = y
        self.font_title.render("Perks:", surface, (x, col1_y_offset)); col1_y_offset += 12
        col1_y_offset = self.render_compendium_list(surface, x, col1_y_offset, self.game.perks, discovered['perks'], 100)

        col2_y_offset = y
        col2_x = x + 120
        self.font_title.render("Curses:", surface, (col2_x, col2_y_offset)); col2_y_offset += 12
        col2_y_offset = self.render_compendium_list(surface, col2_x, col2_y_offset, self.game.curses, discovered['curses'], 100)

        col3_y_offset = y
        col3_x = x + 210
        self.font_title.render("Items:", surface, (col3_x, col3_y_offset)); col3_y_offset += 12
        col3_y_offset = self.render_compendium_list(surface, col3_x, col3_y_offset, self.game.item_icons, discovered['items'], 100)
        
    def render_compendium_list(self, surface, x, y, all_defs, discovered_keys, line_width):
        start_y = y
        for key in sorted(all_defs.keys()):
            font = self.game.white_font if key in discovered_keys else self.font_locked
            text = f"- {all_defs[key].get('name', key.replace('_', ' ').title())}" if key in discovered_keys else "- ???"
            font.render(text, surface, (x, y))
            y += 10
            if y > 150: # Wrap to next column (crude)
                y = start_y
                x += line_width + 10
        return y