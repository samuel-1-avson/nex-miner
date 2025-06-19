# Cavyn Source/data/scripts/game_states/main_menu_state.py

import pygame
import math
from ..state import State
from ..text import Font
from ..core_funcs import load_img
from ..gameplay_state import GameplayState, render_panel_9slice
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
        # Core Menu Logic
        self.options = ["MISSIONS", "OPERATOR HUB", "OPERATIVES", "UPGRADES", "SETTINGS", "QUIT"]
        self.play_options = ["STANDARD OP", "ZEN MODE", "HARDCORE", "SIMULATIONS", "DAILY DIRECTIVE"]
        self.selection_index = 0
        self.submenu_index = 0
        self.in_submenu = False
        
        # --- NEW: Enhanced Visuals & UX ---
        self.master_clock = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.highlight_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))

        # Dynamic Background
        try:
            # --- FIX: Corrected the path to the background images ---
            self.bg_far = load_img(self.game.get_path('data', 'images', 'backgrounds', 'background.png'))
            self.bg_near = load_img(self.game.get_path('data', 'images', 'backgrounds', 'background_sunken.png'))
            self.bg_near.set_alpha(150)
        except Exception as e:
            print(f"Warning: Could not load menu backgrounds. {e}")
            self.bg_far, self.bg_near = None, None
        self.scroll_far = 0
        self.scroll_near = 0

        # Animated Character Display
        self.player_anim = None
        self.update_player_animation()
        self.platform_img = load_img(self.game.get_path('data', 'images', 'tile.png'))
        self.platform_img = pygame.transform.scale(self.platform_img, (self.platform_img.get_width() * 2, self.platform_img.get_height()))

    def enter_state(self):
        super().enter_state()
        self.selection_index = 0
        self.submenu_index = 0
        self.in_submenu = False
        # Update the character animation in case it was changed
        self.update_player_animation()

    def update_player_animation(self):
        selected_char_key = self.game.save_data['characters']['selected']
        self.player_anim = self.game.animation_manager.new(selected_char_key + '_idle')

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                move_sound = 'block_land'
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    if 'block_land' in self.game.sounds: self.game.sounds['block_land'].play()
                    if self.in_submenu: self.submenu_index = (self.submenu_index + 1) % len(self.play_options)
                    else: self.selection_index = (self.selection_index + 1) % len(self.options)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    if 'block_land' in self.game.sounds: self.game.sounds['block_land'].play()
                    if self.in_submenu: self.submenu_index = (self.submenu_index - 1 + len(self.play_options)) % len(self.play_options)
                    else: self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                elif event.key == pygame.K_ESCAPE:
                    if self.in_submenu: self.in_submenu = False; self.game.sounds['combo_end'].play()
                elif event.key == pygame.K_RETURN:
                    if self.in_submenu: self.select_submenu_option()
                    else: self.select_option()

    def select_option(self):
        option = self.options[self.selection_index]
        self.game.sounds['coin'].play()
        if option == "MISSIONS": self.in_submenu = True
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
        if self.bg_far:
            self.scroll_far = (self.scroll_far + 0.1) % (self.bg_far.get_height() if self.bg_far else 1)
        if self.bg_near:
            self.scroll_near = (self.scroll_near + 0.3) % (self.bg_near.get_height() if self.bg_near else 1)
        if self.player_anim:
            self.player_anim.play(1/60)

    def render_background(self, surface):
        if self.bg_far:
            surface.blit(self.bg_far, (0, self.scroll_far))
            surface.blit(self.bg_far, (0, self.scroll_far - self.bg_far.get_height()))
        if self.bg_near:
            surface.blit(self.bg_near, (0, self.scroll_near))
            surface.blit(self.bg_near, (0, self.scroll_near - self.bg_near.get_height()))

    def render_title(self, surface):
        title_text = "NEX MINER"
        y_offset = math.sin(self.master_clock / 40) * 3
        
        title_surf = pygame.Surface(self.game.display.get_size(), pygame.SRCALPHA)
        
        w = self.game.white_font.width(title_text, 3)
        x = surface.get_width() // 2 - w // 2
        
        self.game.black_font.render(title_text, title_surf, (x + 2, 32 + y_offset + 2), scale=3)
        self.game.white_font.render(title_text, title_surf, (x, 32 + y_offset), scale=3)
        surface.blit(title_surf, (0, 0))

    def render(self, surface):
        # Background and Title
        self.render_background(surface)
        self.render_title(surface)
        
        # Render Animated Character
        if self.player_anim and self.player_anim.img:
            char_pos_x = 40
            char_pos_y = 90
            surface.blit(self.platform_img, (char_pos_x - 8, char_pos_y + 16))
            self.player_anim.render(surface, (char_pos_x, char_pos_y))

        # Main menu panel
        panel_w = 140
        panel_x = surface.get_width() // 2 - panel_w // 2 + 30
        panel_h = 105 if self.in_submenu else 125
        panel_y = 65
        
        options_list = self.play_options if self.in_submenu else self.options
        current_selection = self.submenu_index if self.in_submenu else self.selection_index
        panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)

        render_panel_9slice(surface, panel_rect, self.panel_img, 8)
        self.render_menu_options(surface, options_list, current_selection, panel_rect)
            
        # --- FIX: Removed the info box that showed bank/high score ---
        # The code that rendered the bottom panel has been deleted.

    def render_menu_options(self, surface, options_list, current_selection_index, panel_rect):
        y_pos = panel_rect.top + 10
        x_base = panel_rect.left + 15
        
        for i, option in enumerate(options_list):
            font = self.game.white_font
            w = font.width(option)
            x_pos = panel_rect.centerx - w // 2

            # Notification Logic
            notification_text = ""
            if option == "OPERATIVES" and 'characters' in self.game.unlock_notifications: notification_text = "!"
            if option == "OPERATOR HUB" and 'artifacts' in self.game.unlock_notifications: notification_text = "!"

            if i == current_selection_index:
                # Animated Selector
                selector_offset = math.sin(self.master_clock / 10) * 2
                self.highlight_font.render(">", surface, (x_pos - 10 + selector_offset, y_pos))
                self.highlight_font.render(option, surface, (x_pos, y_pos))
                if notification_text: self.highlight_font.render(notification_text, surface, (x_pos + w + 5, y_pos - 1))
            else:
                font.render(option, surface, (x_pos, y_pos))
                if notification_text: self.highlight_font.render(notification_text, surface, (x_pos + w + 5, y_pos - 1))
            
            y_pos += 16