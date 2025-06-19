# Cavyn Source/data/scripts/game_states/character_select_state.py
import pygame
from ..state import State
from ..text import Font

class CharacterSelectState(State):
    def __init__(self, game):
        super().__init__(game)
        
        base_characters = [k for k in self.game.characters.keys() if k != 'generated_operative']
        self.character_keys = sorted(base_characters) 
        
        if 'generated_operative' in self.game.save_data['characters']['unlocked']:
            self.character_keys.append('generated_operative')
        else: # Add a placeholder for a locked, custom character
             self.character_keys.append('omnipotent')


        try:
            self.selection_index = self.character_keys.index(self.game.save_data['characters']['selected'])
        except ValueError:
            self.selection_index = 0
            
        self.master_clock = 0
        
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.highlight_font = Font(font_path, (255, 230, 90))
        self.locked_font = Font(font_path, (120, 120, 120))
    
    def enter_state(self):
        super().enter_state()
        self.game.clear_notification('characters')
        
    def update(self):
        self.master_clock += 1

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

        if selected_key not in self.game.characters: # Trying to select a locked 'Omnipotent'
             if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()
             return

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
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        pygame.draw.rect(surface, (200, 200, 220, 230), p_rect, 1, 3)

        title = "SELECT OPERATIVE"
        w = self.game.white_font.width(title)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2 + 1, p_rect.top + 5 + 1))
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.top + 5))

        self.render_character_list(surface, p_rect)
        self.render_details_panel(surface, p_rect)
        self.render_banked_coins(surface, p_rect)

        prompt = "Up/Down: Navigate  -  Enter: Select/Unlock  -  Esc: Back"
        w = self.game.white_font.width(prompt)
        pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1))
        self.game.white_font.render(prompt, surface, pos)
    
    def render_character_list(self, surface, p_rect):
        list_y = p_rect.top + 25
        for i, key in enumerate(self.character_keys):
            # Special handling for the 'Omnipotent' visual placeholder
            if key == 'omnipotent' and key not in self.game.characters:
                 char_name = "Omnipotent"
                 is_unlocked = False
            else:
                char = self.game.characters[key]
                char_name = char.get('name', '???')
                is_unlocked = key in self.game.save_data['characters']['unlocked']

            is_selected_save_file = key == self.game.save_data['characters']['selected']

            font = self.game.white_font
            if i == self.selection_index:
                highlight_rect = pygame.Rect(p_rect.left + 5, list_y - 2, 90, 12)
                pygame.draw.rect(surface, (40, 30, 60), highlight_rect, 0, 2)
                font = self.highlight_font
            
            if not is_unlocked: font = self.locked_font
            if is_selected_save_file and is_unlocked: self.game.white_font.render(">", surface, (p_rect.left + 4, list_y))

            font.render(char_name, surface, (p_rect.left + 10, list_y))
            list_y += 12

    def render_details_panel(self, surface, p_rect):
        det_x = p_rect.left + 115
        det_y = p_rect.top + 25
        selected_key = self.character_keys[self.selection_index]

        # Use placeholder data for Omnipotent if not truly generated
        if selected_key == 'omnipotent' and selected_key not in self.game.characters:
             char = {'name': 'Omnipotent', 'desc': '???'}
        else:
             char = self.game.characters[selected_key]
        
        is_unlocked = selected_key in self.game.save_data['characters']['unlocked']
        
        self.highlight_font.render(char['name'], surface, (det_x, det_y))
        y_offset = det_y + 12
        
        # Render description with glitch effect
        self.render_glitchy_text(surface, char.get('desc', 'No data.'), (det_x, y_offset), p_rect.right - det_x - 5)
        
        y_offset += 45
        if not is_unlocked and 'unlock_cost' in char:
             cost = char['unlock_cost']
             can_afford = self.game.save_data['banked_coins'] >= cost
             cost_font = self.highlight_font if can_afford else self.locked_font
             coin_icon = self.game.animation_manager.new('coin_idle').img
             surface.blit(coin_icon, (det_x, y_offset))
             cost_font.render(f"Unlock: {cost}", surface, (det_x + coin_icon.get_width() + 4, y_offset + 1))

    def render_glitchy_text(self, surface, text, pos, line_width):
        glitch_colors = [(140, 245, 150), (255, 150, 40), (80, 150, 255), (255, 90, 90)]
        x, y = pos
        words = text.split(' ')
        space_width = self.game.white_font.width(' ')
        
        for word in words:
            word_width = self.game.white_font.width(word)
            if x + word_width > pos[0] + line_width and x > pos[0]:
                x = pos[0]
                y += self.game.white_font.line_height + self.game.white_font.line_spacing

            if "FABRICATE" in word.upper():
                char_x = x
                for i, char in enumerate(word):
                    color = glitch_colors[(self.master_clock + i) % len(glitch_colors)]
                    char_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), color)
                    char_font.render(char, surface, (char_x, y))
                    char_x += char_font.width(char)
            else:
                self.game.white_font.render(word, surface, (x, y))
            x += word_width + space_width
        
    def render_banked_coins(self, surface, p_rect):
        bank_txt = f"Credits: {self.game.save_data['banked_coins']}"
        bank_w = self.game.white_font.width(bank_txt)
        bank_pos = (p_rect.right - bank_w - 5, p_rect.top + 6)
        coin_icon = self.game.animation_manager.new('coin_idle').img
        surface.blit(coin_icon, (bank_pos[0] - coin_icon.get_width() - 4, bank_pos[1] - 1))
        self.game.white_font.render(bank_txt, surface, bank_pos)