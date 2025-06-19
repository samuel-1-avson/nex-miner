import os
import sys
import pygame
from pygame.locals import *

# Import our new state classes. The game will start in 'Gameplay'.
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
        self.state_stack = []

        # --- Global Asset Loaders (Optional, but good practice) ---
        # If you had, for example, a font loader or animation loader used by multiple
        # states (like a menu and the game), you could load it once here.
        
        # Start the game by loading the first state
        self.load_states()

    def load_states(self):
        # Create an instance of our Gameplay state and push it onto the stack
        # This makes Gameplay the starting state.
        gameplay_state = Gameplay(self)
        gameplay_state.enter_state()

    def game_loop(self):
        while self.running:
            # Get delta time (time since last frame)
            # Dividing by 1000 converts milliseconds to seconds.
            dt = self.clock.tick(60) / 1000.0

            # --- Main Loop Logic ---
            # It just runs the methods of whatever state is on top of the stack.
            self.get_events()
            self.update(dt)
            self.draw()

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
        # Let the top-most state draw itself to the small display
        self.state_stack[-1].draw(self.display)
        
        # Scale the small display to the big screen
        self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
        pygame.display.update()

# This is the standard entry point for a Python script
if __name__ == '__main__':
    game = Game()
    game.game_loop()
    pygame.quit()
    sys.exit()