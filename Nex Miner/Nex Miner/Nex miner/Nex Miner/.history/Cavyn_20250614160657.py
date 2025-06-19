import os
import sys
import pygame
from pygame.locals import *

# Import our new state class
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
        self.dt = 0 # Delta time

        # State Management
        self.states = []

        # Start the game by creating and adding the first state
        # Later, we will start with a MainMenuState.
        initial_state = GameplayState(self)
        self.states.append(initial_state)

    def run(self):
        """ The main game loop """
        while self.running:
            # Get delta time and events
            self.dt = self.clock.tick(60) * (1 / 1000) # Delta time in seconds
            events = pygame.event.get()

            # The state machine handles all updates and events
            self.update(events)

            # The state machine handles all rendering
            self.render()

        # Exit game
        pygame.quit()
        sys.exit()

    def update(self, events):
        if not self.states:
            self.running = False
            return
            
        # Check for quit event first
        for event in events:
            if event.type == QUIT:
                self.running = False
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    self.running = False

        # Update the current state, passing dt and events
        self.states[-1].update(self.dt, events)


    def render(self):
        # Render the current state to the small display surface
        self.states[-1].render(self.display)
        
        # Scale the small display to the big screen
        self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
        pygame.display.update()

    # --- State Management Methods ---
    def push_state(self, new_state):
        self.states.append(new_state)
        # new_state.enter_state() # We can add enter/exit methods later if needed

    def pop_state(self):
        if len(self.states) > 1:
            self.states.pop()

# The new entry point of our application
if __name__ == "__main__":
    game = Game()
    game.run()