--- START OF FILE Nex Miner/Nex Miner/Nex miner/Nex Miner/data/scripts/game_states/boot_up_state.py ---
# data/scripts/game_states/boot_up_state.py
import pygame
import math
from ..state import State
from .mainframe_intro_state import MainframeIntroState

class BootUpState(State):
    def __init__(self, game):
        super().__init__(game)
        self.timer = 0; self.duration = 240
        self.texts = [
            ("NEX-OS v1.5 INITIALIZING...", 0),
            ("CONNECTING TO MAINFRAME...", 60),
            ("CONNECTION ESTABLISHED.", 120),
            ("AWAITING OPERATIVE INPUT...", 180),
        ]

    def update(self):
        self.timer += 1
        if self.timer > self.duration:
            # --- FIX: Use replace_state to prevent exiting the game by popping the only state ---
            self.game.replace_state(MainframeIntroState(self.game))

    def render(self, surface):
        surface.fill((10, 8, 20)) 
        y_pos = surface.get_height() // 2 - 20
        for text, show_time in self.texts:
            if self.timer > show_time:
                render_text = text
                if self.timer > show_time + 10 and self.timer < self.duration - 10 and (self.timer // 20) % 2 == 0:
                     render_text += "_"
                w, x_pos = self.game.white_font.width(render_text), surface.get_width()//2 - self.game.white_font.width(render_text)//2
                self.game.white_font.render(render_text, surface, (x_pos, y_pos))
                y_pos += 12