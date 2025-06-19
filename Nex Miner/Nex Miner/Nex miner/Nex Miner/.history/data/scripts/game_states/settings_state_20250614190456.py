# Cavyn Source/data/scripts/game_states/settings_state.py
import pygame
from ..state import State
from ..text import Font # Import the Font class to create new instances

class SettingsState(State):
    """
    A state for configuring game settings like volume and screen shake.
    """
    def __init__(self, game):
        super().__init__(game)
        # The order of this list determines the order in the menu
        self.options_keys = ["sfx_volume", "music_volume", "screen_shake"]
        self.selection_index = 0
        self.bar_width = 80
        self.bar_height = 8
        
        # UI colors
        self.panel_color = (15, 12, 28, 220)
        self.border_color = (200, 200, 220, 230)
        self.highlight_color = (255, 230, 90)
        self.bar_fill_color = (100, 150, 255)
        self.bar_bg_color = (10, 5, 20)
        
        # Pre-create all necessary fonts to avoid creating them in the render loop
        font_path = self.game.get_path('data', 'fonts', 'small_font.png')
        self.highlight_font = Font(font_path, self.highlight_color)
        self.font_on = Font(font_path, (120, 220, 130))
        self.font_off = Font(font_path, (200, 80, 80))

    def enter_state(self):
        """Reset the selection when entering the state."""
        self.selection_index = 0

    def exit_state(self):
        """Save the settings when leaving the state."""
        self.game.write_save(self.game.save_data)

    def handle_events(self, events):
        super().handle_events(events)
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.options_keys)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.options_keys)) % len(self.options_keys)
                elif event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                else: # Handle value changes for the selected option
                    self.change_option_value(event.key)

    def change_option_value(self, key):
        """Modifies the value of the currently selected setting."""
        current_option = self.options_keys[self.selection_index]
        settings = self.game.save_data['settings']
        
        if current_option.endswith("_volume"): # Handle volume sliders
            increment = 0.05
            if key in [pygame.K_RIGHT, pygame.K_d]:
                settings[current_option] = min(1.0, round(settings[current_option] + increment, 2))
            elif key in [pygame.K_LEFT, pygame.K_a]:
                settings[current_option] = max(0.0, round(settings[current_option] - increment, 2))
            
            # Apply settings live
            self.game.apply_settings()
            if current_option == "sfx_volume": self.game.sounds['coin'].play()
            
        elif current_option == "screen_shake": # Handle toggles
            if key in [pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN]:
                settings[current_option] = not settings[current_option]
    
    def render(self, surface):
        surface.fill((22, 19, 40)) # Background

        # Main panel
        p_rect = pygame.Rect(30, 15, self.game.DISPLAY_SIZE[0] - 60, self.game.DISPLAY_SIZE[1] - 30)
        p_surf = pygame.Surface(p_rect.size, pygame.SRCALPHA)
        p_surf.fill(self.panel_color)
        surface.blit(p_surf, p_rect.topleft)
        pygame.draw.rect(surface, self.border_color, p_rect, 1, 3)
        
        # Title
        title = "SETTINGS"
        w = self.game.white_font.width(title, 2)
        self.game.black_font.render(title, surface, (surface.get_width()//2 - w//2 + 2, p_rect.top + 10), scale=2)
        self.game.white_font.render(title, surface, (surface.get_width()//2 - w//2, p_rect.top + 8), scale=2)
        
        # Divider Line
        pygame.draw.line(surface, self.border_color, (p_rect.left + 10, p_rect.top + 30), (p_rect.right - 10, p_rect.top + 30), 1)

        # Options list
        y_pos = p_rect.top + 40
        for i, key in enumerate(self.options_keys):
            name_text = key.replace('_', ' ').upper()
            name_pos = (p_rect.left + 15, y_pos)

            # CORRECTED: Use the correct font object for the desired color
            if i == self.selection_index:
                self.highlight_font.render(name_text, surface, name_pos)
            else:
                self.game.white_font.render(name_text, surface, name_pos)

            # Render the value editor for the option
            self.render_option_editor(surface, key, p_rect, y_pos)
            y_pos += 25

        # Bottom prompt
        prompt = "Up/Down: Select - Left/Right: Change - Esc: Save & Back"
        w = self.game.white_font.width(prompt)
        pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, p_rect.bottom - 12)
        self.game.black_font.render(prompt, surface, (pos[0] + 1, pos[1] + 1))
        self.game.white_font.render(prompt, surface, pos)

    def render_option_editor(self, surface, key, p_rect, y_pos):
        editor_x = p_rect.left + 110
        value = self.game.save_data['settings'][key]
        
        if key.endswith("_volume"): # Draw a percentage bar
            # Background bar
            pygame.draw.rect(surface, self.bar_bg_color, (editor_x, y_pos, self.bar_width, self.bar_height))
            # Filled portion
            fill_width = int(self.bar_width * value)
            pygame.draw.rect(surface, self.bar_fill_color, (editor_x, y_pos, fill_width, self.bar_height))
            # Text percentage
            percent_text = f"{int(value * 100)}%"
            self.game.white_font.render(percent_text, surface, (editor_x + self.bar_width + 8, y_pos + 1))
            
        elif isinstance(value, bool): # Draw an ON/OFF toggle
            # CORRECTED: Use the pre-created font for ON/OFF state
            if value:
                self.font_on.render("[ON]", surface, (editor_x, y_pos))
            else:
                self.font_off.render("[OFF]", surface, (editor_x, y_pos))