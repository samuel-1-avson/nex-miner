# data/scripts/game_states/boot_up_state.py
import pygame
import math
from ..state import State
from .mainframe_intro_state import MainframeIntroState

class BootUpState(State):
    """
    A simple state to show a thematic boot-up sequence before the main game.
    """
    def __init__(self, game):
        super().__init__(game)
        self.timer = 0
        self.duration = 240 # 4 seconds at 60fps
        self.texts = [
            ("NEX-OS v1.5 INITIALIZING...", 0),
            ("CONNECTING TO MAINFRAME...", 60),
            ("CONNECTION ESTABLISHED.", 120),
            ("AWAITING OPERATIVE INPUT...", 180),
        ]

    def update(self):
        self.timer += 1
        if self.timer > self.duration:
            # --- FIX: Use replace_state to prevent exiting the game ---
            # This is the key change. It swaps this state with the next one
            # instead of popping the only state from the stack.
            self.game.replace_state(MainframeIntroState(self.game))

    def render(self, surface):
        surface.fill((10, 8, 20)) # Dark blue boot-up background
        
        y_pos = surface.get_height() // 2 - 20
        for text, show_time in self.texts:
            if self.timer > show_time:
                # Add a blinking cursor effect for atmosphere
                render_text = text
                if self.timer > show_time + 10 and self.timer < self.duration - 10 and (self.timer // 20) % 2 == 0:
                     render_text += "_"

                w = self.game.white_font.width(render_text)
                x_pos = surface.get_width() // 2 - w // 2
                self.game.white_font.render(render_text, surface, (x_pos, y_pos))
                y_pos += 12