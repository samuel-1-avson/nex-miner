import os
import sys
import pygame
from pygame.locals import *

# Import the initial state
from data.scripts.states.gameplay import GameplayState

# This Game class is now the heart of our program
class Game:
    def __init__(self):
        # Pygame & Window Initialization
        pygame.init()
        pygame.mixer.init()
        self.DISPLAY_SIZE = (320, 180)
        self.SCALE = 3
        self.screen = pygame.display.set_mode((self.DISPLAY_SIZE[0] * self.SCALE, self.DISPLAY_SIZE[1] * self.SCALE), 0, 32)
        self.display = pygame.Surface(self.DISPLAY_SIZE)
        pygame.display.set_caption('Cavyn: Recharged')
        pygame.mouse.set_visible(False)

        # Game Loop Variables
        self.running = True
        self.clock = pygame.time.Clock()
        self.dt = 0

        # State Management
        self.states = []

        # Start the game by creating and adding the first state
        self.load_states()

    def run(self):
        """ The main game loop """
        while self.running:
            # Get delta time and a list of all events
            self.dt = self.clock.tick(60) * (1 / 1000) # Delta time in seconds
            events = pygame.event.get()

            # The active state handles events, updates, and renders
            if self.states:
                self.states[-1].update(self.dt, events)
                self.states[-1].render(self.display)
            else:
                self.running = False # No states left, shut down

            # Update the main screen
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            pygame.display.update()

        # Exit game
        pygame.quit()
        sys.exit()

    def load_states(self):
        # We start by adding the main gameplay state.
        # Later, we will start with a MainMenuState.
        initial_state = GameplayState(self)
        self.states.append(initial_state)

    # --- State Management Methods ---
    def push_state(self, new_state):
        self.states.append(new_state)
        new_state.enter_state()

    def pop_state(self):
        if self.states:
            self.states[-1].exit_state()
            self.states.pop()
            if self.states:
                self.states[-1].enter_state() # Notify the state below it that it is active again


# The new entry point of our application
if __name__ == "__main__":
    game = Game()
    game.run()