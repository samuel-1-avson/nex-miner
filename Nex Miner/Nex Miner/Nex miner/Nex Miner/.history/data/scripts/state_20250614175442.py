# data/scripts/state.py
import pygame, sys

class State:
    """ Base class for all game states. """
    def __init__(self, game):
        self.game = game

    def handle_events(self, events):
        """ Process all events for this state. """
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
    
    def update(self):
        """ Update the logic of the state. """
        pass

    def render(self, surface):
        """ Draw everything related to this state. """
        pass

    def enter_state(self):
        """ Code that runs when this state becomes active. """
        pass

    def exit_state(self):
        """ Code that runs when this state is no longer active. """
        pass