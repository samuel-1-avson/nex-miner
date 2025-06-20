
import os
import sys
import random
import json
import pygame
from pygame.locals import *

# --- Core Pathing Setup ---
try:
    # This is more robust for running from different directories and for cx_Freeze/PyInstaller
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    # Fallback for environments where __file__ is not defined
    BASE_DIR = os.path.abspath('.')


# --- Imports ---
from data.scripts.state import State
from data.scripts.game_states.main_menu_state import MainMenuState
from data.scripts.anim_loader import AnimationManager
from data.scripts.text import Font
from data.scripts.core_funcs import load_img, write_f
from data.scripts.gemini_agent import GeminiAgent
from data.scripts.game_states.boot_up_state import BootUpState
from dotenv import load_dotenv # <--- ADD THIS LINE

load_dotenv() # <--- AND THIS LINE


class Game:
    """
    The main Game class.
    Handles window creation, the main game loop, asset loading,
    and state management.
    """
    def __init__(self):
        self.load_configs()
        self.save_data = self.load_save()

        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()

        # Display Setup
        self.DISPLAY_SIZE = (320, 180)
        # --- MODIFIED: Increased the default window scale for a bigger screen ---
        self.SCALE = 6
        self.TILE_SIZE = 16
        pygame.display.set_caption('Nex Miner')
        
        window_flags = RESIZABLE if self.save_data['settings'].get('resizable_window', False) else 0
        self.screen = pygame.display.set_mode((self.DISPLAY_SIZE[0] * self.SCALE, self.DISPLAY_SIZE[1] * self.SCALE), window_flags, 32)

        self.display = pygame.Surface(self.DISPLAY_SIZE)
        # --- NEW: Store the game's aspect ratio for scaling calculations ---
        self.aspect_ratio = self.DISPLAY_SIZE[0] / self.DISPLAY_SIZE[1]

        self.WINDOW_TILE_SIZE = (int(self.display.get_width() // self.TILE_SIZE), int(self.display.get_height() // self.TILE_SIZE))
        pygame.mouse.set_visible(False)
        self.clock = pygame.time.Clock()

        # AI Agent Initialization
        try:
            api_key = os.environ.get("GEMINI_API_KEY")
            self.ai_agent = GeminiAgent(api_key=api_key)
        except Exception as e:
            print(f"--- AI AGENT FAILED TO INITIALIZE ---")
            print(f"Error: {e}")
            print(f"Please ensure you have a valid Gemini API key set as an environment variable (GEMINI_API_KEY) or in the main game script.")
            self.ai_agent = None 
            
        # State Management
        self.states = []
        self.time_meter_max = 120
        self.COMBO_DURATION = 180
        
        # Original sound volumes
        self.original_volumes = {
            'block_land': 0.5, 'coin': 0.6, 'chest_open': 0.8, 'coin_end': 0.35,
            'upgrade': 0.7, 'explosion': 0.8, 'combo_end': 0.6,
            'time_slow_start': 0.4, 'time_slow_end': 0.3, 'time_empty': 0.25,
            'jump': 1.0, 'super_jump': 1.0, 'death': 1.0, 'collect_item': 1.0,
            'warp': 1.0, 'land': 0.4,
            'directive_complete': 1.0, 'artifact_equip': 0.7,
            'shoot': 0.5,
        }

        self.load_assets()
        # --- MODIFIED: Load dynamic character into memory ---
        self.load_dynamic_character()
        self.apply_settings()
        self.upgrade_keys = list(self.upgrades.keys())
        self.unlock_notifications = set()

    def update_window_mode(self):
        resizable = self.save_data['settings'].get('resizable_window', False)
        flags = RESIZABLE if resizable else 0
        default_size = (self.DISPLAY_SIZE[0] * self.SCALE, self.DISPLAY_SIZE[1] * self.SCALE)
        self.screen = pygame.display.set_mode(default_size, flags, 32)
        
    def notify_unlock(self, category):
        self.unlock_notifications.add(category)

    def clear_notification(self, category):
        if category in self.unlock_notifications:
            self.unlock_notifications.remove(category)

    def get_path(self, *args):
        return os.path.join(BASE_DIR, *args)

    # --- NEW: Method to load the generated character from save file ---
    def load_dynamic_character(self):
        if 'generated_character' in self.save_data and self.save_data.get('generated_character'):
            char_data = self.save_data['generated_character']
            char_id = char_data.get('id', 'generated_operative')
            self.characters[char_id] = char_data
            
    def load_configs(self):
        try:
            config_paths = {
                'upgrades': self.get_path('data', 'configs', 'upgrades.json'),
                'perks': self.get_path('data', 'configs', 'perks.json'),
                'biomes': self.get_path('data', 'configs', 'biomes.json'),
                'characters': self.get_path('data', 'configs', 'characters.json'),
                'curses': self.get_path('data', 'configs', 'curses.json'),
                'challenges': self.get_path('data', 'configs', 'challenges.json'),
                'artifacts': self.get_path('data', 'configs', 'artifacts.json'),
            }
            for name, path in config_paths.items():
                if not os.path.exists(path):
                    print(f"FATAL ERROR: Config file not found at {path}. Exiting.")
                    pygame.quit()
                    sys.exit()
            with open(config_paths['upgrades'], 'r') as f: self.upgrades = json.load(f)
            with open(config_paths['perks'], 'r') as f: self.perks = json.load(f)
            with open(config_paths['biomes'], 'r') as f: self.biomes = json.load(f)
            with open(config_paths['characters'], 'r') as f: self.characters = json.load(f)
            with open(config_paths['curses'], 'r') as f: self.curses = json.load(f)
            with open(config_paths['challenges'], 'r') as f: self.challenges = json.load(f)
            with open(config_paths['artifacts'], 'r') as f: self.artifacts = json.load(f)
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
            if sound_filename.endswith(('.wav', '.ogg')):
                sound_name = os.path.splitext(sound_filename)[0]
                self.sounds[sound_name] = pygame.mixer.Sound(os.path.join(sfx_dir, sound_filename))

        # --- FIX: Create fallback aliases for sounds to prevent crashes if files are missing. ---
        self.sounds.setdefault('upgrade', self.sounds.get('chest_open'))
        self.sounds.setdefault('super_jump', self.sounds.get('jump'))
        self.sounds.setdefault('collect_item', self.sounds.get('coin'))
        self.sounds.setdefault('coin_end', self.sounds.get('coin'))
        self.sounds.setdefault('time_slow_start', self.sounds.get('warp'))
        self.sounds.setdefault('time_slow_end', self.sounds.get('chest_open'))
        self.sounds.setdefault('time_empty', self.sounds.get('death'))
        self.sounds.setdefault('land', self.sounds.get('death'))
        self.sounds.setdefault('directive_complete', self.sounds.get('upgrade', self.sounds.get('chest_open')))
        self.sounds.setdefault('artifact_equip', self.sounds.get('coin'))
        self.sounds.setdefault('shoot', self.sounds.get('jump'))
        # --- ADDED THIS LINE to prevent the crash ---
        self.sounds.setdefault('combo_end', self.sounds.get('coin_end'))


        self.item_icons = {
            'cube': load_img(self.get_path('data', 'images', 'cube_icon.png')),
            'warp': load_img(self.get_path('data', 'images', 'warp_icon.png')),
            'jump': load_img(self.get_path('data', 'images', 'jump_icon.png')),
            'bomb': load_img(self.get_path('data', 'images', 'bomb_icon.png')),
            'freeze': load_img(self.get_path('data', 'images', 'freeze_icon.png')),
            'shield': load_img(self.get_path('data', 'images', 'shield_icon.png')),
            'hourglass': load_img(self.get_path('data', 'images', 'hourglass_icon.png')),
        }
        self.perk_icons = {}
        for perk_name in self.perks.keys():
            try:
                icon_path = self.get_path('data', 'images', 'perk_icons', f'{perk_name}.png')
                self.perk_icons[perk_name] = load_img(icon_path)
            except pygame.error: pass
        pygame.mixer.music.load(self.get_path('data', 'music.mp3'))
        pygame.mixer.music.play(-1)
        
    def apply_settings(self):
        sfx_vol = self.save_data['settings'].get('sfx_volume', 1.0)
        for name, sound in self.sounds.items():
            original_vol = self.original_volumes.get(name, 1.0)
            if sound: sound.set_volume(original_vol * sfx_vol)
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
                if 'settings' not in data: data['settings'] = {}
                data['settings'].setdefault("sfx_volume", 1.0)
                data['settings'].setdefault("music_volume", 1.0)
                data['settings'].setdefault("screen_shake", True)
                data['settings'].setdefault("resizable_window", False)
                if 'characters' not in data: data['characters'] = {}
                data['characters'].setdefault("unlocked", ["operator"])
                data['characters'].setdefault("selected", "operator")
                data.setdefault('upgrades', {})
                for key in self.upgrades: data['upgrades'].setdefault(key, 0)
                if 'compendium' not in data: data['compendium'] = {}
                data['compendium'].setdefault("perks", [])
                data['compendium'].setdefault("curses", [])
                data['compendium'].setdefault("items", [])
                if 'stats' not in data: data['stats'] = {}
                data['stats'].setdefault("play_time", 0)
                data['stats'].setdefault("total_coins", 0)
                data['stats'].setdefault("runs_started", 0)
                data['stats'].setdefault("daily_challenge_high_score", 0)
                data.setdefault('biomes_unlocked', ["Sector 01: The Core"])
                if 'artifacts' not in data: data['artifacts'] = {}
                data['artifacts'].setdefault("unlocked", [])
                data['artifacts'].setdefault("equipped", None)
                data.setdefault('active_directive', None)
                # --- NEW: Add generated_character field ---
                data.setdefault('generated_character', None)
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {
                "banked_coins": 100, 
                "upgrades": {key: 0 for key in self.upgrades}, 
                "high_score": 0,
                "settings": {"sfx_volume": 1.0, "music_volume": 1.0, "screen_shake": True, "resizable_window": False},
                "characters": {"unlocked": ["operator"], "selected": "operator"},
                "compendium": {"perks": [], "curses": [], "items": []},
                "stats": {"play_time": 0, "total_coins": 0, "runs_started": 0, "daily_challenge_high_score": 0},
                "biomes_unlocked": ["Sector 01: The Core"],
                "artifacts": {"unlocked": [], "equipped": None},
                "active_directive": None,
                "generated_character": None
            }
            self.write_save(default_save)
            return default_save

    def write_save(self, data):
        SAVE_FILE = self.get_path('save.json')
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=4) 

    def run(self):
        last_time = pygame.time.get_ticks()
        while True:
            current_time = pygame.time.get_ticks()
            dt = (current_time - last_time) / 1000.0
            last_time = current_time

            self.save_data['stats']['play_time'] += dt
            events = pygame.event.get()
            
            for event in events:
                if event.type == VIDEORESIZE:
                    if self.save_data['settings'].get('resizable_window', False):
                        self.screen = pygame.display.set_mode(event.size, RESIZABLE, 32)
            
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
            
            # --- MODIFIED: Replaced rendering logic for fixed aspect ratio ---
            self.screen.fill((0, 0, 0)) # Fill window with black for letter/pillarboxing

            # Calculate the scaled dimensions while maintaining the aspect ratio
            win_w, win_h = self.screen.get_size()
            
            new_w = win_w
            new_h = int(new_w / self.aspect_ratio)

            if new_h > win_h:
                new_h = win_h
                new_w = int(new_h * self.aspect_ratio)
            
            # Center the scaled surface in the window
            x_pos = (win_w - new_w) // 2
            y_pos = (win_h - new_h) // 2
            
            # Apply screen shake to the final blit position
            blit_pos = (x_pos + render_offset[0], y_pos + render_offset[1])

            # Scale the game surface and blit it
            scaled_surf = pygame.transform.scale(self.display, (new_w, new_h))
            self.screen.blit(scaled_surf, blit_pos)
            pygame.display.update()
            self.clock.tick(60)

    def get_current_state(self):
        return self.states[-1] if self.states else None

    def push_state(self, new_state):
        if self.states:
            self.states[-1].exit_state()
        new_state.enter_state()
        self.states.append(new_state)

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
            
    # --- NEW: Safe method for replacing the current state ---
    def replace_state(self, new_state):
        if self.states:
            self.states[-1].exit_state()
            self.states.pop()
        self.push_state(new_state)

    # --- NEW: Safely returns to the main menu, no matter how deep the stack ---
    def return_to_main_menu(self):
        # We need the MainMenuState class to check against
        from data.scripts.game_states.main_menu_state import MainMenuState
        while self.states and not isinstance(self.get_current_state(), MainMenuState):
            self.states[-1].exit_state()
            self.states.pop()
        # Ensure the main menu's enter_state is called if it wasn't the last pop
        if self.states and isinstance(self.get_current_state(), MainMenuState):
            self.get_current_state().enter_state()

    # --- NEW: Restarts the game by going to menu and pushing a new gameplay state ---
    def restart_gameplay(self):
        from data.scripts.gameplay_state import GameplayState
        self.return_to_main_menu()
        # >>> BUG FIX: Pass `self` instead of `self.game`
        self.push_state(GameplayState(self))


if __name__ == "__main__":
    game = Game()
    # --- MODIFIED: Start with the new boot up sequence ---
    game.push_state(BootUpState(game))
    game.run()