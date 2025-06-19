# Cavyn Source/Cavyn.py
import os, sys, random, json
import pygame
from pygame.locals import *

# Import our new state classes and existing game object classes
from data.scripts.state import State
from data.scripts.game_states.main_menu_state import MainMenuState
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
        self.time_meter_max = 120
        self.COMBO_DURATION = 180

        # Load shared resources
        self.load_configs()
        self.load_assets()
        self.save_data = self.load_save()
        self.upgrade_keys = list(self.upgrades.keys())

    def load_configs(self):
        """Loads all game data from JSON files."""
        try:
            with open('data/configs/upgrades.json', 'r') as f:
                self.upgrades = json.load(f)
            with open('data/configs/perks.json', 'r') as f:
                self.perks = json.load(f)
            with open('data/configs/biomes.json', 'r') as f:
                self.biomes = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"FATAL ERROR: Could not load config files. Reason: {e}")
            pygame.quit()
            sys.exit()

    def load_assets(self):
        """Loads all assets that are shared across different states."""
        self.animation_manager = AnimationManager()
        self.white_font = Font('data/fonts/small_font.png', (251, 245, 239))
        self.black_font = Font('data/fonts/small_font.png', (0, 0, 1))
        self.backgrounds = {}
        self.sounds = {sound.split('/')[-1].split('.')[0]: pygame.mixer.Sound('data/sfx/' + sound) for sound in os.listdir('data/sfx')}
        # ... (all your self.sounds.set_volume() calls remain here)
        self.sounds['block_land'].set_volume(0.5); self.sounds['coin'].set_volume(0.6)
        self.sounds['chest_open'].set_volume(0.8); self.sounds['coin_end'] = pygame.mixer.Sound('data/sfx/coin.wav')
        self.sounds['coin_end'].set_volume(0.35);
        if 'upgrade' in self.sounds: self.sounds['upgrade'].set_volume(0.7)
        if 'explosion' in self.sounds: self.sounds['explosion'].set_volume(0.8)
        if 'combo_end' in self.sounds: self.sounds['combo_end'].set_volume(0.6)
        self.sounds['time_slow_start'] = pygame.mixer.Sound('data/sfx/warp.wav'); self.sounds['time_slow_start'].set_volume(0.4)
        self.sounds['time_slow_end'] = pygame.mixer.Sound('data/sfx/chest_open.wav'); self.sounds['time_slow_end'].set_volume(0.3)
        self.sounds['time_empty'] = pygame.mixer.Sound('data/sfx/death.wav'); self.sounds['time_empty'].set_volume(0.25)
        
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
        SAVE_FILE = 'save.json'
        try:
            with open(SAVE_FILE, 'r') as f:
                data = json.load(f)
                if 'high_score' not in data: data['high_score'] = 0
                if 'coin_magnet' not in data['upgrades']: data['upgrades']['coin_magnet'] = 0
                return data
        except (FileNotFoundError, json.JSONDecodeError):
            default_save = {"banked_coins": 100, "upgrades": {"jumps": 0, "speed": 0, "item_luck": 0, "coin_magnet": 0}, "high_score": 0}
            self.write_save(default_save)
            return default_save

    def write_save(self, data):
        SAVE_FILE = 'save.json'
        with open(SAVE_FILE, 'w') as f:
            json.dump(data, f, indent=4)

    def run(self):
        while True:
            events = pygame.event.get()
            self.get_current_state().handle_events(events)
            self.get_current_state().update()
            
            self.display.fill((0, 0, 1)) # Default background color
            self.get_current_state().render(self.display)

            render_offset = [0, 0]
            screen_shake = getattr(self.get_current_state(), 'screen_shake', 0)
            if screen_shake > 0:
                render_offset[0] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2
                render_offset[1] = random.randint(0, int(screen_shake)) - int(screen_shake) // 2

            self.screen.blit(pygame.transform.scale(self.display, self.screen.get_size()), render_offset)
            pygame.display.update()
            self.clock.tick(60)

    # === State Management Methods ===
    def get_current_state(self):
        return self.states[-1] if self.states else None

    def push_state(self, new_state):
        new_state.enter_state()
        self.states.append(new_state)

    def pop_state(self):
        if self.states:
            self.states[-1].exit_state()
            self.states.pop()
        
        # Call enter_state on the state that is now on top
        if self.states:
            self.states[-1].enter_state()
        else:
            # If we pop the last state, quit the game
            pygame.quit()
            sys.exit()

if __name__ == "__main__":
    game = Game()
    game.push_state(MainMenuState(game)) # <-- START ON THE MAIN MENU
    game.run()