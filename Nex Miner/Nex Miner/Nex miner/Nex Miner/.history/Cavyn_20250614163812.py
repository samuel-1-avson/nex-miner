# Cavyn Source/Cavyn.py
# This is now the main Game Engine class.
import sys
import os

# This adds the directory containing 'Cavyn.py' to the Python path.
# This makes it see the 'data' folder as a package.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Now, the rest of your imports should work as intended.
import pygame
from pygame.locals import *


# ... etc.
import os, sys, pygame, json
from pygame.locals import *

# Import our new states and other necessary classes
from data.scripts.state import State
from data.scripts.gameplay_state import GameplayState
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font

class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        # Constants and Config
        self.TILE_SIZE = 16
        self.DISPLAY_SIZE = (320, 180)
        self.SCALE = 3
        
        # Pygame Setup
        self.screen = pygame.display.set_mode((self.DISPLAY_SIZE[0] * self.SCALE, self.DISPLAY_SIZE[1] * self.SCALE), 0, 32)
        self.display = pygame.Surface(self.DISPLAY_SIZE)
        self.clock = pygame.time.Clock()
        pygame.display.set_caption('Cavyn: Recharged')
        pygame.mouse.set_visible(True) # Turn mouse on for menus

        # Engine/State Variables
        self.running = True
        self.states = [] # This is the state stack
        
        # Load persistent assets once
        self.load_assets()
        
        # Start with the first state
        self.states.append(GameplayState(self)) # We start directly in the game for now

    def load_assets(self):
        """Load all assets that the game will need, like sounds, fonts, and images."""
        # Note: self.variable for anything the game engine needs to hold onto.
        self.save_data = self.load_save_data()
        self.animation_manager = AnimationManager()
        
        self.white_font = Font('data/fonts/small_font.png', (251, 245, 239))
        self.black_font = Font('data/fonts/small_font.png', (0, 0, 1))

        # Example of loading one sound; you would do this for all
        self.sounds = {sound.split('/')[-1].split('.')[0] : pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
        self.sounds['block_land'].set_volume(0.5)

        # Non-gameplay specific variables can live here
        self.time_meter_max = 120

        # All the 'load_img' calls would go here, stored on self.
        # e.g., self.tile_img = self.load_image('data/images/tile.png')
        print("Assets Loaded.")
        
    def run(self):
        """The main game loop. Manages the active state."""
        while self.running:
            # Get events once and pass them to the active state
            events = pygame.event.get()
            
            active_state = self.states[-1]
            active_state.handle_events(events)
            active_state.update()
            
            # Rendering
            self.display.fill((0,0,0)) # Clear screen
            active_state.render(self.display)
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), (0, 0))
            
            pygame.display.update()
            self.clock.tick(60)

    # Helper methods for state management
    def push_state(self, new_state):
        self.states.append(new_state)

    def pop_state(self):
        if len(self.states) > 1:
            self.states.pop()
        else:
            self.running = False # Quit if we pop the last state

    # Save/Load functions are part of the main game now
    def load_save_data(self):
        # (Your load_save() logic goes here)
        try:
            with open('save.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}

    def write_save(self, data):
        # (Your write_save() logic goes here)
        with open('save.json', 'w') as f:
            json.dump(data, f, indent=4)


if __name__ == '__main__':
    game = Game()
    game.run()