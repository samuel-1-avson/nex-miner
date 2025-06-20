# Cavyn Source/data/scripts/game_states/main_menu_state.py

import pygame
import math
import random
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
        
        # --- Aesthetics & Tech UI ---
        self.master_clock = 0
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.font_main = Font(font_path, (140, 245, 250)) # Bright Cyan
        self.font_dim = Font(font_path, (20, 80, 85))
        self.font_highlight = Font(font_path, (255, 230, 90))
        self.font_red = Font(font_path, (255, 60, 60))
        self.font_green = Font(font_path, (60, 255, 60))
        self.font_blue = Font(font_path, (60, 60, 255))
        
        # Animated selector
        self.selector_y = 70 # The current Y position of the selector
        self.selector_y_target = self.selector_y # The Y position it's moving towards
        
        # Background Effects
        self.scanline_surface = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        for y in range(0, self.game.DISPLAY_SIZE[1], 2):
            pygame.draw.line(self.scanline_surface, (0, 10, 15, 80), (0, y), (self.game.DISPLAY_SIZE[0], y), 1)
        self.hologram_base_img = self.game.item_icons.get('shield') # Re-use the shield icon
        self.bg_elements = [self.create_bg_element() for _ in range(25)]

        # Animated Character Display
        self.player_anim = None
        self.update_player_animation()

    def create_bg_element(self):
        text = f"0x{random.randint(0, 0xFFFFF):05X}"
        pos = [random.randint(0, self.game.DISPLAY_SIZE[0]), random.randint(0, self.game.DISPLAY_SIZE[1])]
        life = random.randint(100, 250)
        return [text, pos, life]

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
                move_sound = 'shoot' # A more 'techy' sound
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
        y_base = 73
        y_spacing = 15
        if self.in_submenu:
            self.selector_y_target = y_base + self.submenu_index * y_spacing
        else:
            self.selector_y_target = y_base + self.selection_index * y_spacing
    
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
        if self.player_anim:
            self.player_anim.play(1/60)
            
        # Animate selector
        self.selector_y += (self.selector_y_target - self.selector_y) * 0.3
        
        # Update background elements
        for i, element in sorted(enumerate(self.bg_elements), reverse=True):
            element[2] -= 1
            if element[2] <= 0: self.bg_elements.pop(i); self.bg_elements.append(self.create_bg_element())

    def render(self, surface):
        surface.fill((2, 4, 16))
        self.render_background(surface)
        self.render_title(surface)
        self.render_character_display(surface)
        self.render_menu_panel(surface)
        self.render_footer_info(surface)
        surface.blit(self.scanline_surface, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)

    def render_background(self, surface):
        # Grid
        grid_color = (10, 30, 45, 100)
        for x in range(0, self.game.DISPLAY_SIZE[0], 24):
            pygame.draw.line(surface, grid_color, (x + (self.master_clock*0.1)%24, 0), (x + (self.master_clock*0.1)%24, self.game.DISPLAY_SIZE[1]))
        for y in range(0, self.game.DISPLAY_SIZE[1], 24):
             pygame.draw.line(surface, grid_color, (0, y + (self.master_clock*0.2)%24), (self.game.DISPLAY_SIZE[0], y+(self.master_clock*0.2)%24))
        # Random background text
        for text, pos, life in self.bg_elements:
            alpha = min(255, life) * 0.4; self.font_dim.color = (self.font_dim.color[0], self.font_dim.color[1], self.font_dim.color[2], alpha)
            self.font_dim.render(text, surface, pos)

    def render_title(self, surface):
        y_offset = 20
        # Main Title with Glitch
        self.render_glitchy_text(surface, "NEX MINER", (surface.get_width()//2, y_offset), self.font_main, scale=3, center=True)
        # Sub-header
        sub_header = "//:HUB INTERFACE v3.1"
        w_sub = self.font_main.width(sub_header); self.font_main.render(sub_header, surface, (surface.get_width()//2 - w_sub//2, y_offset + 25))

    def render_glitchy_text(self, surface, text, pos, font, scale=1, center=False):
        glitch_offset_x = (int(self.master_clock*1.5) % 5) - 2
        glitch_offset_y = (int(self.master_clock*1.1) % 5) - 2
        
        x, y = pos
        w = font.width(text, scale)
        if center: x -= w//2

        self.font_red.render(text, surface, (x + glitch_offset_x, y), scale=scale)
        self.font_green.render(text, surface, (x, y + glitch_offset_y), scale=scale)
        font.render(text, surface, (x, y), scale=scale)

    def render_character_display(self, surface):
        center_x, base_y = 80, 130
        
        # Hologram Base
        if self.hologram_base_img:
            pulse = math.sin(self.master_clock / 20) * 3
            size = (self.hologram_base_img.get_width()*2.5 + pulse, self.hologram_base_img.get_height()*2.5 + pulse)
            pulsing = pygame.transform.scale(self.hologram_base_img, size)
            pos = (center_x - pulsing.get_width()//2, base_y - pulsing.get_height()//2)
            pulsing.set_alpha(100 + pulse*10)
            surface.blit(pulsing, pos, special_flags=pygame.BLEND_RGBA_ADD)

        # Draw character with hologram effect
        if self.player_anim and self.player_anim.img:
            char_img = self.player_anim.img.copy()
            char_img.set_alpha(180) # Semi-transparent
            char_y_bob = math.sin(self.master_clock/30) * 3
            char_pos_x = center_x - char_img.get_width()//2
            char_pos_y = base_y - 25 + char_y_bob
            surface.blit(char_img, (char_pos_x, char_pos_y))
            
            # Hologram scanlines over character
            holo_lines = pygame.Surface(char_img.get_size(), pygame.SRCALPHA)
            for y in range(0, holo_lines.get_height(), 3):
                alpha = 50 + math.sin((y + self.master_clock)/5) * 40
                pygame.draw.line(holo_lines, (100, 200, 220, alpha), (0, y), (holo_lines.get_width(), y))
            surface.blit(holo_lines, (char_pos_x, char_pos_y), special_flags=pygame.BLEND_RGBA_ADD)
            
    def render_menu_panel(self, surface):
        x_base = 160
        options_list = self.play_options if self.in_submenu else self.options
        
        # Animated selector highlight bar
        pygame.draw.line(surface, self.font_highlight.color, (x_base-5, self.selector_y), (x_base+135, self.selector_y), 1)
        pygame.draw.rect(surface, (self.font_highlight.color[0], self.font_highlight.color[1], self.font_highlight.color[2], 15), (x_base-5, self.selector_y - 6, 140, 12))
        
        # Render Menu Items
        y_pos = 70
        for i, option in enumerate(options_list):
            font = self.font_main
            
            w = font.width(option)
            notification_text = ""
            if not self.in_submenu:
                if option == "OPERATIVES" and 'characters' in self.game.unlock_notifications: notification_text = "!"
                if option == "OPERATOR HUB" and 'artifacts' in self.game.unlock_notifications: notification_text = "!"

            if notification_text: self.font_highlight.render(notification_text, surface, (x_base + w + 5, y_pos))
            font.render(option, surface, (x_base, y_pos))
            y_pos += 15

    def render_footer_info(self, surface):
        y_pos = surface.get_height() - 14
        char_name = self.game.characters.get(self.game.save_data['characters']['selected'], {}).get('name', 'UNKNOWN').upper()
        self.font_main.render(f"OPERATIVE_ID: {char_name}", surface, (15, y_pos))
        
        status = "NOMINAL"
        if len(self.game.unlock_notifications) > 0: status = "NEW DATA"
        status_font = self.font_highlight if status == "NEW DATA" else self.font_main
        w = status_font.width(f"SYSTEM STATUS: {status}")
        status_font.render(f"SYSTEM STATUS: {status}", surface, (surface.get_width()-w-15, y_pos))