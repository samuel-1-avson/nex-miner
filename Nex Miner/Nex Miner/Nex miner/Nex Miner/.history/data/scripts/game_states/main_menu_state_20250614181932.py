# data/scripts/game_states/main_menu_state.py
import pygame # <--- ADD THIS LINE
from ..state import State
from ..gameplay_state import GameplayState
from .upgrade_shop_state import UpgradeShopState
from .settings_state import SettingsState # <--- ADD THIS IMPORT




class MainMenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.options = ["PLAY", "UPGRADES", "QUIT"]
        self.selection_index = 0
        self.options = ["PLAY", "UPGRADES", "SETTINGS", "QUIT"] # <--- ADD "SETTINGS"

    def enter_state(self):
        self.selection_index = 0

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.options)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                elif event.key == pygame.K_RETURN:
                    self.select_option()

    def select_option(self):
        option = self.options[self.selection_index]
        if option == "PLAY":
            self.game.push_state(GameplayState(self.game))
        elif option == "UPGRADES":
            self.game.push_state(UpgradeShopState(self.game))
            
        elif option == "SETTINGS": # <--- ADD THIS CASE
            self.game.push_state(SettingsState(self.game))    
        elif option == "QUIT":
            self.game.pop_state() # Will quit because it's the last state

    def render(self, surface):
        surface.fill((22, 19, 40))
        # Title
        title_text = "CAVYN: RECHARGED"
        title_w = self.game.white_font.width(title_text, 3)
        self.game.black_font.render(title_text, surface, (surface.get_width()//2 - title_w//2 + 2, 32), 3)
        self.game.white_font.render(title_text, surface, (surface.get_width()//2 - title_w//2, 30), 3)

        # Options
        y_pos = 90
        for i, option in enumerate(self.options):
            color = (255, 230, 90) if i == self.selection_index else (251, 245, 239)
            font = self.game.white_font if i != self.selection_index else self.game.black_font
            
            w = self.game.white_font.width(option, 2)
            x_pos = surface.get_width()//2 - w//2
            
            if i == self.selection_index:
                 pygame.draw.rect(surface, (255, 230, 90), (x_pos - 10, y_pos - 3, w + 20, 16))

            font.render(option, surface, (x_pos, y_pos), 2)
            y_pos += 30