# Cavyn Source/data/scripts/game_states/character_select_state.py
import pygame
import math
from ..state import State
from ..text import Font

class CharacterSelectState(State):
    def __init__(self, game):
        super().__init__(game)
        
        base_characters = [k for k in self.game.characters.keys() if k != 'generated_operative']
        self.character_keys = sorted(base_characters) 
        
        if 'generated_operative' in self.game.save_data['characters']['unlocked']:
            self.character_keys.append('generated_operative')
        
        try:
            self.selection_index = self.character_keys.index(self.game.save_data['characters']['selected'])
        except ValueError:
            self.selection_index = 0
            
        self.master_clock = 0
        
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.font_main = Font(font_path, (140, 245, 250))
        self.font_highlight = Font(font_path, (255, 230, 90))
        self.font_title = Font(font_path, (255, 255, 255))
        self.font_locked = Font(font_path, (80, 80, 90))
        self.font_cost_can_afford = Font(font_path, (60, 255, 60))
        self.font_cost_cannot_afford = Font(font_path, (255, 60, 60))
        self.font_red = Font(font_path, (255, 60, 60))
        self.font_blue = Font(font_path, (60, 60, 255))
        self.hologram_base_img = self.game.item_icons.get('shield')
        self.player_anim = None
        self.update_player_animation()

    def update_player_animation(self):
        selected_key = self.character_keys[self.selection_index]
        self.player_anim = self.game.animation_manager.new(selected_key + '_idle')
    
    def enter_state(self):
        super().enter_state()
        self.game.clear_notification('characters')
        
    def update(self):
        self.master_clock += 1
        if self.player_anim:
            self.player_anim.play(1/60)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.character_keys)
                    self.update_player_animation()
                    if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.character_keys)) % len(self.character_keys)
                    self.update_player_animation()
                    if 'shoot' in self.game.sounds: self.game.sounds['shoot'].play()
                elif event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key == pygame.K_RETURN:
                    self.handle_selection()
    
    def handle_selection(self):
        selected_key = self.character_keys[self.selection_index]
        unlocked_chars = self.game.save_data['characters']['unlocked']

        def play_confirm_sound():
            if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()

        if selected_key in unlocked_chars:
            self.game.save_data['characters']['selected'] = selected_key
            self.game.write_save(self.game.save_data)
            play_confirm_sound()
            self.game.pop_state()
        else:
            char_info = self.game.characters[selected_key]
            cost = char_info.get('unlock_cost', 0)
            if self.game.save_data['banked_coins'] >= cost:
                self.game.save_data['banked_coins'] -= cost
                self.game.save_data['characters']['unlocked'].append(selected_key)
                self.game.save_data['characters']['selected'] = selected_key
                self.game.notify_unlock('characters')
                self.game.write_save(self.game.save_data)
                play_confirm_sound()
                self.game.pop_state()
            else:
                 if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()
    
    def render(self, surface):
        surface.fill((2, 4, 16))
        self.render_character_display(surface)
        
        # --- Header ---
        self.font_title.render("[ SELECT OPERATIVE ]", surface, (surface.get_width()//2 - self.font_title.width("[ SELECT OPERATIVE ]")//2, 12))
        credits_text = f"CREDITS: {self.game.save_data['banked_coins']}"
        self.font_main.render(credits_text, surface, (surface.get_width() - self.font_main.width(credits_text) - 15, 12))
        pygame.draw.line(surface, self.font_main.color, (15, 25), (surface.get_width()-15, 25), 1)
        
        # --- Lists ---
        self.render_character_list(surface)
        self.render_details_panel(surface)

        # --- Footer ---
        prompt = "SELECT [↑/↓]  -  CONFIRM/UNLOCK [ENTER]  -  BACK [ESC]"
        w = self.font_main.width(prompt)
        self.font_main.render(prompt, surface, (surface.get_width()//2 - w//2, surface.get_height() - 15))
    
    def render_character_list(self, surface):
        x_base, y_base = 20, 45
        for i, key in enumerate(self.character_keys):
            char = self.game.characters[key]
            char_name = char.get('name', '???')
            is_unlocked = key in self.game.save_data['characters']['unlocked']
            is_selected_save_file = key == self.game.save_data['characters']['selected']

            font = self.font_main if is_unlocked else self.font_locked
            prefix = ""
            
            if i == self.selection_index:
                font = self.font_highlight
                prefix += "> "
            if is_selected_save_file and is_unlocked:
                prefix += "[A] "
                
            font.render(prefix + char_name, surface, (x_base, y_base + i * 12))

    def render_details_panel(self, surface):
        x_base, y_base = 120, 40
        selected_key = self.character_keys[self.selection_index]
        char = self.game.characters[selected_key]
        is_unlocked = selected_key in self.game.save_data['characters']['unlocked']
        
        self.font_title.render(char['name'], surface, (x_base, y_base), scale=2)
        y_pos = y_base + 20
        self.font_main.render(char['desc'], surface, (x_base, y_pos), line_width=surface.get_width() - x_base - 15)
        
        y_pos += 35
        if not is_unlocked and 'unlock_cost' in char:
            cost = char['unlock_cost']
            can_afford = self.game.save_data['banked_coins'] >= cost
            cost_font = self.font_cost_can_afford if can_afford else self.font_cost_cannot_afford
            cost_font.render(f"UNLOCK COST: {cost}", surface, (x_base, y_pos))

    def render_character_display(self, surface):
        center_x, base_y = 60, surface.get_height() - 40
        
        if self.hologram_base_img:
            pulse = math.sin(self.master_clock / 15) * 4
            size = (self.hologram_base_img.get_width() * 4 + pulse, self.hologram_base_img.get_height() + pulse/2)
            pulsing = pygame.transform.scale(self.hologram_base_img, size)
            pos = (center_x - pulsing.get_width()//2, base_y - pulsing.get_height()//2)
            pulsing.set_alpha(80 + pulse*8)
            surface.blit(pulsing, pos, special_flags=pygame.BLEND_RGBA_ADD)

        if self.player_anim and self.player_anim.img:
            char_img = self.player_anim.img.copy()
            char_img_large = pygame.transform.scale(char_img, (char_img.get_width()*2, char_img.get_height()*2))
            char_img_large.set_alpha(200)
            
            y_bob = math.sin(self.master_clock/30) * 4
            char_pos_x = center_x - char_img_large.get_width()//2
            char_pos_y = base_y - 35 + y_bob
            
            # Chromatic aberration
            offset = int(self.master_clock/4 % 5 - 2)
            
            # --- FIX ---
            # Correctly create tinted versions of the sprite instead of calling a non-existent method
            red_image = char_img_large.copy(); red_image.fill(self.font_red.color, special_flags=pygame.BLEND_RGBA_MULT)
            blue_image = char_img_large.copy(); blue_image.fill(self.font_blue.color, special_flags=pygame.BLEND_RGBA_MULT)

            surface.blit(red_image, (char_pos_x + offset, char_pos_y), special_flags=pygame.BLEND_RGBA_ADD)
            surface.blit(blue_image, (char_pos_x - offset, char_pos_y), special_flags=pygame.BLEND_RGBA_ADD)
            
            # Main image
            surface.blit(char_img_large, (char_pos_x, char_pos_y))
            
            # Hologram scanlines
            for i in range(0, char_img_large.get_height(), 4):
                 alpha = 70 + math.sin((i + self.master_clock*2)/6) * 60
                 line_y = char_pos_y + i
                 if line_y < base_y + 10:
                    pygame.draw.line(surface, (150, 220, 255, alpha), (char_pos_x, line_y), (char_pos_x+char_img_large.get_width(), line_y), 1)