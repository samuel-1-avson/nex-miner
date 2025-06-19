# Cavyn Source/data/scripts/state.py

import pygame, sys

class State:
    """
    A base class for all game states (e.g., Main Menu, Gameplay, etc.).
    This acts as a blueprint, ensuring every state has the same core methods.
    """
    def __init__(self, game):
        self.game = game # Every state will have a reference to the main Game object.

    def handle_events(self, events):
        """
        Process all events from pygame.event.get() for this state.
        This is where you'll check for key presses, mouse clicks, etc.
        """
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.game.pop_state()

    def update(self):
        """
        Update the logic of the state.
        This is where movement, timers, and AI would go.
        """
        pass

    def render(self, surface):
        """
        Draw everything related to this state onto the provided surface.
        """
        pass