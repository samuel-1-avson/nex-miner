# data/scripts/game_states/game_over_state.py
import pygame, math
from ..state import State
from ..text import Font
# DO NOT import GameplayState at the top level to avoid circular import

class GameOverState(State):
    def __init__(self, game, score, background_surf):
        super().__init__(game)
        self.score = score
        self.background_surf = background_surf
        self.new_high_score = False
        self.run_coins_banked = False
        self.master_clock = 0
        self.end_coin_count = 0
        
        # Options for the player
        self.options = ["RESTART", "MAIN MENU"]
        self.selection_index = 0

    def enter_state(self):
        # This code runs once when the state becomes active
        if self.score > self.game.save_data['high_score']:
            self.game.save_data['high_score'] = self.score
            self.new_high_score = True
            self.game.write_save(self.game.save_data)

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if self.run_coins_banked: # Only allow selection after coins are banked
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
            # Pop this state and the previous gameplay state, then push a new one
            self.game.pop_state() # Pop GameOverState
            self.game.pop_state() # Pop old GameplayState
            self.game.push_state(GameplayState(self.game))
        elif option == "MAIN MENU":
            self.game.pop_state() # Pop GameOverState
            self.game.pop_state() # Pop old GameplayState, returning to MainMenu

    def update(self):
        self.master_clock += 1
        # Animate the coin banking process
        if self.end_coin_count < self.score:
            if self.master_clock % 3 == 0:
                self.game.sounds['coin_end'].play()
                self.end_coin_count = min(self.end_coin_count + 1 + (self.score - self.end_coin_count) // 20, self.score)
        elif not self.run_coins_banked:
            self.game.save_data['banked_coins'] += self.end_coin_count
            self.game.write_save(self.game.save_data)
            self.run_coins_banked = True
            
    def render(self, surface):
        surface.blit(self.background_surf, (0, 0))
        p_color=(15,12,28,220); b_color=(200,200,220,230); hl_color=(255,230,90)
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0]-20, self.game.DISPLAY_SIZE[1]-16)
        p_surf = pygame.Surface(p_rect.size, pygame.SRCALPHA); p_surf.fill(p_color); surface.blit(p_surf, p_rect.topleft)
        pygame.draw.rect(surface, b_color, p_rect, 1, 3)

        title = "GAME OVER"; w = self.game.white_font.width(title, 3)
        self.game.black_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2-w//2+2, p_rect.top+10), scale=3)
        self.game.white_font.render(title, surface, (self.game.DISPLAY_SIZE[0]//2-w//2, p_rect.top+8), scale=3)
        
        y1 = p_rect.top+30; pygame.draw.line(surface, b_color, (p_rect.left+10, y1), (p_rect.right-10, y1), 1)
        score_text = f"SCORE: {self.end_coin_count}"; hs_text = f"HIGH SCORE: {self.game.save_data['high_score']}"
        score_w, hs_w = self.game.white_font.width(score_text, 2), self.game.white_font.width(hs_text, 2)
        self.game.black_font.render(score_text, surface, (self.game.DISPLAY_SIZE[0]/2 - score_w/2+1, y1+8), scale=2); self.game.white_font.render(score_text, surface, (self.game.DISPLAY_SIZE[0]/2-score_w/2, y1+7), scale=2)
        hs_font = Font(self.game.get_path('data/fonts/small_font.png'), hl_color) if self.new_high_score and self.master_clock%40<20 else self.game.white_font
        self.game.black_font.render(hs_text, surface, (self.game.DISPLAY_SIZE[0]/2 - hs_w/2+1, y1+23), scale=2); hs_font.render(hs_text, surface, (self.game.DISPLAY_SIZE[0]/2-hs_w/2, y1+22), scale=2)
        
        y2 = y1 + 42; pygame.draw.line(surface, b_color, (p_rect.left+10, y2), (p_rect.right-10, y2), 1)
        
        if not self.run_coins_banked:
            text = "Banking coins..." if self.master_clock%40<20 else "Banking coins.."
            w = self.game.white_font.width(text); pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, y2+25)
            self.game.black_font.render(text, surface, (pos[0]+1, pos[1]+1)); self.game.white_font.render(text, surface, pos)
        else:
            y_pos = y2 + 20
            for i, option in enumerate(self.options):
                color = hl_color if i == self.selection_index else self.game.white_font.color
                w = self.game.white_font.width(option, 2); x_pos = surface.get_width()//2-w//2
                if i == self.selection_index:
                    pygame.draw.rect(surface, hl_color, (x_pos-10, y_pos-3, w+20, 16))
                    self.game.black_font.render(option, surface, (x_pos, y_pos), scale=2)
                else:
                    self.game.white_font.render(option, surface, (x_pos, y_pos), scale=2) # Removed color kwarg to use font's default
                y_pos += 30