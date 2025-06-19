import pygame
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice, GameplayState

class BiomeSelectState(State):
    def __init__(self, game, selected_mode):
        super().__init__(game)
        self.mode = selected_mode
        self.unlocked_biomes = self.game.save_data['biomes_unlocked']
        self.selection_index = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.font_locked = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (120, 120, 130))
        self.font_title = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.game.biomes)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.game.biomes)) % len(self.game.biomes)
                elif event.key == pygame.K_RETURN:
                    self.select_biome()
    
    def select_biome(self):
        selected_biome_info = self.game.biomes[self.selection_index]
        if selected_biome_info['name'] in self.unlocked_biomes:
            # Pop this state, then push gameplay state with the selected biome
            self.game.pop_state()
            self.game.push_state(GameplayState(self.game, mode=self.mode, start_biome_index=self.selection_index))
        else:
            # Play a "fail" or "locked" sound
            if 'combo_end' in self.game.sounds: self.game.sounds['combo_end'].play()

    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(30, 15, self.game.DISPLAY_SIZE[0] - 60, self.game.DISPLAY_SIZE[1] - 30)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)

        title = "SELECT STARTING BIOME"
        w = self.game.white_font.width(title, 2)
        self.game.white_font.render(title, surface, (surface.get_width()//2 - w//2, p_rect.top + 8), scale=2)

        pygame.draw.line(surface, (200, 200, 220, 100), (p_rect.left+10, p_rect.top + 30), (p_rect.right-10, p_rect.top+30), 1)
        
        y_offset = p_rect.top + 40
        for i, biome in enumerate(self.game.biomes):
            is_unlocked = biome['name'] in self.unlocked_biomes
            is_selected = i == self.selection_index

            font = self.font_locked
            if is_unlocked:
                font = self.font_title if is_selected else self.game.white_font
            
            text = biome['name'] if is_unlocked else '??? ?????'
            w = font.width(text)
            x_pos = surface.get_width()//2 - w//2
            
            if is_selected:
                pygame.draw.rect(surface, (255, 230, 90, 50), (x_pos-5, y_offset-2, w+10, 12), border_radius=2)
            
            font.render(text, surface, (x_pos, y_offset))
            y_offset += 15

        prompt = "Enter: Start Run  -  Esc: Back"
        w = self.game.white_font.width(prompt); pos = (surface.get_width()//2-w//2, p_rect.bottom - 12)
        self.game.white_font.render(prompt, surface, pos)