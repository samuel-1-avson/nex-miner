
import pygame
import datetime
import random
from .state import State
from .gameplay_state import GameplayState, render_panel_9slice

class DailyChallengeState(State):
    def __init__(self, game):
        super().__init__(game)
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.get_daily_seed()
        
        # We need to make sure the key exists before we try to check it
        if 'daily_challenge_high_score' not in self.game.save_data['stats']:
            self.game.save_data['stats']['daily_challenge_high_score'] = 0

    def get_daily_seed(self):
        # Create a seed based on the current date (UTC)
        # This ensures the seed is the same for all players worldwide.
        today = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        self.seed = hash(today)

    def start_run(self):
        # Create a seeded random number generator
        seeded_random = random.Random()
        seeded_random.seed(self.seed)

        # Pop this state and then push the gameplay state, passing the seeded generator.
        self.game.pop_state()
        self.game.push_state(GameplayState(self.game, mode="daily_challenge", seeded_random=seeded_random))
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key == pygame.K_RETURN:
                    self.start_run()
    
    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(30, 15, self.game.DISPLAY_SIZE[0] - 60, self.game.DISPLAY_SIZE[1] - 30)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)
        
        title = "DAILY DIRECTIVE"
        w = self.game.white_font.width(title, 2)
        self.game.white_font.render(title, surface, (surface.get_width()//2 - w//2, p_rect.top + 10), scale=2)

        # Description
        y_offset = p_rect.top + 35
        desc1 = "All operatives receive the same mission."
        desc2 = "Compete for the highest extraction score!"
        self.game.white_font.render(desc1, surface, (surface.get_width()//2 - self.game.white_font.width(desc1)//2, y_offset))
        y_offset += 12
        self.game.white_font.render(desc2, surface, (surface.get_width()//2 - self.game.white_font.width(desc2)//2, y_offset))

        # Show today's high score
        y_offset += 25
        hs_text = f"Today's Top Score: {self.game.save_data['stats'].get('daily_challenge_high_score', 0)}"
        w = self.game.white_font.width(hs_text)
        self.game.white_font.render(hs_text, surface, (surface.get_width()//2 - w//2, y_offset))

        prompt = "Enter: Begin Mission  -  Esc: Back"
        w = self.game.white_font.width(prompt); pos = (surface.get_width()//2-w//2, p_rect.bottom - 12)
        self.game.white_font.render(prompt, surface, pos)