# data/scripts/game_states/pause_state.py
import pygame
from ..state import State
from ..text import Font
from ..ui_utils import render_panel_9slice

class PauseState(State):
    def __init__(self, game, gameplay_state):
        super().__init__(game)
        self.gameplay_state = gameplay_state
        self.options = ["RESUME", "RETURN TO HUB", "QUIT GAME"]
        self.selection_index = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.highlight_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.options)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    self.select_option()

    def select_option(self):
        option = self.options[self.selection_index]
        if option == "RESUME":
            self.game.pop_state()
        elif option == "RETURN TO HUB":
            self.game.return_to_main_menu()
        elif option == "QUIT GAME":
            while self.game.states:
                self.game.pop_state()

    def update(self):
        pass

    def render(self, surface):
        # Render the frozen gameplay in the background
        self.gameplay_state.render(surface)

        # Darken the screen
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 200))
        surface.blit(overlay, (0, 0))

        # Render the menu panel
        panel_w, panel_h = 120, 60
        p_rect = pygame.Rect((surface.get_width() - panel_w) / 2, (surface.get_height() - panel_h) / 2, panel_w, panel_h)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)
        
        # Render Title
        title_text = "PAUSED"
        w = self.game.white_font.width(title_text, 2)
        title_x = p_rect.centerx - w // 2
        self.game.white_font.render(title_text, surface, (title_x, p_rect.top + 6), scale=2)

        # Render Options
        y_pos = p_rect.top + 26
        for i, option in enumerate(self.options):
            font = self.game.white_font
            if i == self.selection_index:
                font = self.highlight_font
            
            w = font.width(option)
            x_pos = p_rect.centerx - w // 2
            font.render(option, surface, (x_pos, y_pos))
            y_pos += 12