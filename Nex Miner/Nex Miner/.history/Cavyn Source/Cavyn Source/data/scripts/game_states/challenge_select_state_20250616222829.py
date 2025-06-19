# Cavyn Source/data/scripts/game_states/challenge_select_state.py
import pygame
from ..state import State
from ..text import Font
from ..gameplay_state import render_panel_9slice, GameplayState

class ChallengeSelectState(State):
    def __init__(self, game):
        super().__init__(game)
        # Load challenges from the JSON config
        self.challenges = self.game.challenges
        self.challenge_keys = list(self.challenges.keys())
        self.selection_index = 0
        self.panel_img = pygame.image.load(self.game.get_path('data', 'images', 'panel_9slice.png')).convert_alpha()
        self.highlight_font = Font(self.game.get_path('data', 'fonts', 'small_font.png'), (255, 230, 90))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()
                elif event.key in [pygame.K_DOWN, pygame.K_s]:
                    self.selection_index = (self.selection_index + 1) % len(self.challenge_keys)
                elif event.key in [pygame.K_UP, pygame.K_w]:
                    self.selection_index = (self.selection_index - 1 + len(self.challenge_keys)) % len(self.challenge_keys)
                elif event.key == pygame.K_RETURN:
                    self.select_challenge()
    
    def select_challenge(self):
        selected_key = self.challenge_keys[self.selection_index]
        challenge_config = self.challenges[selected_key]
        
        # Pop this state and push a new GameplayState configured for the challenge
        self.game.pop_state()
        self.game.push_state(GameplayState(self.game, mode="challenge", challenge_config=challenge_config))

    def render(self, surface):
        surface.fill((22, 19, 40))
        p_rect = pygame.Rect(10, 8, self.game.DISPLAY_SIZE[0] - 20, self.game.DISPLAY_SIZE[1] - 16)
        render_panel_9slice(surface, p_rect, self.panel_img, 8)

        title = "CHALLENGES"
        w = self.game.white_font.width(title, 2)
        self.game.white_font.render(title, surface, (surface.get_width()//2 - w//2, p_rect.top + 10), scale=2)

        pygame.draw.line(surface, (200, 200, 220, 100), (p_rect.left+10, p_rect.top + 28), (p_rect.right-10, p_rect.top+28), 1)
        
        self.render_challenge_list(surface, p_rect)
        self.render_details_panel(surface, p_rect)

        prompt = "Up/Down: Navigate  -  Enter: Start Challenge  -  Esc: Back"
        w = self.game.white_font.width(prompt); pos = (surface.get_width()//2-w//2, p_rect.bottom - 12)
        self.game.white_font.render(prompt, surface, pos)

    def render_challenge_list(self, surface, p_rect):
        list_y = p_rect.top + 35
        for i, key in enumerate(self.challenge_keys):
            challenge = self.challenges[key]
            
            font = self.game.white_font
            if i == self.selection_index:
                highlight_rect = pygame.Rect(p_rect.left + 5, list_y - 2, 100, 12)
                pygame.draw.rect(surface, (40, 30, 60, 150), highlight_rect, 0, 2)
                font = self.highlight_font
            
            font.render(challenge['name'], surface, (p_rect.left + 10, list_y))
            list_y += 14

    def render_details_panel(self, surface, p_rect):
        det_x = p_rect.left + 120
        det_y = p_rect.top + 35
        selected_key = self.challenge_keys[self.selection_index]
        challenge = self.challenges[selected_key]
        
        self.highlight_font.render(challenge['name'], surface, (det_x, det_y), scale=2)
        
        y_offset = det_y + 20
        self.game.white_font.render(challenge['desc'], surface, (det_x, y_offset), line_width=160)