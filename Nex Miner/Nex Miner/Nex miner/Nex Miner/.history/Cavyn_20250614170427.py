# Cavyn Source/Cavyn.py

# this is very spaghetti because it was written in under 8 hours -- (COMMENT FROM ORIGINAL)
# NOTE: This file has been refactored into a Game/State architecture.

import os
import sys
import random
import math
import json

import pygame
from pygame.locals import *

# Import our new state classes and existing game object classes
from data.scripts.state import State
from data.scripts.gameplay_state import GameplayState
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font


class Game:
    """
    The main Game class.
    Handles window creation, the main game loop, asset loading,
    and state management.
    """
    def __init__(self):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()

        # Display Setup
        self.DISPLAY_SIZE = (320, 180)
        self.SCALE = 3
        self.TILE_SIZE = 16
        pygame.display.set_caption('Cavyn: Recharged')
        self.screen = pygame.display.set_mode((self.DISPLAY_SIZE[0] * self.SCALE, self.DISPLAY_SIZE[1] * self.SCALE), 0, 32)
        self.display = pygame.Surface(self.DISPLAY_SIZE)
        self.WINDOW_TILE_SIZE = (int(self.display.get_width() // self.TILE_SIZE), int(self.display.get_height() // self.TILE_SIZE))
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        # State Management
        self.states = []

        # Game constants (that states might need)
        self.SAVE_FILE = 'save.json'
        self.UPGRADES = {
            'jumps': {'name': 'Extra Jump', 'desc': 'Max jumps +1', 'base_cost': 50, 'max_level': 2},
            'speed': {'name': 'Move Speed', 'desc': 'Run faster', 'base_cost': 40, 'max_level': 5},
            'item_luck': {'name': 'Item Luck', 'desc': 'Better chest loot', 'base_cost': 100, 'max_level': 3},
            'coin_magnet': {'name': 'Coin Magnet', 'desc': 'Coins pull to you', 'base_cost': 150, 'max_level': 4},
        }
        self.PERKS = {
            'acrobat': {'name': 'Acrobat', 'desc': 'First jump after wall contact is higher.'},
            'overcharge': {'name': 'Overcharge', 'desc': 'Dashing through tiles creates an explosion.'},
            'feather_fall': {'name': 'Feather Fall', 'desc': 'You fall 20% slower.'},
            'technician': {'name': 'Technician', 'desc': 'Projectiles pierce one tile.'},
            'greedy': {'name': 'Greedy', 'desc': 'Chests & Greed Tiles drop double coins.'},
            'glass_cannon': {'name': 'Glass Cannon', 'desc': 'Faster combo, but instant death.'},
        }
        self.BIOMES = [
            {'name': 'The Depths', 'score_req': 0, 'bg_color': (22, 19, 40), 'bg_layers': ('data/images/background.png', 'data/images/background.png'), 'available_tiles': ['tile', 'chest', 'fragile', 'bounce', 'spike', 'greed', 'magnetic', 'motherlode', 'unstable'], 'special_spawn_rate': {'magnetic': 9}},
            {'name': 'Goo-Grotto', 'score_req': 125, 'bg_color': (19, 40, 30), 'bg_layers': ('data/images/background_cave.png', 'data/images/background_cave.png'), 'available_tiles': ['tile', 'chest', 'fragile', 'bounce', 'spike', 'greed', 'sticky', 'motherlode', 'unstable'], 'special_spawn_rate': {'sticky': 8}},
        ]
        self.upgrade_keys = list(self.UPGRADES.keys())
        self.time_meter_max = 120
        self.COMBO_DURATION = 180

        # Load shared resources
        self.load_assets()
        self.save_data = self.load_save()


    def load_assets(self):
        """Loads all assets that are shared across different states."""
        self.animation_manager = AnimationManager()

        # Fonts
        self.white_font = Font('data/fonts/small_font.png', (251, 245, 239))
        self.black_font = Font('data/fonts/small_font.png', (0, 0, 1))
        
        # Backgrounds
        self.backgrounds = {}

        # Sounds
        self.sounds = {sound.split('/')[-1].split('.')[0]: pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
        self.sounds['block_land'].set_volume(0.5)
        self.sounds['coin'].set_volume(0.6)
        self.sounds['chest_open'].set_volume(0.8)
        self.sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav')
        self.sounds['coin_end'].set_volume(0.35)
        if 'upgrade' in self.sounds: self.sounds['upgrade'].set_volume(0.7)
        if 'explosion' in self.sounds: self.sounds['explosion'].set_volume(0.8)
        if 'combo_end' in self.sounds: self.sounds['combo_end'].set_volume(0.6)
        self.sounds['time_slow_start'] = pygame.mixer.Sound('data/sfx/warp.wav'); self.sounds['time_slow_start'].set_volume(0.4)
        self.sounds['time_slow_end'] = pygame.mixer.Sound('data/sfx/chest_open.wav'); self.sounds['time_slow_end'].set_volume(0.3)
        self.sounds['time_empty'] = pygame.mixer.Sound('data/sfx/death.wav'); self.sounds['time_empty'].set_volume(0.25)
        
        # Music
        pygame.mixer.music.load('data/music.wav')
        pygame.mixer.music.play(-1)
        
    def load_biome_bgs(self, biome_info):
        """Loads the background images for a specific biome."""
        try:
            bg_far_path, bg_near_path = biome_info['bg_layers']
            far_surf = pygame.image.load(bg_far_path).convert()
            self.backgrounds['far'] = pygame.transform.scale(far_surf, self.DISPLAY_SIZE)
            near_surf = pygame.image.load(bg_near_path).convert()
            near_surf.set_colorkey((0,0,0))
            self.backgrounds['near'] = pygame.transform.scale(near_surf, self.DISPLAY_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")
            self.backgrounds['far'], self.backgrounds['near'] = None, None

    def load_save(self):
        try:
            with open(self.SAVE_FILE, 'r') as f:
                data = json.load(f)
                if 'high_score' not in data: data['high_score'] = 0
                if 'coin_magnet' not in data['upgrades']: data['upgrades']['coin_magnet'] = 0
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}
            self.write_save(default_save)
            return default_save

    def write_save(self, data):
        with open(self.SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def run(self):
        """The main loop of the game."""
        while True:
            # Get events to pass to the current state
            events = pygame.event.get()

            # Let the current state handle events and update its logic
            self.get_current_state().handle_events(events)
            self.get_current_state().update()

            # Render the current state to the main display surface
            self.get_current_state().render(self.display)

            # Apply screen shake (a global render effect)
            render_offset = [0, 0]
            screen_shake = getattr(self.get_current_state(), 'screen_shake', 0)
            if screen_shake > 0:
                render_offset[0] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2
                render_offset[1] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2

            # Final blit to the screen and display update
            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), render_offset)
            pygame.display.update()
            self.clock.tick(60)

    # === State Management Methods ===
    def get_current_state(self):
        return self.states[-1] if self.states else None

    def push_state(self, new_state):
        self.states.append(new_state)

    def pop_state(self):
        if len(self.states) > 1:
            self.states.pop()
        else:
            # If we pop the last state, quit the game
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    game = Game()
    # Create the initial state and push it to the stack
    game.push_state(GameplayState(game))
    # Start the game
    game.run()