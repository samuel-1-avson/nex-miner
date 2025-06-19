
# data/scripts/game_states/game_over_state.py
import pygame, math
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice

class GameOverState(State):
    def __init__(self, game, score, background_surf):
        super().__init__(game)
        self.score = score
        self.background_surf = background_surf
        self.new_high_score = False
        self.run_coins_banked = False
        self.master_clock = 0
        self.end_coin_count = 0
        self.options = ["RESTART", "MAIN MENU"]
        self.selection_index = 0
        
        self.highlight_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()

    def enter_state(self):
        super().enter_state()
        if self.score > self.game.save_data['high_score']:
            self.game.save_data['high_score'] = self.score
            self.new_high_score = True
            # The save is now only written once the coins are banked
            
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.run_coins_banked:
                    if event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.selection_index = (self.selection_index + 1) % len(self.options)
                    elif event.key in [pygame.K_UP, pygame.K_w]:
                        self.selection_index = (self.selection_index - 1 + len(self.options)) % len(self.options)
                    elif event.key == pygame.K_RETURN:
                        self.select_option()

    def select_option(self):
        # Import GameplayState here, inside the method, to break the circular dependency
        from ..gameplay_state import GameplayState
        
        option = self.options[self.selection_index]
        if option == "RESTART":
            self.game.pop_state() 
            self.game.pop_state() 
            self.game.push_state(GameplayState(self.game))
        elif option == "MAIN MENU":
            self.game.pop_state() 
            self.game.pop_state()

    def update(self):
        self.master_clock += 1
        if self.end_coin_count < self.score:
            if self.master_clock % 3 == 0 and 'coin_end' in self.game.sounds:
                self.game.sounds['coin_end'].play()
            
            # This makes the counter speed up as it gets closer to the end
            increment = 1 + (self.score - self.end_coin_count) // 20
            self.end_coin_count = min(self.end_coin_count + increment, self.score)

        elif not self.run_coins_banked:
            self.game.save_data['banked_coins'] += self.end_coin_count
            self.game.write_save(self.game.save_data)
            self.run_coins_banked = True
            
    def render(self, surface):
        surface.blit(self.background_surf, (0, 0))
        p_rect = pygame.Rect(30, 15, self.game.DISPLAY_SIZE[0] - 60, self.game.DISPLAY_SIZE[1] - 30)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)
        
        title = "GAME OVER"; w = self.game.white_font.width(title, 3)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2-w//2+2, p_rect.top+12), scale=3)
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2-w//2, p_rect.top+10), scale=3)
        
        y1 = p_rect.top+40;
        score_text = f"SCORE: {self.end_coin_count}"; hs_text = f"HIGH SCORE: {self.game.save_data['high_score']}"
        score_w, hs_w = self.game.white_font.width(score_text, 2), self.game.white_font.width(hs_text, 2)
        
        self.game.black_font.render(score_text, surface, (self.game.DISPLAY_SIZE[0]/2 - score_w/2+1, y1+8), scale=2); 
        self.game.white_font.render(score_text, surface, (self.game.DISPLAY_SIZE[0]/2-score_w/2, y1+7), scale=2)
        
        hs_font = self.highlight_font if self.new_high_score and self.master_clock % 40 < 20 else self.game.white_font
        self.game.black_font.render(hs_text, surface, (self.game.DISPLAY_SIZE[0]/2 - hs_w/2+1, y1+28), scale=2);
        hs_font.render(hs_text, surface, (self.game.DISPLAY_SIZE[0]/2-hs_w/2, y1+27), scale=2)
        
        y2 = y1 + 55
        
        if not self.run_coins_banked:
            text = "Banking coins..."
            w = self.game.white_font.width(text); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, y2+15)
            self.game.black_font.render(text, surface, (pos[0]+1, pos[1]+1)); self.game.white_font.render(text, surface, pos)
        else:
            y_pos = y2 + 10
            for i, option in enumerate(self.options):
                color = self.highlight_font.color
                w = self.game.white_font.width(option, 2); x_pos = surface.get_width()//2-w//2
                if i == self.selection_index:
                    pygame.draw.rect(surface, color, (x_pos-10, y_pos-3, w+20, 16), border_radius=3)
                    self.game.black_font.render(option, surface, (x_pos, y_pos), scale=2)
                else:
                    self.game.white_font.render(option, surface, (x_pos, y_pos), scale=2)
                y_pos += 30
