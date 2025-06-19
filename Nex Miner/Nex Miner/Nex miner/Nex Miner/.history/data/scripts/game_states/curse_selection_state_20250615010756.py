# Cavyn Source/data/scripts/game_states/curse_selection_state.py
import pygame
from ..state import State

class CurseSelectionState(State):
    def __init__(self, game, curses_to_offer, background_surf):
        super().__init__(game)
        self.curses_to_offer = curses_to_offer
        self.background_surf = background_surf
        self.selection_index = 0
        
    def enter_state(self):
        self.selection_index = 0
        if 'combo_end' in self.game.sounds:
            self.game.sounds['combo_end'].play()

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.curses_to_offer)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.curses_to_offer)) % len(self.curses_to_offer)
                elif event.key in [pygame.K_RETURN, pygame.K_e, pygame.K_x]:
                    # Find the gameplay state on the stack and give it the curse
                    gameplay_state = None
                    for state in reversed(self.game.states):
                        if hasattr(state, 'active_curses'):
                            gameplay_state = state
                            break
                    
                    if gameplay_state:
                        chosen_curse = self.curses_to_offer[self.selection_index]
                        gameplay_state.active_curses.add(chosen_curse)
                    
                    self.game.pop_state() # Exit this curse selection screen
                    
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