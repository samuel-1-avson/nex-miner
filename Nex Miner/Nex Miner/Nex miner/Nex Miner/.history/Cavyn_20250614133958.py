import os
import sys
import pygame
from pygame.locals import *

# Import our new state classes
from data.scripts.states.gameplay import Gameplay

class Game:
    def __init__(self):
        # Basic Pygame and Display Setup
        pygame.init()
        pygame.mixer.init()
        pygame.display.set_caption('Cavyn: Recharged')
        self.DISPLAY_SIZE = (320, 180)
        self.SCALE = 3
        self.screen = pygame.display.set_mode((self.DISPLAY_SIZE[0] * self.SCALE, self.DISPLAY_SIZE[1] * self.SCALE), 0, 32)
        self.display = pygame.Surface(self.DISPLAY_SIZE)
        pygame.mouse.set_visible(False)
        
        self.clock = pygame.time.Clock()
        self.running = True
        
        # --- THE STATE STACK ---
        # This is the core of the state machine. It's a list that holds the active states.
        # We can add states (like a pause menu) on top of the stack.
        self.state_stack = []

        # --- Game Variables moved here ---
        # Any variables that need to be accessed by ALL states (like save data or asset loaders)
        # should be stored in self.game_vars. We pass this dictionary to each state.
        self.game_vars = {
            'pygame': pygame, # Pass pygame module itself if needed
            # We will move more things here later
        }

        # Start the game by loading the first state
        self.load_states()

    def load_states(self):
        # Create an instance of our Gameplay state and push it onto the stack
        gameplay_state = Gameplay(self)
        gameplay_state.enter_state()

    def game_loop(self):
        while self.running:
            # Get delta time (time since last frame)
            dt = self.clock.tick(60) / 1000.0  # Delta time in seconds

            # Let the current state handle events
            self.get_events()
            
            # Let the current state update its logic
            self.update(dt)
            
            # Let the current state draw to the display
            self.draw()

            # Update the actual screen
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            pygame.display.update()

    def get_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                self.running = False
            # Pass the event to the current state at the top of the stack
            self.state_stack[-1].handle_event(event)

    def update(self, dt):
        # We just need to update the top-most state
        self.state_stack[-1].update(dt)

    def draw(self):
        # Let the top-most state draw itself
        self.state_stack[-1].draw(self.display)


if __name__ == '__main__':
    game = Game()
    game.game_loop()
    pygame.quit()
    sys.exit()