# Cavyn Source/Cavyn.py
import os
import sys
import random
import json
import pygame
from pygame.locals import *

# --- Core Pathing Setup ---
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    BASE_DIR = os.path.abspath('.')


# --- Imports ---
from data.scripts.state import State
from data.scripts.game_states.main_menu_state import MainMenuState
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font
from data.scripts.core_funcs import load_img, write_f
from data.scripts.gemini_agent import GeminiAgent # --- NEW ---

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

        # --- NEW: AI Agent Initialization ---
        # IMPORTANT: Replace "YOUR_API_KEY" with your actual key. 
        # For production, load this from a secure location (e.g., environment variable).
        # self.ai_agent = GeminiAgent(api_key=os.environ.get("GEMINI_API_KEY")) 
        try:
            self.ai_agent = GeminiAgent(api_key="AIzaSyBsRGlo1wmmvBIfEzwII-zs2d6xxvopIpM") 
        except Exception:
            self.ai_agent = None # Handle case where API key is not set
        # State Management
        self.states = []
        self.time_meter_max = 120
        self.COMBO_DURATION = 180
        
        # Original sound volumes (for scaling with master volume setting)
        self.original_volumes = {
            'block_land': 0.5, 'coin': 0.6, 'chest_open': 0.8, 'coin_end': 0.35,
            'upgrade': 0.7, 'explosion': 0.8, 'combo_end': 0.6,
            'time_slow_start': 0.4, 'time_slow_end': 0.3, 'time_empty': 0.25,
            'jump': 1.0, 'super_jump': 1.0, 'death': 1.0, 'collect_item': 1.0,
            'warp': 1.0, 'land': 0.4 
        }

        # Load shared resources
        self.load_configs()
        self.load_assets()
        self.save_data = self.load_save()
        if self.save_data:
            self.apply_settings()
        self.upgrade_keys = list(self.upgrades.keys())

    def get_path(self, *args):
        """Constructs an absolute path from path components relative to the project root."""
        return os.path.join(BASE_DIR, *args)

    def load_configs(self):
        """Loads all game data from JSON files using absolute paths."""
        try:
            config_paths = {
                'upgrades': self.get_path('data', 'configs', 'upgrades.json'),
                'perks': self.get_path('data', 'configs', 'perks.json'),
                'biomes': self.get_path('data', 'configs', 'biomes.json'),
                'characters': self.get_path('data', 'configs', 'characters.json'),
                'curses': self.get_path('data', 'configs', 'curses.json'),
                'challenges': self.get_path('data', 'configs', 'challenges.json'),
                'artifacts': self.get_path('data', 'configs', 'artifacts.json'), # --- NEW ---
            }

            for name, path in config_paths.items():
                if not os.path.exists(path):
                    print(f"--- DEBUG INFO ---")
                    print(f"Base Directory (__file__): {os.path.abspath(__file__)}")
                    print(f"Calculated BASE_DIR: {BASE_DIR}")
                    print(f"FATAL ERROR: The required config file was not found.")
                    print(f"File aledlegedly missing: '{name}.json'")
                    print(f"Python looked for it at this exact path: {path}")
                    print(f"Please verify that this path is correct and the file exists.")
                    print(f"--------------------")
                    pygame.quit()
                    sys.exit()

            with open(config_paths['upgrades'], 'r') as f: self.upgrades = json.load(f)
            with open(config_paths['perks'], 'r') as f: self.perks = json.load(f)
            with open(config_paths['biomes'], 'r') as f: self.biomes = json.load(f)
            with open(config_paths['characters'], 'r') as f: self.characters = json.load(f)
            with open(config_paths['curses'], 'r') as f: self.curses = json.load(f)
            with open(config_paths['challenges'], 'r') as f: self.challenges = json.load(f)
            with open(config_paths['artifacts'], 'r') as f: self.artifacts = json.load(f) # --- NEW ---

        except (json.JSONDecodeError) as e:
            print(f"FATAL ERROR: Could not parse a JSON config file. It may have a syntax error. Reason: {e}")
            pygame.quit()
            sys.exit()

    def load_assets(self):
        anim_path = self.get_path('data', 'images', 'animations')
        self.animation_manager = AnimationManager(anim_path)
        self.white_font = Font(self.get_path('data', 'fonts', 'small_font.png'), (251, 245, 239))
        self.black_font = Font(self.get_path('data', 'fonts', 'small_font.png'), (0, 0, 1))
        self.backgrounds = {}
        sfx_dir = self.get_path('data', 'sfx')
        self.sounds = {}
        for sound_filename in os.listdir(sfx_dir):
            sound_name = sound_filename.split('.')[0]
            self.sounds[sound_name] = pygame.mixer.Sound(os.path.join(sfx_dir, sound_filename))
        self.sounds['coin_end'] = pygame.mixer.Sound(self.get_path('data', 'sfx', 'coin.wav'))
        self.sounds['time_slow_start'] = pygame.mixer.Sound(self.get_path('data', 'sfx', 'warp.wav'))
        self.sounds['time_slow_end'] = pygame.mixer.Sound(self.get_path('data', 'sfx', 'chest_open.wav'))
        self.sounds['time_empty'] = pygame.mixer.Sound(self.get_path('data', 'sfx', 'death.wav'))
        self.sounds['land'] = pygame.mixer.Sound(self.get_path('data', 'sfx', 'death.wav'))
        self.item_icons = {
            'cube': load_img(self.get_path('data', 'images', 'cube_icon.png')),
            'warp': load_img(self.get_path('data', 'images', 'warp_icon.png')),
            'jump': load_img(self.get_path('data', 'images', 'jump_icon.png')),
            'bomb': load_img(self.get_path('data', 'images', 'bomb_icon.png')),
            'freeze': load_img(self.get_path('data', 'images', 'freeze_icon.png')),
            'shield': load_img(self.get_path('data', 'images', 'shield_icon.png')),
            'hourglass': load_img(self.get_path('data', 'images', 'hourglass_icon.png')),
        }
        pygame.mixer.music.load(self.get_path('data', 'music.wav'))
        pygame.mixer.music.play(-1)
        
    def apply_settings(self):
        sfx_vol = self.save_data['settings'].get('sfx_volume', 1.0)
        for name, sound in self.sounds.items():
            original_vol = self.original_volumes.get(name, 1.0)
            sound.set_volume(original_vol * sfx_vol)
        music_vol = self.save_data['settings'].get('music_volume', 1.0)
        pygame.mixer.music.set_volume(music_vol)

    def load_biome_bgs(self, biome_info):
        try:
            far_path_components = biome_info['bg_layers'][0].replace('\\', '/').split('/')
            near_path_components = biome_info['bg_layers'][1].replace('\\', '/').split('/')
            bg_far_path = self.get_path(*far_path_components)
            bg_near_path = self.get_path(*near_path_components)
            far_surf = pygame.image.load(bg_far_path).convert()
            self.backgrounds['far'] = pygame.transform.scale(far_surf, self.DISPLAY_SIZE)
            near_surf = pygame.image.load(bg_near_path).convert()
            near_surf.set_colorkey((0,0,0))
            self.backgrounds['near'] = pygame.transform.scale(near_surf, self.DISPLAY_SIZE)
        except (pygame.error, FileNotFoundError) as e:
            print(f"Warning: Could not load background for biome {biome_info['name']}. Reason: {e}")
            self.backgrounds['far'], self.backgrounds['near'] = None, None

    def load_save(self):
        SAVE_FILE = self.get_path('save.json')
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                if 'high_score' not in data: data['high_score'] = 0
                if 'settings' not in data:
                    data['settings'] = {"sfx_volume": 1.0, "music_volume": 1.0, "screen_shake": True}
                if 'characters' not in data:
                    data['characters'] = {"unlocked": ["cavyn"], "selected": "cavyn"}
                for key in self.upgrades:
                    if key not in data.get('upgrades', {}):
                        data.setdefault('upgrades', {})[key] = 0
                if 'compendium' not in data:
                    data['compendium'] = {"perks": [], "curses": [], "items": []}
                if 'stats' not in data:
                    data['stats'] = {"play_time": 0, "total_coins": 0, "runs_started": 0}
                if 'biomes_unlocked' not in data:
                    data['biomes_unlocked'] = ["The Depths"]
                # --- NEW: Artifacts and Prophecy ---
                if 'artifacts' not in data: data['artifacts'] = {"unlocked": [], "equipped": None}
                if 'active_prophecy' not in data: data['active_prophecy'] = None
                # ---
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {
                "banked_coins": 100, 
                "upgrades": {key: 0 for key in self.upgrades}, 
                "high_score": 0,
                "settings": {"sfx_volume": 1.0, "music_volume": 1.0, "screen_shake": True},
                "characters": {"unlocked": ["cavyn"], "selected": "cavyn"},
                "compendium": {"perks": [], "curses": [], "items": []},
                "stats": {"play_time": 0, "total_coins": 0, "runs_started": 0},
                "biomes_unlocked": ["The Depths"],
                "artifacts": {"unlocked": [], "equipped": None}, # --- NEW ---
                "active_prophecy": None # --- NEW ---
            }
            self.write_save(default_save)
            return default_save

    def write_save(self, data):
        SAVE_FILE = self.get_path('save.json')
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=4) # Use write_f for consistency if preferred

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            self.save_data['stats']['play_time'] += dt

            events = pygame.event.get()
            current_state = self.get_current_state()
            if not current_state: break

            current_state.handle_events(events)
            current_state.update()

            self.display.fill((0, 0, 1))
            current_state.render(self.display)

            render_offset = [0, 0]
            if self.save_data['settings'].get('screen_shake', True):
                screen_shake = getattr(current_state, 'screen_shake', 0)
                if screen_shake > 0:
                    render_offset[0] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2
                    render_offset[1] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2

            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), render_offset)
            pygame.display.update()

    def get_current_state(self):
        return self.states[-1] if self.states else None

    def push_state(self, new_state):
        if self.states: self.states[-1].exit_state()
        new_state.enter_state(); self.states.append(new_state)

    def pop_state(self):
        if self.states:
            self.states[-1].exit_state()
            self.states.pop()
        if self.states:
            self.states[-1].enter_state()
        else:
            self.write_save(self.save_data)
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    game = Game()
    game.push_state(MainMenuState(game))
    game.run()