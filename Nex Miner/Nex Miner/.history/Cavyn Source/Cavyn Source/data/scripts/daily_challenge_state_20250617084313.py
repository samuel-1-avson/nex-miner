# Cavyn Source/data/scripts/game_states/daily_challenge_state.py
import pygame
import datetime
import random
from ..state import State
from ..gameplay_state import GameplayState, render_panel_9slice

class DailyChallengeState(State):
    def __init__(self, game):
        super().__init__(game)
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.get_daily_seed_and_score()

    def get_daily_seed_and_score(self):
        """Creates a seed and checks/resets the daily high score if the date has changed."""
        today_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
        self.seed = hash(today_str)
        
        last_daily_date = self.game.save_data['stats'].get('last_daily_date', None)
        if last_daily_date != today_str:
            self.game.save_data['stats']['last_daily_date'] = today_str
            self.game.save_data['stats']['daily_challenge_high_score'] = 0
            self.game.write_save(self.game.save_data)

    def start_run(self):
        """Starts the daily challenge run using the daily seed."""
        # Pop this state and then push the gameplay state with the seed.
        self.game.pop_state()
        self.game.push_state(GameplayState(self.game, mode="daily_challenge", seeded_random=random.Random(self.seed)))
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key == pygame.K_RETURN:
                    if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
                    self.start_run()
    
    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(30, 15, self.game.DISPLAY_SIZE[0] - 60, self.game.DISPLAY_SIZE[1] - 30)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)
        
        title = "DAILY CHALLENGE"
        w = self.game.white_font.width(title, 2)
        self.game.white_font.render(title, surface, (surface.get_width()//2 - w//2, p_rect.top + 10), scale=2)

        # Description
        y_offset = p_rect.top + 35
        desc_lines = ["Everyone plays the exact same run.", "The seed changes once per day.", "Compete for the highest score!"]
        for line in desc_lines:
            self.game.white_font.render(line, surface, (surface.get_width()//2 - self.game.white_font.width(line)//2, y_offset), line_width=p_rect.width-10)
            y_offset += 12

        # Show today's high score
        y_offset += 15
        hs_text = f"Today's High Score: {self.game.save_data['stats'].get('daily_challenge_high_score', 0)}"
        w = self.game.white_font.width(hs_text)
        self.game.white_font.render(hs_text, surface, (surface.get_width()//2 - w//2, y_offset))

        prompt = "Enter: Start Run  -  Esc: Back"
        w = self.game.white_font.width(prompt); pos = (surface.get_width()//2-w//2, p_rect.bottom - 12)
        self.game.white_font.render(prompt, surface, pos)