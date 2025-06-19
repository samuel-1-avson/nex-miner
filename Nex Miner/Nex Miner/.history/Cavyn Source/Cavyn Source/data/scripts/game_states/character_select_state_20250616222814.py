# Cavyn Source/data/scripts/game_states/character_select_state.py
import pygame
from ..state import State
from ..text import Font

class CharacterSelectState(State):
    def __init__(self, game):
        super().__init__(game)
        self.character_keys = list(self.game.characters.keys())
        try:
            # Start selection at the currently selected character
            self.selection_index = self.character_keys.index(self.game.save_data['characters']['selected'])
        except ValueError:
            self.selection_index = 0

        # UI colors and fonts
        self.panel_color = (15, 12, 28, 220)
        self.border_color = (200, 200, 220, 230)
        self.highlight_color = (255, 230, 90)
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.highlight_font = Font(font_path, self.highlight_color)
        self.locked_font = Font(font_path, (120, 120, 120))
        self.cant_afford_font = Font(font_path, (200, 80, 80))
        self.can_afford_font = Font(font_path, (140, 245, 150))
    
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.character_keys)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.character_keys)) % len(self.character_keys)
                elif event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key == pygame.K_RETURN:
                    self.handle_selection()
    
    def handle_selection(self):
        selected_key = self.character_keys[self.selection_index]
        unlocked_chars = self.game.save_data['characters']['unlocked']

        def play_confirm_sound():
            if 'upgrade' in self.game.sounds:
                self.game.sounds['upgrade'].play()
            elif 'coin' in self.game.sounds:
                self.game.sounds['coin'].play()

        if selected_key in unlocked_chars:
            # Select the character if already unlocked
            self.game.save_data['characters']['selected'] = selected_key
            self.game.write_save(self.game.save_data)
            play_confirm_sound()
            self.game.pop_state() # Go back to main menu
        else:
            # Try to unlock the character
            char_info = self.game.characters[selected_key]
            cost = char_info['unlock_cost']
            if self.game.save_data['banked_coins'] >= cost:
                self.game.save_data['banked_coins'] -= cost
                self.game.save_data['characters']['unlocked'].append(selected_key)
                # --- IMPROVEMENT: Automatically select the character upon unlocking. ---
                self.game.save_data['characters']['selected'] = selected_key
                self.game.write_save(self.game.save_data)
                play_confirm_sound()
                self.game.pop_state()
    
    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        p_surf = pygame.Surface(p_rect.size, pygame.SRCALPHA)
        p_surf.fill(self.panel_color)
        surface.blit(p_surf, p_rect.topleft)
        pygame.draw.rect(surface, self.border_color, p_rect, 1, 3)

        title = "SELECT CHARACTER"
        w = self.game.white_font.width(title, 3)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2 + 2, p_rect.top + 10), 3)
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.top + 8), 3)

        self.render_character_list(surface, p_rect)
        self.render_details_panel(surface, p_rect)
        self.render_banked_coins(surface, p_rect)

        prompt = "Up/Down: Navigate  -  Enter: Select/Unlock  -  Esc: Back"
        w = self.game.white_font.width(prompt)
        pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1))
        self.game.white_font.render(prompt, surface, pos)
    
    def render_character_list(self, surface, p_rect):
        list_y = p_rect.top + 45
        for i, key in enumerate(self.character_keys):
            char = self.game.characters[key]
            is_unlocked = key in self.game.save_data['characters']['unlocked']
            is_selected_char = key == self.game.save_data['characters']['selected']

            font = self.game.white_font
            if i == self.selection_index:
                highlight_rect = pygame.Rect(p_rect.left + 5, list_y - 2, 90, 12)
                pygame.draw.rect(surface, (40, 30, 60, 150), highlight_rect, 0)
                font = self.highlight_font
            
            if not is_unlocked:
                font = self.locked_font

            font.render(char['name'], surface, (p_rect.left + 10, list_y))

            if is_selected_char:
                self.game.white_font.render(">", surface, (p_rect.left + 4, list_y))

            list_y += 14

    def render_details_panel(self, surface, p_rect):
        det_x = p_rect.left + 110
        det_y = p_rect.top + 45
        selected_key = self.character_keys[self.selection_index]
        char = self.game.characters[selected_key]
        is_unlocked = selected_key in self.game.save_data['characters']['unlocked']
        is_selected_char = selected_key == self.game.save_data['characters']['selected']
        
        self.highlight_font.render(char['name'], surface, (det_x, det_y))
        
        y_offset = det_y + 12
        for line in char['desc'].splitlines():
            self.game.white_font.render(line, surface, (det_x, y_offset), line_width=160)
            y_offset += 10
        
        y_offset += 10 # Extra spacing
        if is_selected_char:
             self.can_afford_font.render("[SELECTED]", surface, (det_x, y_offset))
        elif is_unlocked:
             self.game.white_font.render("[SELECT]", surface, (det_x, y_offset))
        else: # Character is locked
            cost = char['unlock_cost']
            can_afford = self.game.save_data['banked_coins'] >= cost
            font = self.can_afford_font if can_afford else self.cant_afford_font
            coin_icon = self.game.animation_manager.new('coin_idle').img
            surface.blit(coin_icon, (det_x, y_offset))
            font.render(f"[Unlock for {cost}]", surface, (det_x + coin_icon.get_width() + 4, y_offset + 1))

    def render_banked_coins(self, surface, p_rect):
        bank_txt = f"Bank: {self.game.save_data['banked_coins']}"
        bank_w = self.game.white_font.width(bank_txt)
        bank_pos = (p_rect.right - bank_w - 15, p_rect.top + 35)
        coin_icon = self.game.animation_manager.new('coin_idle').img
        surface.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 4, bank_pos[1] - 1))
        self.game.black_font.render(bank_txt, surface, (bank_pos[0] + 1, bank_pos[1] + 1))
        self.game.white_font.render(bank_txt, surface, bank_pos)