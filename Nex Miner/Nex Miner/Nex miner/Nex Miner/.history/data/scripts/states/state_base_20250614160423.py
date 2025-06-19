import pygame

class State:
    """
    This is a base class for all game states.
    It provides a template for the functions that the main Game object will call.
    """
    def __init__(self, game):
        self.game = game
        self.prev_state = None # Useful for states like 'Pause' or 'Options'

    def update(self, dt, events):
        """
        Updates the state's logic.
        dt (delta time): Time elapsed since the last frame.
        events: A list of all pygame events from the current frame.
        """
        pass

    def render(self, surface):
        """
        Draws the state to the provided surface.
        """
        pass

    def enter_state(self):
        """
        Called when this state becomes the active state.
        Can be used to reset timers, animations, etc.
        """
        if len(self.game.states) > 1:
            self.prev_state = self.game.states[-2] # Set the previous state

    def exit_state(self):
        """
        Called when this state is no longer the active state.
        """
        pass