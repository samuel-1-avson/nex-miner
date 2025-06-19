from ..state import State
from ..gameplay_state import GameplayState
from .upgrade_shop_state import UpgradeShopState
from .settings_state import SettingsState
from .character_select_state import CharacterSelectState
from .player_hub_state import PlayerHubState
from .biome_select_state import BiomeSelectState
from .challenge_select_state import ChallengeSelectState # --- NEW ---
import pygame

class MainMenuState(State):
    def __init__(self, game):
        super().__init__(game)
        self.options = ["PLAY", "PLAYER HUB", "CHARACTERS", "UPGRADES", "SETTINGS", "QUIT"]
        self.play_options = ["CLASSIC", "ZEN MODE", "HARDCORE", "CHALLENGES"]
        self.selection_index = 0
        self.submenu_index = 0
        self.in_submenu = False

    def enter_state(self):
        self.selection_index = 0
        self.submenu_index = 0
        self.in_submenu = False

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.in_submenu:
                    if event.key in [pygame.K_DOWN, pygame.K_s]: self.submenu_index = (self.submenu_index + 1) % len(self.play_options)
                    elif event.key in [pygame.K_UP, pygame.K_w]: self.submenu_index = (self.submenu_index - 1 + len(self.play_options)) % len(self.play_options)
                    elif event.key == pygame.K_ESCAPE: self.in_submenu = False
                    elif event.key == pygame.K_RETURN: self.select_submenu_option()
                else:
                    if event.key in [pygame.K_DOWN, pygame.K_s]: self.selection_index = (self.selection_index + 1) % len(self.options)
                    elif event.key in [pygame.K_UP, pygame.K_w]: self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                    elif event.key == pygame.K_RETURN: self.select_option()

    def select_option(self):
        option = self.options[self.selection_index]
        if option == "PLAY": self.in_submenu = True
        elif option == "PLAYER HUB": self.game.push_state(PlayerHubState(self.game))
        elif option == "CHARACTERS": self.game.push_state(CharacterSelectState(self.game))
        elif option == "UPGRADES": self.game.push_state(UpgradeShopState(self.game))
        elif option == "SETTINGS": self.game.push_state(SettingsState(self.game))    
        elif option == "QUIT": self.game.pop_state()

    def select_submenu_option(self):
        option = self.play_options[self.submenu_index]
        if option == "CLASSIC": self.game.push_state(BiomeSelectState(self.game, selected_mode="classic"))
        elif option == "ZEN MODE": self.game.push_state(BiomeSelectState(self.game, selected_mode="zen"))
        elif option == "HARDCORE": self.game.push_state(BiomeSelectState(self.game, selected_mode="hardcore"))
        elif option == "CHALLENGES": self.game.push_state(ChallengeSelectState(self.game)) # --- MODIFIED ---
        self.in_submenu = False

    def render(self, surface):
        surface.fill((22, 19, 40))
        title_text = "CAVYN: RECHARGED"
        title_w = self.game.white_font.width(title_text, 3)
        self.game.black_font.render(title_text, surface, (surface.get_width()//2 - title_w//2 + 2, 32), 3)
        self.game.white_font.render(title_text, surface, (surface.get_width()//2 - title_w//2, 30), 3)

        if self.in_submenu: self.render_menu_options(surface, self.play_options, self.submenu_index)
        else: self.render_menu_options(surface, self.options, self.selection_index)
            
        bank_txt = f"Bank: {self.game.save_data['banked_coins']}"; bank_pos = (12, surface.get_height() - 20)
        coin_icon = self.game.animation_manager.new('coin_idle').img
        surface.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 4, bank_pos[1] - 1))
        self.game.black_font.render(bank_txt, surface, (bank_pos[0] + 1, bank_pos[1] + 1)); self.game.white_font.render(bank_txt, surface, bank_pos)
        hs_txt = f"High Score: {self.game.save_data['high_score']}"; hs_w = self.game.white_font.width(hs_txt); hs_pos = (surface.get_width() - hs_w - 10, surface.get_height() - 20)
        self.game.black_font.render(hs_txt, surface, (hs_pos[0] + 1, hs_pos[1] + 1)); self.game.white_font.render(hs_txt, surface, hs_pos)

    def render_menu_options(self, surface, options_list, current_selection_index):
        y_pos = 80
        for i, option in enumerate(options_list):
            font = self.game.white_font if i != current_selection_index else self.game.black_font
            w = self.game.white_font.width(option, 2)
            x_pos = surface.get_width()//2 - w//2
            if i == current_selection_index: pygame.draw.rect(surface, (255, 230, 90), (x_pos - 10, y_pos - 3, w + 20, 16))
            font.render(option, surface, (x_pos, y_pos), 2); y_pos += 25