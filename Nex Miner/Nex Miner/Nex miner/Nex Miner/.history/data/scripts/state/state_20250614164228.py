import pygame, sys

class State:
    # Does your __init__ look like this?
    def __init__(self, game): # 'game' here is an instance of the Game class
        self.game = game

    # ... other methods ...
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
                    pygame.quit()
                    sys.exit()

    def update(self, time_scale):
        """
        Update the logic of the state.
        This is where movement, timers, and AI would go.
        'time_scale' is passed from the main loop to handle slow-motion effects.
        """
        pass

    def render(self, surface):
        """
        Draw everything related to this state onto the provided surface.
        """
        pass