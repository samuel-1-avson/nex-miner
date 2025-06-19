# data/scripts/game_states/perk_selection_state.py
import pygame
from ..state import State

class PerkSelectionState(State):
    def __init__(self, game, perks_to_offer, background_surf):
        super().__init__(game)
        self.perks_to_offer = perks_to_offer
        self.background_surf = background_surf
        self.selection_index = 0
        
    def enter_state(self):
        self.selection_index = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.perks_to_offer)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.perks_to_offer)) % len(self.perks_to_offer)
                elif event.key in [pygame.K_RETURN, pygame.K_e, pygame.K_x]:
                    # Find the gameplay state on the stack and give it the perk
                    gameplay_state = None
                    for state in reversed(self.game.states):
                        # A bit of a hacky way to find it, but it works
                        if hasattr(state, 'active_perks'):
                            gameplay_state = state
                            break
                    
                    if gameplay_state:
                        chosen_perk = self.perks_to_offer[self.selection_index]
                        gameplay_state.active_perks.add(chosen_perk)
                        gameplay_state.perks_gained_this_run += 1
                        if 'upgrade' in self.game.sounds: self.game.sounds['upgrade'].play()
                    
                    self.game.pop_state() # Exit this perk selection screen
                    
    def render(self, surface):
        surface.blit(self.background_surf, (0, 0))
        overlay = pygame.Surface(self.game.DISPLAY_SIZE, pygame.SRCALPHA)
        overlay.fill((10, 5, 20, 200))
        surface.blit(overlay, (0, 0))

        title = "SELECT UPGRADE PROTOCOL"
        title_w = self.game.white_font.width(title, 2)
        title_pos = (self.game.DISPLAY_SIZE[0]//2 - title_w//2, 20)
        self.game.black_font.render(title, surface, (title_pos[0]+1, title_pos[1]+1), scale=2)
        self.game.white_font.render(title, surface, title_pos, scale=2)
        
        y_start, panel_h, margin = 50, 35, 5
        for i, key in enumerate(self.perks_to_offer):
            r = pygame.Rect(40, y_start + i * (panel_h + margin), self.game.DISPLAY_SIZE[0] - 80, panel_h)
            color = (255, 230, 90) if i == self.selection_index else (150, 150, 180)
            pygame.draw.rect(surface, color, r, 1)

            # Use lowercase 'perks' from the game object
            perk = self.game.perks[key]
            self.game.white_font.render(perk['name'].upper(), surface, (r.x + 8, r.y + 7))
            self.game.black_font.render(perk['desc'], surface, (r.x + 9, r.y + 19))
            self.game.white_font.render(perk['desc'], surface, (r.x + 8, r.y + 18))