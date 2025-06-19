# data/scripts/game_states/pause_state.py
import pygame
import math
from ..state import State
from ..text import Font

class PauseState(State):
    def __init__(self, game, gameplay_state):
        super().__init__(game)
        self.gameplay_state = gameplay_state
        self.options = ["RESUME", "RETURN TO HUB", "QUIT GAME"]
        self.selection_index = 0
        self.master_clock = 0
        
        # --- Minimalist Fonts ---
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.font_main = Font(font_path, (200, 210, 220))
        self.font_highlight = Font(font_path, (255, 230, 90))
        self.font_title = Font(font_path, (255, 255, 255))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.options)
                    if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                    if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                elif event.key == pygame.K_RETURN:
                    self.select_option()

    def select_option(self):
        option = self.options[self.selection_index]
        if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
        if option == "RESUME":
            self.game.pop_state()
        elif option == "RETURN TO HUB":
            self.game.return_to_main_menu()
        elif option == "QUIT GAME":
            while self.game.states:
                self.game.pop_state()

    def update(self):
        self.master_clock += 1

    def render(self, surface):
        # Render the frozen gameplay, slightly darkened.
        self.gameplay_state.render(surface)
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((18, 16, 28, 220))
        surface.blit(overlay, (0, 0))

        # --- Menu Rendering ---
        center_x = surface.get_width() // 2
        y_pos = 60
        
        # Title
        self.font_title.render("MISSION PAUSED", surface, (center_x - self.font_title.width("MISSION PAUSED", 2)//2, y_pos), scale=2)
        
        y_pos += 30
        spacing = 15

        # Options
        for i, option in enumerate(self.options):
            font = self.font_main
            text_width = font.width(option)
            
            if i == self.selection_index:
                # Add pulsing effect to the selected option's selector
                pulse = math.sin(self.master_clock / 10) * 2
                self.font_highlight.render('>', surface, (center_x - text_width//2 - 10 + pulse, y_pos))
                self.font_highlight.render(option, surface, (center_x - text_width//2, y_pos))
            else:
                font.render(option, surface, (center_x - text_width//2, y_pos))
                
            y_pos += spacing