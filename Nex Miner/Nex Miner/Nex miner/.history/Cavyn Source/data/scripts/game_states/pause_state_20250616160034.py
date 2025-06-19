# data/scripts/game_states/pause_state.py
import pygame
from ..state import State

class PauseState(State):
    def __init__(self, game, gameplay_state):
        super().__init__(game)
        # Keep a reference to the gameplay state to render it behind
        self.gameplay_state = gameplay_state

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Pressing ESC again or Enter will unpause
                if event.key in [pygame.K_ESCAPE, pygame.K_RETURN]:
                    self.game.pop_state()

    def update(self):
        # We don't update the gameplay state while paused
        pass

    def render(self, surface):
        # First, render the frozen gameplay state
        self.gameplay_state.render(surface)

        # Then, render the pause overlay on top
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 200)) # Dark, semi-transparent
        surface.blit(overlay, (0, 0))

        # Render "PAUSED" text
        title_text = "PAUSED"
        w = self.game.white_font.width(title_text, 3)
        x_pos = self.game.DISPLAY_SIZE[0] // 2 - w // 2
        y_pos = self.game.DISPLAY_SIZE[1] // 2 - 10
        
        self.game.black_font.render(title_text, surface, (x_pos + 2, y_pos + 2), scale=3)
        self.game.white_font.render(title_text, surface, (x_pos, y_pos), scale=3)

        prompt_text = "Press ESC or ENTER to resume"
        w_prompt = self.game.white_font.width(prompt_text, 1)
        x_prompt = self.game.DISPLAY_SIZE[0] // 2 - w_prompt // 2
        y_prompt = y_pos + 30
        self.game.black_font.render(prompt_text, surface, (x_prompt+1, y_prompt+1))
        self.game.white_font.render(prompt_text, surface, (x_prompt, y_prompt))