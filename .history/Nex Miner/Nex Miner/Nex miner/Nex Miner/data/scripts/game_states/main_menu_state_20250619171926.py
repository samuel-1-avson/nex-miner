# Cavyn Source/data/scripts/game_states/main_menu_state.py

import pygame
import math
import random
from ..state import State
from ..text import Font
from ..core_funcs import load_img
from ..gameplay_state import GameplayState # Keep for mode selection
from .upgrade_shop_state import UpgradeShopState
from .settings_state import SettingsState
from .character_select_state import CharacterSelectState
from .player_hub_state import PlayerHubState
from .biome_select_state import BiomeSelectState
from .challenge_select_state import ChallengeSelectState
from ..daily_challenge_state import DailyChallengeState


class MainMenuState(State):
    def __init__(self, game):
        super().__init__(game)
        # --- Core Menu Logic ---
        self.options = ["MISSIONS", "OPERATOR HUB", "OPERATIVES", "UPGRADES", "SETTINGS", "QUIT"]
        self.play_options = ["STANDARD OP", "ZEN MODE", "HARDCORE", "SIMULATIONS", "DAILY DIRECTIVE"]
        self.selection_index = 0
        self.submenu_index = 0
        self.in_submenu = False
        
        # --- Minimalist Aesthetics ---
        self.master_clock = 0
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.font_main = Font(font_path, (200, 210, 220)) # Off-white for main text
        self.font_highlight = Font(font_path, (255, 230, 90)) # Gold for selection
        self.font_title = Font(font_path, (255, 255, 255))
        
        self.selector_y = 0
        self.selector_y_target = 0
        
        # Background Effects
        self.bg_scroll = 0
        
        # Animated Character Display
        self.player_anim = None
        self.update_player_animation()

    def enter_state(self):
        super().enter_state()
        self.selection_index = 0
        self.submenu_index = 0
        self.in_submenu = False
        self.update_player_animation()
        self.update_selector_target()
        self.selector_y = self.selector_y_target
        pygame.mixer.music.set_volume(0.3 * self.game.save_data['settings'].get('music_volume', 1.0))

    def update_player_animation(self):
        selected_char_key = self.game.save_data['characters']['selected']
        self.player_anim = self.game.animation_manager.new(selected_char_key + '_idle')

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                move_sound = 'shoot'
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    if move_sound in self.game.sounds: self.game.sounds[move_sound].play()
                    if self.in_submenu: self.submenu_index = (self.submenu_index + 1) % len(self.play_options)
                    else: self.selection_index = (self.selection_index + 1) % len(self.options)
                    self.update_selector_target()
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    if move_sound in self.game.sounds: self.game.sounds[move_sound].play()
                    if self.in_submenu: self.submenu_index = (self.submenu_index - 1 + len(self.play_options)) % len(self.play_options)
                    else: self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                    self.update_selector_target()
                elif event.key == pygame.K_ESCAPE:
                    if self.in_submenu: self.in_submenu = False; self.game.sounds['combo_end'].play(); self.update_selector_target()
                elif event.key == pygame.K_RETURN:
                    if self.in_submenu: self.select_submenu_option()
                    else: self.select_option()

    def update_selector_target(self):
        base_y = 100
        spacing = 15
        if self.in_submenu:
            self.selector_y_target = base_y + self.submenu_index * spacing
        else:
            self.selector_y_target = base_y + self.selection_index * spacing
    
    def select_option(self):
        option = self.options[self.selection_index]
        self.game.sounds['coin'].play()
        if option == "MISSIONS":
            self.in_submenu = True; self.submenu_index = 0; self.update_selector_target()
        elif option == "OPERATOR HUB": self.game.push_state(PlayerHubState(self.game))
        elif option == "OPERATIVES": self.game.push_state(CharacterSelectState(self.game))
        elif option == "UPGRADES": self.game.push_state(UpgradeShopState(self.game))
        elif option == "SETTINGS": self.game.push_state(SettingsState(self.game))    
        elif option == "QUIT": self.game.pop_state()

    def select_submenu_option(self):
        option = self.play_options[self.submenu_index]
        self.game.sounds['upgrade'].play()
        if option == "STANDARD OP": self.game.push_state(BiomeSelectState(self.game, selected_mode="classic"))
        elif option == "ZEN MODE": self.game.push_state(BiomeSelectState(self.game, selected_mode="zen"))
        elif option == "HARDCORE": self.game.push_state(BiomeSelectState(self.game, selected_mode="hardcore"))
        elif option == "SIMULATIONS": self.game.push_state(ChallengeSelectState(self.game))
        elif option == "DAILY DIRECTIVE": self.game.push_state(DailyChallengeState(self.game))
        self.in_submenu = False

    def update(self):
        self.master_clock += 1
        self.bg_scroll = (self.bg_scroll + 0.1) % 16
        if self.player_anim:
            self.player_anim.play(1/60)
        self.selector_y += (self.selector_y_target - self.selector_y) * 0.2

    def render(self, surface):
        surface.fill((18, 16, 28))
        self.render_background_grid(surface)
        self.render_title(surface)
        self.render_character(surface)
        self.render_menu_options(surface)

    def render_background_grid(self, surface):
        grid_color = (25, 22, 40)
        for x in range(0, surface.get_width() + 16, 16):
            pygame.draw.line(surface, grid_color, (x - self.bg_scroll, 0), (x - self.bg_scroll, surface.get_height()))
        for y in range(0, surface.get_height() + 16, 16):
            pygame.draw.line(surface, grid_color, (0, y - self.bg_scroll), (surface.get_width(), y - self.bg_scroll))

    def render_title(self, surface):
        y_pos = 35
        self.font_title.render("NEX MINER", surface, (surface.get_width()//2 - self.font_title.width("NEX MINER", 3)//2, y_pos), scale=3)

    def render_character(self, surface):
        if not self.player_anim or not self.player_anim.img: return
        
        center_x, base_y = 65, 130
        
        # Simple glowing base
        glow_radius = 20
        alpha = 50 + math.sin(self.master_clock / 30) * 20
        pygame.draw.circle(surface, (255, 230, 90, alpha), (center_x, base_y), glow_radius, 0)
        
        # Character
        char_img = self.player_anim.img
        char_pos_x = center_x - char_img.get_width()//2
        char_pos_y = base_y - 14 + math.sin(self.master_clock/25) * 2
        surface.blit(char_img, (char_pos_x, char_pos_y))
        
    def render_menu_options(self, surface):
        center_x = surface.get_width() * 0.6
        base_y = 100
        spacing = 15
        
        options_list = self.play_options if self.in_submenu else self.options
        
        # Render selector first
        selector_w = self.font_highlight.width(">")
        surface.blit(self.font_highlight.letters[self.font_highlight.font_order.index('>')], (center_x - 30, self.selector_y))
        
        # Render options
        y = base_y
        for i, option in enumerate(options_list):
            font_to_use = self.font_highlight if i == (self.submenu_index if self.in_submenu else self.selection_index) else self.font_main
            
            notification_text = ""
            if not self.in_submenu:
                if option == "OPERATIVES" and 'characters' in self.game.unlock_notifications: notification_text = "!"
                if option == "OPERATOR HUB" and 'artifacts' in self.game.unlock_notifications: notification_text = "!"

            font_to_use.render(option, surface, (center_x, y))
            if notification_text:
                self.font_highlight.render(notification_text, surface, (center_x + font_to_use.width(option) + 5, y - 1))
            
            y += spacing