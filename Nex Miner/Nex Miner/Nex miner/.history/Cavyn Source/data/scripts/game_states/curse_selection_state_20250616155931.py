# Cavyn Source/data/scripts/game_states/curse_selection_state.py
import pygame
import random
from ..state import State

class CurseSelectionState(State):
    def __init__(self, game, gameplay_state, curses_to_offer, background_surf):
        super().__init__(game)
        self.gameplay_state = gameplay_state
        self.curses_to_offer = curses_to_offer
        self.background_surf = background_surf
        self.selection_index = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.curses_to_offer)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.curses_to_offer)) % len(self.curses_to_offer)
                elif event.key in [pygame.K_RETURN, pygame.K_e, pygame.K_x]:
                    chosen_curse = self.curses_to_offer[self.selection_index]
                    self.gameplay_state.active_curses.add(chosen_curse)
                    self.game.pop_state()
                elif event.key == pygame.K_r:
                    self.reroll_curses()

    def reroll_curses(self):
        if not self.gameplay_state.curse_reroll_available:
            return

        self.gameplay_state.curse_reroll_available = False
        if 'time_slow_start' in self.game.sounds: self.game.sounds['time_slow_start'].play()
        
        current_curses_offered = set(self.curses_to_offer)
        all_curses = set(self.game.curses.keys())
        
        candidates = list(all_curses - self.gameplay_state.active_curses - current_curses_offered)

        if len(candidates) < len(self.curses_to_offer):
            candidates = list(all_curses - self.gameplay_state.active_curses)
            
        if len(candidates) >= len(self.curses_to_offer):
            self.curses_to_offer = random.sample(candidates, k=len(self.curses_to_offer))
        
        self.selection_index = 0
                    
    def render(self, surface):
        surface.blit(self.background_surf, (0, 0))
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((40, 5, 10, 210)) # Ominous red overlay
        surface.blit(overlay, (0, 0))

        title = "ACCEPT A CURSE"
        title_w = self.game.white_font.width(title, 2)
        title_pos = (self.game.DISPLAY_SIZE[0]//2 - title_w//2, 20)
        self.game.black_font.render(title, surface, (title_pos[0]+1, title_pos[1]+1), scale=2)
        self.game.white_font.render(title, surface, title_pos, scale=2)
        
        y_start, panel_h, margin = 50, 35, 5
        for i, key in enumerate(self.curses_to_offer):
            r = pygame.Rect(40, y_start + i * (panel_h + margin), self.game.DISPLAY_SIZE[0] - 80, panel_h)
            color = (255, 90, 90) if i == self.selection_index else (180, 150, 150)
            pygame.draw.rect(surface, color, r, 1)

            curse = self.game.curses[key]
            self.game.white_font.render(curse['name'].upper(), surface, (r.x + 8, r.y + 7))
            self.game.black_font.render(curse['desc'], surface, (r.x + 9, r.y + 19))
            self.game.white_font.render(curse['desc'], surface, (r.x + 8, r.y + 18))
            
        if self.gameplay_state.curse_reroll_available:
            prompt = "Press [R] to Reroll"
            w = self.game.white_font.width(prompt)
            pos = (self.game.DISPLAY_SIZE[0]//2 - w//2, surface.get_height() - 20)
            self.game.black_font.render(prompt, surface, (pos[0]+1, pos[1]+1))
            self.game.white_font.render(prompt, surface, pos)